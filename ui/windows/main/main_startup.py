"""Проверки при запуске и фоновая проверка обновлений."""
import os
import threading
import tkinter as tk

from ui.integrations.dependency_check import run_dependency_check
from ui.integrations.zapret_check import run_zapret_check


class MainStartupMixin:
    def check_dependencies_on_startup(self):
        """Проверяет зависимости при запуске программы"""
        print("=== НАЧАЛО ПРОВЕРКИ ЗАВИСИМОСТЕЙ ===")

        # ВАЖНО: Не скрываем окно, а делаем его видимым
        # Обновляем окно, чтобы оно было готово к отображению диалогов
        self.root.update()
        print("Главное окно обновлено")

        # Запускаем проверку зависимостей (окно видимо)
        print("Запуск run_dependency_check...")
        try:
            dependencies_ok = run_dependency_check(self.root)
            print(f"Результат проверки зависимостей: {dependencies_ok}")
        except Exception as e:
            print(f"ОШИБКА при проверке зависимостей: {e}")
            import traceback
            traceback.print_exc()
            dependencies_ok = False

        print("=== КОНЕЦ ПРОВЕРКИ ЗАВИСИМОСТЕЙ ===")

        return dependencies_ok

    def check_zapret_on_startup(self):
        """Проверяет наличие zapret при запуске программы"""
        print("=== НАЧАЛО ПРОВЕРКИ ZAPRET ===")

        # Делаем окно видимым
        self.root.update()

        # Запускаем проверку zapret
        print("Запуск проверки Zapret...")
        try:
            zapret_ok = run_zapret_check(self.root)
            print(f"Результат проверки Zapret: {zapret_ok}")
        except Exception as e:
            print(f"ОШИБКА при проверке Zapret: {e}")
            import traceback
            traceback.print_exc()
            zapret_ok = False

        print("=== КОНЕЦ ПРОВЕРКИ ZAPRET ===")

        return zapret_ok

    def ensure_lists_files(self):
        """Проверяет наличие обязательных файлов в files/lists/ и создаёт их при отсутствии."""
        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        lists_dir = os.path.join(manager_dir, "files", "lists")
        required_files = [
            "ipset-all_user.txt",
            "ipset-exclude_user.txt",
            "list-exclude_user.txt",
            "list-general_user.txt",
        ]
        if not os.path.isdir(lists_dir):
            os.makedirs(lists_dir, exist_ok=True)
        for filename in required_files:
            path = os.path.join(lists_dir, filename)
            if not os.path.isfile(path):
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        pass
                except OSError as e:
                    print(f"Не удалось создать {filename}: {e}")

    # def check_files_on_startup(self):
    #     """Проверяет наличие zapret при запуске программы"""
    #     print("=== НАЧАЛО ПРОВЕРКИ ФАЙЛОВ ===")
    #
    #     # Делаем окно видимым
    #     self.root.update()
    #
    #     # Запускаем проверку zapret
    #     print("Запуск проверки файлов...")
    #     try:
    #         files_ok = run_file_check(self.root)
    #         print(f"Результат проверки файлов: {files_ok}")
    #     except Exception as e:
    #         print(f"ОШИБКА при проверке файлов: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         files_ok = False
    #
    #     print("=== КОНЕЦ ПРОВЕРКИ ФАЙЛОВ ===")
    #
    #     return files_ok

    def check_updates_on_startup(self):
        """Проверяет обновления при запуске программы"""
        # Запускаем в отдельном потоке, чтобы не блокировать UI
        thread = threading.Thread(target=self._check_updates_using_updater, daemon=True)
        thread.start()

    def _check_updates_using_updater(self):
        """Проверяет обновления с использованием существующего Updater'а"""
        try:
            from core.manager_updater import ManagerUpdater
            from core.zapret_updater import ZapretUpdater

            manager_update_info = None
            zapret_update_info = None

            # Проверка обновления менеджера
            try:
                manager_updater = ManagerUpdater()
                latest_version, update_info = manager_updater.check_for_updates()

                if latest_version and update_info:
                    manager_update_info = {
                        'current': manager_updater.current_version,
                        'available': latest_version,
                        'name': 'менеджера'
                    }
                    print(f"🔄 Обновление менеджера найдено: {manager_updater.current_version} → {latest_version}")
                else:
                    print(f"✅ Версия менеджера актуальна: {manager_updater.current_version}")

            except Exception as e:
                print(f"⚠️ Не удалось проверить обновление менеджера: {e}")
                import traceback
                traceback.print_exc()

            # Проверка обновления службы Zapret
            try:
                zapret_updater = ZapretUpdater()
                latest_version, update_info = zapret_updater.check_for_updates()

                if latest_version and update_info:
                    zapret_update_info = {
                        'current': zapret_updater.current_version,
                        'available': latest_version,
                        'name': 'zapret службы'
                    }
                    print(f"🔄 Обновление службы Zapret найдено: {zapret_updater.current_version} → {latest_version}")
                else:
                    print(f"✅ Версия службы Zapret актуальна: {zapret_updater.current_version}")

            except Exception as e:
                print(f"⚠️ Не удалось проверить обновление службы Zapret: {e}")
                import traceback
                traceback.print_exc()

            # Показываем уведомление если есть обновления
            if manager_update_info or zapret_update_info:
                print(f"\n🎯 Найдены обновления! Показываю уведомление...")
                self.root.after(0, lambda: self.show_update_notification(
                    manager_update_info,
                    zapret_update_info
                ))
            else:
                print(f"\n✅ Все компоненты обновлены")

        except Exception as e:
            print(f"❌ Ошибка при проверке обновлений: {e}")
            import traceback
            traceback.print_exc()
