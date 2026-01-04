import os
import tempfile
import tarfile
import shutil
import subprocess
import time
from core.updater_base import BaseUpdater
from core.manager_config import ZAPRET_CONFIG

class ZapretUpdater(BaseUpdater):
    def __init__(self):
        super().__init__(
            version_url=ZAPRET_CONFIG["version_url"],
            current_version=ZAPRET_CONFIG["current_version"],
            name="zapret службы"
        )

    def get_sudo_password(self, parent_window):
        """Получает sudo пароль через окно"""
        try:
            from ui.windows.sudo_password_window import SudoPasswordWindow

            # Создаем окно
            password_window = SudoPasswordWindow(
                parent_window,
                on_password_valid=lambda pwd: None  # Заглушка
            )

            # Получаем пароль из метода run()
            password = password_window.run()

            if password:
                print("Sudo пароль получен")
                return password
            else:
                print("Пользователь отменил ввод пароля")
                return None

        except Exception as e:
            print(f"Ошибка при получении sudo пароля: {e}")
            import traceback
            traceback.print_exc()
            return None

    def run_with_sudo(self, command, password, description=""):
        """Выполняет команду с sudo"""
        try:
            if description:
                print(f"Выполнение: {description}")

            # Добавляем sudo в начало команды
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

    def stop_and_remove_zapret(self, password, progress_callback=None):
        """Останавливает и удаляет старую версию zapret"""
        commands = [
            (['steamos-readonly', 'disable'], "Отключение защиты SteamOS"),
            (['systemctl', 'stop', 'zapret'], "Остановка службы zapret"),
            (['systemctl', 'disable', 'zapret'], "Отключение автозапуска"),
            (['rm', '-f', '/usr/lib/systemd/system/zapret.service'], "Удаление файла службы"),
            (['rm', '-rf', '/opt/zapret/'], "Удаление директории zapret")
        ]

        for cmd, description in commands:
            if progress_callback:
                progress_callback(description, None)

            result = self.run_with_sudo(cmd, password, description)
            if result['returncode'] != 0:
                print(f"Предупреждение при {description}: {result['stderr']}")

        return True

    def download_archive(self, download_url, temp_dir, password, progress_callback=None):
        """Скачивает архив zapret"""
        try:
            # Создаем временный файл для архива
            archive_path = os.path.join(temp_dir, "zapret.tar.gz")

            if progress_callback:
                progress_callback("Скачивание архива Zapret...", 10)

            # Скачиваем через curl
            result = self.run_with_sudo(
                ['curl', '-L', '-o', archive_path, download_url],
                "Скачивание архива Zapret...",
                password
            )

            if not result or result['returncode'] != 0:
                print(f"Ошибка скачивания: {result['stderr'] if result else 'No result'}")
                return None

            # Проверяем, что архив существует и не пустой
            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                print("Скачанный архив пустой или не существует")
                return None

            if progress_callback:
                progress_callback("Архив успешно скачан", 20)

            return archive_path

        except Exception as e:
            print(f"Ошибка при скачивании архива: {e}")
            return None

    def extract_archive(self, archive_path, temp_dir, password, progress_callback=None):
        """Извлекает архив zapret"""
        try:
            if progress_callback:
                progress_callback("Извлечение архива...", 30)

            extract_dir = os.path.join(temp_dir, "zapret_extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Извлекаем архив
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=extract_dir)

            if progress_callback:
                progress_callback("Архив успешно извлечен", 40)

            return extract_dir

        except Exception as e:
            print(f"Ошибка при извлечении архива: {e}")
            return None

    def copy_zapret_files(self, extract_dir, password, progress_callback=None):
        """Копирует файлы zapret в /opt/zapret"""
        try:
            # Создаем директорию /opt/zapret если не существует
            if progress_callback:
                progress_callback("Создание директории /opt/zapret...", 50)

            result = self.run_with_sudo(
                ['mkdir', '-p', '/opt/zapret'],
                password,
                "Создание директории /opt/zapret..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось создать /opt/zapret")
                return False

            # Ищем папку system в распакованном архиве
            system_dir = None
            for root, dirs, files in os.walk(extract_dir):
                if 'system' in dirs:
                    system_dir = os.path.join(root, 'system')
                    break

            if not system_dir:
                print("Не найдена папка 'system' в архиве")
                return False

            # Копируем файлы из system в /opt/zapret
            if progress_callback:
                progress_callback("Копирование файлов системы...", 60)

            # Копируем все файлы из system
            for item in os.listdir(system_dir):
                src = os.path.join(system_dir, item)
                dst = os.path.join('/opt/zapret', item)

                if os.path.isfile(src):
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

            # Копируем бинарный файл nfqws для текущей архитектуры
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
                # Ищем папку bins
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
                        if result and result['returncode'] == 0:
                            self.run_with_sudo(['chmod', '+x', '/opt/zapret/nfqws'], password)

            # Создаем файл FWTYPE
            if progress_callback:
                progress_callback("Настройка параметров...", 75)

            result = self.run_with_sudo(
                ['bash', '-c', 'echo "iptables" > /opt/zapret/FWTYPE'],
                password,
                "Создание файла FWTYPE..."
            )

            # Устанавливаем права на файлы
            self.run_with_sudo(['chmod', '-R', 'o+r', '/opt/zapret/'], password)

            return True

        except Exception as e:
            print(f"Ошибка при копировании файлов: {e}")
            return False

    def update_manager_config(self, extract_dir):
        """Обновляет файл конфигурации менеджера"""
        try:
            # Ищем файл manager_config.py в архиве
            config_path = None

            for root, dirs, files in os.walk(extract_dir):
                if 'manager_config.py' in files:
                    config_path = os.path.join(root, 'manager_config.py')
                    break

            if not config_path:
                print("Файл manager_config.py не найден в архиве")
                return

            # Целевой путь
            target_path = "/home/deck/Zapret_DPI_Manager/core/manager_config.py"

            # Копируем файл
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
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

            # Создаем временный файл
            temp_service = tempfile.NamedTemporaryFile(mode='w', delete=False)
            temp_service.write(service_content)
            temp_service.close()

            # Копируем в системную директорию
            result = self.run_with_sudo(
                ['cp', temp_service.name, '/usr/lib/systemd/system/zapret.service'],
                password,
                "Копирование файла службы..."
            )

            # Удаляем временный файл
            os.unlink(temp_service.name)

            if not result or result['returncode'] != 0:
                print("Не удалось создать службу")
                return False

            # Устанавливаем права
            self.run_with_sudo(['chmod', '644', '/usr/lib/systemd/system/zapret.service'], password)

            return True

        except Exception as e:
            print(f"Ошибка при создании службы: {e}")
            return False

    def enable_service(self, password, progress_callback=None):
        """Включает и запускает службу"""
        try:
            if progress_callback:
                progress_callback("Обновление systemd...", 85)

            # Обновляем systemd
            result = self.run_with_sudo(
                ['systemctl', 'daemon-reload'],
                password,
                "Обновление systemd..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось обновить systemd")
                return False

            # Включаем автозапуск
            if progress_callback:
                progress_callback("Включение автозапуска...", 90)

            result = self.run_with_sudo(
                ['systemctl', 'enable', 'zapret.service'],
                password,
                "Включение автозапуска службы..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось включить автозапуск")
                # Продолжаем, даже если не удалось включить автозапуск

            # Запускаем службу
            if progress_callback:
                progress_callback("Запуск службы...", 95)

            result = self.run_with_sudo(
                ['systemctl', 'start', 'zapret.service'],
                password,
                "Запуск службы Zapret..."
            )

            if progress_callback:
                progress_callback("Служба успешно запущена", 100)

            # Проверяем статус
            time.sleep(2)
            check_result = self.run_with_sudo(
                ['systemctl', 'is-active', 'zapret'],
                password,
                "Проверка статуса службы..."
            )

            return True

        except Exception as e:
            print(f"Ошибка при включении службы: {e}")
            return False

    def update_zapret(self, download_url, parent_window, progress_callback=None):
        """Выполняет обновление zapret службы"""
        password = self.get_sudo_password(parent_window)
        if not password:
            if progress_callback:
                progress_callback("❌ Пароль не введен, отмена обновления", None)
            return False

        try:
            # Останавливаем и удаляем старую версию
            if not self.stop_and_remove_zapret(password, progress_callback):
                return False

            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp()

            # Скачиваем архив
            archive_path = self.download_archive(download_url, temp_dir, password, progress_callback)
            if not archive_path:
                shutil.rmtree(temp_dir)
                return False

            # Распаковываем архив
            extract_dir = self.extract_archive(archive_path, temp_dir, password, progress_callback)
            if not extract_dir:
                shutil.rmtree(temp_dir)
                return False

            # Копируем файлы
            if not self.copy_zapret_files(extract_dir, password, progress_callback):
                shutil.rmtree(temp_dir)
                return False

            # Обновляем файл конфигурации менеджера
            self.update_manager_config(extract_dir)

            # Создаем службу
            if not self.create_service_file(password, progress_callback):
                shutil.rmtree(temp_dir)
                return False

            # Включаем и запускаем службу
            if not self.enable_service(password, progress_callback):
                shutil.rmtree(temp_dir)
                return False

            # Включаем защиту SteamOS
            self.run_with_sudo(['steamos-readonly', 'enable'], password, "Включение защиты SteamOS...")

            # Очищаем временные файлы
            shutil.rmtree(temp_dir)

            return True

        except Exception as e:
            print(f"Ошибка обновления zapret: {e}")
            import traceback
            traceback.print_exc()
            return False
