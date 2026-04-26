"""Свойства главного окна, размер, фокус."""
import os
import tkinter as tk

from core.dpi_utils import center_toplevel_on_screen, fit_toplevel_to_content


class MainChromeMixin:
    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg='#182030')

        # Устанавливаем WM_CLASS
        try:
            self.root.wm_class("ZapretDPIManager")
        except Exception:
            pass

        # Устанавливаем иконку
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            icon_path = os.path.join(manager_dir, "ico/zapret.png")
            if os.path.exists(icon_path):
                # Для PNG файлов в tkinter
                icon = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon)
        except Exception as e:
            print(f"Не удалось установить иконку: {e}")

    def _apply_main_window_size(self):
        """Размер и minsize по содержимому, чтобы UI не обрезался при высоком DPI."""
        fit_toplevel_to_content(
            self.root,
            min_width=320,
            min_height=200,
            margin_width=8,
            margin_height=12,
        )
        center_toplevel_on_screen(self.root)

    def on_focus_in(self, event):
        """Обрабатывает получение фокуса окном"""
        self.load_current_strategy()  # Обновляем стратегию при получении фокуса
        self.update_game_filter_indicator()

    def on_focus_out(self, event):
        """Обрабатывает потерю фокуса окном - закрываем меню"""
        self.close_all_menus()

    def close_all_menus(self):
        """Закрывает все открытые выпадающие меню"""
        if self.settings_menu_open:
            self.close_settings_menu()
