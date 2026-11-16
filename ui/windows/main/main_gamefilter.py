"""Game Filter: индикатор, предупреждение, перезапуск службы."""
import os
import threading
import tkinter as tk

from ui.windows.gamefilter_window import GameFilterWindow, clear_active_game_preset_disk
from ui.windows.main.main_gamefilter_warning import show_game_filter_warning_dialog
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
        """Выполняет фактическое переключение Game Filter"""
        try:
            # Получаем текущее состояние
            was_enabled = self.is_game_filter_enabled()

            if was_enabled:
                # Удаляем файл (выключаем)
                with preset_switch_transaction(get_manager_dir()):
                    disable_standalone_gamefilter(get_manager_dir())
                new_icon = "⌨"
                status_message = "Game Filter выключен"
                print("🎮🔴 Game Filter выключен")
            else:
                mode = protocol_mode_for_enable or GAMEFILTER_PROTOCOL_BOTH
                custom_ports = validate_game_filter_custom_ports(mode, custom_ports)
                manager_dir = get_manager_dir()
                had_preset = get_active_preset_id() is not None
                with preset_switch_transaction(manager_dir):
                    clear_active_game_preset_disk(manager_dir)
                    directory = os.path.dirname(self.game_filter_file)
                    if directory:
                        os.makedirs(directory, exist_ok=True)
                    write_game_filter_settings(mode, custom_ports, manager_dir)
                    with open(self.game_filter_file, 'w'):
                        pass
                if had_preset:
                    self.show_status_message(
                        "Активный пресет игры снят (несовместим с отдельным GameFilter)", warning=True)
                    self.update_game_filter_indicator()

                new_icon = "⌨"
                status_message = (
                    f"Game Filter включен ({_game_filter_protocol_label(mode)})"
                )
                print(f"🎮🟢 Game Filter включен, режим: {mode}")

            # Меняем иконку
            self.game_filter_indicator.config(text=new_icon)

            # Обновляем всплывающую подсказку
            if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
                self.hide_game_filter_tooltip()
                self.show_game_filter_tooltip()

            # Показываем сообщение о смене состояния
            self.show_status_message(status_message, success=True)

            # Перезапускаем службу zapret
            self._restart_zapret_service(status_message)

        except Exception as e:
            error_msg = f"Ошибка переключения Game Filter: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)

    def _restart_zapret_service(self, status_message):
        """Перезапускает службу zapret после изменения Game Filter"""
        # Блокируем UI
        self.game_filter_indicator.config(state=tk.DISABLED)

        # Показываем анимацию загрузки (меняем цвет индикатора на оранжевый)
        self.game_filter_indicator.config(fg='#ff9500')
        self.show_status_message(f"{status_message}, перезапуск службы...")
        self.root.update()

        def restart_service_thread():
            try:
                # Запускаем перезапуск службы
                success, message = self.service_manager.restart_service()

                if success:
                    self.root.after(0, lambda: self.show_status_message(
                        f"{status_message}, служба перезапущена", success=True))
                else:
                    self.root.after(0, lambda: self.show_status_message(
                        f"{status_message}, но служба не перезапущена: {message}", warning=True))

            except Exception as e:
                self.root.after(0, lambda: self.show_status_message(
                    f"Ошибка перезапуска службы: {e}", error=True))
            finally:
                # Восстанавливаем UI и обновляем индикатор
                self.root.after(0, lambda: self.game_filter_indicator.config(state=tk.NORMAL))
                self.root.after(0, self.update_game_filter_indicator)

                # Обновляем статус службы через 1 секунду
                self.root.after(1000, self.check_service_status)

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=restart_service_thread, daemon=True)
        thread.start()

    def restart_zapret_after_preset(self, status_message):
        """Перезапускает службу zapret после изменения пресета (без изменения иконки GameFilter)."""
        self.show_status_message(f"{status_message}, перезапуск службы...")
        self.root.update()

        def restart_thread():
            try:
                success, message = self.service_manager.restart_service()
                if success:
                    self.root.after(0, lambda: self.show_status_message(
                        f"{status_message}, служба перезапущена", success=True))
                else:
                    self.root.after(0, lambda: self.show_status_message(
                        f"{status_message}, но служба не перезапущена: {message}", warning=True))
            except Exception as e:
                self.root.after(0, lambda: self.show_status_message(
                    f"Ошибка перезапуска службы: {e}", error=True))
            finally:
                self.root.after(1000, self.check_service_status)

        thread = threading.Thread(target=restart_thread, daemon=True)
        thread.start()
