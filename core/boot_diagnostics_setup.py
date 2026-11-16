"""Install or disable a prepared boot recorder; never restart Zapret or change its config."""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


FILES = {
    'collector.py': 'var/lib/zapret-diagnostics/collector.py',
    'config.json': 'var/lib/zapret-diagnostics/config.json',
    'zapret-diagnostics.service': 'etc/systemd/system/zapret-diagnostics.service',
    'zapret-diagnostics-dropin.conf': 'etc/systemd/system/zapret.service.d/80-boot-diagnostics.conf',
    'zapret-diagnostics-journald.conf': 'etc/systemd/journald.conf.d/80-zapret-diagnostics.conf',
}
SERVICE = 'zapret-diagnostics.service'
STATE = 'var/lib/zapret-diagnostics/installation.json'


def run_command(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=45)


def atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.new')
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def check_payload(bundle):
    for name in FILES:
        path = bundle / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
            raise ValueError(f'Invalid prepared file: {path}')
    compile((bundle / 'collector.py').read_text(), 'collector.py', 'exec')
    config = json.loads((bundle / 'config.json').read_text())
    manager = Path(config['manager_dir'])
    if not manager.is_absolute() or not (manager / 'config.txt').is_file():
        raise ValueError('manager_dir must identify an installed manager with config.txt')
    if config.get('data_dir') != '/var/log/zapret-diagnostics' or config.get('proc_root') != '/proc':
        raise ValueError('Deployment requires the production log/proc paths')
    return config


def restore_files(root, state, include_collector=True):
    for name, relative in FILES.items():
        if not include_collector and name in ('collector.py', 'config.json'):
            continue
        target = root / relative
        previous = state['previous'][relative]
        if previous['exists']:
            source = root / state['backup'] / relative
            atomic_write(target, source.read_bytes(), previous['mode'])
        else:
            target.unlink(missing_ok=True)


def install_bundle(bundle, root=Path('/'), run=run_command):
    bundle, root = Path(bundle), Path(root)
    chtime = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    config = check_payload(bundle)
    state_path = root / STATE
    if state_path.exists() and json.loads(state_path.read_text()).get('active'):
        raise RuntimeError('Diagnostics is already installed; disable it before replacing the recorder')
    state = {'active': False, 'created': chtime, 'manager_dir': config['manager_dir'],
             'backup': 'var/lib/zapret-diagnostics/backup-' + chtime, 'previous': {}}
    for relative in FILES.values():
        target = root / relative
        if target.is_symlink():
            raise ValueError(f'Refusing to replace a symlink: {target}')
        previous = {'exists': target.exists()}
        if target.exists():
            previous['mode'] = target.stat().st_mode & 0o777
            backup = root / state['backup'] / relative
            atomic_write(backup, target.read_bytes())
        state['previous'][relative] = previous
    logdir = root / 'var/log/zapret-diagnostics'
    logdir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(logdir, 0o700)
    private = root / 'var/lib/zapret-diagnostics'
    private.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    atomic_write(logdir / 'storage-check', b'Persistent storage write and fsync succeeded.\n')
    enabled = False
    try:
        for name, relative in FILES.items():
            atomic_write(root / relative, (bundle / name).read_bytes(),
                         0o600 if name in ('collector.py', 'config.json') else 0o644)
        run(['systemctl', 'daemon-reload'])
        run(['systemctl', 'restart', 'systemd-journald.service'])
        run(['journalctl', '--flush'])
        run(['journalctl', '--sync'])
        enabled = True  # enable may have created its symlink even when starting fails.
        run(['systemctl', 'enable', '--now', SERVICE])
        run(['systemctl', 'is-active', '--quiet', SERVICE])
        run([sys.executable, '-I', str(root / FILES['collector.py']), 'event',
             '--config', str(root / FILES['config.json']), '--name', 'prepared'])
        state['active'] = True
        state['installed_sha256'] = {relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
                                     for relative in FILES.values()}
        atomic_write(state_path, (json.dumps(state, indent=2) + '\n').encode())
        return state
    except Exception as error:
        rollback = []
        if enabled:
            try:
                run(['systemctl', 'disable', '--now', SERVICE])
            except Exception as exc:
                rollback.append(str(exc))
        try:
            restore_files(root, state)
            run(['systemctl', 'daemon-reload'])
            run(['systemctl', 'restart', 'systemd-journald.service'])
        except Exception as exc:
            rollback.append(str(exc))
        raise RuntimeError(f'Installation failed: {error}; rollback errors: {rollback}') from error


def disable(root=Path('/'), run=run_command):
    root = Path(root)
    state_path = root / STATE
    state = json.loads(state_path.read_text())
    if not state.get('active'):
        return state
    # A subsequent manual edit must never be silently discarded.
    for relative in list(FILES.values())[2:]:
        target = root / relative
        if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest() != state['installed_sha256'][relative]:
            raise RuntimeError(f'Diagnostic configuration changed externally: {target}')
    run(['systemctl', 'disable', '--now', SERVICE])
    restore_files(root, state, include_collector=False)
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'restart', 'systemd-journald.service'])
    run(['journalctl', '--flush'])
    state['active'] = False
    atomic_write(state_path, (json.dumps(state, indent=2) + '\n').encode())
    return state


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest='action', required=True)
    install = subparsers.add_parser('install')
    install.add_argument('--bundle', type=Path, required=True)
    subparsers.add_parser('disable')
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        parser.error('Administrative authentication is required')
    try:
        result = install_bundle(args.bundle) if args.action == 'install' else disable()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
