from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request

from core.app_logging import get_error_logger
from core.updater_base import BaseUpdater
from core.manager_config import VERSION_CONFIG
from core.manager_updater import ManagerUpdater
from core.runtime_resources import PRESERVED_UPDATE_FILES, LEGACY_RESOURCE_FILES
from core.update_backup import UpdateBackup
from core.platform_info import (
    is_valve_steamos,
    distro_log_label,
    os_release_id_normalized,
    ZAPRET_SYSTEMD_UNIT_DIR,
    ZAPRET_SYSTEMD_UNIT_PATH,
    ZAPRET_SYSTEMD_UNIT_PATH_LEGACY,
)


def validate_fwtype(value):
    backend = value.strip()
    if backend not in ("iptables", "nftables"):
        raise ValueError(f"Неверный FWTYPE: {backend!r}; ожидается iptables или nftables")
    return backend


class ZapretUpdater(BaseUpdater):
    def __init__(self):
        super().__init__(
            version_url=VERSION_CONFIG["version_url"],
            current_version=VERSION_CONFIG["current_version"],
            name="zapret службы",
        )
        self.is_steamos = self.check_if_steamos()

    def check_if_steamos(self):
        """Только официальная SteamOS Valve (ID=steamos)."""
        print(
            f"Проверка Valve SteamOS… Дистрибутив: {distro_log_label()} "
            f"(ID={os_release_id_normalized() or '?'})"
        )
        return is_valve_steamos()

    def get_sudo_password(self, parent_window):
        """Получает sudo пароль через окно.

        Tkinter разрешает создавать окна и wait_window только в потоке с mainloop.
        Обновление zapret запускается из фонового потока — диалог планируем через after(0).
        """
        try:
            from ui.windows.sudo_password_window import SudoPasswordWindow
        except Exception as e:
            print(f"Ошибка импорта SudoPasswordWindow: {e}")
            import traceback
            traceback.print_exc()
            return None

        if parent_window is None:
            print("Нет родительского окна для диалога пароля")
            return None

        def _show_dialog():
            password_window = SudoPasswordWindow(
                parent_window,
                on_password_valid=lambda pwd: None,
            )
            return password_window.run()

        try:
            if threading.current_thread() is threading.main_thread():
                password = _show_dialog()
            else:
                holder = [None]
                done = threading.Event()

                def _on_main():
                    try:
                        holder[0] = _show_dialog()
                    except Exception as e:
                        print(f"Ошибка при получении sudo пароля: {e}")
                        import traceback
                        traceback.print_exc()
                        holder[0] = None
                    finally:
                        done.set()

                parent_window.after(0, _on_main)
                done.wait()
                password = holder[0]
        except Exception as e:
            print(f"Ошибка при получении sudo пароля: {e}")
            import traceback
            traceback.print_exc()
            return None

        if password:
            print("Sudo пароль получен")
            return password
        print("Пользователь отменил ввод пароля")
        return None

    def run_with_sudo(self, command, password, description=""):
        """Выполняет команду с sudo"""
        try:
            if description:
                print(f"Выполнение: {description}")

            sudo_cmd = ['sudo', '-S'] + command

            process = subprocess.Popen(
                sudo_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=f"{password}\n", timeout=30)

            return {
                'returncode': process.returncode,
                'stdout': stdout,
                'stderr': stderr
            }

        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': 'Таймаут выполнения команды'
            }
        except Exception as e:
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }

    @staticmethod
    def validate_fwtype(value):
        return validate_fwtype(value)

    def snapshot_fwtype(self, password):
        """Retain explicit choices; legacy installations adopt the bundle default."""
        self.__dict__.pop('_saved_fwtype', None)
        result = self.run_with_sudo(
            ['bash', '-c', 'if [ -e /opt/zapret/FWTYPE ] || [ -L /opt/zapret/FWTYPE ]; then cat /opt/zapret/FWTYPE; else exit 3; fi'],
            password, "Сохранение FWTYPE...",
        )
        if result and result['returncode'] == 3:
            configured = None
        elif result and result['returncode'] == 0:
            configured = self.validate_fwtype(result['stdout'])
        else:
            raise ValueError("Не удалось прочитать FWTYPE: " + (result or {}).get('stderr', 'нет ответа'))
        choice = self.run_with_sudo(
            ['bash', '-c', 'if [ -e /opt/zapret/FWTYPE.user ] || [ -L /opt/zapret/FWTYPE.user ]; then cat /opt/zapret/FWTYPE.user; else exit 3; fi'],
            password, "Сохранение выбранного фаервола...",
        )
        if choice and choice['returncode'] == 3:
            self._saved_fwtype = None
            return
        if not choice or choice['returncode'] != 0:
            raise ValueError("Не удалось прочитать FWTYPE.user: " + (choice or {}).get('stderr', 'нет ответа'))
        selected = self.validate_fwtype(choice['stdout'])
        if selected != configured:
            raise ValueError("FWTYPE.user не соответствует FWTYPE; обновление отменено")
        self._saved_fwtype = selected

    def stop_and_remove_zapret(self, password, progress_callback=None):
        """Останавливает и удаляет старую версию zapret"""
        self._update_mutated = False
        self._readonly_unlock_attempted = False
        try:
            self.snapshot_fwtype(password)
        except ValueError as error:
            print(error)
            return False
        commands = [
            (['systemctl', 'stop', 'zapret'], "Остановка службы zapret"),
            (['systemctl', 'disable', 'zapret'], "Отключение автозапуска"),
            (["rm", "-f", ZAPRET_SYSTEMD_UNIT_PATH], "Удаление unit из /etc/systemd/system"),
            (
                ["rm", "-f", ZAPRET_SYSTEMD_UNIT_PATH_LEGACY],
                "Удаление устаревшего unit из /usr (при возможности)",
            ),
            (['rm', '-rf', '/opt/zapret/'], "Удаление директории zapret")
        ]

        if self.is_steamos:
            commands.insert(0, (['steamos-readonly', 'disable'], "Отключение защиты SteamOS"))

        for cmd, description in commands:
            if cmd[0] == 'steamos-readonly':
                self._readonly_unlock_attempted = True
            if progress_callback:
                progress_callback(description, None)

            result = self.run_with_sudo(cmd, password, description)
            if not result or result['returncode'] != 0:
                detail = (result or {}).get('stderr', 'нет ответа')
                print(f"Предупреждение при {description}: {detail}")
                if cmd[0] == 'steamos-readonly':
                    return False
                if cmd[:2] == ['systemctl', 'stop']:
                    # A new installation has no unit. Every other stop failure
                    # must leave the running service and its files intact.
                    state = self.run_with_sudo(
                        ['systemctl', 'show', 'zapret.service', '--property=LoadState', '--value'],
                        password, "Проверка наличия службы zapret",
                    )
                    if not state or state['returncode'] != 0 or state['stdout'].strip() != 'not-found':
                        print("Не удалось остановить zapret; удаление и обновление отменены")
                        return False
                if cmd[:2] == ['rm', '-rf'] or cmd == ['rm', '-f', ZAPRET_SYSTEMD_UNIT_PATH]:
                    return False
            if cmd[:2] == ['systemctl', 'stop']:
                self._update_mutated = True

        return True

    def copy_zapret_files(self, extract_dir, password, progress_callback=None):
        """Копирует файлы zapret в /opt/zapret"""
        try:
            system_dir = None
            for root, dirs, files in os.walk(extract_dir):
                if 'system' in dirs:
                    system_dir = os.path.join(root, 'system')
                    break

            if not system_dir:
                print("Не найдена папка 'system' в архиве")
                return False

            # Validate both inputs before any copy can overwrite FWTYPE.
            with open(os.path.join(system_dir, 'FWTYPE'), encoding='utf-8') as source:
                bundle_fwtype = self.validate_fwtype(source.read())
            if not hasattr(self, '_saved_fwtype'):
                self.snapshot_fwtype(password)
            selected_fwtype = self._saved_fwtype or bundle_fwtype
            result = self.run_with_sudo(['mkdir', '-p', '/opt/zapret'], password,
                                        "Создание директории /opt/zapret...")
            if not result or result['returncode'] != 0:
                print("Не удалось создать /opt/zapret")
                return False

            if progress_callback:
                progress_callback("Копирование файлов системы...", 60)

            for item in os.listdir(system_dir):
                if item in ('FWTYPE', 'FWTYPE.user'):
                    continue  # Write only the validated, selected value below.
                src = os.path.join(system_dir, item)
                dst = os.path.join('/opt/zapret', item)

                if os.path.isfile(src):
                    if item == 'starter.sh':
                        # A service update must retain user-imported BIN aliases.
                        from core.strategy_import import starter_with_manager_bins
                        with open(src, encoding='utf-8') as starter_source:
                            starter_text = starter_with_manager_bins(starter_source.read())
                        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.sh') as staged:
                            staged.write(starter_text)
                            staged.flush()
                            result = self.run_with_sudo(
                                ['cp', staged.name, dst], password, f"Копирование {item}..."
                            )
                    else:
                        result = self.run_with_sudo(
                            ['cp', src, dst],
                            password,
                            f"Копирование {item}..."
                        )
                elif os.path.isdir(src):
                    result = self.run_with_sudo(
                        ['cp', '-r', src, dst],
                        password,
                        f"Копирование папки {item}..."
                    )

                if not result or result['returncode'] != 0:
                    print(f"Не удалось скопировать {item}")
                    return False

            if progress_callback:
                progress_callback("Копирование бинарных файлов...", 70)

            arch = os.uname().machine
            bin_dirs = {
                'x86_64': 'x86_64',
                'i386': 'x86',
                'i686': 'x86',
                'armv7l': 'arm',
                'armv6l': 'arm',
                'aarch64': 'arm64'
            }

            bin_dir_name = bin_dirs.get(arch)
            if bin_dir_name:
                bins_dir = None
                for root, dirs, files in os.walk(extract_dir):
                    if 'bins' in dirs:
                        bins_dir = os.path.join(root, 'bins')
                        break

                if bins_dir:
                    arch_bin_dir = os.path.join(bins_dir, bin_dir_name)
                    nfqws_path = os.path.join(arch_bin_dir, 'nfqws')

                    if os.path.exists(nfqws_path):
                        result = self.run_with_sudo(
                            ['cp', nfqws_path, '/opt/zapret/nfqws'],
                            password,
                            "Копирование бинарного файла nfqws..."
                        )
                        if not result or result['returncode'] != 0:
                            print("Не удалось скопировать nfqws")
                            return False
                        result = self.run_with_sudo(['chmod', '+x', '/opt/zapret/nfqws'], password)
                        if not result or result['returncode'] != 0:
                            return False

            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as staged:
                staged.write(selected_fwtype + '\n')
                staged.flush()
                result = self.run_with_sudo(['cp', staged.name, '/opt/zapret/FWTYPE'],
                                            password, "Восстановление FWTYPE...")
            if not result or result['returncode'] != 0:
                print("Не удалось записать FWTYPE")
                return False
            if self._saved_fwtype:
                # The installed default must never become an explicit choice.
                result = self.run_with_sudo(['cp', '/opt/zapret/FWTYPE', '/opt/zapret/FWTYPE.user'],
                                            password, "Сохранение выбранного фаервола...")
            else:
                result = self.run_with_sudo(['rm', '-f', '/opt/zapret/FWTYPE.user'], password)
            if not result or result['returncode'] != 0:
                print("Не удалось сохранить выбор фаервола")
                return False
            result = self.run_with_sudo(['chmod', '-R', 'o+r', '/opt/zapret/'], password)
            if not result or result['returncode'] != 0:
                return False
            # The snapshot belongs to this completed installation only.
            del self._saved_fwtype

            return True

        except Exception as e:
            print(f"Ошибка при копировании файлов: {e}")
            return False

    def update_manager_config(self, extract_dir):
        """Обновляет файл конфигурации менеджера"""
        try:
            config_path = None

            for root, dirs, files in os.walk(extract_dir):
                if 'manager_config.py' in files:
                    config_path = os.path.join(root, 'manager_config.py')
                    break

            if not config_path:
                print("Файл manager_config.py не найден в архиве")
                return

            home_dir = os.path.expanduser("~")

            target_dir = os.path.join(home_dir, "Zapret_DPI_Manager", "core")
            target_path = os.path.join(target_dir, "manager_config.py")

            os.makedirs(target_dir, exist_ok=True)
            shutil.copy2(config_path, target_path)

            print(f"Файл конфигурации обновлен: {target_path}")

        except Exception as e:
            print(f"Ошибка при обновлении конфигурации: {e}")

    def create_service_file(self, password, progress_callback=None):
        """Создает файл службы systemd"""
        try:
            if progress_callback:
                progress_callback("Создание службы systemd...", 80)

            service_content = """[Unit]
Description=zapret
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/zapret
ExecStart=/bin/bash /opt/zapret/starter.sh
ExecStop=/bin/bash /opt/zapret/stopper.sh

[Install]
WantedBy=multi-user.target
"""

            temp_service = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_service.write(service_content)
            temp_service.close()

            result_mk = self.run_with_sudo(
                ["mkdir", "-p", ZAPRET_SYSTEMD_UNIT_DIR],
                password,
                "Подготовка каталога /etc/systemd/system…",
            )
            if not result_mk or result_mk["returncode"] != 0:
                print("Не удалось создать каталог для службы")
                os.unlink(temp_service.name)
                return False

            result = self.run_with_sudo(
                ["cp", temp_service.name, ZAPRET_SYSTEMD_UNIT_PATH],
                password,
                "Копирование файла службы...",
            )

            os.unlink(temp_service.name)

            if not result or result["returncode"] != 0:
                print("Не удалось создать службу")
                return False

            permissions = self.run_with_sudo(
                ["chmod", "644", ZAPRET_SYSTEMD_UNIT_PATH],
                password,
                "Права на файл службы...",
            )
            if not permissions or permissions['returncode'] != 0:
                return False
            self.run_with_sudo(
                ["rm", "-f", ZAPRET_SYSTEMD_UNIT_PATH_LEGACY],
                password,
                "Удаление устаревшего unit из /usr…",
            )

            return True

        except Exception as e:
            print(f"Ошибка при создании службы: {e}")
            return False

    def enable_service(self, password, progress_callback=None):
        """Включает и запускает службу"""
        try:
            if progress_callback:
                progress_callback("Обновление systemd...", 85)

            result = self.run_with_sudo(
                ['systemctl', 'daemon-reload'],
                password,
                "Обновление systemd..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось обновить systemd")
                return False

            if progress_callback:
                progress_callback("Включение автозапуска...", 90)

            result = self.run_with_sudo(
                ['systemctl', 'enable', 'zapret.service'],
                password,
                "Включение автозапуска службы..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось включить автозапуск")
                return False

            if progress_callback:
                progress_callback("Запуск службы...", 95)

            result = self.run_with_sudo(
                ['systemctl', 'start', 'zapret.service'],
                password,
                "Запуск службы Zapret..."
            )
            if not result or result['returncode'] != 0:
                print("Не удалось запустить службу zapret")
                return False

            time.sleep(2)
            check_result = self.run_with_sudo(
                ['systemctl', 'is-active', 'zapret'],
                password,
                "Проверка статуса службы..."
            )
            if (not check_result or check_result['returncode'] != 0
                    or check_result['stdout'].strip() != 'active'):
                print("Служба zapret не активна после запуска")
                return False
            if progress_callback:
                progress_callback("Служба успешно запущена", 100)
            return True

        except Exception as e:
            print(f"Ошибка при включении службы: {e}")
            return False

    def lock_steamos_system(self, password):
        """Блокирует файловую систему SteamOS (только для SteamOS)"""
        if not self.is_steamos:
            print("Пропускаем блокировку: система не SteamOS")
            return True

        print("Блокировка файловой системы SteamOS...")
        result = self.run_with_sudo(
            ['steamos-readonly', 'enable'],
            password,
            "Включение защиты SteamOS..."
        )

        if not result or result['returncode'] != 0:
            print(f"Предупреждение: Не удалось заблокировать систему: {result['stderr'] if result else 'No result'}")
            return False

        print("Система успешно заблокирована")
        return True

    def install_zapret_from_local_bundle(self, bundle_root, password, progress_callback=None):
        """
        Устанавливает службу из bundle_root/zapret/ (system/, bins/).
        Вызывать после stop_and_remove_zapret и наката файлов менеджера.
        """
        zapret_sub = os.path.join(bundle_root, "zapret")
        if not os.path.isdir(os.path.join(zapret_sub, "system")):
            print("В пакете нет каталога zapret/system")
            return False
        if not self.copy_zapret_files(zapret_sub, password, progress_callback):
            return False
        if not self.create_service_file(password, progress_callback):
            return False
        if not self.enable_service(password, progress_callback):
            return False
        return True

    def replace_from_bundle(self, bundle_root, password, progress_callback=None, manager=None):
        """Replace a validated service and optional manager, restoring both on failure."""
        if not validate_service_bundle(bundle_root):
            return False
        backup_dir = tempfile.mkdtemp(prefix="zapret_update_backup_")
        backup = UpdateBackup(self, password, backup_dir,
                              manager.manager_dir if manager is not None else None)
        captured = False
        completed = False
        retain_backup = False
        self._update_mutated = False
        try:
            backup.capture()
            captured = True
            if not self.stop_and_remove_zapret(password, progress_callback):
                raise RuntimeError("Не удалось подготовить службу к обновлению")
            if manager is not None and not manager.apply_from_directory(
                bundle_root, progress_callback, extra_exclude_prefixes=["zapret"]
            ):
                raise RuntimeError("Не удалось обновить файлы менеджера")
            if not self.install_zapret_from_local_bundle(bundle_root, password, progress_callback):
                raise RuntimeError("Не удалось установить или запустить новую службу")
            completed = True
        except Exception as error:
            detail = f"Обновление не завершено: {error}"
            print(detail)
            get_error_logger().error("Обновление не завершено: %s", error, exc_info=True)
            if captured and self._update_mutated:
                try:
                    backup.restore()
                    print("Предыдущая версия менеджера и службы восстановлена")
                    detail += ". Предыдущая версия восстановлена."
                except Exception:
                    retain_backup = True
                    get_error_logger().exception(
                        "Не удалось восстановить предыдущую версию; резервная копия: %s", backup_dir
                    )
                    print(f"Резервная копия сохранена для восстановления: {backup_dir}")
                    detail += f". Восстановление не удалось. Резервная копия: {backup_dir}"
            if progress_callback:
                progress_callback(detail, None)
        finally:
            # Every exit after a possible unlock, including ordinary False results.
            if (getattr(self, '_readonly_unlock_attempted', False)
                    and not self.lock_steamos_system(password)):
                completed = False
                if progress_callback:
                    progress_callback("Не удалось включить защиту SteamOS", None)
            if not retain_backup:
                try:
                    backup.cleanup()
                    shutil.rmtree(backup_dir, ignore_errors=True)
                except Exception:
                    print(f"Не удалось удалить резервную копию: {backup_dir}")
                    get_error_logger().exception("Не удалось удалить резервную копию: %s", backup_dir)
        return completed

    def install_zapret_service_from_bundle_root(
        self, bundle_root: str, password: str, progress_callback=None
    ) -> bool:
        """Update only the service, retaining a complete backup until it starts."""
        if not is_valid_bundle_root(bundle_root):
            print("Неверный корень полного пакета (нужны main.py и zapret/system)")
            return False
        return self.replace_from_bundle(bundle_root, password, progress_callback)


# --- Полный пакет (менеджер + служба, один архив) ---

BUNDLE_DIR_NAME = "zapret_updater"


def is_valid_bundle_root(path: str) -> bool:
    """В корне пакета: main.py и zapret/system/ (bins — в zapret/bins/)."""
    return bool(
        path
        and os.path.isfile(os.path.join(path, "main.py"))
        and os.path.isdir(os.path.join(path, "zapret", "system"))
    )


def find_bundle_root(extract_dir: str) -> str | None:
    """
    Корень пакета после распаковки:

    1) Сам ``extract_dir``, если архив собран изнутри папки пакета (``tar ... .``) —
       в корне сразу ``main.py`` и ``zapret/system/``.
    2) Иначе подкаталог ``zapret_updater/`` (без учёта регистра), если архив
       собран как ``tar ... zapret_updater``.
    """
    if is_valid_bundle_root(extract_dir):
        return extract_dir

    candidates: list[str] = []
    direct = os.path.join(extract_dir, BUNDLE_DIR_NAME)
    if os.path.isdir(direct):
        candidates.append(direct)
    try:
        for name in os.listdir(extract_dir):
            if name.lower() == BUNDLE_DIR_NAME.lower():
                p = os.path.join(extract_dir, name)
                if os.path.isdir(p) and p not in candidates:
                    candidates.append(p)
    except OSError:
        pass

    for cand in candidates:
        if is_valid_bundle_root(cand):
            return cand
    return None


def download_http_to_file(
    url: str,
    dest_path: str,
    *,
    timeout: float = 120.0,
    reporthook=None,
) -> None:
    """
    Скачивает URL в файл с таймаутом (в отличие от urlretrieve).

    reporthook(blocknum, block_size, total_size) — как у urlretrieve;
    total_size = -1, если размер неизвестен (нет Content-Length).
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Zapret-DPI-Manager/2"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        cl = resp.headers.get("Content-Length")
        try:
            total_size = int(cl) if cl else -1
        except (TypeError, ValueError):
            total_size = -1
        block_size = 64 * 1024
        blocknum = 0
        with open(dest_path, "wb") as out:
            while True:
                chunk = resp.read(block_size)
                if not chunk:
                    break
                out.write(chunk)
                blocknum += 1
                if reporthook:
                    reporthook(blocknum, block_size, total_size)


def service_requires_firewall_helper(system_dir: str) -> bool:
    """Older service scripts contain their own firewall implementation."""
    for script in ('starter.sh', 'stopper.sh'):
        try:
            with open(os.path.join(system_dir, script), encoding='utf-8', errors='replace') as source:
                if any(re.search(r'^\s*(?:source|\.)\s+.*\bfirewall\.sh\b', line) for line in source):
                    return True
        except FileNotFoundError:
            continue  # The required-file check reports a missing service script.
    return False


def validate_service_bundle(bundle_root: str) -> bool:
    """Check the usable service payload before stopping an installed service."""
    arch = {'x86_64': 'x86_64', 'i386': 'x86', 'i686': 'x86',
            'armv7l': 'arm', 'armv6l': 'arm', 'aarch64': 'arm64'}.get(os.uname().machine)
    if not arch:
        print(f"Неподдерживаемая архитектура: {os.uname().machine}")
        return False
    required = ["zapret/system/" + name for name in
                ("starter.sh", "stopper.sh", "FWTYPE")]
    required.append(f"zapret/bins/{arch}/nfqws")
    try:
        if service_requires_firewall_helper(os.path.join(bundle_root, 'zapret/system')):
            required.append('zapret/system/firewall.sh')
        for relative in required:
            path = os.path.join(bundle_root, relative)
            if not os.path.isfile(path) or os.path.islink(path) or os.path.getsize(path) == 0:
                raise ValueError(f"В пакете отсутствует или пуст обязательный файл: {relative}")
        with open(os.path.join(bundle_root, "zapret/system/FWTYPE"), encoding="utf-8") as source:
            validate_fwtype(source.read())
        return True
    except (OSError, ValueError) as error:
        print(error)
        get_error_logger().error('Проверка пакета службы: %s', error)
        return False


def validate_bundle_structure(bundle_root: str) -> bool:
    if not is_valid_bundle_root(bundle_root):
        get_error_logger().error('В полном пакете отсутствует main.py или каталог zapret/system/')
        return False
    if not validate_service_bundle(bundle_root):
        return False
    try:
        manifest_path = os.path.join(bundle_root, 'core/runtime_resources.py')
        legacy = not os.path.lexists(manifest_path)
        if legacy:
            required = LEGACY_RESOURCE_FILES
        else:
            with open(manifest_path, encoding='utf-8-sig') as source:
                manifest = ast.parse(source.read())
            assignments = [node.value for node in manifest.body
                           if isinstance(node, ast.Assign) and any(
                               isinstance(target, ast.Name) and target.id == 'REQUIRED_RESOURCE_FILES'
                               for target in node.targets)]
            if len(assignments) != 1:
                raise ValueError('Нет однозначного списка обязательных файлов в пакете')
            required = ast.literal_eval(assignments[0])
        if (not isinstance(required, tuple) or not all(isinstance(name, str) for name in required)
                or not {'main.py', 'core/manager_config.py'}.issubset(required)):
            raise ValueError('Неверный список обязательных файлов в пакете')
        for relative in required:
            path = os.path.join(bundle_root, relative)
            if os.path.isabs(relative) or '..' in relative.split('/'):
                raise ValueError(f"Недопустимый путь в списке обязательных файлов: {relative}")
            if relative in PRESERVED_UPDATE_FILES and not os.path.lexists(path):
                continue
            if not os.path.isfile(path) or os.path.islink(path):
                raise ValueError(f"В пакете отсутствует обязательный файл: {relative}")
        for root, dirs, files in os.walk(bundle_root):
            dirs[:] = [name for name in dirs if name not in ("scripts", "tests", "__pycache__")]
            for name in files:
                if name.endswith(".py"):
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8-sig") as source:
                        tree = ast.parse(source.read(), filename=path)
                    if legacy:
                        for node in ast.walk(tree):
                            imports = ([alias.name for alias in node.names] if isinstance(node, ast.Import)
                                       else [node.module] if isinstance(node, ast.ImportFrom) and not node.level
                                       else [])
                            for module in imports:
                                if not module:
                                    continue
                                if module.split('.')[0] in ('scripts', 'tests'):
                                    raise ValueError(f'Рабочий модуль зависит от каталога разработки: {module}')
                                if module.split('.')[0] not in ('core', 'ui'):
                                    continue
                                target = os.path.join(bundle_root, *module.split('.'))
                                if not (os.path.isfile(target + '.py') or os.path.isdir(target)):
                                    raise ValueError(f'Нет модуля {module}, импортируемого из {path}')
        return True
    except (OSError, ValueError, SyntaxError) as error:
        print(f"Неверный пакет обновления: {error}")
        get_error_logger().error('Проверка полного пакета: %s', error)
        return False


def extract_bundle(archive_path, destination):
    """Reject paths and links that could escape the fresh extraction directory."""
    target = os.path.realpath(destination)
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            path = os.path.realpath(os.path.join(target, member.name))
            if (os.path.isabs(member.name) or os.path.commonpath([target, path]) != target
                    or not (member.isfile() or member.isdir())):
                raise ValueError(f"Недопустимый путь или тип файла в архиве: {member.name}")
        if hasattr(tarfile, "data_filter"):
            archive.extractall(path=target, filter="data")
        else:
            archive.extractall(path=target)


def read_bundle_manifest(
    version_url: str | None = None, timeout: float = 10
) -> tuple[str | None, str | None]:
    """Первая и вторая строки version.txt: версия и URL архива полного пакета."""
    url = version_url or VERSION_CONFIG["version_url"]
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            content = response.read().decode("utf-8").strip()
        lines = content.split("\n")
        if len(lines) >= 2:
            ver = lines[0].strip()
            download = lines[1].strip()
            if download:
                return ver, download
    except Exception as e:
        print(f"Манифест полного пакета недоступен ({url}): {e}")
        get_error_logger().error(
            "Манифест полного пакета недоступен (%s): %s",
            url,
            e,
            exc_info=True,
        )
    return None, None


def get_bundle_download_url(
    version_url: str | None = None, timeout: float = 10
) -> str | None:
    _, dl = read_bundle_manifest(version_url=version_url, timeout=timeout)
    return dl


class ZapretBundleUpdater(BaseUpdater):
    def __init__(self):
        super().__init__(
            version_url=VERSION_CONFIG["version_url"],
            current_version=VERSION_CONFIG["current_version"],
            name="Zapret DPI Manager",
        )

    def update_bundle(self, download_url, parent_window, progress_callback=None):
        """Скачивает один архив, обновляет менеджер (без zapret/) и службу из zapret/."""
        print("=== ПОЛНОЕ ОБНОВЛЕНИЕ (МЕНЕДЖЕР + СЛУЖБА) ===")
        zapret_u = ZapretUpdater()
        password = zapret_u.get_sudo_password(parent_window)
        if not password:
            if progress_callback:
                progress_callback("Пароль не введён, отмена обновления", None)
            return False

        temp_dir = tempfile.mkdtemp(prefix="zapret_bundle_")
        try:
            archive_path = os.path.join(temp_dir, "bundle.tar.gz")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            if progress_callback:
                progress_callback("Скачивание полного пакета...", 15)

            def download_progress(count, block_size, total_size):
                if progress_callback and total_size > 0:
                    pct = min(int(count * block_size * 100 / total_size), 100)
                    progress_callback(f"Скачивание... {pct}%", 15 + int(25 * pct / 100))

            try:
                download_http_to_file(
                    download_url,
                    archive_path,
                    timeout=120.0,
                    reporthook=download_progress,
                )
            except urllib.error.URLError as e:
                reason = e.reason
                detail = str(reason) if reason is not None else str(e)
                msg = (
                    "Не удалось скачать архив обновления. Проверьте интернет и DNS. "
                    f"({detail})"
                )
                print(msg)
                get_error_logger().error(
                    "Скачивание bundle (%s): %s",
                    download_url,
                    msg,
                    exc_info=True,
                )
                if progress_callback:
                    progress_callback(msg, None)
                return False

            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                print("Архив пустой или не скачан")
                get_error_logger().error(
                    "Архив обновления пустой или отсутствует после скачивания: %s",
                    download_url,
                )
                return False

            if progress_callback:
                progress_callback("Распаковка архива...", 45)
            extract_bundle(archive_path, extract_dir)

            bundle_root = find_bundle_root(extract_dir)
            if not bundle_root:
                print(
                    "Неверная структура архива обновления: нужны main.py и zapret/system/ "
                    "(и zapret/bins/), либо то же внутри папки zapret_updater/."
                )
                get_error_logger().error(
                    "Неверная структура архива обновления (ожидались main.py и zapret/system/)"
                )
                return False
            if not validate_bundle_structure(bundle_root):
                message = 'Пакет обновления не прошёл проверку содержимого. Подробности указаны в журнале ошибок.'
                print(message)
                if progress_callback:
                    progress_callback(message, None)
                return False

            manager_u = ManagerUpdater()
            if not zapret_u.replace_from_bundle(
                bundle_root, password, progress_callback, manager=manager_u
            ):
                return False

            if progress_callback:
                progress_callback("Полное обновление завершено", 100)
            return True
        except Exception as e:
            print(f"Ошибка полного обновления: {e}")
            get_error_logger().exception("Ошибка полного обновления (bundle)")
            return False
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
