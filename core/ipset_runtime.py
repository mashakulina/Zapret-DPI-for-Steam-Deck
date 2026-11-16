"""Persistent IP lists shared by the service and the settings windows.

The nfqws IP-set loader notices file changes itself. Keep its merged lists at
stable, user-owned paths instead of deleting them with the startup temp files.
This module also runs directly with ``python3 -I`` in an installed-only tree.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import os
from pathlib import Path
import pwd
import stat
import tempfile
import time


MERGED_LISTS = {
    'ipset-all_merged.txt': ('ipset-all.txt', 'ipset-all_user.txt'),
    'ipset-exclude_merged.txt': ('ipset-exclude.txt', 'ipset-exclude_user.txt'),
}
RUNTIME_BASE = Path('/run/zapret-ipset')


def _manager_root(manager_dir=None):
    return Path(manager_dir) if manager_dir is not None else Path.home() / 'Zapret_DPI_Manager'


def runtime_directory(manager_dir=None):
    root = _manager_root(manager_dir).resolve()
    uid = root.stat().st_uid
    key = f'{uid}-' + hashlib.sha256(os.fsencode(root)).hexdigest()[:16]
    provisioned = RUNTIME_BASE / key
    # nfqws drops DAC capabilities even with --uid=0:0, so its lists must
    # remain readable outside a user's 0700 home. /run survives temp cleanup.
    if provisioned.is_dir() and not provisioned.is_symlink():
        return provisioned
    # A settings save before the first privileged service start still works.
    # The service provisions /run and rebuilds from the saved source on start.
    return Path('/tmp') / ('zapret-ipset-' + key)


def _prepare_runtime_directory(root, account):
    """The service provisions /run before dropping to the installation owner."""
    if RUNTIME_BASE.is_symlink():
        raise ValueError('Символическая ссылка каталога IPSet не поддерживается')
    RUNTIME_BASE.mkdir(mode=0o755, exist_ok=True)
    parent = RUNTIME_BASE.stat()
    if parent.st_uid != os.geteuid() or parent.st_mode & 0o022:
        raise PermissionError('Каталог IPSet принадлежит другому пользователю')
    # A service with umask 077 must still leave /run traversable to its owner
    # after the helper drops privileges and to nfqws after capability removal.
    os.chmod(RUNTIME_BASE, 0o755)
    key = f'{root.stat().st_uid}-' + hashlib.sha256(os.fsencode(root.resolve())).hexdigest()[:16]
    directory = RUNTIME_BASE / key
    if directory.is_symlink():
        raise ValueError('Символическая ссылка каталога IPSet не поддерживается')
    directory.mkdir(mode=0o755, exist_ok=True)
    if directory.stat().st_uid not in (os.geteuid(), account.pw_uid):
        raise ValueError('Неверный владелец рабочего каталога IPSet')
    os.chown(directory, account.pw_uid, account.pw_gid)
    os.chmod(directory, 0o755)


def _read(path):
    if path.is_symlink():
        raise ValueError(f'Символическая ссылка не поддерживается: {path}')
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None


@contextlib.contextmanager
def _locked(root):
    directory = runtime_directory(root)
    if directory.is_symlink():
        raise ValueError(f'Символическая ссылка не поддерживается: {directory}')
    directory.mkdir(parents=True, exist_ok=True, mode=0o755)
    metadata = directory.stat()
    if metadata.st_uid != os.geteuid() or not stat.S_ISDIR(metadata.st_mode):
        raise ValueError(f'Неверный владелец рабочего каталога IPSet: {directory}')
    os.chmod(directory, 0o755)
    descriptor = os.open(directory / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError('Некорректный файл блокировки IPSet')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _replace(path, data):
    previous = _read(path)
    if previous == data:
        if data is not None and path.name in MERGED_LISTS:
            os.chmod(path, 0o644)
        return
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    before = path.stat() if previous is not None else None
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        mode = 0o644 if path.name in MERGED_LISTS else (stat.S_IMODE(before.st_mode) if before else 0o600)
        os.chmod(temporary, mode)
        # Older nfqws builds compare mtime in whole seconds. Even rapid changes
        # of the same size must produce a different signature for auto reload.
        changed = max(time.time_ns(), before.st_mtime_ns + 1_000_000_000 if before else 0)
        os.utime(temporary, ns=(changed, changed))
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def _merged(root, names):
    # Match the Bash merge: retain order, remove CRLF and duplicate lines.
    seen = set()
    lines = []
    for name in names:
        data = _read(root / 'files' / 'lists' / name)
        if data is None:
            continue
        for line in data.splitlines():
            if line not in seen:
                seen.add(line)
                lines.append(line)
    return b'\n'.join(lines) + (b'\n' if lines else b'')


def _save(root, sources):
    with _locked(root):
        directory = runtime_directory(root)
        paths = [*sources, *(directory / name for name in MERGED_LISTS)]
        originals = {path: _read(path) for path in paths}
        changed = []
        try:
            for path, data in sources.items():
                _replace(path, data)
                changed.append(path)
            # Replace whole files, never truncate a list that nfqws may read.
            outputs = {directory / name: _merged(root, names)
                       for name, names in MERGED_LISTS.items()}
            for path, data in outputs.items():
                _replace(path, data)
                changed.append(path)
        except (OSError, ValueError) as error:
            failures = []
            for path in reversed(changed):
                try:
                    _replace(path, originals[path])
                except (OSError, ValueError) as rollback_error:
                    failures.append(str(rollback_error))
            if failures:
                raise OSError(f'{error}. Не удалось восстановить IP-списки: ' + '; '.join(failures)) from error
            raise
        return directory


def refresh_runtime_ipsets(manager_dir=None):
    return _save(_manager_root(manager_dir), {})


def save_filter_mode(mode, manager_dir=None):
    root = _manager_root(manager_dir)
    if mode == 'none':
        data = b'203.0.113.113/32'
    elif mode == 'any':
        data = b''
    elif mode == 'loaded':
        data = _read(root / 'utils' / 'ipset-all.txt')
        if data is None:
            raise FileNotFoundError('Не найден готовый список utils/ipset-all.txt')
    else:
        raise ValueError('Неизвестный режим IPSet Filter')
    return _save(root, {root / 'files' / 'lists' / 'ipset-all.txt': data})


def save_user_ipsets(blocked, unblocked, manager_dir=None):
    root = _manager_root(manager_dir)
    lists = root / 'files' / 'lists'
    return _save(root, {lists / 'ipset-all_user.txt': blocked.encode('utf-8'),
                        lists / 'ipset-exclude_user.txt': unblocked.encode('utf-8')})


def runtime_apply_status(manager_dir=None, proc_root='/proc', starter_path='/opt/zapret/starter.sh'):
    expected = {str(runtime_directory(manager_dir) / name) for name in MERGED_LISTS}
    ready = legacy = unused = unreadable = False
    try:
        processes = list(Path(proc_root).iterdir())
    except OSError:
        return 'unknown'
    for process in processes:
        if not process.name.isdecimal():
            continue
        try:
            if (process / 'comm').read_text().strip() != 'nfqws':
                continue
            args = (process / 'cmdline').read_bytes().split(b'\0')
        except FileNotFoundError:
            continue  # Process exited while its status was being read.
        except OSError:
            unreadable = True
            continue
        paths = {os.fsdecode(arg.split(b'=', 1)[1]) for arg in args
                 if arg.startswith((b'--ipset=', b'--ipset-exclude='))}
        managed = {path for path in paths if Path(path).name in MERGED_LISTS}
        if managed - expected:
            legacy = True
        elif paths & expected:
            ready = True
        else:
            unused = True
    if legacy:
        try:
            installed = 'core/ipset_runtime.py' in Path(starter_path).read_text()
        except OSError:
            installed = False
        return 'legacy' if installed else 'upgrade'
    if ready:
        return 'ready'
    if unreadable:
        return 'unknown'
    if unused:
        return 'unused'
    try:
        installed = 'core/ipset_runtime.py' in Path(starter_path).read_text()
    except OSError:
        installed = False
    return 'stopped' if installed else 'upgrade'


def runtime_update_message(manager_dir=None):
    return {
        'ready': 'Применено без перезапуска Zapret. При необходимости переподключитесь к игре или сайту.',
        'stopped': 'Сохранено для следующего запуска Zapret.',
        'legacy': 'Сохранено. Для ранее запущенной службы нужен один перезапуск Zapret; далее IPSet применяется без перезапуска.',
        'upgrade': 'Сохранено. Для применения без перезапуска обновите службу Zapret и запустите её заново.',
        'unknown': 'Сохранено. Не удалось проверить, использует ли работающая служба новые IP-списки.',
        'unused': 'Сохранено. Текущая стратегия не использует эти рабочие IP-списки.',
    }[runtime_apply_status(manager_dir)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manager_dir', type=Path)
    parser.add_argument('--user')
    args = parser.parse_args()
    if os.geteuid() == 0:
        account = pwd.getpwnam(args.user) if args.user else pwd.getpwuid(args.manager_dir.stat().st_uid)
        try:
            _prepare_runtime_directory(args.manager_dir, account)
        except PermissionError:
            # Unprivileged user namespaces cannot provision the host /run.
            # Their isolated startup tests use the readable /tmp fallback.
            pass
        if account.pw_uid != 0:
            # The root service prepares user-owned lists; subsequent UI saves
            # must neither request sudo nor write through a privileged helper.
            os.setgroups([])
            os.setgid(account.pw_gid)
            os.setuid(account.pw_uid)
    print(refresh_runtime_ipsets(args.manager_dir))


if __name__ == '__main__':
    main()
