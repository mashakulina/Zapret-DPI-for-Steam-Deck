#!/usr/bin/env python3
import subprocess
import tkinter as tk
import os
import sys
import tempfile
import shutil
import time
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox

from core.app_logging import get_error_logger
from core.dpi_utils import place_toplevel_centered_on_parent
from core.runtime_resources import REQUIRED_RESOURCE_FILES
from core.zapret_updater import extract_bundle, find_bundle_root, get_bundle_download_url


class ZapretFileChecker:
    def __init__(
        self,
        root_window=None,
        *,
        show_info_fn: Callable[[str, str], None] | None = None,
    ):
        self.root = root_window
        self._show_info_fn = show_info_fn
        self.progress_window = None
        self.current_task = ""
        self.sudo_password = None
        self.debug_log = []  # Лог для дебага

        # URL единого архива (zapret_updater.tar.gz) подтягивается по требованию
        # из version.txt — отдельных fallback-каналов нет.
        self.zapret_archive_url: str | None = None

        # Базовые пути
        self.home_dir = Path.home()
        self.manager_dir = self.home_dir / "Zapret_DPI_Manager"

        # Проверяем конкретный состав поставки, а не число файлов прежней версии.
        self.required_files = [self.manager_dir / name for name in REQUIRED_RESOURCE_FILES]
        self.required_dirs = sorted({path.parent for path in self.required_files
                                     if path.parent != self.manager_dir})

    def log_debug(self, message):
        """Добавляет сообщение в лог дебага"""
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}"
        self.debug_log.append(log_msg)
        print(log_msg)

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

    def create_progress_window(self, title="Проверка файлов"):
        """Создает окно прогресса"""
        if not self.root:
            return None

        progress_window = tk.Toplevel(self.root)
        progress_window.title(title)
        progress_window.configure(bg='#182030')
        progress_window.resizable(False, False)
        progress_window.transient(self.root)

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
            if not file_path.is_file():
                missing_files.append(str(file_path))
                self.log_debug(f"✗ Отсутствует файл: {file_path}")
            else:
                self.log_debug(f"✓ Файл присутствует: {file_path}")

        # Отсутствующие каталоги также показываются в результате проверки.
        self.update_progress("Проверка папок...", 30)
        for dir_path in self.required_dirs:
            if not dir_path.is_dir():
                missing_dirs.append(str(dir_path))
                self.log_debug(f"✗ Отсутствует папка: {dir_path}")
            else:
                self.log_debug(f"✓ Папка присутствует: {dir_path}")

        return missing_files, missing_dirs

    def download_archive(self, temp_dir):
        """Скачивает единый архив zapret_updater.tar.gz по ссылке из version.txt"""
        self.current_task = "download"

        try:
            if not self.zapret_archive_url:
                self.zapret_archive_url = get_bundle_download_url()

            if not self.zapret_archive_url:
                self.log_debug("Не удалось получить URL архива из version.txt")
                get_error_logger().error(
                    "Восстановление файлов менеджера: не удалось получить URL из version.txt"
                )
                return None

            archive_path = os.path.join(temp_dir, "zapret_updater.tar.gz")

            self.update_progress("Скачивание архива...", 40)

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
                err = result['stderr'] if result else 'No result'
                self.log_debug(f"Ошибка скачивания: {err}")
                get_error_logger().error(
                    "Восстановление файлов менеджера: ошибка curl (%s): %s",
                    self.zapret_archive_url,
                    err,
                )
                return None

            # Проверяем, что архив существует и не пустой
            if not os.path.exists(archive_path) or os.path.getsize(archive_path) == 0:
                self.log_debug("Скачанный архив пустой или не существует")
                get_error_logger().error(
                    "Восстановление файлов менеджера: архив пуст или отсутствует после curl"
                )
                return None

            self.update_progress("Архив успешно скачан", 50)
            return archive_path

        except Exception as e:
            self.log_debug(f"Ошибка при скачивании архива: {e}")
            get_error_logger().exception("Восстановление файлов менеджера: скачивание архива")
            return None

    def extract_archive(self, archive_path, temp_dir):
        """Извлекает архив"""
        self.current_task = "extract"

        try:
            self.update_progress("Извлечение архива...", 55)

            extract_dir = os.path.join(temp_dir, "zapret_extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Извлекаем архив
            extract_bundle(archive_path, extract_dir)

            self.update_progress("Архив успешно извлечен", 60)
            return extract_dir

        except Exception as e:
            self.log_debug(f"Ошибка при извлечении архива: {e}")
            return None

    def restore_missing_files(self, extract_dir, missing_files, missing_dirs):
        """Восстанавливает только отсутствующие обязательные файлы поставки."""
        self.current_task = "restore"
        bundle_root = find_bundle_root(str(extract_dir))
        source_dir = Path(bundle_root or extract_dir)
        self.log_debug(f"Источник для восстановления: {source_dir}")
        requested_files = {Path(path) for path in missing_files}
        requested_dirs = {Path(path) for path in missing_dirs}
        restored_count = 0

        self.update_progress("Восстановление недостающих файлов...", 70)
        for target in self.required_files:
            if target not in requested_files and not any(target.is_relative_to(path) for path in requested_dirs):
                continue
            # Проверяем повторно: между проверкой и скачиванием файл мог появиться.
            # Существующие пользовательские списки, настройки и стратегии не заменяем.
            if os.path.lexists(target):
                continue
            relative = target.relative_to(self.manager_dir)
            source = source_dir / relative
            if not source.is_file() or source.is_symlink():
                self.log_debug(f"✗ Файл не найден в архиве: {relative}")
                continue
            if not target.resolve().is_relative_to(self.manager_dir.resolve()):
                self.log_debug(f"✗ Путь за пределами папки программы: {relative}")
                continue
            if not source.resolve().is_relative_to(source_dir.resolve()):
                self.log_debug(f"✗ Путь за пределами архива: {relative}")
                continue
            created = False
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                # Режим x защищает от замены файла, созданного уже после lexists.
                with source.open('rb') as source_file, target.open('xb') as target_file:
                    created = True
                    shutil.copyfileobj(source_file, target_file)
                shutil.copystat(source, target)
                restored_count += 1
                self.log_debug(f"✓ Восстановлен файл: {target}")
            except FileExistsError:
                continue
            except OSError as error:
                if created:
                    target.unlink(missing_ok=True)
                self.log_debug(f"✗ Ошибка восстановления {relative}: {error}")
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


def run_file_check(root_window=None, *, show_info_fn: Callable[[str, str], None] | None = None):
    """
    Запускает проверку и восстановление файлов Zapret DPI Manager.

    Для кастомных диалогов приложения используйте ui.integrations.file_check.run_file_check.
    """
    checker = ZapretFileChecker(root_window, show_info_fn=show_info_fn)
    return checker.run_check()


if __name__ == "__main__":
    # Тестирование
    checker = ZapretFileChecker()
    result = checker.run_check()

    if result:
        print("✓ Проверка и восстановление файлов завершены успешно")
    else:
        print("✗ Проверка и восстановление файлов завершены с ошибками")
