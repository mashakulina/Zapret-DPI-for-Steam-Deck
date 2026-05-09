#!/usr/bin/env python3
import getpass
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import time
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

from core.app_logging import get_error_logger
from core.dpi_utils import place_toplevel_centered_on_parent
from core.zapret_updater import (
    ZapretUpdater,
    download_http_to_file,
    find_bundle_root,
    get_bundle_download_url,
    validate_bundle_structure,
)
from core.platform_info import (
    is_valve_steamos,
    distro_log_label,
    os_release_id_normalized,
    zapret_systemd_unit_is_present,
)

class ZapretChecker:
    def __init__(
        self,
        root_window=None,
        *,
        show_info_fn: Callable[[str, str], None] | None = None,
        sudo_password_provider: Callable[[], str | None] | None = None,
    ):
        self.root = root_window
        self._show_info_fn = show_info_fn
        self._sudo_password_provider = sudo_password_provider
        self.progress_window = None
        self.current_task = ""
        self.sudo_password = None
        self.debug_log = []  # Лог для дебага
        self.last_command_result = None  # Результат последней команды
        self.home_dir = os.path.expanduser("~")  # Динамическое определение домашней директории
        self.is_steamos = self.check_if_steamos()  # Только Valve SteamOS

        # Список обязательных файлов для zapret
        self.required_files = [
            "FWTYPE",           # Тип файрвола
            "nfqws",           # Бинарный файл
            "starter.sh",      # Скрипт запуска
            "stopper.sh",      # Скрипт остановки
            "zapret.service"    # Конфигурационный файл сервера
        ]

        # Путь к папке zapret
        self.zapret_dir = "/opt/zapret"

    def check_if_steamos(self):
        """Только официальная SteamOS Valve (ID=steamos)."""
        self.log_debug(
            f"Проверка Valve SteamOS… Дистрибутив: {distro_log_label()} "
            f"(ID={os_release_id_normalized() or '?'})"
        )
        return is_valve_steamos()

    def log_debug(self, message):
        """Добавляет сообщение в лог дебага"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.debug_log.append(log_msg)
        print(log_msg)

    def is_zapret_installed(self):
        """Проверяет, установлен ли zapret"""
        zapret_dir_exists = os.path.exists(self.zapret_dir)

        service_exists = zapret_systemd_unit_is_present()

        return zapret_dir_exists and service_exists

    def check_zapret_files(self):
        """Проверяет наличие всех обязательных файлов в /opt/zapret"""
        self.log_debug("Проверка наличия всех необходимых файлов zapret...")

        if not os.path.exists(self.zapret_dir):
            self.log_debug(f"Папка {self.zapret_dir} не существует")
            return False

        missing_files = []

        for file_name in self.required_files:
            file_path = os.path.join(self.zapret_dir, file_name)

            if not os.path.exists(file_path):
                missing_files.append(file_name)
                self.log_debug(f"Файл {file_name} отсутствует в {self.zapret_dir}")
                continue

            try:
                if os.path.getsize(file_path) == 0:
                    missing_files.append(file_name)
                    self.log_debug(f"Файл {file_name} существует, но пустой")
            except OSError as e:
                missing_files.append(file_name)
                self.log_debug(f"Ошибка при проверке размера файла {file_name}: {e}")

        if missing_files:
            for file_name in missing_files:
                file_path = os.path.join(self.zapret_dir, file_name)
                try:
                    result = subprocess.run(
                        ["ls", "-la", file_path],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        self.log_debug(f"Информация о файле {file_name}: {result.stdout.strip()}")
                    else:
                        self.log_debug(f"Файл {file_name} не найден (ls вернул код {result.returncode})")
                except Exception as e:
                    self.log_debug(f"Ошибка при проверке файла {file_name} через ls: {e}")

            return False

        self.log_debug("Все необходимые файлы zapret присутствуют")
        return True

    def is_zapret_running(self):
        """Проверяет, запущена ли служба zapret"""
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True
            )
            return result.returncode == 0 and result.stdout.strip() == "active"
        except Exception:
            return False

    def show_info(self, title, message):
        """Показывает информационное сообщение"""
        if self._show_info_fn is not None:
            self._show_info_fn(title, message)
            return
        if self.root and self.root.winfo_exists():
            try:
                messagebox.showinfo(title, message, parent=self.root)
            except Exception:
                print(f"{title}: {message}")
        else:
            print(f"{title}: {message}")

    def create_progress_window(self, title="Установка Zapret"):
        """Создает окно прогресса"""
        if not self.root:
            return None

        progress_window = tk.Toplevel(self.root)
        progress_window.title(title)
        progress_window.configure(bg='#182030')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)

        main_frame = tk.Frame(progress_window, bg='#182030', padx=30, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text=title,
            font=("Arial", 14, "bold"),
            fg='#0a84ff',
            bg='#182030'
        )
        title_label.pack(pady=(0, 15))

        self.task_label = tk.Label(
            main_frame,
            text="Подготовка к установке...",
            font=("Arial", 11),
            fg='white',
            bg='#182030',
            wraplength=340
        )
        self.task_label.pack(pady=(0, 10))

        progress_frame = tk.Frame(main_frame, bg='#182030')
        progress_frame.pack(fill=tk.X, pady=(10, 0))

        self.progress_bg = tk.Frame(
            progress_frame,
            bg='#15354D',
            height=12,
            relief=tk.FLAT
        )
        self.progress_bg.pack(fill=tk.X)

        self.progress_bar = tk.Frame(
            self.progress_bg,
            bg='#0a84ff',
            height=12,
            width=0
        )
        self.progress_bar.place(x=0, y=0, relheight=1.0)

        self.percent_label = tk.Label(
            progress_frame,
            text="0%",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.percent_label.pack(pady=(5, 0))

        progress_window.update_idletasks()
        place_toplevel_centered_on_parent(
            progress_window, self.root, min_width=340, min_height=140, margin_width=8, margin_height=10
        )
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
        if self._sudo_password_provider is not None:
            try:
                password = self._sudo_password_provider()
                if password:
                    self.sudo_password = password
                    return True
                return False
            except Exception as e:
                print(f"Ошибка при запросе пароля: {e}")
                return False
        try:
            pwd = getpass.getpass("Пароль sudo: ")
            if pwd:
                self.sudo_password = pwd
                return True
            return False
        except Exception as e:
            print(f"Ошибка при запросе пароля: {e}")
            self.show_info(
                "Ошибка",
                "Не удалось запросить пароль.\nУстановка Zapret невозможна.",
            )
            return False

    def set_sudo_password(self, password):
        """Сохраняет sudo пароль"""
        self.sudo_password = password

    def run_with_sudo(self, command, task_name=""):
        """Выполняет команду с sudo паролем"""
        if not self.sudo_password:
            return None

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
        if self.current_task == "unlock":
            return 5
        elif self.current_task == "download":
            return 20
        elif self.current_task == "extract":
            return 40
        elif self.current_task == "copy_files":
            return 60
        elif self.current_task == "create_service":
            return 80
        elif self.current_task == "enable_service":
            return 90
        elif self.current_task == "lock":
            return 95
        else:
            return 0

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

    def _install_zapret_from_full_bundle(self, bundle_url: str, temp_dir: str) -> bool:
        """Скачивает единый полный пакет (version.txt → zapret_updater.tar.gz) и ставит только службу."""
        archive_path = os.path.join(temp_dir, "bundle.tar.gz")
        extract_dir = os.path.join(temp_dir, "bundle_extracted")
        os.makedirs(extract_dir, exist_ok=True)

        self.current_task = "download"
        try:
            self.update_progress("Скачивание полного пакета...", 10)

            def reporthook(block_count, block_size, total_size):
                if total_size > 0 and self.progress_window:
                    pct = 10 + min(25, int(block_count * block_size * 25 / total_size))
                    self.update_progress(f"Скачивание полного пакета… {pct}%", pct)

            download_http_to_file(
                bundle_url,
                archive_path,
                timeout=120.0,
                reporthook=reporthook,
            )
        except urllib.error.URLError as e:
            reason = e.reason
            detail = str(reason) if reason is not None else str(e)
            self.log_debug(f"Ошибка скачивания полного пакета (сеть): {detail}")
            get_error_logger().error(
                "Установка Zapret: скачивание полного пакета (сеть) %s: %s",
                bundle_url,
                detail,
                exc_info=True,
            )
            return False
        except Exception as e:
            self.log_debug(f"Ошибка скачивания полного пакета: {e}")
            get_error_logger().exception(
                "Установка Zapret: скачивание полного пакета %s",
                bundle_url,
            )
            return False

        if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
            self.log_debug("Архив полного пакета пуст или отсутствует")
            get_error_logger().error(
                "Установка Zapret: архив полного пакета пуст после скачивания (%s)",
                bundle_url,
            )
            return False

        self.current_task = "extract"
        self.update_progress("Распаковка полного пакета...", 35)
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(path=extract_dir)
        except Exception as e:
            self.log_debug(f"Ошибка распаковки полного пакета: {e}")
            get_error_logger().exception("Установка Zapret: распаковка полного пакета")
            return False

        bundle_root = find_bundle_root(extract_dir)
        if not bundle_root or not validate_bundle_structure(bundle_root):
            self.log_debug("Неверная структура полного пакета")
            get_error_logger().error(
                "Установка Zapret: неверная структура полного пакета после распаковки"
            )
            return False

        zu = ZapretUpdater()
        pwd = self.sudo_password

        def pc(msg, pct):
            if pct is not None:
                self.update_progress(msg, min(100, max(0, int(pct))))
            else:
                self.update_progress(msg, self.get_current_progress())

        self.current_task = "copy_files"
        if not zu.install_zapret_service_from_bundle_root(bundle_root, pwd, pc):
            self.log_debug("Не удалось установить службу из полного пакета")
            get_error_logger().error(
                "Установка Zapret: не удалось установить службу из полного пакета"
            )
            return False
        return True

    def install_zapret(self):
        """Основная функция установки zapret"""
        self.log_debug("=== НАЧАЛО УСТАНОВКИ ZAPRET ===")
        if self.is_steamos:
            self.log_debug("Режим Valve SteamOS (readonly, pacman)")
        else:
            self.log_debug(f"Дистрибутив: {distro_log_label()}")
        self.log_debug(f"Текущий пользователь: {os.path.basename(self.home_dir)}")

        if self.root:
            self.root.update()

        if not self.get_sudo_password():
            self.log_debug("Не получен sudo пароль, отмена установки")
            self.show_info("Отмена установки",
                         "Для установки Zapret требуется sudo пароль.\n"
                         "Установка отменена.")
            return False

        if self.root:
            self.progress_window = self.create_progress_window("Установка Zapret")
            if not self.progress_window:
                self.log_debug("Не удалось создать окно прогресса")
            self.update_progress("Начало установки...", 0)

        temp_dir = tempfile.mkdtemp(prefix="zapret_install_")
        self.log_debug(f"Временная директория: {temp_dir}")

        try:
            self.update_progress("Разблокировка системы...", 5)
            if not self.unlock_readonly_system():
                if self.is_steamos:
                    self.log_debug("Не удалось разблокировать систему")
                    self.close_progress_window()
                    self.show_info("Ошибка разблокировки",
                                 "Не удалось разблокировать файловую систему SteamOS.\n"
                                 "Установка Zapret невозможна.")
                    return False
                else:
                    self.log_debug("Пропускаем разблокировку на не-SteamOS системе")

            bundle_url = get_bundle_download_url()
            if not bundle_url:
                self.log_debug("Не удалось получить URL полного пакета из version.txt")
                get_error_logger().error(
                    "Установка Zapret: не удалось получить URL полного пакета из version.txt"
                )
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info(
                    "Ошибка обновления",
                    "Не удалось получить ссылку на архив обновления из version.txt.\n"
                    "Проверьте подключение к интернету.",
                )
                return False

            self.log_debug(f"Установка службы из полного пакета (version.txt): {bundle_url}")
            if not self._install_zapret_from_full_bundle(bundle_url, temp_dir):
                self.log_debug("Не удалось установить службу из полного пакета")
                get_error_logger().error(
                    "Установка Zapret: сбой установки из полного пакета (см. сообщения выше в этом же логе)"
                )
                self.lock_readonly_system()
                self.close_progress_window()
                self.show_info(
                    "Ошибка установки",
                    "Не удалось установить службу Zapret из полного пакета.\n"
                    "Проверьте подключение к интернету и попробуйте снова.",
                )
                return False

            self.update_progress("Блокировка системы...", 95)
            self.lock_readonly_system()
            if self.progress_window:
                self.close_progress_window()
            self.log_debug("=== УСТАНОВКА ZAPRET УСПЕШНО ЗАВЕРШЕНА ===")
            self.show_info(
                "Успешная установка",
                "Zapret успешно установлен из полного пакета обновления и запущен!\n"
                "Служба добавлена в автозагрузку.\n\n"
                + (
                    "Статус: активен"
                    if self.is_zapret_running()
                    else "Статус: требует ручного запуска"
                ),
            )
            return True

        except Exception as e:
            self.log_debug(f"Критическая ошибка установки Zapret: {e}")
            import traceback
            error_trace = traceback.format_exc()
            self.log_debug(f"Трейс ошибки: {error_trace}")
            get_error_logger().exception("Установка Zapret: критическая ошибка")

            try:
                self.lock_readonly_system()
            except Exception:
                pass

            if self.progress_window:
                self.close_progress_window()

            error_log = "\n".join(self.debug_log[-30:])
            self.show_info("Ошибка установки",
                         f"Произошла ошибка при установке Zapret:\n\n"
                         f"Ошибка: {str(e)}\n\n"
                         f"Лог установки:\n{error_log}")
            return False

        finally:
            try:
                self.log_debug(f"Очистка временной директории: {temp_dir}")
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log_debug(f"Ошибка очистки временной директории: {e}")

    def check_and_install_zapret(self):
        """Проверяет и устанавливает zapret при необходимости"""
        if self.is_zapret_installed():
            print("Zapret уже установлен (служба найдена)")

            if not self.check_zapret_files():
                print("Обнаружены отсутствующие файлы, требуется переустановка")
                self.show_info("Проверка файлов Zapret",
                            "Обнаружены отсутствующие или поврежденные файлы Zapret.\n\n"
                            "Выполняется автоматическая переустановка...")

                return self.install_zapret()

            print("Все файлы Zapret присутствуют")
            return True

        print("Zapret не установлен, требуется установка")

        self.show_info("Установка Zapret",
                    "Для работы программы требуется установить службу Zapret.\n\n"
                    "Сейчас будет произведена её автоматическая установка.")

        return self.install_zapret()

def run_zapret_check(
    root_window=None,
    *,
    show_info_fn: Callable[[str, str], None] | None = None,
    sudo_password_provider: Callable[[], str | None] | None = None,
):
    """
    Запускает проверку и установку zapret при старте программы.

    Для GUI используйте ui.integrations.zapret_check.run_zapret_check.
    """
    checker = ZapretChecker(
        root_window,
        show_info_fn=show_info_fn,
        sudo_password_provider=sudo_password_provider,
    )
    return checker.check_and_install_zapret()

if __name__ == "__main__":
    test_checker = ZapretChecker()
    result = test_checker.check_and_install_zapret()

    if result:
        print("Zapret установлен успешно")
    else:
        print("Установка Zapret завершена с ошибками")
