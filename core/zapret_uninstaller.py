#!/usr/bin/env python3

import subprocess
import tkinter as tk
import os
import shutil
import time
import platform
from tkinter import messagebox
from ui.components.custom_messagebox import ask_yesno as custom_show_yesno
from ui.components.custom_messagebox import show_info as custom_show_info

class ZapretUninstaller:
    def __init__(self, root_window=None):
        self.root = root_window
        self.sudo_password = None
        self.progress_window = None
        self.current_task = ""
        self.debug_log = []
        self.is_steamos = self.check_if_steamos()
        self.uninstall_successful = False

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

    def show_info(self, title, message):
        """Показывает информационное сообщение"""
        self.log_debug(f"show_info: {title} - {message}")
        if self.root and self.root.winfo_exists():
            try:
                custom_show_info(self.root, title, message)
            except ImportError:
                messagebox.showinfo(title, message, parent=self.root)
        else:
            print(f"{title}: {message}")

    def show_yesno_dialog(self, title, message):
        """Показывает диалог с выбором Да/Нет"""
        self.log_debug(f"show_yesno_dialog: {title}")
        if self.root and self.root.winfo_exists():
            try:
                return custom_show_yesno(self.root, title, message)
            except ImportError:
                return messagebox.askyesno(title, message, parent=self.root)
        return False

    def create_progress_window(self, title="Удаление Zapret"):
        """Создает окно прогресса"""
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
                fg='#ff3b30',  # Красный цвет для удаления
                bg='#182030'
            )
            title_label.pack(pady=(0, 15))

            # Текущая задача
            self.task_label = tk.Label(
                main_frame,
                text="Подготовка к удалению...",
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
                bg='#ff3b30',  # Красный цвет для удаления
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
            self.log_debug("Окно прогресса создано успешно")
            return progress_window

        except Exception as e:
            self.log_debug(f"Ошибка создания окна прогресса: {e}")
            return None

    def update_progress(self, task, progress_percent):
        """Обновляет прогресс-бар и текст задачи"""
        if self.progress_window and self.progress_window.winfo_exists():
            self.log_debug(f"Обновление прогресса: {task} - {progress_percent}%")
            self.task_label.config(text=task)

            width = self.progress_bg.winfo_width()
            new_width = int(width * progress_percent / 100)
            self.progress_bar.config(width=new_width)

            self.percent_label.config(text=f"{int(progress_percent)}%")
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
            from ui.windows.sudo_password_window import SudoPasswordWindow
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
                         "Не удалось загрузить модуль запроса пароля.\nУдаление Zapret невозможно.")
            return False
        except Exception as e:
            self.log_debug(f"Ошибка при запросе пароля: {e}")
            return False

    def set_sudo_password(self, password):
        """Сохраняет sudo пароль"""
        self.sudo_password = password

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

            return {
                'returncode': process.returncode,
                'stdout': stdout,
                'stderr': stderr,
                'command': ' '.join(command)
            }

        except Exception as e:
            self.log_debug(f"Ошибка выполнения команды с sudo: {e}")
            return {
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'command': ' '.join(command)
            }

    def get_current_progress(self):
        """Рассчитывает текущий прогресс на основе этапа"""
        progress_map = {
            "unlock": 10,
            "stop_service": 20,
            "disable_service": 30,
            "remove_service": 40,
            "remove_zapret_dir": 60,
            "remove_manager_dir": 80,
            "restore_pacman": 85,
            "remove_desktop_shortcuts": 87,
            "remove_dependencies": 89,
            "lock": 90
        }
        progress = progress_map.get(self.current_task, 0)
        self.log_debug(f"Текущая задача: {self.current_task}, прогресс: {progress}")
        return progress

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

    def is_zapret_installed(self):
        """Проверяет, установлен ли zapret"""
        self.log_debug("Проверка установки Zapret...")

        zapret_dir_exists = os.path.exists("/opt/zapret")
        service_exists = os.path.exists("/usr/lib/systemd/system/zapret.service")
        manager_dir_exists = os.path.exists(os.path.expanduser("~/Zapret_DPI_Manager"))

        self.log_debug(f"Папка /opt/zapret существует: {zapret_dir_exists}")
        self.log_debug(f"Служба zapret.service существует: {service_exists}")
        self.log_debug(f"Папка менеджера существует: {manager_dir_exists}")

        return zapret_dir_exists or service_exists or manager_dir_exists

    def stop_zapret_service(self):
        """Останавливает службу zapret"""
        self.current_task = "stop_service"
        self.log_debug("Остановка службы zapret...")

        result = self.run_with_sudo(
            ['systemctl', 'stop', 'zapret'],
            "Остановка службы zapret..."
        )

        if not result:
            self.log_debug("Нет результата от остановки службы")
            return False

        if result['returncode'] != 0:
            # Если служба не запущена, это не ошибка
            if "inactive" in result['stderr'] or "not loaded" in result['stderr']:
                self.log_debug("Служба уже остановлена или не существует")
                return True
            else:
                self.log_debug(f"Ошибка остановки службы: {result['stderr']}")
                return False

        self.log_debug("Служба успешно остановлена")
        return True

    def disable_zapret_service(self):
        """Отключает автозапуск службы zapret"""
        self.current_task = "disable_service"
        self.log_debug("Отключение автозапуска службы zapret...")

        result = self.run_with_sudo(
            ['systemctl', 'disable', 'zapret'],
            "Отключение автозапуска службы..."
        )

        if not result:
            self.log_debug("Нет результата от отключения службы")
            return False

        if result['returncode'] != 0:
            # Если служба уже отключена, это не ошибка
            if "disabled" in result['stderr'] or "does not exist" in result['stderr']:
                self.log_debug("Служба уже отключена или не существует")
                return True
            else:
                self.log_debug(f"Ошибка отключения службы: {result['stderr']}")
                return False

        self.log_debug("Автозапуск службы успешно отключен")
        return True

    def remove_service_file(self):
        """Удаляет файл службы"""
        self.current_task = "remove_service"
        self.log_debug("Удаление файла службы zapret.service...")

        service_path = "/usr/lib/systemd/system/zapret.service"

        # Проверяем, существует ли файл
        check_result = self.run_with_sudo(['ls', '-la', service_path])
        if check_result and check_result['returncode'] != 0:
            self.log_debug("Файл службы не существует, пропускаем удаление")
            return True

        # Удаляем файл
        result = self.run_with_sudo(
            ['rm', service_path],
            "Удаление файла службы..."
        )

        if not result or result['returncode'] != 0:
            self.log_debug(f"Ошибка удаления файла службы: {result['stderr'] if result else 'No result'}")
            return False

        self.log_debug("Файл службы успешно удален")
        return True

    def remove_zapret_directory(self):
        """Удаляет директорию /opt/zapret"""
        self.current_task = "remove_zapret_dir"
        self.log_debug("Удаление директории /opt/zapret...")

        zapret_dir = "/opt/zapret"

        # Проверяем, существует ли директория
        check_result = self.run_with_sudo(['ls', '-la', '/opt/'])
        if check_result and check_result['returncode'] == 0:
            if 'zapret' not in check_result['stdout']:
                self.log_debug("Директория /opt/zapret не существует, пропускам удаление")
                return True
        else:
            self.log_debug("Не удалось проверить существование /opt/zapret")

        # Удаляем директорию
        result = self.run_with_sudo(
            ['rm', '-rf', zapret_dir],
            "Удаление директории /opt/zapret..."
        )

        if not result or result['returncode'] != 0:
            self.log_debug(f"Ошибка удаления директории: {result['stderr'] if result else 'No result'}")
            return False

        self.log_debug("Директория /opt/zapret успешно удалена")
        return True

    def remove_manager_directory(self):
        """Удаляет директорию менеджера"""
        self.current_task = "remove_manager_dir"
        self.log_debug("Удаление директории менеджера...")

        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")

        # Проверяем, существует ли директория
        if not os.path.exists(manager_dir):
            self.log_debug("Директория менеджера не существует, пропускаем удаление")
            return True

        # Пытаемся удалить через sudo (на случай если есть root файлы)
        result = self.run_with_sudo(
            ['rm', '-rf', manager_dir],
            "Удаление директории менеджера..."
        )

        if not result or result['returncode'] != 0:
            # Пробуем удалить без sudo
            self.log_debug("Попытка удаления без sudo...")
            try:
                shutil.rmtree(manager_dir, ignore_errors=True)
                self.log_debug("Директория менеджера успешно удалена без sudo")
                return True
            except Exception as e:
                self.log_debug(f"Ошибка удаления директории без sudo: {e}")
                return False
        else:
            self.log_debug("Директория менеджера успешно удалена")
            return True

    def restore_pacman_conf(self):
        """Восстанавливает оригинальный pacman.conf и инициализирует ключи"""
        self.current_task = "restore_pacman"
        self.log_debug("Восстановление pacman.conf...")

        try:
            # Восстанавливаем оригинальную строку в pacman.conf
            result = self.run_with_sudo(
                ['sed', '-i', 's/TrustAll/Required DatabaseOptional/g', '/etc/pacman.conf'],
                "Восстановление pacman.conf..."
            )

            if not result or result['returncode'] != 0:
                self.log_debug(f"Предупреждение: Не удалось восстановить pacman.conf: {result['stderr'] if result else 'No result'}")
                return False

            # Инициализируем ключи
            self.log_debug("Инициализация ключей pacman...")
            init_result = self.run_with_sudo(['pacman-key', '--init'])
            populate_result = self.run_with_sudo(['pacman-key', '--populate'])

            if (init_result and init_result['returncode'] != 0) or (populate_result and populate_result['returncode'] != 0):
                self.log_debug("Предупреждение: Проблемы с инициализацией ключей pacman")

            # Обновляем базу пакетов
            self.log_debug("Обновление базы пакетов...")
            sync_result = self.run_with_sudo(['pacman', '-Sy'])
            if sync_result and sync_result['returncode'] != 0:
                self.log_debug("Предупреждение: Проблемы с обновлением базы пакетов")

            self.log_debug("Pacman.conf успешно восстановлен")
            return True

        except Exception as e:
            self.log_debug(f"Ошибка при восстановлении pacman.conf: {e}")
            return False

    def remove_dependencies(self):
        """Удаляет зависимости (ipset)"""
        self.current_task = "remove_dependencies"
        self.log_debug("Удаление зависимостей (ipset)...")

        result = self.run_with_sudo(
            ['pacman', '-Rns', '--noconfirm', 'ipset'],
            "Удаление зависимостей..."
        )

        if not result:
            self.log_debug("Нет результата от удаления зависимостей")
            return False

        if result['returncode'] != 0:
            # Если пакет не установлен, это не ошибка
            if "не установлен" in result['stdout'] or "not found" in result['stdout'].lower():
                self.log_debug("Пакет ipset не установлен, пропускаем удаление")
                return True
            else:
                self.log_debug(f"Предупреждение при удалении зависимостей: {result['stderr']}")
                return False

        self.log_debug("Зависимости успешно удалены")
        return True

    def remove_desktop_shortcuts(self):
        """Удаляет ярлыки с рабочего стола"""
        self.current_task = "remove_desktop_shortcuts"
        self.log_debug("Удаление ярлыков с рабочего стола...")

        desktop_paths = [
            os.path.expanduser("~/Рабочий стол/Zapret_DPI_Manager.desktop"),  # Русский
            os.path.expanduser("~/Desktop/Zapret_DPI_Manager.desktop"),       # Английский
        ]

        desktop_removed = False
        for desktop_path in desktop_paths:
            if os.path.exists(desktop_path):
                try:
                    os.remove(desktop_path)
                    self.log_debug(f"Ярлык удален: {desktop_path}")
                    desktop_removed = True
                except Exception as e:
                    self.log_debug(f"Не удалось удалить ярлык {desktop_path}: {e}")

        if not desktop_removed:
            self.log_debug("Ярлыки на рабочем столе не найдены")

        return True

    def remove_sudo_cache(self):
        """Удаляет файл кэша sudo пароля"""
        self.current_task = "remove_sudo_cache"
        self.log_debug("Удаление файла кэша sudo пароля...")

        cache_path = os.path.expanduser("~/.zapret_sudo_cache")

        if not os.path.exists(cache_path):
            self.log_debug("Файл кэша sudo пароля не существует, пропускаем удаление")
            return True

        try:
            os.remove(cache_path)
            self.log_debug(f"Файл кэша sudo пароля успешно удален: {cache_path}")
            return True
        except Exception as e:
            self.log_debug(f"Не удалось удалить файл кэша sudo пароля {cache_path}: {e}")
            return False

    def reload_systemd(self):
        """Обновляет systemd"""
        self.log_debug("Обновление systemd...")

        result = self.run_with_sudo(
            ['systemctl', 'daemon-reload'],
            "Обновление systemd..."
        )

        if result and result['returncode'] != 0:
            self.log_debug(f"Предупреждение при обновлении systemd: {result['stderr']}")

        return True

    def remove_desktop_shortcuts(self):
        """Удаляет все ярлыки с рабочего стола и из меню приложений"""
        self.current_task = "remove_desktop_shortcuts"
        self.log_debug("Удаление ярлыков Zapret DPI Manager...")

        # Список всех возможных путей к ярлыкам
        shortcut_paths = [
            # Рабочий стол (русский и английский)
            os.path.expanduser("~/Рабочий стол/Zapret_DPI_Manager.desktop"),
            os.path.expanduser("~/Desktop/Zapret_DPI_Manager.desktop"),

            # Меню приложений
            os.path.expanduser("~/.local/share/applications/Zapret_DPI_Manager.desktop"),

            # Системные меню приложений (если установлены с sudo)
            "/usr/share/applications/Zapret_DPI_Manager.desktop",
            "/usr/local/share/applications/Zapret_DPI_Manager.desktop",
        ]

        removed_count = 0
        for shortcut_path in shortcut_paths:
            if os.path.exists(shortcut_path):
                try:
                    # Пытаемся удалить через sudo (для системных файлов)
                    result = self.run_with_sudo(['rm', '-f', shortcut_path])
                    if result and result['returncode'] != 0:
                        # Если не удалось через sudo, пробуем обычное удаление
                        os.remove(shortcut_path)

                    self.log_debug(f"Ярлык удален: {shortcut_path}")
                    removed_count += 1

                except Exception as e:
                    self.log_debug(f"Не удалось удалить ярлык {shortcut_path}: {e}")

        # Обновляем кэш меню приложений
        try:
            user_apps_dir = os.path.expanduser("~/.local/share/applications")
            if os.path.exists(user_apps_dir):
                subprocess.run(['update-desktop-database', user_apps_dir],
                            capture_output=True, text=True)
        except Exception as e:
            self.log_debug(f"Не удалось обновить кэш меню: {e}")

        self.log_debug(f"Удалено ярлыков: {removed_count}")
        return True

    def uninstall_zapret(self):
        """Основная функция удаления zapret"""
        self.log_debug("=== ЗАПУСК УДАЛЕНИЯ ZAPRET ===")
        self.log_debug(f"Обнаружена система: {'SteamOS' if self.is_steamos else 'другая ОС'}")

        # Проверяем, установлен ли что-то для удаления
        if not self.is_zapret_installed():
            self.log_debug("Zapret не установлен, нечего удалять")
            self.show_info("Информация",
                         "Zapret не установлен на этой системе.\n"
                         "Нечего удалять.")
            return True

        # Показываем подтверждение удаления
        self.log_debug("Запрос подтверждения удаления...")
        if not self.show_yesno_dialog(
            "Подтверждение удаления",
            "Вы уверены, что хотите полностью удалить Zapret?\n\n"
            "Будут удалены:\n"
            "• Служба Zapret DPI\n"
            "• Менеджер Zapret DPI Manager\n\n"
            "Это действие нельзя отменить!"
        ):
            self.log_debug("Пользователь отменил удаление")
            return False

        # Запрашиваем sudo пароль
        if not self.get_sudo_password():
            self.log_debug("Не получен sudo пароль, отмена удаления")
            self.show_info("Отмена удаления",
                         "Для удаления Zapret требуется sudo пароль.\n"
                         "Удаление отменено.")
            return False

        # Создаем окно прогресса
        if self.root:
            self.progress_window = self.create_progress_window("Удаление Zapret")
            if not self.progress_window:
                self.log_debug("Не удалось создать окно прогресса")
            self.update_progress("Подготовка к удалению...", 0)

        try:
            # 1. Разблокируем файловую систему (только для SteamOS)
            self.update_progress("Разблокировка системы...", 5)
            if not self.unlock_readonly_system():
                if self.is_steamos:
                    self.log_debug("Не удалось разблокировать систему")
                    self.close_progress_window()
                    self.show_info("Ошибка разблокировки",
                                 "Не удалось разблокировать файловую систему SteamOS.\n"
                                 "Удаление Zapret невозможно.")
                    return False
                else:
                    self.log_debug("Пропускаем разблокировку на не-SteamOS системе")

            # 2. Останавливаем службу
            self.update_progress("Остановка службы...", 20)
            if not self.stop_zapret_service():
                self.log_debug("Предупреждение: не удалось остановить службу, продолжаем...")

            # 3. Отключаем автозапуск
            self.update_progress("Отключение автозапуска...", 30)
            if not self.disable_zapret_service():
                self.log_debug("Предупреждение: не удалось отключить автозапуск, продолжаем...")

            # 4. Удаляем файл службы
            self.update_progress("Удаление службы...", 40)
            if not self.remove_service_file():
                self.log_debug("Предупреждение: не удалось удалить файл службы, продолжаем...")

            # 5. Обновляем systemd
            self.reload_systemd()

            # 6. Удаляем директорию /opt/zapret
            self.update_progress("Удаление системных файлов...", 60)
            if not self.remove_zapret_directory():
                self.log_debug("Предупреждение: не удалось удалить /opt/zapret, продолжаем...")

            # 7. Удаляем директорию менеджера
            self.update_progress("Удаление файлов менеджера...", 80)
            if not self.remove_manager_directory():
                self.log_debug("Предупреждение: не удалось удалить директорию менеджера, продолжаем...")

            # 8. Восстанавливаем pacman.conf
            self.update_progress("Восстановление pacman.conf...", 85)
            if not self.restore_pacman_conf():
                self.log_debug("Предупреждение: не удалось восстановить pacman.conf, продолжаем...")

            # 9. Удаляем ярлыки
            self.update_progress("Удаление ярлыков и кэш пароля...", 87)
            self.remove_desktop_shortcuts()
            self.remove_sudo_cache()

            # 10. Удаляем зависимости
            self.update_progress("Удаление зависимостей...", 89)
            if not self.remove_dependencies():
                self.log_debug("Предупреждение: не удалось удалить зависимости, продолжаем...")

            # 11. Блокируем файловую систему (только для SteamOS)
            self.update_progress("Блокировка системы...", 90)
            self.lock_readonly_system()

            # Обновляем прогресс
            self.update_progress("Удаление завершено!", 100)

            # Закрываем окно прогресса
            if self.progress_window:
                self.close_progress_window()

            self.log_debug("=== УДАЛЕНИЕ ZAPRET УСПЕШНО ЗАВЕРШЕНО ===")
            self.uninstall_successful = True
            self.show_info("Удаление завершено",
                         "Zapret успешно удален с системы!\n\n"
                         "Удалены:\n"
                         "• Служба Zapret DPI\n"
                         "• Менеджер Zapret DPI Manager\n\n"
                         "Программа будет закрыта.")
            return True

        except Exception as e:
            self.log_debug(f"Критическая ошибка при удалении Zapret: {e}")
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
            error_log = "\n".join(self.debug_log[-30:])
            self.show_info("Ошибка удаления",
                         f"Произошла ошибка при удалении Zapret:\n\n"
                         f"Ошибка: {str(e)}\n\n"
                         f"Частичное удаление могло произойти.\n"
                         f"Лог удаления:\n{error_log}")
            return False

    def show_info(self, title, message):
        """Показывает информационное сообщение и закрывает программу если это завершающее сообщение"""
        self.log_debug(f"show_info: {title} - {message}")

        if self.root and self.root.winfo_exists():
            try:
                custom_show_info(self.root, title, message)
            except ImportError:
                messagebox.showinfo(title, message, parent=self.root)

            # Если это сообщение об успешном завершении и программа была успешно удалена,
            # закрываем программу после нажатия OK
            if title == "Удаление завершено" and self.uninstall_successful:
                self.log_debug("Закрытие программы после успешного удаления...")
                if self.root:
                    self.root.quit()
                    self.root.destroy()
                sys.exit(0)
        else:
            print(f"{title}: {message}")

    def run_uninstall(self):
        """Запускает процесс удаления и возвращает True если нужно закрыть программу"""
        result = self.uninstall_zapret()

        # Если удаление успешно завершено, возвращаем специальный флаг
        if result and self.uninstall_successful:
            return "close_app"
        return result

def run_zapret_uninstall(root_window=None):
    """
    Запускает удаление zapret
    """
    uninstaller = ZapretUninstaller(root_window)
    return uninstaller.run_uninstall()

if __name__ == "__main__":
    # Тестирование
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    uninstaller = ZapretUninstaller(root)
    result = uninstaller.run_uninstall()
    print(f"Результат удаления: {result}")
