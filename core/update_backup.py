"""Back up an installed manager and service before replacing either component."""
from __future__ import annotations

import os
from pathlib import Path
import shutil
import tempfile

from core.platform_info import ZAPRET_SYSTEMD_UNIT_PATH, ZAPRET_SYSTEMD_UNIT_PATH_LEGACY


class UpdateBackup:
    def __init__(self, updater, password, directory, manager_dir=None):
        self.updater = updater
        self.password = password
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.manager_dir = Path(manager_dir) if manager_dir is not None else None
        self.manager_existed = self.manager_dir is not None and self.manager_dir.exists()
        self.paths = [('/opt/zapret', 'service'),
                      (ZAPRET_SYSTEMD_UNIT_PATH, 'unit'),
                      (ZAPRET_SYSTEMD_UNIT_PATH_LEGACY, 'legacy-unit')]
        self.present = {}
        self.active = False
        self.enabled = False
        self.enabled_state = 'disabled'

    def command(self, argv):
        result = self.updater.run_with_sudo(argv, self.password, 'Резервная копия обновления...')
        if not result:
            raise RuntimeError('Нет ответа при резервном копировании/восстановлении')
        return result

    def checked(self, argv):
        result = self.command(argv)
        if result['returncode']:
            raise RuntimeError(result.get('stderr') or 'Ошибка: ' + ' '.join(argv))
        return result

    def capture(self):
        # All snapshots finish before the first stop/remove/copy operation.
        for action, attribute, absent in (
            ('is-active', 'active', ('inactive', 'failed', 'unknown')),
            ('is-enabled', 'enabled', ('disabled', 'static', 'indirect', 'not-found', 'masked')),
        ):
            result = self.command(['systemctl', action, 'zapret.service'])
            value = result.get('stdout', '').strip()
            if attribute == 'enabled':
                self.enabled_state = value
            if result['returncode'] == 0:
                setattr(self, attribute, value in ('active', 'enabled', 'enabled-runtime'))
            elif value not in absent:
                # systemctl may print no state when the unit does not exist.
                state = self.checked(['systemctl', 'show', 'zapret.service', '--property=LoadState', '--value'])
                if state['stdout'].strip() != 'not-found':
                    raise RuntimeError('Не удалось сохранить состояние службы zapret')
        for source, name in self.paths:
            result = self.command([
                'bash', '-c',
                'if [ -e "$1" ] || [ -L "$1" ]; then cp -a -- "$1" "$2"; else exit 3; fi',
                'zapret-backup', source, str(self.directory / name),
            ])
            if result['returncode'] not in (0, 3):
                raise RuntimeError('Не удалось сохранить ' + source + ': ' + result.get('stderr', ''))
            self.present[name] = result['returncode'] == 0
        if self.manager_existed:
            shutil.copytree(self.manager_dir, self.directory / 'manager', symlinks=True)

    def restore_manager(self):
        if self.manager_dir is None:
            return
        if not self.manager_existed:
            if self.manager_dir.exists():
                shutil.rmtree(self.manager_dir)
            return
        # Prepare a complete replacement before moving the failed installation away.
        parent = self.manager_dir.parent
        staged = Path(tempfile.mkdtemp(prefix='.zapret-restore-', dir=parent))
        failed = staged.with_name(staged.name + '-failed')
        moved = False
        try:
            shutil.copytree(self.directory / 'manager', staged, dirs_exist_ok=True, symlinks=True)
            if self.manager_dir.exists():
                os.replace(self.manager_dir, failed)
                moved = True
            try:
                os.replace(staged, self.manager_dir)
            except OSError:
                if moved:
                    os.replace(failed, self.manager_dir)
                    moved = False
                raise
        finally:
            shutil.rmtree(staged, ignore_errors=True)
            if moved:
                shutil.rmtree(failed, ignore_errors=True)

    def restore(self):
        stopped = self.command(['systemctl', 'stop', 'zapret.service'])
        if stopped['returncode']:
            state = self.checked(['systemctl', 'show', 'zapret.service', '--property=LoadState', '--value'])
            if state['stdout'].strip() != 'not-found':
                raise RuntimeError('Не удалось остановить службу для восстановления')
        # A failed first installation may already have enabled its new unit.
        # Remove those links while the unit is still available, including when
        # no old unit exists to enable/disable after restoring the snapshot.
        disabled = self.command(['systemctl', 'disable', 'zapret.service'])
        if disabled['returncode']:
            # A copy failure may precede creation of the replacement unit;
            # refresh systemd's cached LoadState before accepting its absence.
            self.checked(['systemctl', 'daemon-reload'])
            state = self.checked(['systemctl', 'show', 'zapret.service', '--property=LoadState', '--value'])
            if state['stdout'].strip() != 'not-found':
                raise RuntimeError('Не удалось отключить новую службу для восстановления')
        self.restore_manager()
        for destination, name in self.paths:
            self.checked(['rm', '-rf', destination])
            if self.present[name]:
                self.checked(['mkdir', '-p', str(Path(destination).parent)])
                self.checked(['cp', '-a', str(self.directory / name), destination])
        self.checked(['systemctl', 'daemon-reload'])
        if self.present['unit'] or self.present['legacy-unit']:
            mode = ['--runtime'] if self.enabled_state == 'enabled-runtime' else []
            self.checked(['systemctl', *mode, 'enable' if self.enabled else 'disable', 'zapret.service'])
            if self.active:
                self.checked(['systemctl', 'start', 'zapret.service'])
                state = self.checked(['systemctl', 'is-active', 'zapret.service'])
                if state['stdout'].strip() != 'active':
                    raise RuntimeError('Восстановленная служба zapret не активна')

    def cleanup(self):
        # cp -a retains root ownership; ordinary shutil.rmtree cannot remove it.
        self.checked(['rm', '-rf', str(self.directory)])
