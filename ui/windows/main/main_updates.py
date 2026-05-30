"""Уведомления и окно обновлений."""
import threading

from ui.windows.main.update_notification import show_update_notification_dialog


class MainUpdatesMixin:
    def show_update_notification(self, bundle_update_info):
        """Показывает окно уведомления об обновлениях с номерами версий"""
        self._last_bundle_update_info = bundle_update_info
        show_update_notification_dialog(self, bundle_update_info)

    def open_update_window(self, notification_window):
        """Открывает окно обновления с логом (описание релиза) и закрывает уведомление"""
        notification_window.destroy()
        pending = getattr(self, "_last_bundle_update_info", None)
        from ui.windows.update_window import show_update_window

        self.root.after(0, lambda p=pending: show_update_window(self.root, pending_update=p))

    def _prepare_and_show_updates(self):
        """Подготавливает и показывает окно обновления"""
        try:
            from core.zapret_updater import ZapretBundleUpdater
            from ui.windows.update_window import show_update_progress_window

            update_tasks = []

            try:
                bundle_updater = ZapretBundleUpdater()
                latest_b, bundle_info = bundle_updater.check_for_updates()
                if latest_b and bundle_info:
                    update_tasks.append({
                        'name': 'Zapret DPI Manager',
                        'updater_class': 'ZapretBundleUpdater',
                        'download_url': bundle_info.get('download_url'),
                    })
                    print("🔄 Доступно обновление")
            except Exception as e:
                print(f"⚠️ Проверка обновления: {e}")

            if not update_tasks:
                self.root.after(0, lambda: self.show_status_message("Нет доступных обновлений", warning=True))
                return

            self.root.after(0, lambda: show_update_progress_window(self.root, update_tasks))

            self.root.after(2000, self.check_service_status)

        except Exception as e:
            print(f"❌ Ошибка при подготовке обновления: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.show_status_message(f"Ошибка обновления: {e}", error=True))
