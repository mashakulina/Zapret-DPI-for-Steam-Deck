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

    def copy_with_overwrite(self, src, dst):
        """Копирует файлы с перезаписью, но не удаляет то, чего нет в src"""
        if os.path.isfile(src):
            # Просто копируем файл
            shutil.copy2(src, dst)
        elif os.path.isdir(src):
            # Создаем директорию если не существует
            if not os.path.exists(dst):
                os.makedirs(dst)

            # Копируем содержимое директории рекурсивно
            for item in os.listdir(src):
                src_item = os.path.join(src, item)
                dst_item = os.path.join(dst, item)

                if os.path.isfile(src_item):
                    # Копируем файл с перезаписью
                    shutil.copy2(src_item, dst_item)
                elif os.path.isdir(src_item):
                    # Рекурсивно копируем поддиректорию
                    self.copy_with_overwrite(src_item, dst_item)

    def update_manager(self, download_url, progress_callback=None):
        """Выполняет обновление менеджера - простая замена файлов"""
        try:
            print(f"Начинаю обновление менеджера...")

            if progress_callback:
                progress_callback("Скачивание обновления...", 10)

            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp()

            # Скачиваем архив
            archive_path = os.path.join(temp_dir, "update.tar.gz")
            print(f"Скачиваю архив в: {archive_path}")
            print(f"URL: {download_url}")

            urllib.request.urlretrieve(download_url, archive_path)

            if progress_callback:
                progress_callback("Распаковка...", 30)

            # Создаем временную директорию для распаковки
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Распаковываем архив
            print(f"Распаковываю архив в: {extract_dir}")
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)

            if progress_callback:
                progress_callback("Замена файлов...", 60)

            # Находим распакованную директорию
            extracted_items = os.listdir(extract_dir)
            print(f"В архиве найдено: {extracted_items}")

            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                # Если есть одна директория - используем ее как корень
                update_dir = os.path.join(extract_dir, extracted_items[0])
            else:
                # Иначе используем саму extract_dir
                update_dir = extract_dir

            print(f"Корень обновления: {update_dir}")
            print(f"Целевая директория: {self.manager_dir}")

            # Копируем все файлы из обновления в директорию менеджера
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self.manager_dir, item)

                print(f"Копирую: {src} -> {dst}")
                self.copy_with_overwrite(src, dst)

            if progress_callback:
                progress_callback("Настройка прав...", 90)

            # Устанавливаем права на выполнение для Python файлов
            for root, dirs, files in os.walk(self.manager_dir):
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        os.chmod(file_path, 0o755)
                        print(f"Установлены права на выполнение: {file_path}")

            # Очищаем временные файлы
            shutil.rmtree(temp_dir)

            if progress_callback:
                progress_callback("Обновление завершено!", 100)

            print("Обновление менеджера успешно завершено!")
            return True

        except Exception as e:
            print(f"Ошибка обновления менеджера: {e}")
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
