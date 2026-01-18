import os
import shutil
import subprocess
import sys
import tempfile
import tarfile
import urllib.request
from core.updater_base import BaseUpdater
from core.manager_config import MANAGER_CONFIG

class ManagerUpdater(BaseUpdater):
    def __init__(self):
        super().__init__(
            version_url=MANAGER_CONFIG["version_url"],
            current_version=MANAGER_CONFIG["current_version"],
            name="менеджера"
        )
        self.manager_dir = "/home/deck/Zapret_DPI_Manager"

        # Файлы и папки, которые НЕ должны заменяться при обновлении
        self.exclude_from_update = [
            "config.txt",
            "utils/chosen_strategies.txt",
            "utils/name_strategy.txt",
            "utils/working_strategies.txt",
            "files/lists/ipset-all2.txt",
            "files/lists/other2.txt"
        ]

        # Полные пути для удобства
        self.exclude_paths = [
            os.path.join(self.manager_dir, item) for item in self.exclude_from_update
        ]

    def should_exclude(self, file_path, extracted_root):
        """Проверяет, нужно ли исключить файл из обновления"""
        # Получаем относительный путь от корня распакованного архива
        rel_path = os.path.relpath(file_path, extracted_root)

        # Проверяем, находится ли файл в списке исключений
        for exclude in self.exclude_from_update:
            if rel_path == exclude or rel_path.startswith(exclude + '/'):
                return True

        return False

    def copy_with_exclusions(self, src_dir, dst_dir, progress_callback=None):
        """
        Копирует файлы из src_dir в dst_dir с заменой,
        исключая файлы из списка exclude_from_update
        """
        try:
            total_files = 0
            copied_files = 0

            # Считаем общее количество файлов для прогресса
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if not self.should_exclude(file_path, src_dir):
                        total_files += 1

            print(f"Всего файлов для копирования: {total_files}")

            if total_files == 0:
                print("Нет файлов для копирования")
                return True

            # Копируем файлы с учетом исключений
            for root, dirs, files in os.walk(src_dir):
                for file in files:
                    src_file = os.path.join(root, file)

                    # Пропускаем исключенные файлы
                    if self.should_exclude(src_file, src_dir):
                        print(f"Пропускаю (исключен): {os.path.relpath(src_file, src_dir)}")
                        continue

                    # Получаем относительный путь
                    rel_path = os.path.relpath(src_file, src_dir)
                    dst_file = os.path.join(dst_dir, rel_path)

                    # Создаем целевую директорию если нужно
                    os.makedirs(os.path.dirname(dst_file), exist_ok=True)

                    # Копируем файл
                    shutil.copy2(src_file, dst_file)
                    copied_files += 1

                    # Обновляем прогресс
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

    def update_manager(self, download_url, progress_callback=None):
        """Выполняет обновление менеджера путем замены файлов с учетом исключений"""
        try:
            print(f"Начинаю обновление менеджера...")
            print(f"Директория менеджера: {self.manager_dir}")

            # Шаг 1: Создаем временные директории
            if progress_callback:
                progress_callback("Подготовка...", 5)

            temp_dir = tempfile.mkdtemp(prefix="zapret_update_")
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            print(f"Временная директория: {temp_dir}")

            # Шаг 2: Скачиваем архив
            if progress_callback:
                progress_callback("Скачивание обновления...", 20)

            archive_path = os.path.join(temp_dir, "update.tar.gz")
            print(f"Скачиваю архив в: {archive_path}")
            print(f"URL: {download_url}")

            def download_progress(count, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = min(int(count * block_size * 100 / total_size), 100)
                    progress = 20 + int(30 * (percent / 100))  # 20-50%
                    progress_callback(f"Скачивание... {percent}%", progress)

            urllib.request.urlretrieve(download_url, archive_path, download_progress)

            # Шаг 3: Распаковываем архив
            if progress_callback:
                progress_callback("Распаковка архива...", 50)

            print(f"Распаковываю архив в: {extract_dir}")
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)

            # Шаг 4: Находим корень обновления
            extracted_items = os.listdir(extract_dir)
            print(f"В архиве найдено: {extracted_items}")

            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                update_root = os.path.join(extract_dir, extracted_items[0])
            else:
                update_root = extract_dir

            print(f"Корень обновления: {update_root}")

            # Шаг 5: Копируем файлы с заменой (кроме исключенных)
            if progress_callback:
                progress_callback("Применение обновления...", 70)

            success = self.copy_with_exclusions(update_root, self.manager_dir, progress_callback)

            if not success:
                raise Exception("Ошибка при копировании файлов")

            # Шаг 6: Устанавливаем права на выполнение
            if progress_callback:
                progress_callback("Настройка прав...", 96)

            # Устанавливаем права на выполнение для Python файлов
            for root, dirs, files in os.walk(self.manager_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        os.chmod(file_path, 0o755)
                        print(f"Установлены права на выполнение: {file_path}")

            # Шаг 7: Очищаем временные файлы
            shutil.rmtree(temp_dir)

            if progress_callback:
                progress_callback("Обновление завершено!", 100)

            print("Обновление менеджера успешно завершено!")
            return True

        except Exception as e:
            print(f"Ошибка обновления менеджера: {e}")
            import traceback
            traceback.print_exc()

            # В случае ошибки не нужно восстанавливать файлы,
            # так как оригинальная директория не была удалена

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
