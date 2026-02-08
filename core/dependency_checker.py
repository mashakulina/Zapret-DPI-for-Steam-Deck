#!/usr/bin/env python3
import subprocess
import tkinter as tk
import os
import sys
import time
import shutil
import tempfile
from ui.components.custom_messagebox import show_info as custom_show_info
from ui.windows.sudo_password_window import SudoPasswordWindow
from tkinter import messagebox

class DependencyChecker:
    def __init__(self, root_window=None):
        self.root = root_window
        self.dependencies = ['curl', 'nft']
        self.sudo_password = None
        self.progress_window = None
        self.current_task = ""
        self.debug_log = []  # Лог для дебага
        self.last_command_result = None  # Результат последней команды
        self.is_steamos = self.check_if_steamos()  # Проверяем систему
        self.log_debug(f"Система определена как: {'SteamOS' if self.is_steamos else 'другая ОС'}")

    def check_if_steamos(self):
        """Проверяет, является ли система SteamOS"""
        self.log_debug("Проверка системы на SteamOS...")

        # Способ 1: Проверка по наличию команды steamos-readonly
        try:
            result = subprocess.run(['which', 'steamos-readonly'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.log_debug("Найдена команда steamos-readonly")
                return True
        except:
            pass

        # Способ 2: Проверка по релизу системы
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'steamos' in content or 'steamdeck' in content:
                    self.log_debug("Обнаружен SteamOS в /etc/os-release")
                    return True
        except:
            pass

        # Способ 3: Проверка по другим признакам
        try:
            if os.path.exists('/home/deck'):
                self.log_debug("Обнаружен пользователь deck")
                return True
        except:
            pass

        self.log_debug("Система не является SteamOS")
        return False

    def log_debug(self, message):
        """Добавляет сообщение в лог дебага"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.debug_log.append(log_msg)
        print(log_msg)

    def is_package_installed(self, package_name):
        """Проверяет, установлен ли пакет"""
        self.log_debug(f"Проверка установки пакета: {package_name}")
        try:
            if package_name == 'curl':
                result = subprocess.run(['curl', '--version'],
                                      capture_output=True, text=True)
                self.log_debug(f"curl --version: код={result.returncode}, вывод={result.stdout[:100]}...")
            else:
                result = subprocess.run(['which', package_name],
                                      capture_output=True, text=True)
                self.log_debug(f"which {package_name}: код={result.returncode}, вывод={result.stdout.strip()}")

            installed = result.returncode == 0
            self.log_debug(f"Пакет {package_name} установлен: {installed}")
            return installed
        except Exception as e:
            self.log_debug(f"Ошибка проверки пакета {package_name}: {e}")
            return False

    def show_info(self, title, message):
        """Показывает информационное сообщение через кастомное окно"""
        self.log_debug(f"show_info: {title} - {message}")
        if self.root and self.root.winfo_exists():
            try:
                custom_show_info(self.root, title, message)
            except ImportError as e:
                self.log_debug(f"Ошибка импорта кастомного messagebox: {e}")
                messagebox.showinfo(title, message, parent=self.root)
        else:
            print(f"{title}: {message}")

    def create_progress_window(self, title="Установка зависимостей"):
        """Создает окно прогресса в стиле приложения"""
        if not self.root:
            self.log_debug("Нет root окна для создания прогресса")
            return None

        self.log_debug(f"Создание окна прогресса: {title}")
        try:
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

            # Прогресс-бар в стиле приложения
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

            # Сам прогресс-бар (синяя часть)
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

            # Обновляем окно
            progress_window.update()
            self.log_debug("Окно прогресса создано успешно")
            return progress_window

        except Exception as e:
            self.log_debug(f"Ошибка создания окна прогресса: {e}")
            return None

    def update_progress(self, task, progress_percent):
        """Обновляет прогресс-бар и текст задачи"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.log_debug(f"Обновление прогресса: {task} - {progress_percent}%")
            # Обновляем текст задачи
            self.task_label.config(text=task)

            # Обновляем прогресс-бар
            width = self.progress_bg.winfo_width()
            new_width = int(width * progress_percent / 100)
            self.progress_bar.config(width=new_width)

            # Обновляем процент
            self.percent_label.config(text=f"{int(progress_percent)}%")

            # Обновляем окно
            self.progress_window.update()
        else:
            self.log_debug(f"Невозможно обновить прогресс: окно не существует")

    def close_progress_window(self):
        """Закрывает окно прогресса"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.log_debug("Закрытие окна прогресса")
            self.progress_window.destroy()
            self.progress_window = None
        else:
            self.log_debug("Окно прогресса уже закрыто")

    def get_sudo_password(self):
        """Запрашивает sudo пароль у пользователя"""
        self.log_debug("Запрос sudo пароля...")
        try:
            password_window = SudoPasswordWindow(
                self.root,
                on_password_valid=lambda pwd: self.set_sudo_password(pwd)
            )

            password = password_window.run()

            if password:
                self.sudo_password = password
                self.log_debug("Sudo пароль получен (длина: {})".format(len(password)))
                return True
            else:
                self.log_debug("Пользователь отменил ввод пароля")
                return False

        except ImportError as e:
            self.log_debug(f"Ошибка импорта SudoPasswordWindow: {e}")
            self.show_info("Ошибка",
                         "Не удалось загрузить модуль запроса пароля.\nУстановка зависимостей невозможна.")
            return False
        except Exception as e:
            self.log_debug(f"Ошибка при запросе пароля: {e}")
            return False

    def set_sudo_password(self, password):
        """Сохраняет sudo пароль"""
        self.sudo_password = password
        self.log_debug("Sudo пароль установлен")

    def run_with_sudo(self, command, task_name=""):
        """Выполняет команду с sudo паролем"""
        if not self.sudo_password:
            self.log_debug(f"Нет sudo пароля для команды: {' '.join(command)}")
            return None

        # Обновляем задачу если есть окно прогресса
        if task_name and self.progress_window:
            self.update_progress(task_name, self.get_current_progress())

        self.log_debug(f"Выполнение команды: sudo {' '.join(command)}")

        try:
            process = subprocess.Popen(
                ['sudo', '-S'] + command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            stdout, stderr = process.communicate(input=self.sudo_password + '\n')

            self.log_debug(f"Результат команды: код={process.returncode}")
            if stdout:
                self.log_debug(f"stdout: {stdout[:200]}...")
            if stderr:
                self.log_debug(f"stderr: {stderr[:200]}...")

            self.last_command_result = {
                'returncode': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'command': ' '.join(command)
            }

            return self.last_command_result

        except Exception as e:
            self.log_debug(f"Ошибка выполнения команды с sudo: {e}")
            self.last_command_result = {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(command)
            }
            return self.last_command_result

    def get_current_progress(self):
        """Рассчитывает текущий прогресс на основе этапа"""
        # Разные значения прогресса для SteamOS и других ОС
        if self.is_steamos:
            progress_map = {
                "unlock": 10,
                "pacman": 20,
                "db_lock_check": 25,
                "keys": 30,
                "install": 60,
                "download": 70,
                "local_install": 80,
                "lock": 90
            }
        else:
            progress_map = {
                "install": 60,
                "download": 70,
                "local_install": 80
            }

        progress = progress_map.get(self.current_task, 0)
        self.log_debug(f"Текущая задача: {self.current_task}, прогресс: {progress}")
        return progress

    def remove_pacman_db_lock(self):
        """Удаляет блокировочные файлы базы данных pacman (только для SteamOS)"""
        if not self.is_steamos:
            self.log_debug("Пропускаем удаление блокировочных файлов: система не SteamOS")
            return True

        self.current_task = "db_lock_check"
        self.log_debug("Проверка и удаление блокировочных файлов pacman...")

        lock_files = [
            '/usr/lib/holo/pacmandb/db.lck',
            '/var/lib/pacman/db.lck',
            '/var/lib/pacman/db.lck.lock'
        ]

        for lock_file in lock_files:
            try:
                # Проверяем существование файла
                self.log_debug(f"Проверка существования файла: {lock_file}")
                check_result = self.run_with_sudo(['ls', '-la', lock_file],
                                                f"Проверка блокировочного файла: {lock_file}")

                if check_result and check_result['returncode'] == 0:
                    self.log_debug(f"Блокировочный файл найден: {lock_file}")

                    # Удаляем файл
                    self.log_debug(f"Удаление блокировочного файла: {lock_file}")
                    delete_result = self.run_with_sudo(['rm', '-f', lock_file],
                                                      f"Удаление блокировочного файла: {lock_file}")

                    if delete_result and delete_result['returncode'] == 0:
                        self.log_debug(f"Блокировочный файл успешно удален: {lock_file}")
                    else:
                        self.log_debug(f"Не удалось удалить блокировочный файл: {lock_file}")
                        if delete_result:
                            self.log_debug(f"Ошибка удаления: {delete_result['stderr']}")
                else:
                    self.log_debug(f"Блокировочный файл не найден: {lock_file}")

            except Exception as e:
                self.log_debug(f"Ошибка при работе с блокировочным файлом {lock_file}: {e}")
                # Продолжаем проверку других файлов

        self.log_debug("Проверка блокировочных файлов завершена")
        return True

    def unlock_readonly_system(self):
        """Разблокирует систему SteamOS (только для SteamOS)"""
        if not self.is_steamos:
            self.log_debug("Пропускаем разблокировку: система не SteamOS")
            return True

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
        """Блокирует систему SteamOS (только для SteamOS)"""
        if not self.is_steamos:
            self.log_debug("Пропускаем блокировку: система не SteamOS")
            return True

        self.current_task = "lock"
        self.log_debug("Блокировка файловой системы SteamOS...")

        result = self.run_with_sudo(
            ['steamos-readonly', 'enable'],
            "Блокировка системы SteamOS..."
        )

        if not result or result['returncode'] != 0:
            self.log_debug(f"Предупреждение: Не удалось заблокировать систему: {result['stderr'] if result else 'No result'}")
            return True  # Возвращаем True, чтобы не прерывать процесс

        self.log_debug("Система успешно заблокирована")
        return True

    def fix_pacman_conf(self):
        """Модифицирует pacman.conf (для всех ОС, использующих pacman)"""
        self.current_task = "pacman"
        self.log_debug("Модификация pacman.conf...")

        try:
            # Проверяем существование файла
            self.log_debug("Проверка существования /etc/pacman.conf")
            check_result = self.run_with_sudo(['ls', '-la', '/etc/pacman.conf'])

            if check_result and check_result['returncode'] == 0:
                self.log_debug(f"Файл pacman.conf существует: {check_result['stdout']}")
            else:
                self.log_debug("Файл pacman.conf не найден, возможно используется другой пакетный менеджер")
                return True  # Возвращаем True, если pacman не используется

            # Резервная копия
            self.log_debug("Создание резервной копии pacman.conf...")
            result = self.run_with_sudo(
                ['cp', '/etc/pacman.conf', '/etc/pacman.conf.backup'],
                "Создание резервной копии pacman.conf..."
            )

            if not result or result['returncode'] != 0:
                self.log_debug(f"Ошибка создания резервной копии: {result['stderr'] if result else 'No result'}")
                return False

            # Модификация
            self.log_debug("Модификация pacman.conf...")
            result = self.run_with_sudo([
                'sed', '-i',
                's/Required DatabaseOptional/TrustAll/g',
                '/etc/pacman.conf'
            ], "Модификация pacman.conf...")

            if not result or result['returncode'] != 0:
                self.log_debug(f"Не удалось модифицировать pacman.conf: {result['stderr'] if result else 'No result'}")
                return False

            # Проверяем изменения
            self.log_debug("Проверка изменений в pacman.conf...")
            check_changes = self.run_with_sudo(['grep', '-n', 'TrustAll', '/etc/pacman.conf'])
            if check_changes and check_changes['returncode'] == 0:
                self.log_debug(f"Изменения применены: {check_changes['stdout']}")
            else:
                self.log_debug("Изменения не найдены в файле")

            self.log_debug("pacman.conf успешно модифицирован")
            return True

        except Exception as e:
            self.log_debug(f"Ошибка модификации pacman.conf: {e}")
            import traceback
            traceback.print_exc()
            return False

    def init_pacman_keys(self):
        """Инициализирует ключи pacman (для всех ОС, использующих pacman)"""
        self.current_task = "keys"
        self.log_debug("Инициализация ключей pacman...")

        try:
            # Проверяем существование pacman-key
            self.log_debug("Проверка наличия pacman-key...")
            check_key = self.run_with_sudo(['which', 'pacman-key'])
            if check_key and check_key['returncode'] != 0:
                self.log_debug("pacman-key не найден, возможно используется другой пакетный менеджер")
                return True  # Возвращаем True, если pacman не используется

            # Инициализация ключей
            self.log_debug("Инициализация ключей pacman...")
            result_init = self.run_with_sudo(
                ['pacman-key', '--init'],
                "Инициализация ключей pacman..."
            )

            if not result_init or result_init['returncode'] != 0:
                self.log_debug(f"Ошибка инициализации ключей: {result_init['stderr'] if result_init else 'No result'}")
                return False

            # Заполнение ключей
            self.log_debug("Заполнение ключей pacman...")
            result_populate = self.run_with_sudo(
                ['pacman-key', '--populate'],
                "Заполнение ключей pacman..."
            )

            if not result_populate or result_populate['returncode'] != 0:
                self.log_debug(f"Ошибка заполнения ключей: {result_populate['stderr'] if result_populate else 'No result'}")
                return False

            # Обновление базы
            self.log_debug("Обновление базы пакетов...")
            self.run_with_sudo(
                ['pacman', '-Sy'],
                "Обновление базы пакетов..."
            )

            self.log_debug("Ключи pacman успешно инициализированы")
            return True

        except Exception as e:
            self.log_debug(f"Ошибка инициализации ключей: {e}")
            return False

    def install_dependency_with_fallback(self, package_name, dep_num, total_deps):
        """Устанавливает зависимость с fallback на локальный файл для ipset"""
        self.current_task = "install"
        self.log_debug(f"Установка зависимости: {package_name} ({dep_num}/{total_deps})")

        # Расчет прогресса для этой зависимости
        base_progress = 60
        dep_progress = int(base_progress + (dep_num / total_deps * 40))
        self.log_debug(f"Прогресс для {package_name}: {dep_progress}%")

        try:
            # Обновляем прогресс
            if self.progress_window:
                self.update_progress(
                    f"Установка {package_name}...",
                    dep_progress
                )

            # Определяем пакетный менеджер в зависимости от системы
            if self.is_steamos:
                # Для SteamOS используем pacman
                install_cmd = ['pacman', '-S', '--noconfirm', package_name]
                package_manager = "pacman"
            else:
                # Для других систем определяем пакетный менеджер
                if os.path.exists('/usr/bin/apt'):
                    install_cmd = ['apt', 'install', '-y', package_name]
                    package_manager = "apt"
                elif os.path.exists('/usr/bin/yum'):
                    install_cmd = ['yum', 'install', '-y', package_name]
                    package_manager = "yum"
                elif os.path.exists('/usr/bin/dnf'):
                    install_cmd = ['dnf', 'install', '-y', package_name]
                    package_manager = "dnf"
                elif os.path.exists('/usr/bin/zypper'):
                    install_cmd = ['zypper', '--non-interactive', 'install', package_name]
                    package_manager = "zypper"
                elif os.path.exists('/usr/bin/pacman'):
                    install_cmd = ['pacman', '-S', '--noconfirm', package_name]
                    package_manager = "pacman"
                else:
                    self.log_debug(f"Не удалось определить пакетный менеджер для установки {package_name}")
                    return False

            self.log_debug(f"Используется пакетный менеджер: {package_manager}")
            self.log_debug(f"Запуск установки: {' '.join(install_cmd)}")

            result = self.run_with_sudo(
                install_cmd,
                f"Установка {package_name}..."
            )

            if not result:
                self.log_debug(f"Нет результата от установки {package_name}")
                return False

            if result['returncode'] == 0:
                self.log_debug(f"Пакет {package_name} успешно установлен")
                return True

            # Если ошибка, анализируем ее
            error_msg = result['stderr']
            self.log_debug(f"Ошибка установки {package_name}: код={result['returncode']}, ошибка={error_msg}")

            # Для ipset на SteamOS пробуем fallback методы
            if package_name == 'ipset' and self.is_steamos:
                # Проверяем ошибку блокировки БД
                if self.is_dblock_error(error_msg):
                    self.log_debug("Обнаружена ошибка блокировки БД, повторная попытка после очистки...")

                    # Удаляем блокировочные файлы
                    self.remove_pacman_db_lock()

                    # Повторная попытка установки
                    self.log_debug("Повторная попытка установки после удаления блокировочных файлов...")
                    retry_result = self.run_with_sudo(
                        ['pacman', '-S', '--noconfirm', package_name],
                        f"Повторная установка {package_name}..."
                    )

                    if retry_result and retry_result['returncode'] == 0:
                        self.log_debug(f"Пакет {package_name} успешно установлен после удаления блокировочных файлов")
                        return True

                # Проверяем ошибку таймаута/сети
                if self.is_timeout_error(error_msg):
                    self.log_debug("Обнаружена ошибка таймаута/сети, пробуем скачать с GitHub...")

                    # Скачиваем из GitHub
                    local_package = self.download_ipset_from_github()

                    if local_package:
                        self.log_debug(f"Пакет скачан успешно, устанавливаем из локального файла...")

                        # Устанавливаем из локального файла
                        if self.install_ipset_from_local(local_package):
                            self.log_debug(f"Пакет {package_name} успешно установлен из локального файла")
                            return True
                        else:
                            self.log_debug(f"Не удалось установить {package_name} из локального файла")
                    else:
                        self.log_debug(f"Не удалось скачать {package_name} с GitHub")

            # Для других пакетов или если fallback не сработал
            self.log_debug(f"Не удалось установить {package_name} стандартным способом")
            return False

        except Exception as e:
            self.log_debug(f"Исключение при установке {package_name}: {e}")
            return False

    def download_ipset_from_github(self):
        """Скачивает пакет ipset из GitHub репозитория с помощью curl"""
        self.current_task = "download"
        self.log_debug("Скачивание пакета ipset из GitHub с помощью curl...")

        github_url = "https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/raw/main/ipset-7.23-1-x86_64.pkg.tar.zst"
        temp_dir = tempfile.mkdtemp(prefix="ipset_install_")
        local_file = os.path.join(temp_dir, "ipset-7.23-1-x86_64.pkg.tar.zst")

        try:
            if self.progress_window:
                self.update_progress("Скачивание ipset из GitHub...", 70)

            self.log_debug(f"Создана временная папка: {temp_dir}")
            self.log_debug(f"Скачивание из: {github_url}")
            self.log_debug(f"Сохранение в: {local_file}")

            # Скачиваем файл с помощью curl
            self.log_debug("Запуск curl для скачивания...")

            # Используем curl с параметрами:
            # -L: следовать редиректам
            # -o: указать файл для сохранения
            # --connect-timeout: таймаут соединения 30 секунд
            # --max-time: максимальное время скачивания 300 секунд
            curl_command = [
                'curl', '-L',
                '--connect-timeout', '30',
                '--max-time', '300',
                '-o', local_file,
                github_url
            ]

            self.log_debug(f"Команда curl: {' '.join(curl_command)}")

            result = subprocess.run(
                curl_command,
                capture_output=True,
                text=True,
                timeout=330  # Общий таймаут чуть больше max-time
            )

            if result.returncode == 0:
                # Проверяем скачанный файл
                if os.path.exists(local_file) and os.path.getsize(local_file) > 0:
                    file_size = os.path.getsize(local_file)
                    self.log_debug(f"Файл успешно скачан: {local_file} (размер: {file_size} байт)")
                    return local_file
                else:
                    self.log_debug("Файл создан, но пуст или не существует")
                    return None
            else:
                self.log_debug(f"Ошибка curl: код={result.returncode}")
                self.log_debug(f"stderr: {result.stderr}")
                self.log_debug(f"stdout: {result.stdout}")
                return None

        except subprocess.TimeoutExpired:
            self.log_debug("Таймаут при скачивании через curl")
            return None
        except Exception as e:
            self.log_debug(f"Неожиданная ошибка при скачивании через curl: {e}")
            return None
        finally:
            # Удаляем временную папку если файл не скачан
            if 'local_file' in locals() and (not os.path.exists(local_file) or os.path.getsize(local_file) == 0):
                if os.path.exists(temp_dir):
                    try:
                        shutil.rmtree(temp_dir)
                        self.log_debug(f"Временная папка удалена: {temp_dir}")
                    except:
                        pass

    def install_ipset_from_local(self, package_path):
        """Устанавливает ipset из локального файла пакета"""
        self.current_task = "local_install"
        self.log_debug(f"Установка ipset из локального файла: {package_path}")

        if not package_path or not os.path.exists(package_path):
            self.log_debug(f"Файл пакета не найден: {package_path}")
            return False

        try:
            if self.progress_window:
                self.update_progress("Установка ipset из локального файла...", 80)

            # Устанавливаем пакет из локального файла
            result = self.run_with_sudo(
                ['pacman', '-U', '--noconfirm', package_path],
                "Установка ipset из локального файла..."
            )

            if not result:
                self.log_debug("Нет результата от установки из локального файла")
                return False

            if result['returncode'] == 0:
                self.log_debug("ipset успешно установлен из локального файла")
                return True
            else:
                self.log_debug(f"Ошибка установки из локального файла: код={result['returncode']}, ошибка={result['stderr']}")
                return False

        except Exception as e:
            self.log_debug(f"Исключение при установке из локального файла: {e}")
            return False
        finally:
            # Удаляем временный файл после установки
            temp_dir = os.path.dirname(package_path)
            if os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    self.log_debug(f"Временная папка удалена: {temp_dir}")
                except:
                    pass

    def is_timeout_error(self, stderr):
        """Проверяет, является ли ошибка ошибкой таймаута"""
        timeout_indicators = [
            "Operation too slow",
            "Less than 1 bytes/sec",
            "не удалось получить некоторые файлы",
            "ошибка в библиотеке загрузки"
        ]

        stderr_lower = stderr.lower()
        for indicator in timeout_indicators:
            if indicator.lower() in stderr_lower:
                self.log_debug(f"Обнаружена ошибка таймаута: {indicator}")
                return True
        return False

    def is_dblock_error(self, stderr):
        """Проверяет, связана ли ошибка с блокировкой базы данных"""
        dblock_indicators = [
            "could not lock database",
            "failed to lock database",
            "db.lck",
            "блокировка базы данных"
        ]

        stderr_lower = stderr.lower()
        for indicator in dblock_indicators:
            if indicator in stderr_lower:
                self.log_debug(f"Обнаружена ошибка блокировки БД: {indicator}")
                return True
        return False

    def install_dependency(self, package_name, dep_num, total_deps):
        """Устанавливает одну зависимость (старая версия для обратной совместимости)"""
        return self.install_dependency_with_fallback(package_name, dep_num, total_deps)

    def check_and_install_dependencies(self):
        """Основная функция проверки и установки зависимостей"""
        self.log_debug("=== НАЧАЛО ПРОВЕРКИ ЗАВИСИМОСТЕЙ ===")
        self.log_debug(f"Обнаружена система: {'SteamOS' if self.is_steamos else 'другая ОС'}")

        if self.root:
            self.root.update()

        # Проверяем зависимости
        self.log_debug(f"Проверка зависимостей: {self.dependencies}")
        missing_deps = []
        for dep in self.dependencies:
            if not self.is_package_installed(dep):
                missing_deps.append(dep)

        self.log_debug(f"Отсутствующие зависимости: {missing_deps}")

        if not missing_deps:
            self.log_debug("Все зависимости установлены, проверка завершена")
            return True

        # 1. Показываем информацию об отсутствующих зависимостях
        deps_list = ", ".join(missing_deps)
        self.log_debug(f"Показ информации об отсутствующих зависимостях: {deps_list}")
        self.show_info("Необходимые зависимости",
                     f"Для работы программы требуются следующие зависимости:\n\n"
                     f"{deps_list}\n\n"
                     "Сейчас будет произведена их автоматическая установка.")

        # 2. Запрашиваем sudo пароль (ПОСЛЕ того как пользователь увидел сообщение и нажал OK)
        if not self.get_sudo_password():
            self.log_debug("Не получен sudo пароль, отмена установки")
            self.show_info("Отмена установки",
                         "Для установки зависимостей требуется sudo пароль.\n"
                         "Установка отменена.")
            return False

        # 3. Создаем окно прогресса (ТОЛЬКО ПОСЛЕ ввода пароля)
        if self.root:
            self.progress_window = self.create_progress_window("Установка зависимостей")
            if not self.progress_window:
                self.log_debug("Не удалось создать окно прогресса")
            self.update_progress("Подготовка к установке...", 0)

        try:
            # Для SteamOS выполняем дополнительные шаги
            if self.is_steamos:
                # 4. Разблокируем систему (только для SteamOS)
                self.log_debug("Шаг 1: Разблокировка системы...")
                if not self.unlock_readonly_system():
                    self.log_debug("Ошибка разблокировки системы")
                    if self.progress_window:
                        self.close_progress_window()
                    self.show_info("Проблема с разблокировкой",
                                 "Не удалось разблокировать систему для установки зависимостей.\n"
                                 "Программа может работать некорректно.")
                    return False

            # 5. Модифицируем pacman.conf (для всех ОС)
            self.log_debug("Шаг 2: Модификация pacman.conf...")
            if not self.fix_pacman_conf():
                self.log_debug("Ошибка модификации pacman.conf")
                # Если это SteamOS, пытаемся заблокировать систему перед выходом
                if self.is_steamos:
                    self.lock_readonly_system()
                if self.progress_window:
                    self.close_progress_window()
                self.show_info("Проблема с настройкой",
                             "Не удалось настроить пакетный менеджер.\n"
                             "Установка зависимостей невозможна.")
                return False

            # 6. Удаляем блокировочные файлы базы данных pacman (только для SteamOS)
            if self.is_steamos:
                self.log_debug("Шаг 3: Проверка и удаление блокировочных файлов pacman...")
                self.remove_pacman_db_lock()  # Не прерываем процесс даже при ошибке

            # 7. Инициализируем ключи (для всех ОС)
            self.log_debug("Шаг 4: Инициализация ключей pacman...")
            if not self.init_pacman_keys():
                self.log_debug("Ошибка инициализации ключей")
                # Если это SteamOS, пытаемся заблокировать систему перед выходом
                if self.is_steamos:
                    self.lock_readonly_system()
                if self.progress_window:
                    self.close_progress_window()
                self.show_info("Проблема с ключами",
                             "Не удалось инициализировать ключи pacman.\n"
                             "Установка зависимостей невозможна.\n\n"
                             "Рекомендуется:\n"
                             "• Запустить программу с другой точкой доступа\n"
                             "• Подключиться через VPN")
                return False

            # 8. Устанавливаем зависимости
            self.log_debug("Шаг 5: Установка зависимостей...")
            success_count = 0
            failed_deps = []

            for i, dep in enumerate(missing_deps, 1):
                self.log_debug(f"Установка зависимости {i}/{len(missing_deps)}: {dep}")
                if self.install_dependency_with_fallback(dep, i, len(missing_deps)):
                    success_count += 1
                    self.log_debug(f"Зависимость {dep} установлена успешно")
                else:
                    failed_deps.append(dep)
                    self.log_debug(f"Не удалось установить зависимость {dep}")

            self.log_debug(f"Итог установки: успешно={success_count}, неудачно={len(failed_deps)}")

            # 9. Блокируем систему (только для SteamOS)
            if self.is_steamos:
                self.log_debug("Шаг 6: Блокировка системы...")
                self.lock_readonly_system()

            # Закрываем окно прогресса
            if self.progress_window:
                self.close_progress_window()

            # 10. Показываем итоги
            if success_count == len(missing_deps):
                self.log_debug("Все зависимости успешно установлены")
                self.show_info("Успешная установка",
                             "Все зависимости успешно установлены!\n"
                             f"{'Система заблокирована.' if self.is_steamos else ''}\n"
                             "Программа готова к работе.")
                return True
            elif success_count > 0:
                self.log_debug(f"Частичная установка: {success_count}/{len(missing_deps)}")
                self.show_info("Частичная установка",
                             f"Установлено {success_count} из {len(missing_deps)} зависимостей.\n\n"
                             f"Не удалось установить: {', '.join(failed_deps) if failed_deps else 'нет'}\n\n"
                             f"{'Система заблокирована.' if self.is_steamos else ''}\n\n"
                             "Программа может работать некорректно.")
                return True
            else:
                self.log_debug("Ни одна зависимость не установлена")
                self.show_info("Неудачная установка",
                             "Не удалось установить ни одну зависимость.\n\n"
                             f"{'Система заблокирована.' if self.is_steamos else ''}\n\n"
                             "Рекомендуется:\n"
                             "• Запустить программу с другой точкой доступа\n"
                             "• Подключиться через VPN\n\n"
                             "Программа может работать некорректно.")
                return False

        except Exception as e:
            self.log_debug(f"Критическая ошибка при установке зависимостей: {e}")
            import traceback
            self.log_debug(f"Трассировка: {traceback.format_exc()}")

            # Пытаемся заблокировать систему даже при ошибке
            if self.is_steamos:
                try:
                    self.lock_readonly_system()
                except:
                    pass

            if self.progress_window:
                self.close_progress_window()

            self.show_info("Ошибка установки",
                         f"Произошла критическая ошибка при установке зависимостей:\n\n"
                         f"{str(e)}\n\n"
                         "Программа может работать некорректно.")
            return False

def run_dependency_check(root_window=None):
    """
    Запускает проверку зависимостей при старте программы
    """
    checker = DependencyChecker(root_window)
    result = checker.check_and_install_dependencies()

    return result

if __name__ == "__main__":
    test_checker = DependencyChecker()
    result = test_checker.check_and_install_dependencies()

    if result:
        print("Проверка зависимостей завершена успешно или с частичным успехом")
    else:
        print("Проверка зависимостей завершена с ошибками")
