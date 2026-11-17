"""systemd/zapret: статус, переключение, sudo, статусная строка."""
import subprocess
import queue
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
        self._ensure_status_dispatch()
        self._status_generation = getattr(self, '_status_generation', 0) + 1
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
                self._post_ui(self.root.after, 0, lambda: self.show_status_message(
                    "Служба Zapret успешно перезапущена", success=True))
            else:
                self._post_ui(self.root.after, 0, lambda m=message: self.show_status_message(
                    f"Ошибка: {_shorten_service_error_message(m)}", error=True))

        except Exception as e:
            self._post_ui(self.root.after, 0, lambda message=str(e): self.show_status_message(
                f"Ошибка перезапуска службы: {message}", error=True))
        finally:
            # Восстанавливаем UI
            self._post_ui(self.root.after, 0, lambda: self.restart_icon.config(state=tk.NORMAL))
            self.restarting = False

            # Обновляем статус службы через 1 секунду
            self._post_ui(self.root.after, 1000, self.check_service_status)
    def ensure_sudo_password(self, parent=None):
        """Проверяет и получает пароль sudo если нужно"""
        owner = parent if parent is not None else self.root
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return False

        if not self.service_manager.sudo_password:
            # Убедимся, что окно действительно видимо
            owner.update_idletasks()

            # Проверяем видимость окна
            if not owner.winfo_viewable():
                owner.deiconify()  # Делаем окно видимым
                owner.update_idletasks()

            # Даем время на отрисовку
            owner.update()

            # Показываем окно ввода пароля
            password_window = SudoPasswordWindow(
                owner,
                on_password_valid=lambda pwd: self.service_manager.set_sudo_password(pwd)
            )
            password = password_window.run()

            if not password:
                self.show_status_message("Требуется пароль sudo", warning=True)
                return False

        return True


    def check_service_status(self):
        """Обновляет статус в фоне, не блокируя события Tk."""
        self._status_generation = getattr(self, '_status_generation', 0) + 1
        self.schedule_status_update()

    def check_autostart_status(self):
        """Использует тот же фоновый снимок службы и автозапуска."""
        self.check_service_status()

    def _ensure_status_dispatch(self):
        if getattr(self, '_status_poll_ready', False):
            return
        self._status_poll_ready = True
        self._status_poll_closed = False
        self._status_poll_busy = False
        self._status_poll_id = self._status_next_id = None
        self._status_results = queue.Queue()
        self._status_events = queue.Queue()
        self.root.bind('<Destroy>', self._stop_status_updates, add='+')
        self._status_poll_id = self.root.after(30, self._poll_status_updates)

    def _post_ui(self, callback, *args, **kwargs):
        # Все worker callbacks только публикуют данные; Tk вызывает UI poll.
        if not getattr(self, '_status_poll_closed', False):
            self._status_events.put((callback, args, kwargs))

    def schedule_status_update(self):
        """Периодический systemctl не занимает поток обработки ввода Tk."""
        self._ensure_status_dispatch()
        if self._status_poll_closed or self._status_poll_busy:
            return
        if self._status_next_id is not None:
            self.root.after_cancel(self._status_next_id)
            self._status_next_id = None
        self._status_poll_busy = True
        generation = getattr(self, '_status_generation', 0)
        results = self._status_results

        def read_status():
            # Worker touches only the queue, never Tk or application state.
            values = []
            for verb in ('is-active', 'is-enabled'):
                try:
                    result = subprocess.run(['systemctl', verb, 'zapret'],
                        capture_output=True, text=True, timeout=3)
                    values.append((result.returncode, result.stdout.strip()))
                except (OSError, subprocess.SubprocessError):
                    values.append(None)
            results.put((generation, *values))

        threading.Thread(target=read_status, daemon=True).start()
        if self._status_poll_id is None:
            self._status_poll_id = self.root.after(30, self._poll_status_updates)

    def _poll_status_updates(self):
        self._status_poll_id = None
        if self._status_poll_closed:
            return
        for _ in range(200):
            try:
                callback, args, kwargs = self._status_events.get_nowait()
            except queue.Empty:
                break
            callback(*args, **kwargs)
            if self._status_poll_closed:
                return
        try:
            generation, active, enabled = self._status_results.get_nowait()
        except queue.Empty:
            if self._status_poll_id is None:
                self._status_poll_id = self.root.after(30, self._poll_status_updates)
            return
        self._status_poll_busy = False
        if generation == getattr(self, '_status_generation', 0):
            running = active == (0, 'active')
            known_stopped = active is not None and (
                active == (3, 'inactive') or active[0] == 4)
            self.service_running = running
            color = '#30d158' if running else '#ff3b30' if known_stopped else '#ff9500'
            self.status_indicator.config(text='⬤', fg=color)
            self.zapret_button.config(text='Остановить Zapret DPI' if running else 'Запустить Zapret DPI')
            self.autostart_enabled = enabled is not None and enabled[0] == 0
            self.autostart_button.config(text='Отключить автозапуск' if self.autostart_enabled else 'Включить автозапуск')
        self._status_next_id = self.root.after(5000, self.schedule_status_update)
        if self._status_poll_id is None:
            self._status_poll_id = self.root.after(30, self._poll_status_updates)

    def _stop_status_updates(self, event):
        if event.widget != self.root or self._status_poll_closed:
            return
        self._status_poll_closed = True
        self._status_generation = getattr(self, '_status_generation', 0) + 1
        for attribute in ('_status_poll_id', '_status_next_id'):
            identifier = getattr(self, attribute, None)
            if identifier is not None:
                self.root.after_cancel(identifier)
                setattr(self, attribute, None)

    def toggle_zapret(self):
        """Переключает состояние Zapret (запуск/остановка)"""
        self._ensure_status_dispatch()
        self._status_generation = getattr(self, '_status_generation', 0) + 1
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
            self._post_ui(self.root.after, 1000, self.check_service_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку
            self._post_ui(self.root.after, 100, lambda: self.zapret_button.config(state=tk.NORMAL))

    def toggle_autostart(self):
        """Переключает автозапуск"""
        self._ensure_status_dispatch()
        self._status_generation = getattr(self, '_status_generation', 0) + 1
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

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
            result = subprocess.run(['systemctl', 'is-enabled', 'zapret'],
                capture_output=True, text=True, timeout=3)
            if result.returncode not in (0, 1):
                raise RuntimeError(result.stderr.strip() or 'Не удалось проверить автозапуск')
            current_state = result.returncode == 0

            if current_state:
                # Отключаем автозапуск
                success, message = self.service_manager.disable_autostart()
                if success:
                    self.show_status_message("Автозапуск отключен", success=True)
                else:
                    self.show_status_message(f"Ошибка отключения: {message}", error=True)
            else:
                # Включаем автозапуск
                success, message = self.service_manager.enable_autostart()
                if success:
                    self.show_status_message("Автозапуск включен", success=True)
                else:
                    self.show_status_message(f"Ошибка включения: {message}", error=True)

            # Обновляем статус после операции
            self._post_ui(self.root.after, 1000, self.check_autostart_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку и обновляем текст
            self._post_ui(self.root.after, 100, lambda: self.autostart_button.config(state=tk.NORMAL))
            self._post_ui(self.root.after, 100, self.check_autostart_status)  # Еще раз проверяем состояние

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        if threading.current_thread() is threading.main_thread():
            self._ensure_status_dispatch()
        self._post_ui(self._update_status_message, message, success, warning, error)

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
