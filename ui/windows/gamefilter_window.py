# -*- coding: utf-8 -*-
"""Окно GameFilter: пресеты игр, GameFilter и IPSet Filter."""
import os
import tkinter as tk

from ui.components.button_styler import create_hover_button
from ui.components.responsive_buttons import pack_responsive_buttons
from ui.components.window_navigation import run_child_window
from ui.windows.ipset_settings_window import IpsetFilterWindow
from ui.windows.main.protocols import MainWindowActions
from ui.components.custom_messagebox import show_info, show_error
from core.dpi_utils import application_tk_root, place_toplevel_centered_on_parent
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale
from core.game_filter_settings import (
    GAMEFILTER_PROTOCOL_BOTH,
    GAMEFILTER_PROTOCOL_TCP,
    GAMEFILTER_PROTOCOL_UDP,
    disable_standalone_gamefilter,
    normalize_game_filter_protocol_mode,
    read_game_filter_protocol_mode,
    read_game_filter_custom_ports,
    validate_game_filter_custom_ports,
    write_game_filter_settings,
)
from core.game_presets import (
    get_game_presets,
    is_custom_preset,
    apply_custom_preset,
    clear_custom_preset,
    validate_custom_preset,
    preset_switch_transaction,
    get_active_preset_id,
    set_active_preset,
    clear_active_preset,
    remove_preset_lines_from_config,
    get_manager_dir,
    games_data_file,
    substitute_gamefilter_in_config,
    restore_gamefilter_for_preset,
)


def _preset_read_nonempty_lines(path):
    """Читает непустые строки файла без комментариев."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def _preset_write_lines(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if lines:
            f.write("\n".join(lines) + "\n")
        else:
            f.write("")


def _list_general_user_path(manager_dir):
    return os.path.join(manager_dir, "files", "lists", "list-general_user.txt")


def _ipset_all_user_path(manager_dir):
    return os.path.join(manager_dir, "files", "lists", "ipset-all_user.txt")


def _preset_remove_list_general_user_domains(manager_dir, games_list_file):
    source_path = games_data_file(manager_dir, games_list_file)
    source_domains = set(_preset_read_nonempty_lines(source_path))
    if not source_domains:
        return
    current_domains = _preset_read_nonempty_lines(_list_general_user_path(manager_dir))
    filtered_domains = [domain for domain in current_domains if domain not in source_domains]
    _preset_write_lines(_list_general_user_path(manager_dir), filtered_domains)


def _preset_apply_list_general_user_domains(manager_dir, games_list_file):
    source_path = games_data_file(manager_dir, games_list_file)
    source_domains = _preset_read_nonempty_lines(source_path)
    if not source_domains:
        raise FileNotFoundError(f"Файл не найден или пуст: {source_path}")
    current_domains = _preset_read_nonempty_lines(_list_general_user_path(manager_dir))
    merged_domains = sorted(set(current_domains).union(set(source_domains)))
    _preset_write_lines(_list_general_user_path(manager_dir), merged_domains)


def _preset_remove_ipset_user_entries(manager_dir, games_ipset_file):
    source_path = games_data_file(manager_dir, games_ipset_file)
    source_set = set(_preset_read_nonempty_lines(source_path))
    if not source_set:
        return
    current_entries = _preset_read_nonempty_lines(_ipset_all_user_path(manager_dir))
    filtered = [line for line in current_entries if line not in source_set]
    _preset_write_lines(_ipset_all_user_path(manager_dir), filtered)


def _preset_apply_ipset_user_entries(manager_dir, games_ipset_file):
    source_path = games_data_file(manager_dir, games_ipset_file)
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Файл не найден: {source_path}")
    source_entries = _preset_read_nonempty_lines(source_path)
    if not source_entries:
        raise FileNotFoundError(f"Файл не найден или пуст: {source_path}")
    current_entries = _preset_read_nonempty_lines(_ipset_all_user_path(manager_dir))
    merged = sorted(set(current_entries).union(set(source_entries)))
    _preset_write_lines(_ipset_all_user_path(manager_dir), merged)


def _preset_remove_roblox_domains(manager_dir):
    _preset_remove_list_general_user_domains(manager_dir, "list-general_roblox.txt")


def _preset_remove_roblox_ipset(manager_dir):
    _preset_remove_ipset_user_entries(manager_dir, "ipset-all_roblox.txt")


def _preset_remove_fallguys_domains(manager_dir):
    _preset_remove_list_general_user_domains(manager_dir, "list-general_fallguys.txt")


def _preset_remove_fallguys_ipset(manager_dir):
    _preset_remove_ipset_user_entries(manager_dir, "ipset-all_fallguys.txt")


def _preset_set_ipset_none(manager_dir):
    target_path = os.path.join(manager_dir, "files", "lists", "ipset-all.txt")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("203.0.113.113/32")


def clear_active_game_preset_disk(manager_dir: str) -> None:
    """Снимает активный пресет с диска (без перезапуска службы и без диалогов)."""
    with preset_switch_transaction(manager_dir):
        active_before = get_active_preset_id(manager_dir)
        if active_before:
            if is_custom_preset(active_before, manager_dir):
                clear_custom_preset(active_before, manager_dir)
                clear_active_preset(manager_dir)
                return
            if active_before == "roblox":
                _preset_remove_roblox_domains(manager_dir)
                _preset_remove_roblox_ipset(manager_dir)
            elif active_before == "fall_guys":
                _preset_remove_fallguys_domains(manager_dir)
                _preset_remove_fallguys_ipset(manager_dir)
            else:
                remove_preset_lines_from_config(active_before, manager_dir)
            if active_before == "elite_dangerous":
                _preset_set_ipset_none(manager_dir)
            restore_gamefilter_for_preset(active_before, manager_dir)
        clear_active_preset(manager_dir)


class GameFilterProtocolModeWindow:
    """Отдельное окно: выбор TCP/UDP для подстановки {GameFilter} в службе."""

    def _setup_dialog(self, title):
        self._anchor = application_tk_root(self._parent) or self._parent
        scale = max(float(warning_dialog_scale(self._anchor)),
                    float(logical_ui_scale(self._anchor)))
        self._s = lambda value: max(1, int(round(value * scale)))
        self.root = tk.Toplevel(self._parent)
        self.root.withdraw()
        self.root.title(title)
        self.root.configure(bg="#182030")
        self.root.transient(self._anchor)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._cancel)
        self.root.bind("<Escape>", lambda event: self._cancel())
        self._main = tk.Frame(self.root, bg="#182030", padx=self._s(18), pady=self._s(14))
        self._main.pack(fill=tk.BOTH, expand=True)
        self._footer = tk.Frame(self._main, bg="#182030")
        self._footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(self._s(16), 0))
        viewport = tk.Frame(self._main, bg="#182030")
        viewport.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(viewport, bg="#182030", bd=0, highlightthickness=0,
                                 width=1, height=1)
        self._scrollbar = tk.Scrollbar(viewport, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._body = tk.Frame(self._canvas, bg="#182030")
        self._body_item = self._canvas.create_window((0, 0), window=self._body, anchor=tk.NW)
        self._wrap_widgets = []
        self._actions = []
        self._actions_stacked = None
        self._fitting = True
        self._canvas.bind("<Configure>", self._resize_body)
        self._body.bind("<Configure>", self._update_scroll)
        self._footer.bind("<Configure>", lambda event: self._arrange_actions(event.width))
        self.root.bind("<Button-4>", lambda event: self._canvas.yview_scroll(-1, "units"))
        self.root.bind("<Button-5>", lambda event: self._canvas.yview_scroll(1, "units"))
        self.root.bind("<MouseWheel>", lambda event: self._canvas.yview_scroll(-int(event.delta / 120), "units"))

    def _wrap(self, widget, inset=0):
        self._wrap_widgets.append((widget, inset))
        return widget

    def _label(self, text, *, color="#cccccc", bottom=8):
        label = self._wrap(tk.Label(
            self._body, text=text, font=("Arial", 10), bg="#182030", fg=color,
            justify=tk.LEFT, anchor=tk.W, wraplength=self._s(460)))
        label.pack(fill=tk.X, pady=(0, self._s(bottom)))
        return label

    def _action_buttons(self, actions):
        style = dict(font=("Arial", 11), bg="#15354D", fg="white", bd=0,
                     padx=self._s(18), pady=self._s(8), width=12,
                     highlightthickness=0, cursor="hand2")
        self._actions = [create_hover_button(self._footer, text=text, command=command, **style)
                         for text, command in actions]
        self._arrange_actions(sum(button.winfo_reqwidth() for button in self._actions)
                              + 10 * (len(self._actions) - 1))

    def _arrange_actions(self, width):
        if not self._actions:
            return
        gap = 10
        stacked = sum(button.winfo_reqwidth() for button in self._actions) + gap * (len(self._actions) - 1) > width
        if stacked == self._actions_stacked:
            return
        self._actions_stacked = stacked
        for index, button in enumerate(self._actions):
            button.pack_forget()
            button.pack(side=tk.TOP if stacked else tk.LEFT, anchor=tk.W,
                        padx=(0, gap if not stacked and index < len(self._actions) - 1 else 0),
                        pady=(0, gap if stacked and index < len(self._actions) - 1 else 0))

    def _resize_body(self, event):
        self._canvas.itemconfigure(self._body_item, width=event.width)
        for widget, inset in self._wrap_widgets:
            widget.configure(wraplength=max(40, event.width - self._s(inset)))
        self._update_scroll()

    def _update_scroll(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        if self._fitting:
            return
        if self._body.winfo_reqheight() > self._canvas.winfo_height() + 1:
            if not self._scrollbar.winfo_manager():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        elif self._scrollbar.winfo_manager():
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def _fit_dialog(self):
        self._fitting = True
        self._scrollbar.pack_forget()
        self.root.update_idletasks()
        max_width = max(1, self.root.winfo_screenwidth() - 32)
        max_height = max(1, self.root.winfo_screenheight() - 80)
        horizontal_margin = 2 * self._s(18)
        available = max(1, max_width - horizontal_margin)
        row_width = sum(button.winfo_reqwidth() for button in self._actions) + 10 * (len(self._actions) - 1)
        action_width = row_width if row_width <= available else max(button.winfo_reqwidth() for button in self._actions)
        content_width = min(max(self._body.winfo_reqwidth(), action_width), available)
        self._arrange_actions(content_width)
        self._canvas.configure(width=content_width)
        self._canvas.itemconfigure(self._body_item, width=content_width)
        for widget, inset in self._wrap_widgets:
            widget.configure(wraplength=max(40, content_width - self._s(inset)))
        self.root.update_idletasks()
        chrome_height = 2 * self._s(14) + self._s(16) + self._footer.winfo_reqheight()
        available_height = max(1, max_height - chrome_height)
        overflow = self._body.winfo_reqheight() > available_height
        bar_width = self._scrollbar.winfo_reqwidth() if overflow else 0
        width = min(content_width + horizontal_margin + bar_width, max_width)
        content_width = max(1, width - horizontal_margin - bar_width)
        if overflow:
            self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        self._canvas.configure(width=content_width)
        self._canvas.itemconfigure(self._body_item, width=content_width)
        for widget, inset in self._wrap_widgets:
            widget.configure(wraplength=max(40, content_width - self._s(inset)))
        self.root.update_idletasks()
        content_height = min(self._body.winfo_reqheight(), available_height)
        self._canvas.configure(height=content_height)
        self.root.update_idletasks()
        height = min(content_height + chrome_height, max_height)
        place_toplevel_centered_on_parent(
            self.root, self._anchor, fixed_content_size=(width, height), immediate=True)
        self._fitting = False
        self._update_scroll()

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_confirm,
        initial_mode: str | None = None,
        title: str = "Режим протокола",
        hint: str = "Игровые порты ({GameFilter}) в службе:",
        confirm_text: str = "Далее",
        on_back=None,
    ):
        self._parent = parent
        self._on_confirm = on_confirm
        self._on_back = on_back
        self._setup_dialog(title)
        self._label(hint)

        start = (
            normalize_game_filter_protocol_mode(initial_mode)
            if initial_mode is not None
            else read_game_filter_protocol_mode(get_manager_dir())
        )
        self._var = tk.StringVar(value=start)
        rb_style = {
            "font": ("Arial", 10),
            "fg": "white",
            "bg": "#182030",
            "selectcolor": "#1E4A6E",
            "activebackground": "#182030",
            "activeforeground": "#4fc3f7",
            "highlightthickness": 0,
            "bd": 0,
            "cursor": "hand2",
            "variable": self._var,
        }
        for text, value in (("Включить TCP и UDP", GAMEFILTER_PROTOCOL_BOTH),
                            ("Включить только TCP", GAMEFILTER_PROTOCOL_TCP),
                            ("Включить только UDP", GAMEFILTER_PROTOCOL_UDP)):
            radio = self._wrap(tk.Radiobutton(self._body, text=text, value=value, **rb_style), 30)
            radio.pack(anchor=tk.W, pady=self._s(3))
        self._action_buttons(((confirm_text, self._confirm), ("Назад", self._back)))
        self._fit_dialog()

    def _confirm(self) -> None:
        mode = self._var.get()
        self._close()
        self._on_confirm(mode)

    def _close(self):
        self.root.destroy()
        parent = getattr(self, "_parent", None)
        if parent is not None:
            try:
                if parent.winfo_exists():
                    parent.grab_set()
            except tk.TclError:
                pass

    def _back(self) -> None:
        self._close()
        if self._on_back:
            self._on_back()

    def _cancel(self) -> None:
        self._close()

    def run_modal(self) -> None:
        self.root.update_idletasks()
        self.root.update()
        try:
            self.root.grab_set()
        except tk.TclError:
            pass
        self._parent.wait_window(self.root)


class GameFilterPortsChoiceWindow(GameFilterProtocolModeWindow):
    """Первый шаг настройки: стандартные либо пользовательские порты."""

    def __init__(self, parent, *, on_confirm, initial_custom=False):
        self._parent = parent
        self._on_confirm = on_confirm
        self._on_back = None
        self._setup_dialog("GameFilter: выбор портов")
        self._var = tk.BooleanVar(self.root, value=initial_custom)
        for text, value in (("Без указания портов", False), ("С указанием портов", True)):
            radio = self._wrap(tk.Radiobutton(
                self._body, text=text, value=value, variable=self._var,
                bg="#182030", fg="white", selectcolor="#1E4A6E",
                activebackground="#182030", activeforeground="white", cursor="hand2",
                font=("Arial", 10), bd=0, highlightthickness=0), 30)
            radio.pack(anchor=tk.W, pady=self._s(3))
        self._action_buttons((("Далее", self._confirm), ("Отмена", self._cancel)))
        self._fit_dialog()


class GameFilterPortsWindow(GameFilterProtocolModeWindow):
    """Ввод диапазонов; проверка выполняется до закрытия окна."""

    def __init__(self, parent, *, mode, on_confirm, initial_ports=None, on_back=None):
        self._parent = parent
        self._on_confirm = on_confirm
        self._on_back = on_back
        self.mode = normalize_game_filter_protocol_mode(mode)
        self._setup_dialog("GameFilter: диапазоны портов")
        self._label("Порты 1–65535 через запятую или диапазон.\nНапример: 1000-2000,3000")
        initial_ports = initial_ports or {}
        self._shared = tk.BooleanVar(self.root, value=self.mode == "both" and initial_ports.get("tcp") == initial_ports.get("udp"))
        self._entries = {}
        if self.mode == "both":
            shared_check = self._wrap(tk.Checkbutton(
                self._body, text="Одинаковые порты для TCP и UDP", variable=self._shared,
                command=self._update_fields, bg="#182030", fg="white", selectcolor="#1E4A6E",
                activebackground="#182030", activeforeground="white", cursor="hand2",
                font=("Arial", 10), bd=0, highlightthickness=0), 30)
            shared_check.pack(anchor=tk.W, pady=(0, self._s(6)))
        for protocol in ("tcp", "udp"):
            if self.mode not in ("both", protocol):
                continue
            tk.Label(self._body, text=protocol.upper(), bg="#182030", fg="white", font=("Arial", 11)).pack(anchor=tk.W)
            value = tk.StringVar(self.root, value=initial_ports.get(protocol, ""))
            entry = tk.Entry(self._body, textvariable=value, font=("Arial", 11), width=32,
                             bg="#2A3B5C", fg="white", insertbackground="white", bd=0,
                             relief=tk.FLAT, highlightthickness=2, highlightbackground="#3A4B6C",
                             highlightcolor="#4A8FE7", disabledbackground="#2A3B5C",
                             disabledforeground="#8e8e93")
            entry.pack(fill=tk.X, pady=(self._s(5), self._s(8)))
            self._entries[protocol] = (value, entry)
        self._error = self._label("", color="#ff3b30", bottom=6)
        self._error.pack_forget()
        self._action_buttons((("Применить", self._confirm), ("Назад", self._back), ("Отмена", self._cancel)))
        self._udp_draft = initial_ports.get("udp", "")
        self._shared_active = False
        if self.mode == "both":
            self._entries["tcp"][0].trace_add("write", self._sync_shared_ports)
        self._update_fields()
        self._fit_dialog()

    def _sync_shared_ports(self, *_):
        if self.mode == "both" and self._shared.get():
            self._entries["udp"][0].set(self._entries["tcp"][0].get())

    def _update_fields(self):
        if self.mode == "both":
            shared = self._shared.get()
            if shared and not self._shared_active:
                self._udp_draft = self._entries["udp"][0].get()
            if shared:
                self._sync_shared_ports()
            elif self._shared_active:
                self._entries["udp"][0].set(self._udp_draft)
            self._shared_active = shared
            self._entries["udp"][1].configure(state=tk.DISABLED if shared else tk.NORMAL)

    def get_draft_ports(self):
        ports = {key: value.get() for key, (value, _) in self._entries.items()}
        if self.mode == "both" and self._shared.get():
            ports["udp"] = ports["tcp"]
        return ports

    def _confirm(self):
        ports = self.get_draft_ports()
        try:
            ports = validate_game_filter_custom_ports(self.mode, ports)
        except ValueError as error:
            self._error.configure(text=str(error))
            if getattr(self, "_canvas", None) is not None:
                self._error.pack(fill=tk.X, pady=(0, self._s(6)))
                self._fit_dialog()
            return
        self._close()
        self._on_confirm(ports)


class GameFilterWindow:
    """Меню игровых пресетов, GameFilter и режимов IPSet Filter."""

    def __init__(self, parent: tk.Misc, main_window: MainWindowActions):
        self.parent = parent
        self.main_window = main_window
        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.setup_window_properties()
        self.root.title("GameFilter")

        self.setup_ui()
        self._fit_menu()

    def setup_window_properties(self):
        """Настройка свойств окна."""
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        self.root.bind("<Escape>", lambda event: self.close_window())

    def setup_ui(self):
        """Настройка интерфейса."""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        self._main_frame = main_frame

        title_label = tk.Label(
            main_frame,
            text="GameFilter",
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(15, 8))
        self._title_label = title_label

        self._hint_label = tk.Label(
            main_frame,
            text="Готовые игровые пресеты выключают отдельный GameFilter. Пользовательские пресеты восстанавливают сохранённые настройки.",
            font=("Arial", 10),
            fg="#aaaaaa",
            bg="#182030",
            justify=tk.CENTER,
            wraplength=max(340, int(round(340 * logical_ui_scale(self.parent)))),
        )
        self._hint_label.pack(fill=tk.X, pady=(0, 18))

        footer = tk.Frame(main_frame, bg='#182030')
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(20, 0))
        viewport = tk.Frame(main_frame, bg='#182030')
        viewport.pack(fill=tk.BOTH, expand=True)
        self._canvas = tk.Canvas(viewport, bg='#182030', bd=0, highlightthickness=0,
                                 width=1, height=1)
        self._scrollbar = tk.Scrollbar(viewport, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._buttons_frame = tk.Frame(self._canvas, bg='#182030')
        self._buttons_item = self._canvas.create_window(
            (0, 0), window=self._buttons_frame, anchor=tk.NW)
        self._buttons = []
        self._layout_ready = False
        self._canvas.bind('<Configure>', self._resize_menu)
        self._buttons_frame.bind('<Configure>', self._update_menu_scroll)
        self.root.bind('<Button-4>', lambda event: self._canvas.yview_scroll(-1, 'units'))
        self.root.bind('<Button-5>', lambda event: self._canvas.yview_scroll(1, 'units'))
        self.root.bind('<MouseWheel>', lambda event: self._canvas.yview_scroll(-int(event.delta / 120), 'units'))

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

        actions = [("Включить пресет игры", self.open_game_preset_window)]

        # Кнопка Включить/Выключить GameFilter в зависимости от состояния
        if self.main_window.is_game_filter_enabled():
            actions.extend((("Режим и порты…", self._open_protocol_window_for_apply),
                            ("Выключить GameFilter", self.disable_game_filter)))
        else:
            actions.append(("Включить GameFilter", self.enable_game_filter))
        actions.append(("Настройка IPSet Filter", self.open_ipset_filter_settings))

        for index, (text, command) in enumerate(actions):
            button = create_hover_button(self._buttons_frame, text=text, command=command, **button_style)
            button.pack(pady=(0, 10 if index < len(actions) - 1 else 0))
            self._buttons.append(button)

        self._back_button = create_hover_button(
            footer,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        self._back_button.pack()

    def _set_menu_width(self, width):
        self._canvas.itemconfigure(self._buttons_item, width=width)
        self._hint_label.configure(wraplength=width)
        self._title_label.configure(wraplength=width)
        for button in self._buttons:
            wrapped = self._natural_button_width > width
            button.configure(width=0 if wrapped else 25, wraplength=max(1, width - 40) if wrapped else 0)

    def _resize_menu(self, event):
        if not self._layout_ready:
            return
        self._set_menu_width(event.width)
        self._update_menu_scroll()

    def _update_menu_scroll(self, event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox('all'))
        if not self._layout_ready:
            return
        if self._buttons_frame.winfo_reqheight() > self._canvas.winfo_height() + 1:
            if not self._scrollbar.winfo_manager():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        elif self._scrollbar.winfo_manager():
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def _fit_menu(self):
        """Ограничивает список экраном, сохраняя «Назад» на нижней панели."""
        self.root.update_idletasks()
        max_width = max(1, self.root.winfo_screenwidth() - 32)
        max_height = max(1, self.root.winfo_screenheight() - 80)
        self._natural_button_width = max(button.winfo_reqwidth() for button in self._buttons)
        content_width = min(max(self._natural_button_width, self._hint_label.winfo_reqwidth()), max_width - 30)
        self._set_menu_width(content_width)
        self._canvas.configure(width=content_width, height=1)
        self.root.update_idletasks()
        chrome_height = self._main_frame.winfo_reqheight() - 1
        available_height = max(1, max_height - chrome_height)
        overflow = self._buttons_frame.winfo_reqheight() > available_height
        if overflow:
            self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
            content_width = min(content_width, max_width - 30 - self._scrollbar.winfo_reqwidth())
            self._set_menu_width(content_width)
            self._canvas.configure(width=content_width)
            self.root.update_idletasks()
            chrome_height = self._main_frame.winfo_reqheight() - 1
            available_height = max(1, max_height - chrome_height)
        self._canvas.configure(height=min(self._buttons_frame.winfo_reqheight(), available_height))
        self.root.update_idletasks()
        width = min(self.root.winfo_reqwidth(), max_width)
        height = min(self.root.winfo_reqheight(), max_height)
        place_toplevel_centered_on_parent(
            self.root, self.parent, fixed_content_size=(width, height), immediate=True)
        self._layout_ready = True
        self._update_menu_scroll()

    def open_ipset_filter_settings(self):
        """Открывает режимы IPSet Filter с возвратом в то же меню GameFilter."""
        run_child_window(self.root, lambda: IpsetFilterWindow(self.parent).run())

    def enable_game_filter(self):
        self._open_settings_flow(False)

    def _open_settings_flow(self, editing, mode=None, ports=None):
        if mode is None:
            mode = read_game_filter_protocol_mode(get_manager_dir())
            try:
                ports = read_game_filter_custom_ports(get_manager_dir())
            except ValueError as error:
                show_error(self.root, "Ошибка портов GameFilter", f"{error}\nВыберите стандартные порты или задайте диапазоны заново.")
                ports = None

        # Each dialog finishes its modal wait before the next stage is opened.
        # Keep drafts locally so Back never writes to disk or loses entered values.
        stage = "choice"
        custom = ports is not None
        draft_ports = dict(ports or {})
        while True:
            result = {}

            def confirm(value):
                result.update(action="confirm", value=value)

            def back():
                result["action"] = "back"

            if stage == "choice":
                dialog = GameFilterPortsChoiceWindow(
                    self.root, initial_custom=custom, on_confirm=confirm)
            elif stage == "protocol":
                dialog = GameFilterProtocolModeWindow(
                    self.root, initial_mode=mode, title="GameFilter: режим и порты",
                    on_confirm=confirm, on_back=back)
            else:
                dialog = GameFilterPortsWindow(
                    self.root, mode=mode, initial_ports=draft_ports,
                    on_confirm=confirm, on_back=back)
            dialog.run_modal()
            action = result.get("action")
            if action is None:
                return  # Cancel or window-manager close.
            if action == "back":
                if stage == "ports":
                    draft_ports.update(dialog.get_draft_ports())
                    stage = "protocol"
                else:
                    mode = dialog._var.get()
                    stage = "choice"
                continue
            value = result["value"]
            if stage == "choice":
                custom = value
                stage = "protocol"
                continue
            if stage == "protocol":
                mode = value
                if custom:
                    stage = "ports"
                    continue
                selected_ports = None
            else:
                selected_ports = value
            if editing:
                self._after_protocol_chosen_for_apply(mode, selected_ports)
            else:
                self._after_protocol_chosen_for_enable(mode, selected_ports)
            return

    def _after_protocol_chosen_for_enable(self, mode: str, custom_ports=None) -> None:
        self.close_window()
        if custom_ports is None:
            self.main_window._show_game_filter_warning(mode)
        else:
            self.main_window._show_game_filter_warning(mode, custom_ports)

    def _open_protocol_window_for_apply(self) -> None:
        self._open_settings_flow(True)

    def _restore_modal_grab(self):
        try:
            if self.root.winfo_exists():
                self.root.grab_set()
        except tk.TclError:
            pass

    def _after_protocol_chosen_for_apply(self, mode: str, custom_ports=None) -> None:
        try:
            custom_ports = validate_game_filter_custom_ports(mode, custom_ports)
            try:
                authorized = self.main_window.ensure_sudo_password()
            finally:
                self._restore_modal_grab()
            if not authorized:
                return
            write_game_filter_settings(mode, custom_ports, get_manager_dir())
        except (ValueError, OSError) as error:
            try:
                show_error(self.root, "Ошибка настройки GameFilter", str(error))
            finally:
                self._restore_modal_grab()
            return
        self.close_window()
        self.main_window.restart_zapret_after_preset("Режим и порты Game Filter обновлены")

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

    def __init__(self, parent: tk.Misc, main_window: MainWindowActions):
        self.parent = parent
        self.main_window = main_window
        self.root = tk.Toplevel(parent)
        self.manager_dir = get_manager_dir()
        self.preset_vars = {}  # preset_id -> BooleanVar
        self.presets = get_game_presets(self.manager_dir)
        self.setup_window_properties()
        self.root.title("Пресет игры")

        self.setup_ui()
        self._load_preset_state()
        self.root.update_idletasks()
        width = min(max(360, self.root.winfo_reqwidth()), max(1, self.root.winfo_screenwidth() - 32))
        height = min(self.root.winfo_reqheight(), max(1, self.root.winfo_screenheight() - 80))
        place_toplevel_centered_on_parent(
            self.root, self.parent, fixed_content_size=(width, height), immediate=True
        )

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
        title_label.pack(pady=(15, 8))

        tk.Label(
            main_frame,
            text="Готовый пресет выключает отдельный GameFilter. Пользовательский применяет сохранённые настройки GameFilter и IPSet Filter.",
            font=("Arial", 9),
            fg="#aaaaaa",
            bg="#182030",
            justify=tk.CENTER,
            wraplength=340,
        ).pack(pady=(0, 14))

        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        viewport = tk.Frame(main_frame, bg='#182030')
        viewport.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        canvas = tk.Canvas(viewport, bg='#182030', highlightthickness=0, height=220, width=340)
        scrollbar = tk.Scrollbar(viewport, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        check_frame = tk.Frame(canvas, bg='#182030')
        inner = canvas.create_window((0, 0), window=check_frame, anchor='nw')
        check_frame.bind('<Configure>', lambda event: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.bind('<Configure>', lambda event: canvas.itemconfigure(inner, width=event.width))
        self.root.bind('<Button-4>', lambda event: canvas.yview_scroll(-1, 'units'))
        self.root.bind('<Button-5>', lambda event: canvas.yview_scroll(1, 'units'))
        self.root.bind('<MouseWheel>', lambda event: canvas.yview_scroll(-int(event.delta / 120), 'units'))

        for preset_id, preset_data in self.presets.items():
            var = tk.BooleanVar(value=False)
            self.preset_vars[preset_id] = var
            cb = tk.Checkbutton(
                check_frame,
                text=preset_data["name"],
                wraplength=290,
                justify=tk.LEFT,
                anchor=tk.W,
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
            cb.pack(fill=tk.X, anchor='w')
            cb.bind('<Configure>', lambda event: event.widget.configure(wraplength=max(40, event.width - 36)))

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

        apply_btn = create_hover_button(
            buttons_frame,
            text="Применить",
            command=self.apply_preset,
            **button_style
        )


        back_btn = create_hover_button(
            buttons_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        pack_responsive_buttons(buttons_frame, [apply_btn, back_btn])

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

    def _read_nonempty_lines(self, path):
        """Читает непустые строки файла без комментариев."""
        return _preset_read_nonempty_lines(path)

    def _write_lines(self, path, lines):
        """Записывает строки в файл, по одной на строку."""
        _preset_write_lines(path, lines)

    def _apply_roblox_domains(self):
        """Добавляет домены Roblox в list-general_user.txt без дубликатов."""
        _preset_apply_list_general_user_domains(self.manager_dir, "list-general_roblox.txt")

    def _remove_roblox_domains(self):
        """Удаляет домены Roblox из list-general_user.txt."""
        _preset_remove_roblox_domains(self.manager_dir)

    def _apply_roblox_ipset(self):
        """Добавляет CIDR Roblox в ipset-all_user.txt без дубликатов."""
        _preset_apply_ipset_user_entries(self.manager_dir, "ipset-all_roblox.txt")

    def _remove_roblox_ipset(self):
        """Удаляет из ipset-all_user.txt записи Roblox."""
        _preset_remove_roblox_ipset(self.manager_dir)

    def _apply_fallguys_domains(self):
        """Добавляет домены Fall Guys в list-general_user.txt без дубликатов."""
        _preset_apply_list_general_user_domains(self.manager_dir, "list-general_fallguys.txt")

    def _remove_fallguys_domains(self):
        """Удаляет домены Fall Guys из list-general_user.txt."""
        _preset_remove_fallguys_domains(self.manager_dir)

    def _apply_fallguys_ipset(self):
        """Добавляет CIDR Fall Guys в ipset-all_user.txt без дубликатов."""
        _preset_apply_ipset_user_entries(self.manager_dir, "ipset-all_fallguys.txt")

    def _remove_fallguys_ipset(self):
        """Удаляет из ipset-all_user.txt записи Fall Guys."""
        _preset_remove_fallguys_ipset(self.manager_dir)

    def _set_ipset_none(self):
        """Устанавливает IPSetFilter в none."""
        _preset_set_ipset_none(self.manager_dir)

    def _apply_ipset_loaded(self):
        """Копирует utils/ipset-all.txt в files/lists/ipset-all.txt (режим loaded в IPSet Filter)."""
        source_path = os.path.join(self.manager_dir, "utils", "ipset-all.txt")
        target_path = os.path.join(self.manager_dir, "files", "lists", "ipset-all.txt")
        if not os.path.isfile(source_path):
            raise FileNotFoundError(f"Файл не найден: {source_path}")
        with open(source_path, "r", encoding="utf-8") as f:
            content = f.read()
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

    def apply_preset(self):
        """Apply disk changes atomically, then refresh UI and restart the service."""
        if not self.main_window.ensure_sudo_password():
            return
        selected = next((pid for pid, var in self.preset_vars.items() if var.get()), None)
        try:
            presets = get_game_presets(self.manager_dir)
            if selected and selected not in presets:
                raise ValueError("Пресет не найден.")
            if selected and is_custom_preset(selected, self.manager_dir):
                validate_custom_preset(selected, self.manager_dir, check_config=False)
            with preset_switch_transaction(self.manager_dir):
                self._apply_selected_disk(selected, presets)
        except (OSError, ValueError, UnicodeError) as error:
            show_error(self.root, "Ошибка", f"Не удалось применить пресет: {error}")
            return
        if hasattr(self.main_window, "update_game_filter_indicator"):
            self.main_window.update_game_filter_indicator()
        name = presets[selected]['name'] if selected else None
        message = f"Был выбран пресет для {name}" if name else "Применение пресетов снято"
        if hasattr(self.main_window, "show_status_message"):
            self.main_window.show_status_message(message, success=True)
        info_text = message + "."
        if selected == "fall_guys":
            info_text += ("\n\nПресет только для версии из Epic Games Store. "
                          "Для Steam этот пресет не используйте — в настройках игры смените регион на США (восток).")
        show_info(self.root, "Пресет", info_text)
        self.main_window.restart_zapret_after_preset(f"Пресет {name} применён" if name else "Пресет снят")
        self.close_window()

    def _apply_selected_disk(self, preset_id, presets):
        active_before = get_active_preset_id(self.manager_dir)
        if preset_id is None:
            clear_active_game_preset_disk(self.manager_dir)
            return
        if active_before and active_before != preset_id:
            clear_active_game_preset_disk(self.manager_dir)
        if is_custom_preset(preset_id, self.manager_dir):
            apply_custom_preset(preset_id, self.manager_dir)
            set_active_preset(preset_id, self.manager_dir)
            return
        disable_standalone_gamefilter(self.manager_dir)
        preset = presets[preset_id]
        tcp, udp = preset.get("game_filter_tcp"), preset.get("game_filter_udp")
        if tcp is not None and udp is not None:
            substitute_gamefilter_in_config(tcp, udp, self.manager_dir)
        if preset_id == "roblox":
            self._apply_roblox_domains()
            self._apply_roblox_ipset()
        elif preset_id == "fall_guys":
            self._apply_fallguys_domains()
            self._apply_fallguys_ipset()
        elif preset_id == "elite_dangerous":
            self._apply_ipset_loaded()
        lines = preset.get("lines") or []
        if lines:
            path = self.get_config_path()
            existing = ""
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as stream:
                    existing = stream.read()
            block = "\n".join(lines)
            if existing != block and not existing.startswith(block + "\n"):
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(block + "\n" + existing)
        set_active_preset(preset_id, self.manager_dir)

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
