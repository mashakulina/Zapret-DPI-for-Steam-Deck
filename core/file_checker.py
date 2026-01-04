#!/usr/bin/env python3
import subprocess
import tkinter as tk
import os
import sys
import tempfile
import tarfile
import shutil
import time
from pathlib import Path
from core.manager_config import RELEASES_URL
from ui.components.custom_messagebox import show_info as custom_show_info
from tkinter import messagebox

class ZapretFileChecker:
    def __init__(self, root_window=None):
        self.root = root_window
        self.progress_window = None
        self.current_task = ""
        self.sudo_password = None
        self.debug_log = []  # Лог для дебага

        # URL архива с zapret
        self.zapret_archive_url = f"{RELEASES_URL}/zapret_manager.tar.gz"

        # Базовые пути
        self.home_dir = Path.home()
        self.manager_dir = self.home_dir / "Zapret_DPI_Manager"

        # Список обязательных файлов и папок для проверки
        self.required_files = [
            # Основные исполняемые файлы
            self.manager_dir / "main.py",
            self.manager_dir / "core" / "manager_config.py",
            self.manager_dir / "core" / "service_manager.py",
            self.manager_dir / "core" / "zapret_checker.py",
            self.manager_dir / "core" / "dependency_checker.py",

            # UI компоненты
            self.manager_dir / "ui" / "windows" / "main_window.py",
            self.manager_dir / "ui" / "windows" / "sudo_password_window.py",
            self.manager_dir / "ui" / "components" / "custom_messagebox.py",

            # Файлы конфигурации
            self.manager_dir / "utils" / "chosen_strategies.txt",
            self.manager_dir / "utils" / "name_strategy.txt",

            # Иконка
            self.manager_dir / "ico" / "zapret.png",

            # QR код
            self.manager_dir / "utils" / "qr.png",
        ]

        # Проверяемые папки
        self.required_dirs = [
            self.manager_dir / "files" / "bin",
            self.manager_dir / "files" / "lists",
            self.manager_dir / "files" / "strategy",
            self.manager_dir / "core",
            self.manager_dir / "ui" / "windows",
            self.manager_dir / "ui" / "components",
            self.manager_dir / "ico",
            self.manager_dir / "utils",
        ]

        # Минимальное количество файлов в папках (чтобы не проверять каждый файл)
        self.min_files_in_dir = {
            self.manager_dir / "files" / "bin": 58,
            self.manager_dir / "files" / "lists": 42,
            self.manager_dir / "files" / "strategy": 44,
            self.manager_dir / "core": 12,
            self.manager_dir / "ico": 1,
            self.manager_dir / "utils": 3,
            self.manager_dir / "ui" / "windows": 13,
            self.manager_dir / "ui" / "components": 2,
        }

    def log_debug(self, message):
        """Добавляет сообщение в лог дебага"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.debug_log.append(log_msg)
        print(log_msg)

    def show_info(self, title, message):
        """Показывает информационное сообщение"""
        if self.root and self.root.winfo_exists():
            try:
                custom_show_info(self.root, title, message)
            except ImportError:
                messagebox.showinfo(title, message, parent=self.root)
        else:
            print(f"{title}: {message}")

    def create_progress_window(self, title="Проверка файлов"):
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
            text="Подготовка к проверке...",
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

    def get_current_progress(self):
        """Рассчитывает текущий прогресс на основе этапа"""
        if self.current_task == "check":
            return 20
        elif self.current_task == "download":
            return 40
        elif self.current_task == "extract":
            return 60
        elif self.current_task == "restore":
            return 80
        elif self.current_task == "cleanup":
            return 90
        else:
            return 0

    def check_files(self):
        """Проверяет наличие всех необходимых файлов и папок"""
        self.log_debug("=== ПРОВЕРКА ФАЙЛОВ ZAPRET DPI MANAGER ===")

        missing_files = []
        missing_dirs = []

        # Проверяем основные файлы
        self.update_progress("Проверка основных файлов...", 10)
        for file_path in self.required_files:
            if not file_path.exists():
                missing_files.append(str(file_path))
                self.log_debug(f"✗ Отсутствует файл: {file_path}")
            else:
                self.log_debug(f"✓ Файл присутствует: {file_path}")

        # Проверяем папки и минимальное количество файлов в них
        self.update_progress("Проверка папок...", 30)
        for dir_path in self.required_dirs:
            if not dir_path.exists():
                missing_dirs.append(str(dir_path))
                self.log_debug(f"✗ Отсутствует папка: {dir_path}")
            else:
                # Проверяем минимальное количество файлов если задано
                if dir_path in self.min_files_in_dir:
                    file_count = sum(1 for _ in dir_path.iterdir() if _.is_file())
                    min_required = self.min_files_in_dir[dir_path]
                    if file_count < min_required:
                        missing_dirs.append(str(dir_path))
                        self.log_debug(f"✗ В папке недостаточно файлов: {dir_path} ({file_count} из {min_required})")
                    else:
                        self.log_debug(f"✓ Папка в порядке: {dir_path} ({file_count} файлов)")
                else:
                    self.log_debug(f"✓ Папка присутствует: {dir_path}")

        # Проверяем главный скрипт
        main_script = self.manager_dir / "main.py"
        if not main_script.exists():
            missing_files.append(str(main_script))
            self.log_debug("✗ Главный скрипт main.py отсутствует")
        else:
            self.log_debug("✓ Главный скрипт main.py присутствует")

        return missing_files, missing_dirs
    def download_archive(self, temp_dir):
        """Скачивает архив zapret_manager"""
        self.current_task = "download"

        try:
            # Создаем временный файл для архива
            archive_path = os.path.join(temp_dir, "zapret_manager.tar.gz")

            # Скачиваем через curl
            self.update_progress("Скачивание архива...", 40)

            # Используем curl для скачивания
            curl_cmd = ['curl', '-L', '-o', archive_path, self.zapret_archive_url]

            if self.sudo_password:
                # Если есть пароль, используем sudo
                result = self.run_with_sudo(curl_cmd, "Скачивание архива...")
            else:
                # Без sudo
                result = subprocess.run(
                    curl_cmd,
                    capture_output=True,
                    text=True
                )
                result = {
                    'returncode': result.returncode,
                    'stdout': result.stdout,
                    'stderr': result.stderr
                }

            if not result or result['returncode'] != 0:
                self.log_debug(f"Ошибка скачивания: {result['stderr'] if result else 'No result'}")
                return None

            # Проверяем, что архив существует и не пустой
            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                self.log_debug("Скачанный архив пустой или не существует")
                return None

            self.update_progress("Архив успешно скачан", 50)
            return archive_path

        except Exception as e:
            self.log_debug(f"Ошибка при скачивании архива: {e}")
            return None

    def extract_archive(self, archive_path, temp_dir):
        """Извлекает архив"""
        self.current_task = "extract"

        try:
            self.update_progress("Извлечение архива...", 55)

            extract_dir = os.path.join(temp_dir, "zapret_extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Извлекаем архив
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(path=extract_dir)

            self.update_progress("Архив успешно извлечен", 60)
            return extract_dir

        except Exception as e:
            self.log_debug(f"Ошибка при извлечении архива: {e}")
            return None

    def restore_missing_files(self, extract_dir, missing_files, missing_dirs):
        """Восстанавливает недостающие файлы и папки"""
        self.current_task = "restore"

        restored_count = 0

        # Сначала создаем недостающие папки
        self.update_progress("Создание недостающих папок...", 65)
        for dir_path_str in missing_dirs:
            dir_path = Path(dir_path_str)
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                self.log_debug(f"✓ Создана папка: {dir_path}")
                restored_count += 1
            except Exception as e:
                self.log_debug(f"✗ Ошибка создания папки {dir_path}: {e}")

        # Восстанавливаем недостающие файлы
        self.update_progress("Восстановление файлов...", 70)

        # Ищем папку с распакованными файлами
        extracted_root = Path(extract_dir)
        source_dir = None

        # Пытаемся найти корневую папку с файлами
        for item in extracted_root.iterdir():
            if item.is_dir() and "Zapret_DPI_Manager" in item.name:
                source_dir = item
                break

        if not source_dir:
            # Если не нашли, используем саму extract_dir
            source_dir = extracted_root

        self.log_debug(f"Источник для восстановления: {source_dir}")

        # Копируем недостающие файлы
        for file_path_str in missing_files:
            file_path = Path(file_path_str)

            # Определяем относительный путь для поиска в архиве
            rel_path = None
            for base_path in [self.manager_dir, self.home_dir]:
                try:
                    rel_path = file_path.relative_to(base_path)
                    break
                except ValueError:
                    continue

            if not rel_path:
                self.log_debug(f"✗ Не могу определить относительный путь для: {file_path}")
                continue

            # Ищем файл в архиве
            source_file = source_dir / rel_path

            if source_file.exists():
                # Создаем целевую папку если её нет
                file_path.parent.mkdir(parents=True, exist_ok=True)

                try:
                    # Копируем файл
                    shutil.copy2(source_file, file_path)
                    self.log_debug(f"✓ Восстановлен файл: {file_path}")
                    restored_count += 1
                except Exception as e:
                    self.log_debug(f"✗ Ошибка копирования {file_path}: {e}")
            else:
                self.log_debug(f"✗ Файл не найден в архиве: {rel_path}")

        # Восстанавливаем содержимое папок с недостаточным количеством файлов
        self.update_progress("Восстановление содержимого папок...", 80)
        for dir_path_str in missing_dirs:
            dir_path = Path(dir_path_str)

            # Определяем относительный путь папки
            rel_dir_path = None
            for base_path in [self.manager_dir, self.home_dir]:
                try:
                    rel_dir_path = dir_path.relative_to(base_path)
                    break
                except ValueError:
                    continue

            if not rel_dir_path:
                continue

            # Ищем папку в архиве
            source_dir_path = source_dir / rel_dir_path

            if source_dir_path.exists() and source_dir_path.is_dir():
                # Копируем все файлы из папки
                copied_files = 0
                for source_file in source_dir_path.iterdir():
                    if source_file.is_file():
                        target_file = dir_path / source_file.name
                        try:
                            shutil.copy2(source_file, target_file)
                            copied_files += 1
                        except Exception as e:
                            self.log_debug(f"✗ Ошибка копирования {source_file.name}: {e}")

                if copied_files > 0:
                    self.log_debug(f"✓ Восстановлено {copied_files} файлов в папке: {dir_path}")
                    restored_count += copied_files

        return restored_count

    def fix_zapret_files(self):
        """Основная функция проверки и восстановления файлов"""
        self.log_debug("=== НАЧАЛО ПРОВЕРКИ И ВОССТАНОВЛЕНИЯ ФАЙЛОВ ===")

        try:
            # 1. Проверяем файлы (без окна прогресса)
            self.current_task = "check"
            missing_files, missing_dirs = self.check_files()

            if not missing_files and not missing_dirs:
                self.log_debug("Все файлы присутствуют, восстановление не требуется")
                return True  # Просто возвращаем True, без окон

            # 2. Показываем окно уведомления о недостающих файлах
            missing_count = len(missing_files) + len(missing_dirs)
            self.log_debug(f"Обнаружено {missing_count} недостающих элементов")

            # Показываем уведомление пользователю
            self.show_info("Проверка файлов Zapret DPI Manager",
                         f"Обнаружены отсутствующие или поврежденные файлы.\n\n"
                         f"Найдено недостающих элементов: {missing_count}\n"
                         f"• Файлы: {len(missing_files)}\n"
                         f"• Папки: {len(missing_dirs)}\n\n"
                         f"Будет выполнено автоматическое скачивание и восстановление файлов.")

            # 4. Создаем окно прогресса ТОЛЬКО при восстановлении
            if self.root:
                self.progress_window = self.create_progress_window("Восстановление файлов Zapret")
                if self.progress_window:
                    self.update_progress("Подготовка к восстановлению...", 0)

            # 5. Создаем временную директорию
            temp_dir = tempfile.mkdtemp(prefix="zapret_fix_")
            self.log_debug(f"Временная директория: {temp_dir}")

            try:
                # 6. Скачиваем архив
                self.update_progress("Скачивание архива с файлами...", 30)
                archive_path = self.download_archive(temp_dir)

                if not archive_path:
                    self.log_debug("Не удалось скачать архив")
                    self.close_progress_window()
                    self.show_info("Ошибка скачивания",
                                 "Не удалось скачать архив с файлами.\n"
                                 "Проверьте подключение к интернету.")
                    return False

                # 7. Извлекаем архив
                self.update_progress("Распаковка архива...", 50)
                extract_dir = self.extract_archive(archive_path, temp_dir)

                if not extract_dir:
                    self.log_debug("Не удалось извлечь архив")
                    self.close_progress_window()
                    self.show_info("Ошибка извлечения",
                                 "Не удалось извлечь архив.\n"
                                 "Архив может быть поврежден.")
                    return False

                # 8. Восстанавливаем файлы
                self.update_progress("Восстановление недостающих файлов...", 60)
                restored_count = self.restore_missing_files(extract_dir, missing_files, missing_dirs)

                # 9. Проверяем результат
                self.update_progress("Проверка результата...", 90)
                missing_files_after, missing_dirs_after = self.check_files()

                still_missing = len(missing_files_after) + len(missing_dirs_after)

                # 10. Очищаем временную папку
                self.current_task = "cleanup"
                self.update_progress("Очистка временных файлов...", 95)
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    self.log_debug(f"Очищена временная директория: {temp_dir}")
                except Exception as e:
                    self.log_debug(f"Ошибка очистки временной директории: {e}")

                # 11. Завершаем
                self.update_progress("Завершение...", 100)
                self.close_progress_window()

                if still_missing == 0:
                    self.show_info("Восстановление завершено",
                                 f"Все файлы успешно восстановлены!\n"
                                 f"Восстановлено элементов: {restored_count}")
                    return True
                else:
                    self.show_info("Восстановление частично завершено",
                                 f"Восстановлено {restored_count} элементов, но {still_missing} все еще отсутствуют.\n\n"
                                 f"Отсутствуют:\n"
                                 f"Файлы: {len(missing_files_after)}\n"
                                 f"Папки: {len(missing_dirs_after)}")
                    return False

            except Exception as e:
                self.log_debug(f"Ошибка в процессе восстановления: {e}")
                self.close_progress_window()
                self.show_info("Ошибка восстановления",
                             f"Произошла ошибка при восстановлении файлов:\n\n{str(e)}")
                return False

        except Exception as e:
            self.log_debug(f"Критическая ошибка: {e}")
            import traceback
            self.log_debug(f"Трейс ошибки: {traceback.format_exc()}")
            self.close_progress_window()
            self.show_info("Ошибка",
                         f"Произошла критическая ошибка:\n\n{str(e)}")
            return False

    def run_check(self):
        """Запускает проверку и восстановление файлов"""
        # Сначала быстрая проверка без окон
        missing_files, missing_dirs = self.check_files()

        # Если все файлы на месте - возвращаем True без окон
        if not missing_files and not missing_dirs:
            self.log_debug("Все файлы присутствуют")
            return True

        # Если файлы отсутствуют - запускаем полный процесс с окнами
        return self.fix_zapret_files()


def run_file_check(root_window=None):
    """
    Запускает проверку и восстановление файлов Zapret DPI Manager
    """
    checker = ZapretFileChecker(root_window)
    return checker.run_check()


if __name__ == "__main__":
    # Тестирование
    checker = ZapretFileChecker()
    result = checker.run_check()

    if result:
        print("✓ Проверка и восстановление файлов завершены успешно")
    else:
        print("✗ Проверка и восстановление файлов завершены с ошибками")
