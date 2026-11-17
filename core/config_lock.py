"""Reentrant, fail-fast interprocess lock shared by desktop and Decky writes."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import threading


class SettingsBusyError(ValueError):
    pass


_guard = threading.Lock()
_locks = {}
_local = threading.local()


@contextmanager
def manager_settings_lock(manager_dir):
    root = str(Path(manager_dir).resolve())
    with _guard:
        lock = _locks.setdefault(root, threading.RLock())
    if not lock.acquire(blocking=False):
        raise SettingsBusyError('Настройки уже изменяются. Дождитесь завершения операции и повторите попытку.')
    active = getattr(_local, 'active', None)
    if active is None:
        active = _local.active = set()
    descriptor = None
    try:
        if root not in active:
            directory = Path(root) / 'utils'
            directory.mkdir(parents=True, exist_ok=True)
            path = directory / '.settings.lock'
            flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
            try:
                descriptor = os.open(path, flags | os.O_CREAT | os.O_EXCL, 0o644)
                # Decky may create the lock as root with a restrictive umask.
                # Locking a read-only fd lets the desktop user use it as well.
                os.fchmod(descriptor, 0o644)
            except FileExistsError:
                descriptor = os.open(path, flags)
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise SettingsBusyError(
                    'Настройки уже изменяются в другом окне или Decky. Повторите попытку после завершения операции.'
                ) from error
            active.add(root)
        yield
    finally:
        if descriptor is not None:
            active.discard(root)
            os.close(descriptor)
        lock.release()
