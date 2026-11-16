"""Standalone, bounded boot diagnostics. Never changes packet rules or probes the network."""
import argparse
import datetime
import hashlib
import fcntl
import selectors
import threading
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
import uuid

DEFAULTS = dict(data_dir='/var/log/zapret-diagnostics', proc_root='/proc', service_dir='/opt/zapret', runtime_dir='/run/zapret',
                duration_seconds=1800, sample_interval=5, max_boot_bytes=20*1024*1024,
                max_boots=5, max_total_bytes=100*1024*1024, commands={})
COMMANDS = {
    'iptables': ['iptables-save', '-c'], 'ip6tables': ['ip6tables-save', '-c'],
    'nft': ['nft', 'list', 'ruleset'],
    'service': ['systemctl', 'show', 'zapret.service', 'zapret-diagnostics.service'],
    'failed': ['systemctl', '--failed', '--no-pager'], 'sockets': ['ss', '-s'],
    'boot_time': ['systemd-analyze', 'time'],
    'journal_current': ['journalctl', '-b', '0', '-n', '8000', '--no-pager', '--reverse', '-o', 'short-monotonic'],
    'journal_previous': ['journalctl', '-b', '-1', '-n', '8000', '--no-pager', '--reverse', '-o', 'short-monotonic'],
    'journal_zapret_current': ['journalctl', '-u', 'zapret.service', '-b', '0', '-n', '8000', '--no-pager', '--reverse', '-o', 'short-monotonic'],
    'journal_zapret_previous': ['journalctl', '-u', 'zapret.service', '-b', '-1', '-n', '8000', '--no-pager', '--reverse', '-o', 'short-monotonic'],
    'journal_boots': ['journalctl', '--list-boots', '--no-pager'],
}


def load_config(path):
    config = dict(DEFAULTS)
    config.update(json.loads(Path(path).read_text()))
    return config


def read(path, limit=32768):
    try:
        with open(path, 'rb') as stream:
            return stream.read(limit).decode('utf-8', 'replace')
    except OSError as exc:
        return 'unavailable: ' + str(exc)


def stamp():
    return dict(timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                monotonic=time.monotonic())


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def boot_dir(config):
    raw = read(Path(config['proc_root']) / 'sys/kernel/random/boot_id', 80).strip()
    boot = raw if re.fullmatch(r'[a-fA-F0-9-]{1,64}', raw) else 'unknown-boot'
    root = Path(config['data_dir'])
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    directory = root / boot
    directory.mkdir(mode=0o700, exist_ok=True)
    fsync_directory(root.parent)
    fsync_directory(root)
    return directory


def size(directory):
    return sum(p.stat().st_size for p in directory.rglob('*') if p.is_file() and not p.is_symlink())


def write_record(config, filename, record):
    directory = boot_dir(config)
    payload = (json.dumps(dict(stamp(), **record), ensure_ascii=False) + '\n').encode()
    with open(directory/'write.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if size(directory) + len(payload) > config['max_boot_bytes']:
            return False
        fd = os.open(directory / filename, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'ab') as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        fsync_directory(directory)
    return True


def snapshot_config(config, include_lists=True):
    root = Path(config['manager_dir'])
    names = ['config.txt', 'utils/gamefilter.mode', 'utils/gamefilter.enable',
             'utils/gamefilter.ports.json', 'utils/name_strategy.txt',
             'utils/gamefilter.main_bypass.disable', 'utils/gamefilter.discord.disable', 'version.txt']
    names += [str(p.relative_to(root)) for p in (root / 'utils').glob('*.flag')][:32]
    for pattern in ('game_preset_*', 'custom_*.state.json'):
        names += [str(p.relative_to(root)) for p in (root/'utils').glob(pattern)][:32]
    files = {name: read(root / name, 16384) for name in names}
    lists = {}
    for folder in (('files/lists', 'lists', 'ipset') if include_lists else ()):
        for path in list((root / folder).glob('*'))[:128]:
            try:
                if path.is_file() and not path.is_symlink():
                    digest = hashlib.sha256()
                    lines = count = 0
                    with path.open('rb') as stream:
                        for _ in range(16):
                            chunk = stream.read(65536)
                            if not chunk:
                                break
                            digest.update(chunk)
                            lines += chunk.count(b'\n')
                            count += len(chunk)
                    lists[str(path.relative_to(root))] = dict(bytes=path.stat().st_size,
                        hashed_bytes=count, sha256=digest.hexdigest(), lines_in_hashed_bytes=lines)
            except OSError as exc:
                lists[str(path.relative_to(root))] = dict(error=str(exc))
    return dict(files=files, list_metadata=lists,
                fwtype=read(Path(config.get('service_dir','/opt/zapret'))/'FWTYPE',4096),
                firewall_backend=read(Path(config.get('runtime_dir','/run/zapret'))/'firewall-backend',4096),
                clock_ticks=os.sysconf('SC_CLK_TCK'), page_size=os.sysconf('SC_PAGE_SIZE'), cpu_count=os.cpu_count(),
                kernel=read(Path(config['proc_root'])/'version',4096),
                system=read('/etc/os-release',4096), machine=list(os.uname()),
                service_result={k: os.environ.get(k) for k in ('SERVICE_RESULT','EXIT_CODE','EXIT_STATUS')})


def event(config, name):
    return write_record(config, 'events.jsonl', dict(event=name, **snapshot_config(config, include_lists=False)))


def sample(config):
    proc = Path(config['proc_root'])
    names = ['uptime','loadavg','meminfo','stat','softirqs','net/softnet_stat',
             'pressure/cpu','pressure/memory','pressure/io',
             'sys/net/netfilter/nf_conntrack_count','sys/net/netfilter/nf_conntrack_max',
             'sys/net/netfilter/nf_conntrack_acct','net/netfilter/nfnetlink_queue']
    result = {name: read(proc/name, 16384) for name in names}
    processes = []
    for path in proc.iterdir():
        if not path.name.isdigit():
            continue
        comm = read(path/'comm', 256).strip()
        if not any(term in comm.lower() for term in ('nfqws','steam','gamescope')):
            continue
        processes.append(dict(pid=int(path.name), comm=comm, stat=read(path/'stat',4096),
                              status=read(path/'status',8192)))
        if len(processes) == 64:
            break
    return dict(proc=result, processes=processes)


def command(config, name, limit=512*1024):
    argv = config.get('commands', {}).get(name, COMMANDS[name])
    if not argv:
        return dict(disabled=True)
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        output = bytearray()
        deadline = time.monotonic() + config.get('command_timeout', 8)
        code = None
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    code = 'timeout'
                    break
                if not selector.select(min(remaining, 0.1)):
                    continue
                chunk = os.read(process.stdout.fileno(), min(65536, limit + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > limit:
                    code = 'output-limit'
                    break
        if code is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            returncode = process.wait(timeout=max(0.01, deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            returncode = process.wait()
            code = 'timeout'
        process.stdout.close()
        return dict(argv=argv, returncode=code if code is not None else returncode,
                    output=bytes(output[:limit]).decode('utf-8','replace'), truncated=len(output)>limit)
    except OSError as exc:
        return dict(argv=argv,error=str(exc))


def rich_snapshot(config, reason):
    write_record(config, 'snapshots.jsonl', dict(reason=reason, config=snapshot_config(config)))
    for name in ('iptables','ip6tables','nft','service','failed','sockets','boot_time'):
        write_record(config,'snapshots.jsonl',dict(reason=reason,command=name,result=command(config,name)))


def retention(config):
    current = boot_dir(config)
    dirs = sorted((p for p in current.parent.iterdir() if p.is_dir() and not p.is_symlink()),
                  key=lambda p:p.stat().st_mtime, reverse=True)
    total = size(current)
    kept = 1
    for path in dirs:
        if path == current:
            continue
        amount = size(path)
        if kept >= config['max_boots'] or total + amount > config['max_total_bytes']:
            shutil.rmtree(path)
        else:
            kept += 1
            total += amount


def monitor(config):
    import fcntl
    directory = boot_dir(config)
    with open(directory/'monitor.lock','a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        retention(config)
        write_record(config,'lifecycle.jsonl',dict(event='monitor_started',pid=os.getpid()))
        # Rich captures run independently so sampling continues during command timeouts.
        import threading
        worker = threading.Thread(target=rich_snapshot,args=(config,'monitor_started'),daemon=True)
        worker.start()
        deadline = time.monotonic() + config['duration_seconds']
        previous = None
        while time.monotonic() < deadline:
            write_record(config,'samples.jsonl',sample(config))
            retention(config)
            events = directory/'events.jsonl'
            marker = events.stat().st_mtime_ns if events.exists() else None
            if marker != previous and not worker.is_alive():
                previous = marker
                worker = threading.Thread(target=rich_snapshot,args=(config,'service_event'),daemon=True)
                worker.start()
            if size(directory) >= config['max_boot_bytes'] - 65536:
                break
            retention(config)
            time.sleep(max(0.05, min(config['sample_interval'], deadline-time.monotonic())))
        write_record(config,'lifecycle.jsonl',dict(event='monitor_finished'))


def status(config):
    directory = boot_dir(config)
    return dict(boot=directory.name, directory=str(directory), bytes=size(directory),
                files=[p.name for p in directory.iterdir()], limits={k:config[k] for k in
                ('duration_seconds','sample_interval','max_boot_bytes','max_boots','max_total_bytes')})


def collect(config, output):
    output = Path(output).absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        (temp/'status.json').write_text(json.dumps(status(config),indent=2))
        for name in ('journal_current','journal_previous','journal_zapret_current','journal_zapret_previous','journal_boots','service','failed'):
            (temp/(name+'.json')).write_text(json.dumps(command(config,name,2*1024*1024)))
        (temp/'app_errorlog.txt').write_text(read('/tmp/zapterdpimanager.log',256*1024))
        fd = os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        with os.fdopen(fd,'wb') as stream, tarfile.open(fileobj=stream,mode='w:gz') as archive:
            archive.add(temp,arcname='collection')
            root=Path(config['data_dir'])
            for path in root.rglob('*'):
                if path.is_file() and not path.is_symlink() and path.resolve() != output.resolve():
                    archive.add(path,arcname='boots/'+str(path.relative_to(root)),recursive=False)
    return str(output)


def prepare(manager_dir, output_dir):
    output=Path(output_dir)
    output.mkdir(parents=True,exist_ok=True)
    config=dict(DEFAULTS,manager_dir=str(Path(manager_dir).absolute()))
    shutil.copyfile(__file__,output/'collector.py')
    (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    (output/'zapret-diagnostics.service').write_text('''[Unit]
Description=Persistent Zapret boot diagnostics
After=local-fs.target
Before=zapret.service
[Service]
Type=simple
ExecStart=/usr/bin/python3 -I /var/lib/zapret-diagnostics/collector.py monitor --config /var/lib/zapret-diagnostics/config.json
Nice=10
CPUQuota=5%
MemoryMax=96M
UMask=0077
NoNewPrivileges=yes
[Install]
WantedBy=multi-user.target
''')
    prefix='/usr/bin/timeout 2s /usr/bin/python3 -I /var/lib/zapret-diagnostics/collector.py event --config /var/lib/zapret-diagnostics/config.json --name '
    (output/'zapret-diagnostics-dropin.conf').write_text('[Service]\nStandardOutput=journal\nStandardError=journal\n'+''.join(k+'=-'+prefix+v+'\n' for k,v in [('ExecStartPre','startup'),('ExecStartPost','started'),('ExecStopPost','stopped')]))
    (output/'zapret-diagnostics-journald.conf').write_text('[Journal]\nStorage=persistent\nSystemKeepFree=256M\nSyncIntervalSec=5s\n')
    return str(output)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    subs=parser.add_subparsers(dest='action',required=True)
    prep=subs.add_parser('prepare'); prep.add_argument('--manager-dir',required=True); prep.add_argument('--output-dir',required=True)
    for action in ('monitor','event','collect','status'):
        sub=subs.add_parser(action); sub.add_argument('--config',required=True)
        if action=='event': sub.add_argument('--name',required=True,choices=['startup','started','stopped','prepared'])
        if action=='collect': sub.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    if args.action=='prepare': result=prepare(args.manager_dir,args.output_dir)
    else:
        config=load_config(args.config)
        result={'monitor':lambda:monitor(config),'event':lambda:event(config,args.name),
                'collect':lambda:collect(config,args.output),'status':lambda:status(config)}[args.action]()
    if result is not None: print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':
    main()
