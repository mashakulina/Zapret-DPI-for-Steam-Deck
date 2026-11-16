"""Выбор движка фаервола установленной службы Zapret."""
import queue
import threading
import tkinter as tk

from core import firewall_settings
from core.dpi_utils import application_tk_root, place_toplevel_centered_on_parent
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale
from ui.components.button_styler import create_hover_button
from ui.components.custom_messagebox import show_error
from ui.components.window_navigation import run_child_window
from ui.windows.sudo_password_window import SudoPasswordWindow


class FirewallSettingsWindow:
    """Компактный диалог; backend можно подменить без системных изменений."""

    def __init__(self, parent, main_window=None, *, backend=None):
        self._parent = parent
        self._main_window = main_window
        self._backend = backend if backend is not None else firewall_settings
        self._state = None
        self._available = {}
        self._busy = False
        self._results = queue.Queue()
        self._closed = False
        self._anchor = application_tk_root(parent) or parent
        scale = max(float(warning_dialog_scale(self._anchor)),
                    float(logical_ui_scale(self._anchor)))
        self._s = lambda value: max(1, int(round(value * scale)))
        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.root.title("Фаервол")
        self.root.configure(bg="#182030")
        self.root.transient(self._anchor)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.bind("<Escape>", lambda event: self._close())
        self._main = tk.Frame(self.root, bg="#182030", padx=self._s(18), pady=self._s(14))
        self._main.pack(fill=tk.BOTH, expand=True)
        self._footer = tk.Frame(self._main, bg="#182030")
        self._footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(self._s(16), 0))
        self._actions_frame = tk.Frame(self._footer, bg="#182030")
        self._actions_frame.pack(anchor=tk.CENTER)
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
        self._label("Выберите фаервол для Zapret:")
        self._var = tk.StringVar(master=self.root, value="")
        self._radios = []
        for text, value in (("nftables (рекомендуется)", "nftables"),
                            ("iptables (совместимость)", "iptables")):
            radio = self._wrap(tk.Radiobutton(
                self._body, text=text, value=value, variable=self._var,
                font=("Arial", 10), fg="white", bg="#182030",
                selectcolor="#1E4A6E", activebackground="#182030",
                activeforeground="white", highlightthickness=0, bd=0,
                cursor="hand2", justify=tk.LEFT, anchor=tk.W), 30)
            radio.pack(anchor=tk.W, fill=tk.X, pady=self._s(3))
            self._radios.append(radio)
        self.state_label = self._label("Чтение состояния…", color="#AAAAAA")
        self._label("Для применения может потребоваться пароль администратора. "
                    "Работающая служба будет перезапущена.", color="#8e8e93")
        self.status_label = self._label("", color="#AAAAAA", bottom=0)
        self._action_buttons((("Применить", self._apply), ("Назад", self._close)))
        self._fit_dialog()
        self._start_task("read", self._read)

    def _wrap(self, widget, inset=0):
        self._wrap_widgets.append((widget, inset))
        return widget

    def _label(self, text, *, color="#cccccc", bottom=8):
        label = self._wrap(tk.Label(
            self._body, text=text, font=("Arial", 10), bg="#182030", fg=color,
            justify=tk.LEFT, anchor=tk.W, wraplength=self._s(400)))
        label.pack(fill=tk.X, pady=(0, self._s(bottom)))
        return label

    def _action_buttons(self, actions):
        style = dict(font=("Arial", 11), bg="#15354D", fg="white", bd=0,
                     padx=self._s(18), pady=self._s(8), width=12,
                     highlightthickness=0, cursor="hand2")
        self._actions = [create_hover_button(self._actions_frame, text=text, command=command, **style)
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
            button.pack(side=tk.TOP if stacked else tk.LEFT, anchor=tk.CENTER,
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
        # Bound the preferred text width: previous Canvas wraps must not grow it.
        preferred_width = min(self._body.winfo_reqwidth(), self._s(400))
        content_width = min(max(preferred_width, action_width), available)
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

    def _read(self):
        return self._backend.read_state(), self._backend.available_backends()

    def _start_task(self, kind, operation):
        self._task_kind = kind
        self._set_busy(True)

        def worker():
            try:
                self._results.put((kind, operation(), None))
            except Exception as error:
                self._results.put((kind, None, str(error)))

        threading.Thread(target=worker, daemon=True).start()
        self.root.after(50, self._poll)

    def _set_busy(self, busy):
        self._busy = busy
        for widget in self._actions + self._radios:
            widget.configure(state=tk.DISABLED if busy else tk.NORMAL)
        if busy and self._task_kind == "read":
            self._actions[1].configure(state=tk.NORMAL)
        self.root.configure(cursor="watch" if busy else "")
        if not busy:
            valid = bool(self._state and self._state.get("installed") and not self._state.get("error"))
            self._actions[0].configure(state=tk.NORMAL if valid else tk.DISABLED)
            for radio in self._radios:
                radio.configure(state=tk.NORMAL if valid else tk.DISABLED)

    def _poll(self):
        if self._closed:
            return
        try:
            kind, result, error = self._results.get_nowait()
        except queue.Empty:
            self.root.after(50, self._poll)
            return
        if result is not None:
            state, available = result[:2]
            if len(result) > 2:
                error = result[2]
            self._state, self._available = state, available
            configured = state.get("configured")
            active = state.get("active")
            self._var.set(configured if configured in ("nftables", "iptables") else "")
            actual = active or ("не определён" if state.get("service_active") else "служба остановлена")
            self.state_label.configure(text=f"В конфигурации: {configured or 'не определён'}\nАктивный фаервол: {actual}")
            error = error or state.get("error")
            self.status_label.configure(text=error or ("Настройка применена." if kind == "apply" else ""),
                                        fg="#ff3b30" if error else "#30d158")
        else:
            self._state = None
            self.state_label.configure(text="Не удалось прочитать состояние фаервола.")
            self.status_label.configure(text=error or "Ошибка чтения состояния", fg="#ff3b30")
        self._set_busy(False)
        self._fit_dialog()
        if error and kind == "apply":
            show_error(self.root, "Фаервол", error)

    def _password(self):
        main = self._main_window
        if main is not None:
            if not run_child_window(self.root, lambda: main.ensure_sudo_password(parent=self.root)):
                return None
            return main.service_manager.sudo_password
        return run_child_window(self.root, lambda: SudoPasswordWindow(self.root).run())

    def _apply(self):
        if self._busy or not self._state:
            return
        selected = self._var.get()
        if (selected == self._state.get("configured")
                and (not self._state.get("service_active") or selected == self._state.get("active"))):
            self.status_label.configure(text="Этот фаервол уже выбран.", fg="#AAAAAA")
            self._fit_dialog()
            return
        if selected not in ("nftables", "iptables"):
            show_error(self.root, "Фаервол", "Выберите nftables или iptables.")
            return
        if not self._available.get(selected):
            show_error(self.root, "Фаервол", f"{selected} не установлен. Установите необходимые инструменты и откройте это окно снова.")
            return
        password = self._password()
        if password is None:
            return
        self.status_label.configure(text="Применение настройки…", fg="#AAAAAA")

        def apply_and_read():
            try:
                self._backend.apply_backend(selected, password=password)
            except Exception as error:
                # Rollback may itself fail: read real state instead of restoring the old display.
                try:
                    current = self._read()
                except Exception:
                    raise error
                return (*current, str(error))
            return (*self._read(), None)

        def operation():
            state, available, error = apply_and_read()
            return state, available, error

        self._start_task("apply", operation)

    def _close(self):
        if self._busy and self._task_kind == "apply":
            return
        self._closed = True
        self.root.destroy()

    def run(self):
        self.root.grab_set()
        self.root.focus_set()
        self.root.wait_window()
