import os
import shutil
import subprocess
import sys

from core.updater_base import BaseUpdater
from core.manager_config import VERSION_CONFIG


class ManagerUpdater(BaseUpdater):
    def __init__(self):
        super().__init__(
            version_url=VERSION_CONFIG["version_url"],
            current_version=VERSION_CONFIG["current_version"],
            name="менеджера",
        )
        home_dir = os.path.expanduser("~")
        target_dir = os.path.join(home_dir, "Zapret_DPI_Manager")
        self.manager_dir = target_dir

        # Файлы и папки, которые НЕ должны заменяться при обновлении
        self.exclude_from_update = [
            "config.txt",
            "utils/chosen_strategies.txt",
            "utils/name_strategy.txt",
            "utils/working_strategies.txt",
            "files/lists/ipset-all_user.txt",
            "files/lists/ipset-exclude_user.txt",
            "files/lists/list-exclude_user.txt",
            "files/lists/list-general_user.txt",
        ]

        self.exclude_paths = [
            os.path.join(self.manager_dir, item) for item in self.exclude_from_update
        ]

    def should_exclude(self, file_path, extracted_root, extra_exclude_prefixes=None):
        """Проверяет, нужно ли исключить файл из обновления"""
        rel_path = os.path.relpath(file_path, extracted_root).replace("\\", "/")

        for prefix in extra_exclude_prefixes or ():
            p = prefix.strip("/").replace("\\", "/")
            if not p:
                continue
            if rel_path == p or rel_path.startswith(p + "/"):
                return True

        for exclude in self.exclude_from_update:
            if rel_path == exclude or rel_path.startswith(exclude + "/"):
                return True

        return False

    def copy_with_exclusions(self, src_dir, dst_dir, progress_callback=None, extra_exclude_prefixes=None):
        """
        Копирует файлы из src_dir в dst_dir с заменой,
        исключая файлы из списка exclude_from_update
        """
        try:
            total_files = 0
            copied_files = 0

            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self.should_exclude(file_path, src_dir, extra_exclude_prefixes):
                        total_files += 1

            print(f"Всего файлов для копирования: {total_files}")

            if total_files == 0:
                print("Нет файлов для копирования")
                return True

            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    src_file = os.path.join(root, file)

                    if self.should_exclude(src_file, src_dir, extra_exclude_prefixes):
                        print(f"Пропускаю (исключен): {os.path.relpath(src_file, src_dir)}")
                        continue

                    rel_path = os.path.relpath(src_file, src_dir)
                    dst_file = os.path.join(dst_dir, rel_path)

                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                    shutil.copy2(src_file, dst_file)
                    copied_files += 1

                    if progress_callback and total_files > 0:
                        progress = 70 + int(25 * (copied_files / total_files))  # 70-95%
                        progress_callback(f"Копирование файлов... ({copied_files}/{total_files})", progress)

                    print(f"Скопирован: {rel_path}")

            print(f"Скопировано {copied_files} из {total_files} файлов")
            return True

        except Exception as e:
            print(f"Ошибка при копировании файлов: {e}")
            import traceback
            traceback.print_exc()
            return False

    def apply_execute_bits_to_py_files(self, progress_callback=None):
        if progress_callback:
            progress_callback("Настройка прав...", 96)
        for root, dirs, files in os.walk(self.manager_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    os.chmod(file_path, 0o755)
                    print(f"Установлены права на выполнение: {file_path}")

    def apply_from_directory(
        self,
        update_root,
        progress_callback=None,
        extra_exclude_prefixes=None,
    ):
        """Накатывает файлы менеджера из уже распакованной директории (без скачивания)."""
        try:
            print(f"Накат менеджера из: {update_root}")
            if progress_callback:
                progress_callback("Применение обновления менеджера...", 70)
            if not self.copy_with_exclusions(
                update_root, self.manager_dir, progress_callback, extra_exclude_prefixes
            ):
                return False
            self.apply_execute_bits_to_py_files(progress_callback)
            if progress_callback:
                progress_callback("Обновление менеджера завершено", 100)
            return True
        except Exception as e:
            print(f"Ошибка наката менеджера: {e}")
            import traceback
            traceback.print_exc()
            return False

    def restart_manager(self):
        """Перезапускает менеджер"""
        try:
            main_script = os.path.join(self.manager_dir, "main.py")
            if os.path.exists(main_script):
                print(f"Перезапускаю менеджер: {main_script}")
                subprocess.Popen([sys.executable, main_script])
                return True
            print(f"Файл main.py не найден: {main_script}")
            return False
        except Exception as e:
            print(f"Ошибка перезапуска: {e}")
            return False
