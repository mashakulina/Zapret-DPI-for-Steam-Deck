"""systemd/zapret: статус, переключение, sudo, статусная строка."""
import subprocess
import threading
import tkinter as tk

from core.app_logging import LOG_FILE_PATH
from ui.windows.sudo_password_window import SudoPasswordWindow


def _shorten_service_error_message(message: str, limit: int = 700) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 60].rstrip() + f"\n… Полный вывод: {LOG_FILE_PATH}"


class MainServiceMixin:
    def restart_zapret_service_properly(self, event=None):
        """Правильный перезапуск службы - использует тот же механизм что и другие кнопки"""
        if self.restarting:
            return

        # 1. Проверяем пароль ЧЕРЕЗ ensure_sudo_password (как другие кнопки)
        if not self.ensure_sudo_password():
            return  # Если пароль не получен - выходим

        # 2. Запускаем перезапуск
        self._perform_restart()

    def _perform_restart(self):
        """Выполняет перезапуск службы"""
        try:
            # Сначала блокируем UI
            self.restarting = True
            self.restart_icon.config(state=tk.DISABLED)

            # Показываем сообщение
            self.show_status_message("Перезапуск службы Zapret...")

            # Обновляем окно чтобы оно было видимым
            self.root.update_idletasks()
            self.root.update()

            # Запускаем в отдельном потоке
            thread = threading.Thread(target=self._restart_zapret_thread, daemon=True)
            thread.start()

        except Exception as e:
            print(f"Ошибка при запуске перезапуска: {e}")
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
            self.restarting = False
            self.restart_icon.config(state=tk.NORMAL)

    def _restart_zapret_thread(self):
        """Поток для перезапуска службы"""
        try:
            # Запускаем перезапуск службы
            success, message = self.service_manager.restart_service()

            if success:
                self.root.after(0, lambda: self.show_status_message(
                    "Служба Zapret успешно перезапущена", success=True))
            else:
                self.root.after(0, lambda m=message: self.show_status_message(
                    f"Ошибка: {_shorten_service_error_message(m)}", error=True))

        except Exception as e:
            self.root.after(0, lambda: self.show_status_message(
                f"Ошибка перезапуска службы: {e}", error=True))
        finally:
            # Восстанавливаем UI
            self.root.after(0, lambda: self.restart_icon.config(state=tk.NORMAL))
            self.restarting = False

            # Обновляем статус службы через 1 секунду
            self.root.after(1000, self.check_service_status)
    def ensure_sudo_password(self):
        """Проверяет и получает пароль sudo если нужно"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return False

        if not self.service_manager.sudo_password:
            # Убедимся, что окно действительно видимо
            self.root.update_idletasks()

            # Проверяем видимость окна
            if not self.root.winfo_viewable():
                self.root.deiconify()  # Делаем окно видимым
                self.root.update_idletasks()

            # Даем время на отрисовку
            self.root.update()

            # Маленькая задержка чтобы окно стало видимым
            import time
            time.sleep(0.1)

            # Показываем окно ввода пароля
            password_window = SudoPasswordWindow(
                self.root,
                on_password_valid=lambda pwd: self.service_manager.set_sudo_password(pwd)
            )
            password = password_window.run()

            if not password:
                self.show_status_message("Требуется пароль sudo", warning=True)
                return False

        return True


    def check_service_status(self):
        """Проверяет статус службы Zapret"""
        try:
            # Проверяем статус службы
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True
            )

            status_output = result.stdout.strip()

            if result.returncode == 0 and status_output == "active":
                # Служба активна
                self.service_running = True
                self.status_indicator.config(text="⬤", fg='#30d158')  # Зеленый круг
                self.zapret_button.config(text="Остановить Zapret DPI")
            elif result.returncode == 3 and status_output == "inactive":
                # Служба неактивна
                self.service_running = False
                self.status_indicator.config(text="⬤", fg='#ff3b30')  # Красный круг
                self.zapret_button.config(text="Запустить Zapret DPI")
            elif result.returncode == 4:  # Код возврата 4 означает "неактивен" или "не существует"
                self.service_running = False
                self.status_indicator.config(text="⬤", fg='#ff3b30')  # Красный круг
                self.zapret_button.config(text="Запустить Zapret DPI")
            else:
                # Неизвестный статус
                self.service_running = False
                self.status_indicator.config(text="⬤", fg='#ff9500')  # Оранжевый круг
                self.zapret_button.config(text="Запустить Zapret DPI")

            # Теперь проверяем автозапуск ОТДЕЛЬНО
            self.check_autostart_status()

        except Exception as e:
            print(f"Ошибка проверки статуса службы: {e}")
            self.service_running = False
            self.status_indicator.config(text="⬤", fg='#ff9500')  # Оранжевый круг
            # Все равно проверяем автозапуск
            self.check_autostart_status()

    def check_autostart_status(self):
        """Проверяет и обновляет статус автозапуска"""
        try:
            # Проверяем статус автозапуска
            result = subprocess.run(
                ["systemctl", "is-enabled", "zapret"],
                capture_output=True,
                text=True
            )

            # systemctl is-enabled возвращает:
            # - 0: enabled (включен)
            # - 1: disabled (отключен)
            # - другие коды: ошибка или не существует

            if result.returncode == 0:
                # Автозапуск включен
                self.autostart_enabled = True
                self.autostart_button.config(text="Отключить автозапуск")
                # print("DEBUG: Автозапуск включен")
            elif result.returncode == 1:
                # Автозапуск отключен
                self.autostart_enabled = False
                self.autostart_button.config(text="Включить автозапуск")
                # print("DEBUG: Автозапуск отключен")
            else:
                # Неизвестный статус (служба может не существовать)
                self.autostart_enabled = False
                self.autostart_button.config(text="Включить автозапуск")
                # print(f"DEBUG: Статус автозапуска неизвестен, код возврата: {result.returncode}")
                # print(f"DEBUG: Вывод: {result.stdout.strip()}")
                # print(f"DEBUG: Ошибка: {result.stderr.strip()}")

        except Exception as e:
            print(f"Ошибка проверки автозапуска: {e}")
            self.autostart_enabled = False
            self.autostart_button.config(text="Включить автозапуск")

    def schedule_status_update(self):
        """Периодически обновляет статус службы"""
        try:
            self.check_service_status()
        except Exception as e:
            print(f"Ошибка при обновлении статуса: {e}")
        finally:
            self.root.after(5000, self.schedule_status_update)  # Проверка каждые 5 секунд

    def toggle_zapret(self):
        """Переключает состояние Zapret (запуск/остановка)"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Меняем состояние UI
        self.zapret_button.config(state=tk.DISABLED)
        if self.service_running:
            self.zapret_button.config(text="Остановка...")
            self.show_status_message("Остановка службы...")
        else:
            self.zapret_button.config(text="Запуск...")
            self.show_status_message("Запуск службы...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_zapret_thread)
        thread.daemon = True
        thread.start()

    def _toggle_zapret_thread(self):
        """Поток для переключения состояния службы"""
        try:
            if self.service_running:
                # Останавливаем службу
                success, message = self.service_manager.stop_service()
                if success:
                    self.show_status_message("Служба остановлена", success=True)
                else:
                    self.show_status_message(f"Ошибка остановки: {message}", error=True)
            else:
                # Запускаем службу
                success, message = self.service_manager.start_service()
                if success:
                    self.show_status_message("Служба запущена", success=True)
                else:
                    self.show_status_message(
                        f"Ошибка запуска: {_shorten_service_error_message(message)}",
                        error=True,
                    )

            # Обновляем статус после операции
            self.root.after(1000, self.check_service_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку
            self.root.after(100, lambda: self.zapret_button.config(state=tk.NORMAL))

    def toggle_autostart(self):
        """Переключает автозапуск"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        # Сначала проверяем текущий статус
        self.check_autostart_status()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Меняем состояние UI
        self.autostart_button.config(state=tk.DISABLED)
        if self.autostart_enabled:
            self.autostart_button.config(text="Отключение...")
            self.show_status_message("Отключение автозапуска...")
        else:
            self.autostart_button.config(text="Включение...")
            self.show_status_message("Включение автозапуска...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_autostart_thread)
        thread.daemon = True
        thread.start()

    def _toggle_autostart_thread(self):
        """Поток для переключения автозапуска"""
        try:
            # Двойная проверка состояния перед выполнением
            current_state = self.autostart_enabled

            if current_state:
                # Отключаем автозапуск
                success, message = self.service_manager.disable_autostart()
                if success:
                    self.show_status_message("Автозапуск отключен", success=True)
                    self.autostart_enabled = False
                else:
                    self.show_status_message(f"Ошибка отключения: {message}", error=True)
            else:
                # Включаем автозапуск
                success, message = self.service_manager.enable_autostart()
                if success:
                    self.show_status_message("Автозапуск включен", success=True)
                    self.autostart_enabled = True
                else:
                    self.show_status_message(f"Ошибка включения: {message}", error=True)

            # Обновляем статус после операции
            self.root.after(1000, self.check_autostart_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку и обновляем текст
            self.root.after(100, lambda: self.autostart_button.config(state=tk.NORMAL))
            self.root.after(100, self.check_autostart_status)  # Еще раз проверяем состояние

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        self.root.after(0, lambda: self._update_status_message(message, success, warning, error))

    def _update_status_message(self, message, success, warning, error):
        """Обновляет статусное сообщение в основном потоке"""
        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg='#30d158')  # Зеленый
        elif warning:
            self.status_message.config(fg='#ff9500')  # Оранжевый
        elif error:
            self.status_message.config(fg='#ff3b30')  # Красный
        else:
            self.status_message.config(fg='#AAAAAA')  # Серый

        # Автоматически очищаем сообщение через 3 секунды (кроме ошибок)
        if message and not error:
            self.root.after(3000, lambda: self.status_message.config(text=""))
