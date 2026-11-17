"""Game Filter: индикатор, предупреждение, перезапуск службы."""
import os
import threading
import queue
import tkinter as tk

from ui.windows.gamefilter_window import GameFilterWindow, clear_active_game_preset_disk
from ui.windows.main.main_gamefilter_warning import show_game_filter_warning_dialog
from core.game_mode import toggle_gamefilter_disk
from core.config_lock import manager_settings_lock
from core.strategy_settings import strategy_change
from core.game_filter_extras import clear_game_mode_extras_if_inactive
from core.game_presets import get_active_preset_id, get_game_presets, get_manager_dir, preset_switch_transaction
from core.game_filter_settings import (
    read_game_filter_protocol_mode,
    read_game_filter_custom_ports,
    validate_game_filter_custom_ports,
    write_game_filter_settings,
    disable_standalone_gamefilter,
    GAMEFILTER_PROTOCOL_BOTH,
    GAMEFILTER_PROTOCOL_TCP,
    GAMEFILTER_PROTOCOL_UDP,
)


def _game_filter_protocol_label(mode: str) -> str:
    if mode == GAMEFILTER_PROTOCOL_TCP:
        return "только TCP"
    if mode == GAMEFILTER_PROTOCOL_UDP:
        return "только UDP"
    return "TCP и UDP"


class MainGameFilterMixin:
    def update_game_filter_indicator(self):
        """Обновляет цвет индикатора Game Filter"""
        active_preset = get_active_preset_id()
        if self.is_game_filter_enabled() or active_preset is not None:
            self.game_filter_indicator.config(fg='#30d158')  # Зеленый
        else:
            self.game_filter_indicator.config(fg='#ff3b30')  # Красный

    def is_game_filter_enabled(self):
        """Проверяет, включен ли Game Filter"""
        return os.path.exists(self.game_filter_file)

    def show_game_filter_tooltip(self, event=None):
        """Показывает всплывающее окошко со статусом Game Filter"""
        # Не показываем если уже есть
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            return

        # Определяем текст в зависимости от состояния
        active_preset = get_active_preset_id()
        preset = get_game_presets().get(active_preset)
        if preset:
            status_text = f"Пресет игры: {preset['name']}"
            if self.is_game_filter_enabled():
                mode = read_game_filter_protocol_mode()
                status_text += f"\nGameFilter: {_game_filter_protocol_label(mode)}"
            status_text += "\nНажмите для настроек / выключения"
        elif self.is_game_filter_enabled():
            mode = read_game_filter_protocol_mode()
            status_text = (
                "GameFilter включен\n"
                f"Подстановка {{GameFilter}}: {_game_filter_protocol_label(mode)}\n"
                "Нажмите для настроек / выключения"
            )
        else:
            status_text = "GameFilter выключен\nНажмите для включения"

        if self.is_game_filter_enabled():
            try:
                ports = read_game_filter_custom_ports()
                if ports:
                    status_text += "\n" + "\n".join(f"{key.upper()}: {value}" for key, value in ports.items())
            except ValueError:
                status_text += "\nОшибка диапазонов портов — откройте настройки"

        # Позиционируем подсказку рядом с иконкой
        x = self.game_filter_indicator.winfo_rootx() - 20
        y = self.game_filter_indicator.winfo_rooty() + self.game_filter_indicator.winfo_height() + 5

        # Создаем всплывающее окно
        self.game_filter_tooltip = tk.Toplevel(self.root)
        self.game_filter_tooltip.wm_overrideredirect(True)
        self.game_filter_tooltip.geometry(f"+{x}+{y}")
        self.game_filter_tooltip.configure(bg='#15354D', relief=tk.SOLID, bd=1)

        # Добавляем текст
        label = tk.Label(self.game_filter_tooltip,
                        text=status_text,
                        font=("Arial", 10),
                        fg='white',
                        bg='#15354D',
                        padx=10,
                        pady=5,
                        justify=tk.LEFT,
                        wraplength=500)
        label.pack()

    def hide_game_filter_tooltip(self, event=None):
        """Скрывает всплывающее окошко Game Filter"""
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            self.game_filter_tooltip.destroy()
            self.game_filter_tooltip = None

    def toggle_game_filter(self, event=None):
        """Открывает окно GameFilter при клике на иконку."""
        gamefilter_window = GameFilterWindow(self.root, self)
        gamefilter_window.run()

    def _show_game_filter_warning(self, protocol_mode: str = GAMEFILTER_PROTOCOL_BOTH, custom_ports=None):
        """Показывает предупреждение о Game Filter с адаптацией под Steam Deck"""
        if custom_ports is None:
            show_game_filter_warning_dialog(self, protocol_mode)
        else:
            show_game_filter_warning_dialog(self, protocol_mode, custom_ports)

    def _on_warning_accept(self, warning_window, protocol_mode: str = GAMEFILTER_PROTOCOL_BOTH, custom_ports=None):
        """Обработчик нажатия на кнопку 'Понятно, включить'"""
        try:
            custom_ports = validate_game_filter_custom_ports(protocol_mode, custom_ports)
        except ValueError as error:
            self.show_status_message(str(error), error=True)
            return
        warning_window.destroy()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Выполняем включение Game Filter
        if custom_ports is None:
            self._perform_game_filter_toggle(protocol_mode_for_enable=protocol_mode)
        else:
            self._perform_game_filter_toggle(protocol_mode_for_enable=protocol_mode, custom_ports=custom_ports)

    def _perform_game_filter_toggle(self, protocol_mode_for_enable: str | None = None, custom_ports=None):
        """Save and restart in one worker; the Tk thread only updates widgets."""
        try:
            mode = protocol_mode_for_enable or GAMEFILTER_PROTOCOL_BOTH
            ports = validate_game_filter_custom_ports(mode, custom_ports)
        except ValueError as error:
            self.show_status_message(str(error), error=True)
            return
        manager_dir = get_manager_dir()
        enabling = not self.is_game_filter_enabled()
        status = f"Game Filter включен ({_game_filter_protocol_label(mode)})" if enabling else "Game Filter выключен"

        def mutate():
            if enabling:
                # The desktop wizard explicitly chooses default/custom ranges.
                clear_active_game_preset_disk(manager_dir)
                write_game_filter_settings(mode, ports, manager_dir)
                with open(self.game_filter_file, 'w'):
                    pass
            else:
                # The shared core clears mode, ports and inactive extras together.
                if os.path.isfile(self.game_filter_file):
                    toggle_gamefilter_disk(manager_dir)
                else:
                    disable_standalone_gamefilter(manager_dir)
                    clear_game_mode_extras_if_inactive(manager_dir)

        self._restart_zapret_service(status, mutation=mutate, manager_dir=manager_dir)

    def _restart_zapret_service(self, status_message, mutation=None, on_success=None, manager_dir=None):
        """Keep mutation, validation, restart and recovery under one worker lock."""
        if getattr(self, '_game_filter_operation', False):
            self.show_status_message("Настройки GameFilter уже применяются", warning=True)
            return
        self._game_filter_operation = True
        self.game_filter_indicator.config(state=tk.DISABLED, fg='#ff9500')
        self.show_status_message(f"{status_message}, применение и перезапуск...")
        root_path = manager_dir or get_manager_dir()
        results = queue.Queue()

        def work():
            try:
                with manager_settings_lock(root_path):
                    prior_state = self.service_manager.get_service_status()
                    if prior_state not in ('active', 'activating', 'inactive', 'failed'):
                        raise RuntimeError('Не удалось определить прежнее состояние службы. Настройки не изменены.')
                    restore = (self.service_manager.restart_service if prior_state in ('active', 'activating')
                               else self.service_manager.stop_service)
                    with strategy_change(root_path, self.service_manager.restart_service, restore=restore):
                        if mutation is not None:
                            mutation()
                results.put((True, status_message + ", служба перезапущена"))
            except Exception as error:
                results.put((False, str(error)))

        def poll():
            try:
                success, message = results.get_nowait()
            except queue.Empty:
                self.root.after(50, poll)
                return
            self._game_filter_operation = False
            self.game_filter_indicator.config(state=tk.NORMAL)
            self.update_game_filter_indicator()
            if getattr(self, 'game_filter_tooltip', None):
                self.hide_game_filter_tooltip()
                self.show_game_filter_tooltip()
            if success:
                self.show_status_message(message, success=True)
                if on_success is not None:
                    on_success()
            else:
                self.show_status_message(f"Ошибка применения: {message}", error=True)
            self.root.after(1000, self.check_service_status)

        try:
            # Finish the bounded service operation and any disk rollback even
            # when closing the main window ends Tk's event loop. The worker
            # publishes only to Queue and never calls Tk during shutdown.
            threading.Thread(target=work, daemon=False).start()
        except RuntimeError as error:
            results.put((False, str(error)))
        self.root.after(50, poll)

    def restart_zapret_after_preset(self, status_message, mutation=None, on_success=None, manager_dir=None):
        """Apply a preset/settings mutation in the same worker as its restart."""
        self._restart_zapret_service(status_message, mutation=mutation,
                                    on_success=on_success, manager_dir=manager_dir)
