#!/usr/bin/env python3
import subprocess
import tkinter as tk
import os
import sys
import tempfile
import threading
import tarfile
import shutil
import time
from pathlib import Path
from ui.windows.sudo_password_window import SudoPasswordWindow
from core.manager_config import RELEASES_URL
from ui.components.custom_messagebox import show_info as custom_show_info
from tkinter import messagebox

class ZapretChecker:
    def __init__(self, root_window=None):
        self.root = root_window
        self.progress_window = None
        self.current_task = ""
        self.sudo_password = None
        self.debug_log = []  # Лог для дебага
        self.last_command_result = None  # Результат последней команды

        # Из manager_config.py

        self.zapret_archive_url = f"{RELEASES_URL}/zapret.tar.gz"

    def log_debug(self, message):
        """Добавляет сообщение в лог дебага"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.debug_log.append(log_msg)
        print(log_msg)

    def is_zapret_installed(self):
        """Проверяет, установлен ли zapret"""
        # Проверяем наличие папки /opt/zapret
        zapret_dir_exists = os.path.exists("/opt/zapret")

        # Проверяем наличие службы
        service_exists = os.path.exists("/usr/lib/systemd/system/zapret.service")

        return zapret_dir_exists and service_exists

    def is_zapret_running(self):
        """Проверяет, запущена ли служба zapret"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and result.stdout.strip() == "active"
        except:
            return False

    def show_info(self, title, message):
        """Показывает информационное сообщение"""
        if self.root and self.root.winfo_exists():
            try:

                custom_show_info(self.root, title, message)
            except ImportError:
                messagebox.showinfo(title, message, parent=self.root)
        else:
            print(f"{title}: {message}")

    def create_progress_window(self, title="Установка Zapret"):
        """Создает окно прогресса"""
        if not self.root:
            return None

        progress_window = tk.Toplevel(self.root)
        progress_window.title(title)
        progress_window.geometry("400x180")
        progress_window.configure(bg='#182030')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)

        # Центрируем окно
        progress_window.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - (400 // 2)
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - (180 // 2)

        # Основной фрейм
        main_frame = tk.Frame(progress_window, bg='#182030', padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text=title,
            font=("Arial", 14, "bold"),
            fg='#0a84ff',
            bg='#182030'
        )
        title_label.pack(pady=(0, 15))

        # Текущая задача
        self.task_label = tk.Label(
            main_frame,
            text="Подготовка к установке...",
            font=("Arial", 11),
            fg='white',
            bg='#182030',
            wraplength=340
        )
        self.task_label.pack(pady=(0, 10))

        # Прогресс-бар
        progress_frame = tk.Frame(main_frame, bg='#182030')
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        # Фон прогресс-бара
        self.progress_bg = tk.Frame(
            progress_frame,
            bg='#15354D',
            height=12,
            relief=tk.FLAT
        )
        self.progress_bg.pack(fill=tk.X)

        # Сам прогресс-бар
        self.progress_bar = tk.Frame(
            self.progress_bg,
            bg='#0a84ff',
            height=12,
            width=0
        )
        self.progress_bar.place(x=0, y=0, relheight=1.0)

        # Процент выполнения
        self.percent_label = tk.Label(
            progress_frame,
            text="0%",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.percent_label.pack(pady=(5, 0))

        progress_window.update()
        return progress_window

    def update_progress(self, task, progress_percent):
        """Обновляет прогресс-бар и текст задачи"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.task_label.config(text=task)

            width = self.progress_bg.winfo_width()
            new_width = int(width * progress_percent / 100)
            self.progress_bar.config(width=new_width)

            self.percent_label.config(text=f"{int(progress_percent)}%")
            self.progress_window.update()

    def close_progress_window(self):
        """Закрывает окно прогресса"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.progress_window.destroy()
            self.progress_window = None

    def get_sudo_password(self):
        """Запрашивает sudo пароль у пользователя"""
        try:
            password_window = SudoPasswordWindow(
                self.root,
                on_password_valid=lambda pwd: self.set_sudo_password(pwd)
            )
            password = password_window.run()

            if password:
                self.sudo_password = password
                return True
            else:
                return False

        except ImportError as e:
            print(f"Ошибка импорта SudoPasswordWindow: {e}")
            self.show_info("Ошибка",
                         "Не удалось загрузить модуль запроса пароля.\nУстановка Zapret невозможна.")
            return False
        except Exception as e:
            print(f"Ошибка при запросе пароля: {e}")
            return False

    def set_sudo_password(self, password):
        """Сохраняет sudo пароль"""
        self.sudo_password = password

    def run_with_sudo(self, command, task_name=""):
        """Выполняет команду с sudo паролем"""
        if not self.sudo_password:
            return None

        # Обновляем задачу если есть окно прогресса
        if task_name and self.progress_window:
            self.update_progress(task_name, self.get_current_progress())

        try:
            process = subprocess.Popen(
                ['sudo', '-S'] + command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=self.sudo_password + '\n')

            return {
                'returncode': process.returncode,
                'stdout': stdout,
                'stderr': stderr
            }

        except Exception as e:
            print(f"Ошибка выполнения команды с sudo: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e)
            }

    def get_current_progress(self):
        """Рассчитывает текущий прогресс на основе этапа"""
        if self.current_task == "download":
            return 20
        elif self.current_task == "extract":
            return 40
        elif self.current_task == "copy_files":
            return 60
        elif self.current_task == "create_service":
            return 80
        elif self.current_task == "enable_service":
            return 90
        else:
            return 0

    def download_archive(self, temp_dir):
        """Скачивает архив zapret"""
        self.current_task = "download"

        try:
            # Создаем временный файл для архива
            archive_path = os.path.join(temp_dir, "zapret.tar.gz")

            # Скачиваем через curl
            self.update_progress("Скачивание архива Zapret...", 10)
            result = self.run_with_sudo(
                ['curl', '-L', '-o', archive_path, self.zapret_archive_url],
                "Скачивание архива Zapret..."
            )

            if not result or result['returncode'] != 0:
                print(f"Ошибка скачивания: {result['stderr'] if result else 'No result'}")
                return None

            # Проверяем, что архив существует и не пустой
            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                print("Скачанный архив пустой или не существует")
                return None

            self.update_progress("Архив успешно скачан", 20)
            return archive_path

        except Exception as e:
            print(f"Ошибка при скачивании архива: {e}")
            return None

    def extract_archive(self, archive_path, temp_dir):
        """Извлекает архив zapret"""
        self.current_task = "extract"

        try:
            self.update_progress("Извлечение архива...", 30)

            extract_dir = os.path.join(temp_dir, "zapret_extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Извлекаем архив
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=extract_dir)

            self.update_progress("Архив успешно извлечен", 40)
            return extract_dir

        except Exception as e:
            print(f"Ошибка при извлечении архива: {e}")
            return None

    def copy_zapret_files(self, extract_dir):
        """Копирует файлы zapret в /opt/zapret"""
        self.current_task = "copy_files"

        try:
            # Создаем директорию /opt/zapret если не существует
            self.update_progress("Создание директории /opt/zapret...", 50)

            result = self.run_with_sudo(
                ['mkdir', '-p', '/opt/zapret'],
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
            self.update_progress("Копирование файлов системы...", 60)

            # Копируем все файлы из system
            for item in os.listdir(system_dir):
                src = os.path.join(system_dir, item)
                dst = os.path.join('/opt/zapret', item)

                if os.path.isfile(src):
                    result = self.run_with_sudo(
                        ['cp', src, dst],
                        f"Копирование {item}..."
                    )
                elif os.path.isdir(src):
                    result = self.run_with_sudo(
                        ['cp', '-r', src, dst],
                        f"Копирование папки {item}..."
                    )

                if not result or result['returncode'] != 0:
                    print(f"Не удалось скопировать {item}")

            # Копируем бинарный файл nfqws для текущей архитектуры
            self.update_progress("Копирование бинарных файлов...", 70)

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
                            "Копирование бинарного файла nfqws..."
                        )
                        if result and result['returncode'] == 0:
                            self.run_with_sudo(['chmod', '+x', '/opt/zapret/nfqws'])

            # Создаем файл FWTYPE
            self.update_progress("Настройка параметров...", 75)
            result = self.run_with_sudo(
                ['bash', '-c', 'echo "iptables" > /opt/zapret/FWTYPE'],
                "Создание файла FWTYPE..."
            )

            # Устанавливаем права на файлы
            self.run_with_sudo(['chmod', '-R', 'o+r', '/opt/zapret/'])

            return True

        except Exception as e:
            print(f"Ошибка при копировании файлов: {e}")
            return False

    def create_service_file(self):
        """Создает файл службы systemd"""
        self.current_task = "create_service"

        try:
            self.update_progress("Создание службы systemd...", 80)

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
                "Копирование файла службы..."
            )

            # Удаляем временный файл
            os.unlink(temp_service.name)

            if not result or result['returncode'] != 0:
                print("Не удалось создать службу")
                return False

            # Устанавливаем права
            self.run_with_sudo(['chmod', '644', '/usr/lib/systemd/system/zapret.service'])

            return True

        except Exception as e:
            print(f"Ошибка при создании службы: {e}")
            return False

    def enable_service(self):
        """Включает и запускает службу"""
        self.current_task = "enable_service"

        try:
            self.update_progress("Обновление systemd...", 85)

            # Обновляем systemd
            result = self.run_with_sudo(
                ['systemctl', 'daemon-reload'],
                "Обновление systemd..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось обновить systemd")
                return False

            # Включаем автозапуск
            self.update_progress("Включение автозапуска...", 90)
            result = self.run_with_sudo(
                ['systemctl', 'enable', 'zapret.service'],
                "Включение автозапуска службы..."
            )

            if not result or result['returncode'] != 0:
                print("Не удалось включить автозапуск")
                # Продолжаем, даже если не удалось включить автозапуск

            # Запускаем службу
            self.update_progress("Запуск службы...", 95)
            result = self.run_with_sudo(
                ['systemctl', 'start', 'zapret.service'],
                "Запуск службы Zapret..."
            )

            self.update_progress("Служба успешно запущена", 100)

            # Проверяем статус
            time.sleep(2)
            check_result = self.run_with_sudo(
                ['systemctl', 'is-active', 'zapret'],
                "Проверка статуса службы..."
            )

            return True

        except Exception as e:
            print(f"Ошибка при включении службы: {e}")
            return False

    def unlock_readonly_system(self):
        """Разблокирует систему SteamOS"""
        self.current_task = "unlock"
        self.log_debug("Разблокировка файловой системы SteamOS...")

        result = self.run_with_sudo(
            ['steamos-readonly', 'disable'],
            "Разблокировка системы SteamOS..."
        )

        if not result or result['returncode'] != 0:
            self.log_debug(f"Ошибка разблокировки: {result['stderr'] if result else 'No result'}")
            return False

        self.log_debug("Система успешно разблокирована")
        return True

    def lock_readonly_system(self):
        """Блокирует систему SteamOS"""
        self.current_task = "lock"
        self.log_debug("Блокировка файловой системы SteamOS...")

        result = self.run_with_sudo(
            ['steamos-readonly', 'enable'],
            "Блокировка системы SteamOS..."
        )

        if not result or result['returncode'] != 0:
            self.log_debug(f"Предупреждение: Не удалось заблокировать систему: {result['stderr'] if result else 'No result'}")
            # Все равно продолжаем, но логируем предупреждение
            return True  # Возвращаем True, чтобы не прерывать процесс

        self.log_debug("Система успешно заблокирована")
        return True

    def install_zapret(self):
        """Основная функция установки zapret"""
        self.log_debug("=== НАЧАЛО УСТАНОВКИ ZAPRET ===")

        if self.root:
            self.root.update()

        # Запрашиваем sudo пароль
        if not self.get_sudo_password():
            self.log_debug("Не получен sudo пароль, отмена установки")
            self.show_info("Отмена установки",
                         "Для установки Zapret требуется sudo пароль.\n"
                         "Установка отменена.")
            return False

        # Создаем окно прогресса
        if self.root:
            self.progress_window = self.create_progress_window("Установка Zapret")
            if not self.progress_window:
                self.log_debug("Не удалось создать окно прогресса")
            self.update_progress("Начало установки...", 0)

        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp(prefix="zapret_install_")
        self.log_debug(f"Временная директория: {temp_dir}")

        try:
            # 0. Разблокируем файловую систему SteamOS
            self.update_progress("Разблокировка системы...", 5)
            if not self.unlock_readonly_system():
                self.log_debug("Не удалось разблокировать систему")
                self.close_progress_window()
                self.show_info("Ошибка разблокировки",
                             "Не удалось разблокировать файловую систему SteamOS.\n"
                             "Установка Zapret невозможна.")
                return False

            # 1. Скачиваем архив
            self.update_progress("Скачивание архива Zapret...", 10)
            archive_path = self.download_archive(temp_dir)

            if not archive_path:
                self.log_debug("Не удалось скачать архив")
                # Пытаемся заблокировать систему перед выходом
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info("Ошибка скачивания",
                             "Не удалось скачать архив Zapret.\n"
                             "Проверьте подключение к интернету и URL:\n"
                             f"{self.zapret_archive_url}")
                return False

            # 2. Извлекаем архив
            self.update_progress("Извлечение архива...", 30)
            extract_dir = self.extract_archive(archive_path, temp_dir)

            if not extract_dir:
                self.log_debug("Не удалось извлечь архив")
                # Пытаемся заблокировать систему перед выходом
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info("Ошибка извлечения",
                             "Не удалось извлечь архив Zapret.\n"
                             "Архив может быть поврежден или иметь неправильный формат.")
                return False

            # 3. Копируем файлы
            self.update_progress("Копирование файлов системы...", 50)
            if not self.copy_zapret_files(extract_dir):
                self.log_debug("Не удалось скопировать файлы")
                # Пытаемся заблокировать систему перед выходом
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info("Ошибка копирования",
                             "Не удалось скопировать файлы Zapret.\n"
                             "Проверьте права доступа к /opt/zapret.")
                return False

            # 4. Создаем службу
            self.update_progress("Создание службы systemd...", 70)
            if not self.create_service_file():
                self.log_debug("Не удалось создать службу")
                # Пытаемся заблокировать систему перед выходом
                self.lock_readonly_system()
                self.close_progress_window()

                # Показываем подробную информацию об ошибке
                error_details = "\n".join(self.debug_log[-20:])  # Последние 20 строк лога
                self.show_info("Ошибка создания службы",
                             "Не удалось создать службу systemd.\n\n"
                             "Лог ошибки:\n"
                             f"{error_details}\n\n"
                             "Проверьте:\n"
                             "1. Права доступа к /usr/lib/systemd/system/\n"
                             "2. Достаточно ли места на диске\n"
                             "3. Не заблокирована ли система")
                return False

            # 5. Включаем службу
            self.update_progress("Запуск службы Zapret...", 90)
            if not self.enable_service():
                self.log_debug("Проблемы при запуске службы")
                # Блокируем систему даже при проблемах с запуском службы
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info("Предупреждение",
                             "Zapret установлен, но возникли проблемы при запуске службы.\n\n"
                             "Лог установки:\n"
                             f"{'\\n'.join(self.debug_log[-15:])}\n\n"
                             "Попробуйте запустить вручную:\n"
                             "sudo systemctl start zapret")
                return True  # Все равно считаем успешной установку

            # 6. Блокируем файловую систему SteamOS обратно
            self.update_progress("Блокировка системы...", 95)
            self.lock_readonly_system()

            # Закрываем окно прогресса
            if self.progress_window:
                self.close_progress_window()

            self.log_debug("=== УСТАНОВКА ZAPRET УСПЕШНО ЗАВЕРШЕНА ===")
            self.show_info("Успешная установка",
                         "Zapret успешно установлен и запущен!\n"
                         "Служба добавлена в автозагрузку.\n\n"
                         "Статус: активен" if self.is_zapret_running() else "Статус: требует ручного запуска")
            return True

        except Exception as e:
            self.log_debug(f"Критическая ошибка установки Zapret: {e}")
            import traceback
            error_trace = traceback.format_exc()
            self.log_debug(f"Трейс ошибки: {error_trace}")

            # Пытаемся заблокировать систему даже при ошибке
            try:
                self.lock_readonly_system()
            except:
                pass

            if self.progress_window:
                self.close_progress_window()

            # Показываем детальную информацию об ошибке
            error_log = "\n".join(self.debug_log[-30:])  # Последние 30 строк лога
            self.show_info("Ошибка установки",
                         f"Произошла ошибка при установке Zapret:\n\n"
                         f"Ошибка: {str(e)}\n\n"
                         f"Лог установки:\n{error_log}")
            return False

        finally:
            # Очищаем временную директорию
            try:
                self.log_debug(f"Очистка временной директории: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log_debug(f"Ошибка очистки временной директории: {e}")

    def check_and_install_zapret(self):
        """Проверяет и устанавливает zapret при необходимости"""
        # Проверяем, установлен ли уже zapret
        if self.is_zapret_installed():
            print("Zapret уже установлен")
            return True

        # Показываем информацию о необходимости установки
        self.show_info("Установка Zapret",
                     "Для работы программы требуется установить службу Zapret.\n\n"
                     "Сейчас будет произведена её автоматическая установка.")

        # Устанавливаем zapret
        return self.install_zapret()

def run_zapret_check(root_window=None):
    """
    Запускает проверку и установку zapret при старте программы
    """
    checker = ZapretChecker(root_window)
    return checker.check_and_install_zapret()

if __name__ == "__main__":
    test_checker = ZapretChecker()
    result = test_checker.check_and_install_zapret()

    if result:
        print("Zapret установлен успешно")
    else:
        print("Установка Zapret завершена с ошибками")
