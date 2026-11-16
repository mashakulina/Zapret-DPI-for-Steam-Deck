"""Transactional firewall selection; also a standalone, stdlib-only sudo helper."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

DEFAULT_BACKEND = 'nftables'
BACKENDS = ('nftables', 'iptables')
CONFIG_PATH = Path('/opt/zapret/FWTYPE')
STATE_DIR = Path('/run/zapret')


class FirewallSettingsError(RuntimeError):
    pass


def _run(argv, **kwargs):
    return subprocess.run(argv, capture_output=True, text=True, timeout=kwargs.pop('timeout', 45), **kwargs)


def available_backends():
    return {name: all(shutil.which(tool) for tool in tools)
            for name, tools in {'nftables': ('nft',), 'iptables': ('iptables', 'ip6tables')}.items()}


class FirewallSettingsEngine:
    """Inject paths and command runner only in-process, never through the root CLI."""

    def __init__(self, config_path=CONFIG_PATH, state_dir=STATE_DIR, runner=_run,
                 which=shutil.which):
        self.config_path = Path(config_path)
        self.choice_path = self.config_path.with_name(self.config_path.name + '.user')
        self.state_dir = Path(state_dir)
        self.runner = runner
        self.which = which

    def _command(self, *argv):
        try:
            return self.runner(list(argv))
        except (OSError, subprocess.SubprocessError) as exc:
            raise FirewallSettingsError(f'Не удалось выполнить {argv[0]}: {exc}') from exc

    def _configured(self):
        try:
            raw = self.config_path.read_bytes()
            backend = raw.decode('ascii').rstrip('\n')
        except (OSError, UnicodeError) as exc:
            raise FirewallSettingsError(f'Не удалось прочитать {self.config_path}: {exc}') from exc
        if backend not in BACKENDS:
            raise FirewallSettingsError('Некорректный FWTYPE: ожидается nftables или iptables')
        return backend, raw

    def _is_active(self):
        result = self._command('systemctl', 'is-active', 'zapret')
        value = result.stdout.strip()
        if result.returncode == 0 and value == 'active':
            return True
        if result.returncode == 3 and value in ('inactive', 'failed'):
            return False
        raise FirewallSettingsError('Не удалось определить состояние службы zapret: ' +
                                    (result.stderr.strip() or value or 'нет ответа'))

    def _explicit_choice(self, backend):
        try:
            choice = self.choice_path.read_bytes().decode('ascii').rstrip('\n')
        except FileNotFoundError:
            return False
        except (OSError, UnicodeError) as exc:
            raise FirewallSettingsError(f'Не удалось прочитать {self.choice_path}: {exc}') from exc
        if choice not in BACKENDS or choice != backend:
            raise FirewallSettingsError('FWTYPE.user не соответствует FWTYPE; проверьте настройку фаервола')
        return True

    def read_state(self):
        state = dict(installed=self.config_path.is_file(), configured=None, active=None,
                     service_active=False, explicit=False, error=None)
        try:
            state['configured'], _ = self._configured()
            state['explicit'] = self._explicit_choice(state['configured'])
            state['service_active'] = self._is_active()
            if state['service_active']:
                try:
                    marker = (self.state_dir / 'firewall-backend').read_text().strip()
                except OSError:
                    marker = None
                if marker in BACKENDS:
                    state['active'] = marker
        except FirewallSettingsError as exc:
            state['error'] = str(exc)
        return state

    def _service(self, action):
        result = self._command('systemctl', action, 'zapret')
        if result.returncode:
            raise FirewallSettingsError(f'Ошибка {action} службы zapret: ' +
                                        (result.stderr.strip() or result.stdout.strip()))

    def _verify_started(self, backend):
        if not self._is_active():
            raise FirewallSettingsError('Служба zapret не запущена')
        try:
            marker = (self.state_dir / 'firewall-backend').read_text().strip()
        except OSError as exc:
            raise FirewallSettingsError('Нет подтверждения активного firewall') from exc
        if marker != backend:
            raise FirewallSettingsError('Активный firewall не соответствует выбранному')
        if self._command('pgrep', '-x', 'nfqws').returncode:
            raise FirewallSettingsError('Процесс nfqws не запущен')

    def _atomic_write(self, content, metadata, path=None):
        path = self.config_path if path is None else path
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = stream.name
                os.fchmod(stream.fileno(), stat.S_IMODE(metadata.st_mode))
                if os.geteuid() == 0:
                    os.fchown(stream.fileno(), metadata.st_uid, metadata.st_gid)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
            temporary = None
        finally:
            if temporary is not None:
                os.unlink(temporary)

    @contextlib.contextmanager
    def _locked(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.state_dir / 'firewall-settings.lock',
                             os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise FirewallSettingsError('Настройки firewall уже изменяются') from exc
            yield
        finally:
            os.close(descriptor)

    def apply(self, backend):
        if backend not in BACKENDS:
            raise FirewallSettingsError('Выберите nftables или iptables')
        try:
            with self._locked():
                previous, content = self._configured()
                state = self.read_state()
                if state['error']:
                    raise FirewallSettingsError(state['error'])
                metadata = self.config_path.stat()
                if previous == backend and (not state['service_active'] or state['active'] == backend):
                    if not state['explicit']:
                        self._atomic_write((backend + '\n').encode('ascii'), metadata, self.choice_path)
                    return dict(state, explicit=True, changed=not state['explicit'])
                tools = ('nft',) if backend == 'nftables' else ('iptables', 'ip6tables')
                missing = [tool for tool in tools if not self.which(tool)]
                if missing:
                    raise FirewallSettingsError('Не найдены утилиты: ' + ', '.join(missing))
                choice_content = self.choice_path.read_bytes() if state['explicit'] else None
                choice_metadata = self.choice_path.stat() if state['explicit'] else metadata
                was_active = state['service_active']
                if was_active:
                    self._service('stop')
                    if self._is_active():
                        raise FirewallSettingsError('Служба zapret не остановлена; FWTYPE не изменён')
                try:
                    self._atomic_write((backend + '\n').encode('ascii'), metadata)
                    # The starter must see an explicit choice before restarting.
                    # Both files are restored below if applying it fails.
                    self._atomic_write((backend + '\n').encode('ascii'), metadata, self.choice_path)
                    if was_active:
                        self._service('start')
                        self._verify_started(backend)
                except Exception as exc:
                    failures = []
                    if was_active:
                        try:
                            self._service('stop')
                        except Exception as rollback_exc:
                            failures.append(str(rollback_exc))
                    try:
                        self._atomic_write(content, metadata)
                    except Exception as rollback_exc:
                        failures.append('восстановление FWTYPE: ' + str(rollback_exc))
                    try:
                        if state['explicit']:
                            try:
                                current_choice = self.choice_path.read_bytes()
                            except FileNotFoundError:
                                current_choice = None
                            if current_choice != choice_content:
                                self._atomic_write(choice_content, choice_metadata, self.choice_path)
                        else:
                            self.choice_path.unlink(missing_ok=True)
                    except Exception as rollback_exc:
                        failures.append('восстановление выбора фаервола: ' + str(rollback_exc))
                    if was_active and not failures:
                        try:
                            # Keep the previous backend during rollback even if
                            # the new starter would migrate an unmarked default.
                            if not state['explicit']:
                                self._atomic_write(content, metadata, self.choice_path)
                            self._service('start')
                            self._verify_started(previous)
                        except Exception as rollback_exc:
                            failures.append(str(rollback_exc))
                        finally:
                            if not state['explicit']:
                                try:
                                    self.choice_path.unlink(missing_ok=True)
                                except OSError as rollback_exc:
                                    failures.append('восстановление выбора фаервола: ' + str(rollback_exc))
                    detail = '; ошибка отката: ' + '; '.join(failures) if failures else '; прежнее состояние восстановлено'
                    raise FirewallSettingsError(str(exc) + detail) from exc
                return dict(self.read_state(), changed=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise FirewallSettingsError(str(exc)) from exc


def read_state():
    return FirewallSettingsEngine().read_state()


def apply_backend(backend, password=None):
    if backend not in BACKENDS:
        raise FirewallSettingsError('Выберите nftables или iptables')
    state = read_state()
    if state['error']:
        raise FirewallSettingsError(state['error'])
    if (state['explicit'] and state['configured'] == backend
            and (not state['service_active'] or state['active'] == backend)):
        return dict(state, changed=False)
    command = ['/usr/bin/python3', '-I', str(Path(__file__).resolve()), '--apply', backend]
    kwargs = {}
    if os.geteuid() != 0:
        command = ['sudo', '-S', '-p', '', '--'] + command if password is not None else ['sudo', '-n', '--'] + command
        if password is not None:
            kwargs['input'] = password + '\n'
    try:
        result = _run(command, timeout=600, **kwargs)
        try:
            response = json.loads(result.stdout)
        except ValueError as exc:
            raise FirewallSettingsError(result.stderr.strip() or
                                        'Помощник настройки firewall не вернул результат') from exc
        if not isinstance(response, dict):
            raise FirewallSettingsError('Некорректный ответ помощника настройки firewall')
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        raise FirewallSettingsError('Не удалось применить настройки firewall: ' + str(exc)) from exc
    if result.returncode or not response.get('ok'):
        raise FirewallSettingsError(response.get('error') or result.stderr.strip() or 'Ошибка изменения firewall')
    return response['state']


def _main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', required=True, choices=BACKENDS)
    args = parser.parse_args()
    os.environ['PATH'] = '/usr/sbin:/usr/bin:/sbin:/bin'
    try:
        if os.geteuid() != 0:
            raise FirewallSettingsError('Требуются права root')
        result = FirewallSettingsEngine().apply(args.apply)
        print(json.dumps(dict(ok=True, state=result), ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=str(exc)), ensure_ascii=False))
        return 1


if __name__ == '__main__':
    sys.exit(_main())
