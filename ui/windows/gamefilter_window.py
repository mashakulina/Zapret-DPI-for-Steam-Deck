# -*- coding: utf-8 -*-
"""Окно GameFilter: пресеты игр и включение GameFilter."""
import tkinter as tk
import os
from ui.components.button_styler import create_hover_button
from ui.components.custom_messagebox import show_info, show_error
from core.game_presets import (
    GAME_PRESETS,
    get_active_preset_id,
    set_active_preset,
    clear_active_preset,
    remove_preset_lines_from_config,
    get_manager_dir,
)


class GameFilterWindow:
    """Окно выбора действия GameFilter: пресет игры, включить GameFilter или назад."""

    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("GameFilter")

        self.setup_ui()

    def setup_window_properties(self):
        """Настройка свойств окна."""
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def setup_ui(self):
        """Настройка интерфейса."""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="GameFilter",
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(15, 30))

        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 10,
            'width': 25,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        preset_btn = create_hover_button(
            main_frame,
            text="Включить пресет игры",
            command=self.open_game_preset_window,
            **button_style
        )
        preset_btn.pack(pady=(0, 10))

        # Кнопка Включить/Выключить GameFilter в зависимости от состояния
        if self.main_window.is_game_filter_enabled():
            enable_gf_btn = create_hover_button(
                main_frame,
                text="Выключить GameFilter",
                command=self.disable_game_filter,
                **button_style
            )
        else:
            enable_gf_btn = create_hover_button(
                main_frame,
                text="Включить GameFilter",
                command=self.enable_game_filter,
                **button_style
            )
        enable_gf_btn.pack(pady=(0, 10))

        back_btn = create_hover_button(
            main_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_btn.pack(pady=(10, 0))

    def enable_game_filter(self):
        """Закрывает окно и запускает включение GameFilter через предупреждение в main_window."""
        self.close_window()
        self.main_window._show_game_filter_warning()

    def disable_game_filter(self):
        """Выключение GameFilter: sudo, переключение, перезапуск службы."""
        self.close_window()
        if not self.main_window.ensure_sudo_password():
            return
        self.main_window._perform_game_filter_toggle()

    def open_game_preset_window(self):
        """Открывает окно выбора пресета игры."""
        self.close_window()
        preset_window = GamePresetWindow(self.parent, self.main_window)
        preset_window.run()

    def close_window(self):
        """Закрывает окно."""
        self.root.destroy()

    def run(self):
        """Запускает окно (модально)."""
        self.root.update_idletasks()
        self.root.update()
        try:
            self.root.grab_set()
        except tk.TclError:
            pass
        self.root.wait_window()


class GamePresetWindow:
    """Окно выбора пресета игры: чекбоксы (один на выбор), Применить и Назад."""

    def __init__(self, parent, main_window):
        self.parent = parent
        self.main_window = main_window
        self.root = tk.Toplevel(parent)
        self.manager_dir = get_manager_dir()
        self.preset_vars = {}  # preset_id -> BooleanVar
        self.setup_window_properties()
        self.root.title("Пресет игры")

        self.setup_ui()
        self._load_preset_state()

    def setup_window_properties(self):
        """Настройка свойств окна."""
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

    def setup_ui(self):
        """Настройка интерфейса."""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            main_frame,
            text="Включить пресет игры",
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(15, 20))

        check_frame = tk.Frame(main_frame, bg='#182030')
        check_frame.pack(fill=tk.X, pady=(0, 20))

        for preset_id, preset_data in GAME_PRESETS.items():
            var = tk.BooleanVar(value=False)
            self.preset_vars[preset_id] = var
            cb = tk.Checkbutton(
                check_frame,
                text=preset_data["name"],
                variable=var,
                font=("Arial", 11),
                fg='white',
                bg='#182030',
                selectcolor='#1E4A6E',
                activebackground='#182030',
                activeforeground='#4fc3f7',
                highlightthickness=0,
                cursor='hand2',
                command=lambda p=preset_id: self._on_preset_click(p),
            )
            cb.pack(anchor='w')

        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 10,
            'width': 15,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        apply_btn = create_hover_button(
            buttons_frame,
            text="Применить",
            command=self.apply_preset,
            **button_style
        )
        apply_btn.pack(side=tk.LEFT, padx=(0, 10))

        back_btn = create_hover_button(
            buttons_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_btn.pack(side=tk.LEFT)

    def _on_preset_click(self, preset_id):
        """Взаимное исключение: при отметке одного пресета снимаем остальные."""
        if self.preset_vars[preset_id].get():
            for pid, var in self.preset_vars.items():
                if pid != preset_id:
                    var.set(False)

    def _load_preset_state(self):
        """Загружает состояние чекбоксов по файлам-маркерам в utils."""
        active = get_active_preset_id(self.manager_dir)
        for preset_id, var in self.preset_vars.items():
            var.set(preset_id == active)

    def get_config_path(self):
        """Путь к config.txt в каталоге менеджера."""
        return os.path.join(self.manager_dir, "config.txt")

    def apply_preset(self):
        """Применяет выбранный пресет: файл-маркер в utils и запись в config.txt."""
        if not self.main_window.ensure_sudo_password():
            return

        selected = [pid for pid, var in self.preset_vars.items() if var.get()]

        if not selected:
            active_before = get_active_preset_id(self.manager_dir)
            if active_before:
                remove_preset_lines_from_config(active_before, self.manager_dir)
            clear_active_preset(self.manager_dir)
            show_info(self.root, "Пресет", "Пресет не выбран. Снято применение пресетов.")
            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message("Применение пресетов снято", success=True)
            self.main_window.restart_zapret_after_preset("Пресет снят")
            self.close_window()
            return

        preset_id = selected[0]
        if preset_id not in GAME_PRESETS:
            show_error(self.root, "Ошибка", "Пресет не найден.")
            return

        preset = GAME_PRESETS[preset_id]
        lines = preset["lines"]
        name = preset["name"]

        set_active_preset(preset_id, self.manager_dir)

        config_path = self.get_config_path()
        try:
            existing = ""
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    existing = f.read()
            new_content = "\n".join(lines) + "\n" + existing
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            if hasattr(self.main_window, "show_status_message"):
                self.main_window.show_status_message(f"Пресет {name} добавлен в config.txt", success=True)
            show_info(self.root, "Готово", f"Пресет {name} добавлен в начало config.txt.")
            self.main_window.restart_zapret_after_preset(f"Пресет {name} применён")
        except Exception as e:
            show_error(self.root, "Ошибка", f"Не удалось записать config.txt: {e}")
            return
        self.close_window()

    def close_window(self):
        """Закрывает окно (возврат в главное меню)."""
        self.root.destroy()

    def run(self):
        """Запускает окно (модально)."""
        self.root.update_idletasks()
        self.root.update()
        try:
            self.root.grab_set()
        except tk.TclError:
            pass
        self.root.wait_window()
