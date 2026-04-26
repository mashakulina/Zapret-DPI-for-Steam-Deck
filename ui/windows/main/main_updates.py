"""Уведомления и окно обновлений."""
import threading

from ui.windows.main.update_notification import show_update_notification_dialog


class MainUpdatesMixin:
    def show_update_notification(self, manager_update_info, zapret_update_info):
        """Показывает окно уведомления об обновлениях с номерами версий"""
        show_update_notification_dialog(self, manager_update_info, zapret_update_info)

    def open_update_window(self, notification_window):
        """Открывает окно обновления и закрывает уведомление"""
        notification_window.destroy()

        # Запускаем процесс обновления
        thread = threading.Thread(target=self._prepare_and_show_updates, daemon=True)
        thread.start()

    def _prepare_and_show_updates(self):
        """Подготавливает и показывает окно обновления"""
        try:
            from core.manager_updater import ManagerUpdater
            from core.zapret_updater import ZapretUpdater
            from ui.windows.update_window import show_update_progress_window

            # Получаем информацию об обновлениях
            update_tasks = []

            # Проверяем обновление менеджера
            try:
                manager_updater = ManagerUpdater()
                latest_manager_version, manager_update_info = manager_updater.check_for_updates()

                if latest_manager_version and manager_update_info:
                    update_tasks.append({
                        'name': 'Zapret DPI Manager',
                        'updater_class': 'ManagerUpdater',
                        'download_url': manager_update_info.get('download_url')
                    })
                    print(f"🔄 Обновление менеджера доступно")

            except Exception as e:
                print(f"⚠️ Не удалось получить информацию об обновлении менеджера: {e}")

            # Проверяем обновление службы Zapret
            try:
                zapret_updater = ZapretUpdater()
                latest_zapret_version, zapret_update_info = zapret_updater.check_for_updates()

                if latest_zapret_version and zapret_update_info:
                    update_tasks.append({
                        'name': 'Служба Zapret',
                        'updater_class': 'ZapretUpdater',
                        'download_url': zapret_update_info.get('download_url')
                    })
                    print(f"🔄 Обновление службы Zapret доступно")

            except Exception as e:
                print(f"⚠️ Не удалось получить информацию об обновлении службы Zapret: {e}")

            if not update_tasks:
                self.root.after(0, lambda: self.show_status_message("Нет доступных обновлений", warning=True))
                return

            # Показываем окно прогресса обновления
            self.root.after(0, lambda: show_update_progress_window(self.root, update_tasks))

            # После завершения обновления проверяем статус службы
            self.root.after(2000, self.check_service_status)

        except Exception as e:
            print(f"❌ Ошибка при подготовке обновления: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.show_status_message(f"Ошибка обновления: {e}", error=True))
