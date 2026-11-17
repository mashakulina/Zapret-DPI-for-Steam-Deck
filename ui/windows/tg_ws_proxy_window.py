"""Flowseal GUI integration. Workers communicate exclusively through a queue."""

from ui.components.window_navigation import prepare_window_navigation
import queue
import threading
import tkinter as tk
from tkinter import ttk
import webbrowser

from core.dpi_utils import application_tk_root, geometry_resize_keep_position, place_toplevel_centered_on_parent
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale
from core.tg_ws_proxy import PROJECT_URL, ProxyError, TgWsProxy
from core.tg_proxy_connection import connection_link, copy_with_desktop, open_in_telegram
from ui.components.button_styler import create_hover_button
from ui.components.custom_messagebox import ask_yesno, show_error, show_info
from ui.windows.sudo_password_window import SudoPasswordWindow


def window_content_size(window, scale):
    """Canvas content does not determine a Toplevel's requested size."""
    return (min(round(560 * scale), max(240, window.winfo_screenwidth() - 32)),
            min(round(690 * scale), max(240, window.winfo_screenheight() - 80)))


class TgWsProxyWindow:
    def __init__(self, parent, service=None):
        self.parent = parent
        self.events = queue.Queue()
        self.closed = threading.Event()
        self.busy = False
        self.service = service
        self.plan_error = None
        try:
            self.service = service or TgWsProxy()
        except ProxyError as exc:
            self.plan_error = str(exc)
        self.window = tk.Toplevel(parent)
        self.window.withdraw()
        self.window.transient(parent)
        self.window.title("TG WS Proxy by Flowseal")
        self.window.configure(bg="#182030")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        prepare_window_navigation(self.window)
        self.window.bind("<Escape>", lambda event: self.close())
        self.window.bind("<Destroy>", self._destroyed, add="+")
        self._build()
        self.poll_id = self.window.after(100, self._poll)
        if self.service:
            self._start_worker("status")

    def _build(self):
        # Match the established settings windows: Tk scales point-sized fonts.
        anchor = application_tk_root(self.parent) or self.parent
        logical = logical_ui_scale(anchor)
        try:
            self._scale = max(logical, warning_dialog_scale(anchor))
        except (AttributeError, tk.TclError):
            self._scale = logical
        self._layout_ready = False
        self._s = lambda value: max(1, round(value * self._scale))
        s = self._s
        self._footer = tk.Frame(self.window, bg="#182030", padx=s(15), pady=s(10))
        self._footer.pack(side=tk.BOTTOM, fill=tk.X)
        self._footer_center = tk.Frame(self._footer, bg="#182030")
        self._footer_center.pack()
        style = dict(font=("Arial", 11), bg="#15354D", fg="white", bd=0,
                     padx=s(10), pady=s(8), highlightthickness=0, cursor="hand2")
        help_button = create_hover_button(self._footer_center, text="Инструкция", command=self._show_help,
                                          width=20, **style)
        self.back_button = create_hover_button(self._footer_center, text="Назад", command=self.close,
                                                width=20, **style)
        self._footer_buttons = [help_button, self.back_button]
        for index, button in enumerate(self._footer_buttons):
            button.pack(side=tk.LEFT, padx=(0, 15 if index == 0 else 0))
        self._footer_stacked = False

        self._canvas = canvas = tk.Canvas(self.window, bg="#182030", highlightthickness=0, bd=0,
                                          width=s(530), height=1)
        self._scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        canvas.pack(fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=self._scrollbar.set)
        self._body = frame = tk.Frame(canvas, bg="#182030", padx=s(20), pady=s(15))
        self._content_item = canvas.create_window((0, 0), window=frame, anchor="nw")
        self.labels = []

        def label(text, color="white", heading=False):
            widget = tk.Label(frame, text=text, bg="#182030", fg=color, justify=tk.LEFT,
                              anchor=tk.CENTER if heading else tk.W,
                              font=("Arial", 14, "bold") if heading else ("Arial", 10),
                              wraplength=s(490))
            widget.pack(fill=tk.X, pady=(0, s(20 if heading else 10)))
            self.labels.append(widget)
            return widget

        label("TG WS Proxy by Flowseal", heading=True)
        if self.service:
            plan = self.service.plan
            label(f"ОС: {plan.distro} · Архитектура: {plan.architecture}\nУстановка: {plan.description}", "#cccccc")
        else:
            label(self.plan_error, "#ff3b30")
        self.version_label = label("Версия: проверка…" if self.service else "Установка недоступна")
        self.auto_label = label("")
        self.status_label = label("", "#0a84ff")
        self._action_frame = tk.Frame(frame, bg="#182030")
        self._action_frame.pack()
        self.buttons = []
        for text, command in (("Установить / обновить", self.install), ("Запустить GUI", self.launch),
                              ("Открыть в Telegram", self.open_telegram),
                              ("Скопировать ссылку", self.copy_link),
                              ("Автозапуск: вкл. / выкл.", self.toggle_autostart),
                              ("Удалить TG WS Proxy", self.uninstall)):
            button = create_hover_button(self._action_frame, text=text, command=command, width=25, **style)
            self.buttons.append(button)
        self._columns = None
        if not self.service:
            for button in self.buttons:
                button.configure(state=tk.DISABLED)
        frame.bind("<Configure>", self._update_scroll)
        canvas.bind("<Configure>", self._resize_content)
        # Toplevel bindings also cover labels and buttons in the scrolling area.
        self.window.bind("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        self.window.bind("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        self.window.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))
        frame.after_idle(self._fit_content)

    def _arrange_actions(self, available):
        gap = 15
        columns = 2 if max(button.winfo_reqwidth() for button in self.buttons) * 2 + gap <= available else 1
        if columns == self._columns:
            return
        self._columns = columns
        for index, button in enumerate(self.buttons):
            button.grid_forget()
            button.grid(row=index // columns, column=index % columns,
                        padx=(0, gap if columns == 2 and index % columns == 0 else 0),
                        pady=(0, 10 if index // columns < (len(self.buttons) - 1) // columns else 0))

    def _arrange_footer(self, available):
        gap = 15
        stacked = sum(button.winfo_reqwidth() for button in self._footer_buttons) + gap > available
        if stacked == self._footer_stacked:
            return
        self._footer_stacked = stacked
        for index, button in enumerate(self._footer_buttons):
            button.pack_forget()
            button.pack(side=tk.TOP if stacked else tk.LEFT,
                        padx=(0, 0 if stacked or index else gap),
                        pady=(0, 10 if stacked and index == 0 else 0))

    def _fit_content(self):
        was_ready = self._layout_ready
        self._layout_ready = False
        self._scrollbar.pack_forget()
        self.window.update_idletasks()
        _, max_height = window_content_size(self.window, self._scale)
        max_width = max(1, self.window.winfo_screenwidth() - 32)
        self._arrange_actions(max_width - self._s(40) - self._scrollbar.winfo_reqwidth())
        self._arrange_footer(max_width - self._s(30))
        self.window.update_idletasks()
        # A scrollbar must not steal the few pixels that keep two columns
        # visible: that would double the form's height and create false overflow.
        width = min(max_width, max(self._body.winfo_reqwidth() + self._scrollbar.winfo_reqwidth(),
                                  self._footer.winfo_reqwidth()))
        self._canvas.configure(width=width)
        self._canvas.itemconfigure(self._content_item, width=width)
        self.window.update_idletasks()
        available = max(1, max_height - self._footer.winfo_reqheight())
        self._canvas.configure(height=min(self._body.winfo_reqheight(), available))
        height = min(max_height, self._body.winfo_reqheight() + self._footer.winfo_reqheight())
        if was_ready:
            geometry_resize_keep_position(self.window, width, height)
        else:
            place_toplevel_centered_on_parent(self.window, self.parent,
                                             fixed_content_size=(width, height), immediate=True)
        self._layout_ready = True
        self._update_scroll()

    def _resize_content(self, event):
        self._canvas.itemconfigure(self._content_item, width=event.width)
        content_width = max(100, event.width - self._s(40))
        for label in self.labels:
            label.configure(wraplength=content_width)
        self._arrange_actions(content_width)
        self._arrange_footer(self.window.winfo_width() - self._s(30))
        self._update_scroll()

    def _update_scroll(self, event=None):
        if not self._layout_ready:
            return
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        if self._body.winfo_reqheight() > self._canvas.winfo_height() + 1:
            if not self._scrollbar.winfo_manager():
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=self._canvas)
        elif self._scrollbar.winfo_manager():
            self._scrollbar.pack_forget()
            self._canvas.yview_moveto(0)

    def _show_help(self):
        # Keep the full instruction readable even on a small screen at 200%.
        existing = getattr(self, "_help_window", None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_set()
            return
        window = self._help_window = tk.Toplevel(self.window)
        window.withdraw()
        window.title("Инструкция TG WS Proxy")
        window.configure(bg="#182030")
        window.transient(self.window)
        s = self._s
        footer = tk.Frame(window, bg="#182030", padx=s(15), pady=s(10))
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        center = tk.Frame(footer, bg="#182030")
        center.pack()
        previous_grab = self.window.grab_current()

        def close():
            window.destroy()
            try:
                if previous_grab is not None and previous_grab.winfo_exists():
                    previous_grab.grab_set()
                self.window.focus_set()
            except tk.TclError:
                pass

        style = dict(font=("Arial", 11), width=20, padx=s(10), pady=s(8))
        buttons = [create_hover_button(center, text="Официальный проект",
                                        command=lambda: webbrowser.open(PROJECT_URL), **style),
                   create_hover_button(center, text="Назад", command=close, **style)]
        for index, button in enumerate(buttons):
            button.pack(side=tk.LEFT, padx=(0, 15 if index == 0 else 0))
        viewport = tk.Frame(window, bg="#182030")
        viewport.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(viewport, bg="#182030", highlightthickness=0, bd=0, height=1)
        scrollbar = ttk.Scrollbar(viewport, orient=tk.VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(fill=tk.BOTH, expand=True)
        body = tk.Frame(canvas, bg="#182030", padx=s(20), pady=s(15))
        item = canvas.create_window((0, 0), window=body, anchor="nw")
        heading = tk.Label(body, text="Инструкция TG WS Proxy", bg="#182030", fg="white",
                           font=("Arial", 14, "bold"), wraplength=s(560))
        heading.pack(fill=tk.X, pady=(0, s(20)))
        message = tk.Label(body, bg="#182030", fg="white", font=("Arial", 10),
                           justify=tk.LEFT, anchor=tk.W, wraplength=s(560),
                           text="После установки GUI запускается отдельно, а автозапуск после входа на рабочий стол "
                           "включается автоматически. Закрытие менеджера не останавливает прокси. "
                           "При закрытии окна начатая установка продолжится.\n\n"
                           "Первое подключение: запустите GUI, затем нажмите «Открыть в Telegram» и подтвердите "
                           "подключение. Кнопка «Скопировать ссылку» работает через буфер обмена рабочего стола. "
                           "Адрес обычно 127.0.0.1, порт 1443.\n\n"
                           "Предупреждение Flowseal об IPv6 не означает сбой прокси. Если Telegram не подключается, "
                           "отключите попытки IPv6 в настройках подключения самого Telegram. Изменять сетевые "
                           "настройки Linux не требуется.\n\n"
                           "Наличие программы не означает, что прокси работает: состояние проверяйте в GUI и Telegram.")
        message.pack(fill=tk.X)
        ready = False
        stacked = False

        def update_scroll(event=None):
            if not ready:
                return
            canvas.configure(scrollregion=canvas.bbox("all"))
            if body.winfo_reqheight() > canvas.winfo_height() + 1:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=canvas)
            elif scrollbar.winfo_manager():
                scrollbar.pack_forget()
                canvas.yview_moveto(0)

        def resize(event):
            nonlocal stacked
            canvas.itemconfigure(item, width=event.width)
            for label in (heading, message):
                label.configure(wraplength=max(80, event.width - s(40)))
            needs_stack = sum(button.winfo_reqwidth() for button in buttons) + 15 > window.winfo_width() - s(30)
            if needs_stack != stacked:
                stacked = needs_stack
                for index, button in enumerate(buttons):
                    button.pack_forget()
                    button.pack(side=tk.TOP if stacked else tk.LEFT,
                                padx=(0, 0 if stacked or index else 15),
                                pady=(0, 10 if stacked and index == 0 else 0))
            update_scroll()

        body.bind("<Configure>", update_scroll)
        canvas.bind("<Configure>", resize)
        window.bind("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        window.bind("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        window.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))
        window.bind("<Escape>", lambda event: close())
        window.protocol("WM_DELETE_WINDOW", close)
        prepare_window_navigation(window)
        window.update_idletasks()
        width = min(max(body.winfo_reqwidth() + scrollbar.winfo_reqwidth(), footer.winfo_reqwidth()),
                    max(1, window.winfo_screenwidth() - 32))
        canvas.configure(width=width)
        canvas.itemconfigure(item, width=width)
        window.update_idletasks()
        max_height = max(1, window.winfo_screenheight() - 80)
        canvas.configure(height=min(body.winfo_reqheight(), max(1, max_height - footer.winfo_reqheight())))
        height = min(body.winfo_reqheight() + footer.winfo_reqheight(), max_height)
        place_toplevel_centered_on_parent(window, self.window, fixed_content_size=(width, height), immediate=True)
        ready = True
        update_scroll()
        window.grab_set()
        window.focus_set()

    def _set_busy(self, value):
        self.busy = value
        for button in self.buttons:
            button.configure(state=tk.DISABLED if value else tk.NORMAL)

    def _start_worker(self, action, password=None):
        if self.busy or self.closed.is_set():
            return
        self._set_busy(True)
        threading.Thread(target=self._work, args=(action, password), daemon=action not in ("install", "uninstall")).start()

    def _work(self, action, password):
        """No Tk calls, including after(), dialogs and widget reads, in this method."""
        try:
            if action == "install":
                version = self.service.install(password, lambda text: self.events.put(("progress", text)))
                try:
                    self.service.set_autostart(True)
                    self.service.launch()
                except (ProxyError, OSError) as exc:
                    raise ProxyError(f"Версия {version} установлена, но настройка автозапуска/запуск не завершены: {exc}") from exc
                text = f"Установлена версия {version}. Запуск GUI запрошен; проверьте трэй и Telegram."
            elif action == "launch":
                self.service.launch()
                text = "Запуск GUI запрошен. Проверьте трэй; состояние прокси смотрите в GUI."
            elif action == "uninstall":
                self.service.uninstall(password, lambda text: self.events.put(("progress", text)))
                text = "TG WS Proxy и его автозапуск удалены. Настройки подключения сохранены."
            elif action == "open_telegram":
                open_in_telegram(connection_link(self.service.flowseal_dir / "config.json"))
                text = "Ссылка передана Telegram. Подтвердите подключение в Telegram."
            elif action == "copy_link":
                link = connection_link(self.service.flowseal_dir / "config.json")
                if not copy_with_desktop(link):
                    self.events.put(("clipboard", link))
                    return
                text = "Ссылка подключения скопирована. Откройте её в Telegram."
            elif action == "autostart":
                self.service.set_autostart(not self.service.autostart_enabled())
                text = "Настройка автозапуска сохранена."
            else:
                text = ""
            self.events.put(("done", (text, self.service.version(), self.service.autostart_enabled())))
        except Exception as exc:
            # Avoid arbitrary subprocess output (which could include sensitive stdin).
            text = str(exc) if isinstance(exc, ProxyError) else "Операция не завершена. Проверьте доступ к файлам, сеть и окружение рабочего стола."
            self.events.put(("error", text))

    def _poll(self):
        if self.closed.is_set():
            return
        content_changed = False
        while True:
            try:
                kind, payload = self.events.get_nowait()
            except queue.Empty:
                break
            content_changed = True
            if kind == "clipboard":
                self._set_busy(False)
                try:
                    self.window.clipboard_clear()
                    self.window.clipboard_append(payload)
                    self.window.update_idletasks()
                    self.status_label.configure(text="Ссылка подключения скопирована. Откройте её в Telegram.")
                except tk.TclError:
                    show_error(self.window, "Буфер обмена", "Не удалось скопировать ссылку. "
                               "Нажмите «Открыть в Telegram» для подключения без буфера обмена.")
            elif kind == "progress":
                self.status_label.configure(text=payload)
            elif kind == "done":
                text, version, auto = payload
                self.status_label.configure(text=text)
                self.version_label.configure(text=f"Установленная версия: {version}")
                self.auto_label.configure(text="Автозапуск после входа на рабочий стол: " + ("включён" if auto else "выключен"))
                self._set_busy(False)
            else:
                self.status_label.configure(text=payload)
                self._set_busy(False)
                show_error(self.window, "TG WS Proxy", payload)
        if not self.closed.is_set():
            if content_changed and getattr(self, "_layout_ready", False):
                self._body.after_idle(self._fit_content)
            self.poll_id = self.window.after(100, self._poll)

    def install(self):
        if self.busy or self.closed.is_set() or not self.service:
            return
        # Reserve before the modal dialog, which runs a nested Tk event loop.
        self._set_busy(True)
        password = None
        if self.service.plan.backend:
            password = SudoPasswordWindow(self.window).run()
            if password is None or self.closed.is_set():
                if not self.closed.is_set():
                    self._set_busy(False)
                    self.status_label.configure(text="Установка отменена.")
                return
        if not self._prepare_connection_notice():
            if not self.closed.is_set():
                self._set_busy(False)
            return
        self._set_busy(False)
        self._start_worker("install", password)

    def launch(self):
        if self.busy or self.closed.is_set() or not self.service:
            return
        if not self._prepare_connection_notice():
            return
        self._start_worker("launch")

    def _prepare_connection_notice(self):
        """Show the upstream's one-time IPv6 note in our UI, then acknowledge it."""
        marker = self.service.flowseal_dir / ".ipv6_warned"
        try:
            if marker.exists():
                return True
            show_info(self.window, "Подключение Telegram", "TG WS Proxy использует локальный IPv4-прокси. "
                      "Если Telegram не подключается, отключите попытки подключения через IPv6 "
                      "в настройках самого Telegram. Это рекомендация при проблемах, а не сообщение "
                      "о сбое. Отключать IPv6 в системе не требуется.")
            if self.closed.is_set():
                return False
            marker.parent.mkdir(parents=True, exist_ok=True)
            marker.touch(exist_ok=True)
            return True
        except OSError:
            show_error(self.window, "Настройки TG WS Proxy", "Нет доступа к каталогу настроек Flowseal. "
                       "Проверьте права доступа и повторите запуск.")
            return False

    def toggle_autostart(self):
        self._start_worker("autostart")

    def open_telegram(self):
        self._start_worker("open_telegram")

    def copy_link(self):
        self._start_worker("copy_link")

    def uninstall(self):
        if self.busy or self.closed.is_set() or not self.service:
            return
        self._set_busy(True)
        try:
            if not ask_yesno(self.window, "Удаление TG WS Proxy", "Удалить TG WS Proxy? "
                             "Запущенный экземпляр будет остановлен, автозапуск отключён. "
                             "Настройки подключения останутся для повторной установки."):
                return
            if self.closed.is_set():
                return
            password = None
            if self.service.plan.backend:
                password = SudoPasswordWindow(self.window).run()
                if self.closed.is_set():
                    return
                if password is None:
                    self.status_label.configure(text="Удаление отменено.")
                    return
        finally:
            if not self.closed.is_set():
                self._set_busy(False)
        self._start_worker("uninstall", password)

    def _destroyed(self, event):
        if event.widget is self.window:
            self.closed.set()

    def close(self):
        self.closed.set()
        self.window.after_cancel(self.poll_id)
        self.window.destroy()

    def run(self):
        prepare_window_navigation(self.window)
        self.window.wait_window()
