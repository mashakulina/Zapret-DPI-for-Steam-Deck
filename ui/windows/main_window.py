#!/usr/bin/env python3
from __future__ import annotations

import os
import tkinter as tk

from core.service_manager import ServiceManager
from ui.windows.main.main_chrome import MainChromeMixin
from ui.windows.main.main_decky import MainDeckyMixin
from ui.windows.main.main_gamefilter import MainGameFilterMixin
from ui.windows.main.main_service import MainServiceMixin
from ui.windows.main.main_startup import MainStartupMixin
from ui.windows.main.main_tooltips import MainTooltipsMixin
from ui.windows.main.main_ui import MainUIMixin
from ui.windows.main.main_updates import MainUpdatesMixin


class MainWindow(
    MainChromeMixin,
    MainTooltipsMixin,
    MainStartupMixin,
    MainUpdatesMixin,
    MainUIMixin,
    MainGameFilterMixin,
    MainServiceMixin,
    MainDeckyMixin,
):
    """Главное окно: композиция миксинов из ui.windows.main."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.setup_window_properties()
        self.root.title("Zapret DPI Manager")

        # Переменные для состояния кнопок
        self.zapret_running = False
        self.autostart_enabled = False
        self.service_running = False  # Статус службы
        self.settings_menu_open = False  # Флаг для меню настроек
        self.restarting = False  # Флаг перезапуска службы

        self.service_manager = ServiceManager()

        # Путь к файлу gamefilter.enable
        home_dir = os.path.expanduser("~")
        self.game_filter_file = os.path.join(home_dir, "Zapret_DPI_Manager", "utils", "gamefilter.enable")

        self.decky_plugin_path = os.path.join(home_dir, "homebrew", "plugins", "DeckyZapretDPI")
        self.decky_plugin_installed = os.path.isdir(self.decky_plugin_path)

        self.setup_ui()
        self._apply_main_window_size()
        # Сначала проверяем зависимости
        self.check_dependencies_on_startup()
        # Затем проверяем zapret
        self.check_zapret_on_startup()
        # Проверка и создание обязательных файлов в files/lists/
        self.ensure_lists_files()
        # Проверяем целостность файлов
        # self.check_files_on_startup()
        self.load_current_strategy()
        self.check_service_status()  # Проверяем статус службы при запуске
        self.update_game_filter_indicator()  # GameFilter / активный пресет игры (маркер в utils)
        self.schedule_status_update()  # Запускаем периодическую проверку
        self.status_tooltip = None  # Всплывающее окошко для статуса
        self.root.after(100, self.check_updates_on_startup)

        # Bind событий фокус
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)

    def run(self) -> None:
        """Запускает главное окно"""
        self.root.mainloop()


if __name__ == "__main__":
    app = MainWindow()
    app.run()
