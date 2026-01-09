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

        # Файлы, которые нужно сохранить при обновлении
        self.files_to_preserve = [
            os.path.join(self.manager_dir, "config.txt"),
            os.path.join(self.manager_dir, "utils", "chosen_strategies.txt"),
            os.path.join(self.manager_dir, "utils", "name_strategy.txt"),
            os.path.join(self.manager_dir, "files", "lists", "ipset-all2.txt"),
            os.path.join(self.manager_dir, "files", "lists", "other2.txt"),
            os.path.join(self.manager_dir, "files", "lists", "working_strategies.txt")
        ]

        # Временная директория для сохранения файлов
        self.temp_preserve_dir = None

    def preserve_config_files(self):
        """Сохраняет конфигурационные файлы во временную директорию"""
        try:
            # Создаем временную директорию для сохранения
            self.temp_preserve_dir = tempfile.mkdtemp(prefix="zapret_preserve_")
            print(f"Временная директория для сохранения: {self.temp_preserve_dir}")

            preserved_files = []

            for file_path in self.files_to_preserve:
                if os.path.exists(file_path):
                    # Создаем относительный путь для сохранения структуры
                    rel_path = os.path.relpath(file_path, self.manager_dir)
                    preserve_path = os.path.join(self.temp_preserve_dir, rel_path)

                    # Создаем директорию если нужно
                    os.makedirs(os.path.dirname(preserve_path), exist_ok=True)

                    # Копируем файл
                    shutil.copy2(file_path, preserve_path)
                    preserved_files.append(file_path)
                    print(f"Сохранен: {file_path}")
                else:
                    print(f"Файл не существует (будет пропущен): {file_path}")

            return preserved_files

        except Exception as e:
            print(f"Ошибка при сохранении файлов: {e}")
            import traceback
            traceback.print_exc()
            return []

    def restore_config_files(self):
        """Восстанавливает сохраненные конфигурационные файлы"""
        try:
            if not self.temp_preserve_dir or not os.path.exists(self.temp_preserve_dir):
                print("Нет сохраненных файлов для восстановления")
                return False

            restored_files = []

            # Проходим по всем сохраненным файлам
            for root, dirs, files in os.walk(self.temp_preserve_dir):
                for file in files:
                    # Полный путь к сохраненному файлу
                    preserved_file = os.path.join(root, file)

                    # Восстанавливаем оригинальный путь
                    rel_path = os.path.relpath(preserved_file, self.temp_preserve_dir)
                    original_path = os.path.join(self.manager_dir, rel_path)

                    # Создаем директорию если нужно
                    os.makedirs(os.path.dirname(original_path), exist_ok=True)

                    # Копируем файл обратно
                    shutil.copy2(preserved_file, original_path)
                    restored_files.append(original_path)
                    print(f"Восстановлен: {original_path}")

            # Очищаем временную директорию
            shutil.rmtree(self.temp_preserve_dir)
            self.temp_preserve_dir = None

            print(f"Восстановлено {len(restored_files)} файлов")
            return True

        except Exception as e:
            print(f"Ошибка при восстановлении файлов: {e}")
            import traceback
            traceback.print_exc()
            return False

    def clean_manager_directory(self, exclude_patterns=None):
        """Очищает директорию менеджера, кроме указанных файлов"""
        try:
            if not os.path.exists(self.manager_dir):
                print(f"Директория не существует: {self.manager_dir}")
                return True

            print(f"Очищаю директорию: {self.manager_dir}")

            # Удаляем все, кроме папок с сохраненными файлами
            for item in os.listdir(self.manager_dir):
                item_path = os.path.join(self.manager_dir, item)

                # Проверяем, нужно ли сохранять этот файл/папку
                should_preserve = False
                for preserve_file in self.files_to_preserve:
                    # Если текущий элемент является частью пути к сохраняемому файлу
                    if item_path in preserve_file or os.path.commonpath([item_path, preserve_file]) == item_path:
                        should_preserve = True
                        break

                if should_preserve:
                    print(f"Пропускаю (для сохранения): {item_path}")
                    continue

                # Удаляем элемент
                try:
                    if os.path.isfile(item_path) or os.path.islink(item_path):
                        os.remove(item_path)
                        print(f"Удален файл: {item_path}")
                    elif os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                        print(f"Удалена директория: {item_path}")
                except Exception as e:
                    print(f"Не удалось удалить {item_path}: {e}")

            # Теперь очищаем поддиректории, но сохраняем конфигурационные файлы
            # Проходим по всем файлам в директории
            for root, dirs, files in os.walk(self.manager_dir):
                for file in files:
                    file_path = os.path.join(root, file)

                    # Проверяем, нужно ли сохранять этот файл
                    should_preserve = False
                    for preserve_file in self.files_to_preserve:
                        if os.path.samefile(file_path, preserve_file) if os.path.exists(preserve_file) else file_path == preserve_file:
                            should_preserve = True
                            break

                    if not should_preserve:
                        try:
                            os.remove(file_path)
                            print(f"Удален файл: {file_path}")
                        except Exception as e:
                            print(f"Не удалось удалить {file_path}: {e}")

                # Удаляем пустые директории (кроме корневой)
                for dir_name in dirs[:]:  # Копируем список для безопасной модификации
                    dir_path = os.path.join(root, dir_name)

                    # Проверяем, содержит ли директория сохраняемые файлы
                    contains_preserved = False
                    for preserve_file in self.files_to_preserve:
                        if dir_path in preserve_file:
                            contains_preserved = True
                            break

                    # Если директория пуста и не содержит сохраняемых файлов
                    if not contains_preserved and not os.listdir(dir_path):
                        try:
                            os.rmdir(dir_path)
                            print(f"Удалена пустая директория: {dir_path}")
                        except Exception as e:
                            print(f"Не удалось удалить директорию {dir_path}: {e}")

            return True

        except Exception as e:
            print(f"Ошибка при очистке директории: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_manager(self, download_url, progress_callback=None):
        """Выполняет полное обновление менеджера с сохранением конфигураций"""
        try:
            print(f"Начинаю обновление менеджера...")

            # Шаг 1: Сохраняем конфигурационные файлы
            if progress_callback:
                progress_callback("Сохранение конфигураций...", 10)

            preserved_files = self.preserve_config_files()
            print(f"Сохранено {len(preserved_files)} файлов")

            # Шаг 2: Очищаем директорию менеджера
            if progress_callback:
                progress_callback("Очистка директории...", 20)

            self.clean_manager_directory()

            # Шаг 3: Скачиваем архив
            if progress_callback:
                progress_callback("Скачивание обновления...", 30)

            # Создаем временную директорию
            temp_dir = tempfile.mkdtemp(prefix="zapret_update_")

            # Скачиваем архив
            archive_path = os.path.join(temp_dir, "update.tar.gz")
            print(f"Скачиваю архив в: {archive_path}")
            print(f"URL: {download_url}")

            urllib.request.urlretrieve(download_url, archive_path)

            # Шаг 4: Распаковываем архив
            if progress_callback:
                progress_callback("Распаковка...", 50)

            # Создаем временную директорию для распаковки
            extract_dir = os.path.join(temp_dir, "extracted")
            os.makedirs(extract_dir, exist_ok=True)

            # Распаковываем архив
            print(f"Распаковываю архив в: {extract_dir}")
            with tarfile.open(archive_path, 'r:gz') as tar:
                tar.extractall(extract_dir)

            # Шаг 5: Находим корень обновления
            extracted_items = os.listdir(extract_dir)
            print(f"В архиве найдено: {extracted_items}")

            if len(extracted_items) == 1 and os.path.isdir(os.path.join(extract_dir, extracted_items[0])):
                update_dir = os.path.join(extract_dir, extracted_items[0])
            else:
                update_dir = extract_dir

            print(f"Корень обновления: {update_dir}")
            print(f"Целевая директория: {self.manager_dir}")

            # Шаг 6: Копируем обновление
            if progress_callback:
                progress_callback("Копирование файлов...", 70)

            # Копируем все файлы из обновления
            print(f"Копирую содержимое из {update_dir} в {self.manager_dir}")

            # Создаем целевую директорию если не существует
            os.makedirs(self.manager_dir, exist_ok=True)

            # Копируем все файлы и директории
            for item in os.listdir(update_dir):
                src = os.path.join(update_dir, item)
                dst = os.path.join(self.manager_dir, item)

                print(f"Копирую: {src} -> {dst}")

                if os.path.isfile(src):
                    shutil.copy2(src, dst)
                elif os.path.isdir(src):
                    shutil.copytree(src, dst, dirs_exist_ok=True)

            # Шаг 7: Восстанавливаем конфигурации
            if progress_callback:
                progress_callback("Восстановление конфигураций...", 85)

            self.restore_config_files()

            # Шаг 8: Устанавливаем права
            if progress_callback:
                progress_callback("Настройка прав...", 95)

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

            # Пытаемся восстановить конфигурации в случае ошибки
            if self.temp_preserve_dir and os.path.exists(self.temp_preserve_dir):
                print("Пытаюсь восстановить конфигурации после ошибки...")
                self.restore_config_files()

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
