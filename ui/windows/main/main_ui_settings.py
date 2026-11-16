"""Главное окно: окно настроек и действия."""
import tkinter as tk

from ui.components.window_navigation import run_child_window

from ui.components.button_styler import create_hover_button, uniform_button_width_for_font
from ui.windows.connection_check_window import ConnectionCheckWindow
from ui.windows.dns_settings_window import DNSSettingsWindow
from ui.windows.firewall_settings_window import FirewallSettingsWindow
from ui.windows.tg_ws_proxy_window import TgWsProxyWindow
from ui.windows.hostlist_settings_window import HostlistSettingsWindow
from ui.windows.ipset_settings_window import IpsetSettingsWindow
from ui.windows.service_unlock_window import ServiceUnlockWindow
from ui.windows.strategy_selector_window import StrategySelectorWindow
from ui.windows.strategy_import_window import StrategyImportWindow
from ui.windows.game_preset_editor_window import GamePresetEditorWindow
from ui.components.custom_messagebox import show_error
from ui.windows.update_window import show_update_window
from core.dpi_utils import place_toplevel_centered_on_parent
from core.app_logging import open_error_log_in_kate
from ui.integrations.zapret_uninstall import run_zapret_uninstall


class MainUISettingsMixin:
    SETTINGS_SECTIONS = ("Стратегии", "Сеть и доступ", "Дополнения", "Обслуживание")

    def open_settings_menu(self):
        """Открывает окно настроек поверх главного окна."""
        try:
            if not self.root.winfo_exists():
                return
        except tk.TclError:
            return
        existing = getattr(self, "settings_menu", None)
        if getattr(existing, "_navigation_child_open", False):
            return
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_set()
            return

        self.hide_icon_tooltip()
        menu_items = [
            (title, lambda section=title: self.open_settings_section(section))
            for title in self.SETTINGS_SECTIONS
        ]
        self.settings_menu = self._create_settings_menu(
            "Настройки", menu_items, self.close_settings_menu,
        )
        self.settings_menu_open = True
        self._show_settings_menu(self.settings_menu)

    def _settings_section_items(self, title):
        """Создаёт действия раздела с актуальным состоянием дополнений."""
        if title == "Стратегии":
            return [
                ("Сменить стратегию", self.open_service_window),
                ("Настройка стратегий", self.open_strategy_import),
                ("Добавление пресета для игры", self.open_game_preset_editor),
            ]
        if title == "Сеть и доступ":
            return [
                ("Настройки Hostlist", self.open_hostlist_settings),
                ("Настройки IPSet", self.open_ipset_settings),
                ("Настройки DNS", self.open_dns_settings),
                ("Фаервол", self.open_firewall_settings),
                ("Разблокировать сервисы", self.open_service_unlock),
                ("Проверка соединения", self.open_connection_check),
            ]
        if title == "Дополнения":
            installed = self.is_decky_zapret_plugin_installed()
            return [
                ("TG WS Proxy by Flowseal", self.open_tg_ws_proxy),
                ("Удалить плагин Zapret DPI" if installed else "Установить плагин Zapret DPI",
                 self.remove_decky_plugin if installed else self.install_decky_plugin),
                ("Открыть лог ошибок", self.open_error_log),
            ]
        if title == "Обслуживание":
            return [
                ("Обновить Zapret", self.open_update_settings),
                ("Удалить Zapret", self.uninstall_zapret),
            ]
        raise ValueError(f"Неизвестный раздел настроек: {title}")

    def open_settings_section(self, title):
        """Ожидает закрытия раздела, пока корневое меню скрыто навигацией."""
        items = self._settings_section_items(title)
        window = self._create_settings_menu(
            title, items, lambda: self._close_settings_window(window),
        )
        self.settings_section_menu = window
        if title == "Дополнения":
            self.decky_plugin_menu = window
            self.decky_plugin_button = window._settings_buttons[1]
        try:
            if self._show_settings_menu(window):
                window.wait_window()
        finally:
            self.settings_section_menu = None
            if title == "Дополнения":
                self.decky_plugin_button = None
                self.decky_plugin_menu = None

    def _create_settings_menu(self, title, menu_items, close_command):
        """Собирает скрытое меню; показ — после регистрации его состояния."""
        window = tk.Toplevel(self.root)
        window.withdraw()
        window.title(title)
        window.configure(bg='#182030')
        window.transient(self.root)
        window.protocol("WM_DELETE_WINDOW", close_command)
        window.bind("<Escape>", lambda event: close_command())

        # Отступы компактного меню — в px, шрифты в pt масштабирует сам Tk.
        main_frame = tk.Frame(window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        heading = tk.Label(main_frame, text=title, font=('Arial', 14, 'bold'),
                           bg='#182030', fg='white')
        heading.pack(fill=tk.X, pady=(0, 30))
        heading.bind('<Configure>', lambda event: heading.configure(wraplength=max(1, event.width)))

        labels = [text for text, _ in menu_items]
        if title == "Дополнения":
            labels.extend(("Установить плагин Zapret DPI", "Удалить плагин Zapret DPI"))
        button_width = max(32, uniform_button_width_for_font(window, ('Arial', 11), *labels))
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 10,
            'pady': 8,
            'width': button_width,
            'anchor': tk.CENTER,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        footer = tk.Frame(main_frame, bg='#182030')
        footer.pack(side=tk.BOTTOM, fill=tk.X, pady=(25, 0))
        create_hover_button(footer, text="Назад", command=close_command,
                            **dict(button_style, width=20)).pack()
        list_frame = tk.Frame(main_frame, bg='#182030')
        list_frame.pack(fill=tk.BOTH, expand=True)
        canvas = tk.Canvas(list_frame, bg='#182030', bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=canvas.yview)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        buttons_frame = tk.Frame(canvas, bg='#182030')
        inner = canvas.create_window((0, 0), window=buttons_frame, anchor='nw')
        layout_ready = False
        wrapped = None
        buttons = []

        def fit_buttons(viewport_width):
            nonlocal wrapped
            # При нехватке ширины переносим подписи всей группы одинаково.
            wraplength = max(1, viewport_width - 20) if natural_button_width > viewport_width else 0
            if wraplength == wrapped:
                return
            wrapped = wraplength
            for button in buttons:
                button.configure(width=0 if wraplength else button_width, wraplength=wraplength)

        def update_viewport(event=None):
            viewport_width = event.width if event is not None else canvas.winfo_width()
            viewport_height = event.height if event is not None else canvas.winfo_height()
            canvas.itemconfigure(inner, width=viewport_width)
            if not layout_ready:
                return
            fit_buttons(viewport_width)
            if buttons_frame.winfo_reqheight() > viewport_height + 1:
                if not scrollbar.winfo_manager():
                    scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=canvas)
            elif scrollbar.winfo_manager():
                scrollbar.pack_forget()
                canvas.yview_moveto(0)

        canvas.bind("<Configure>", update_viewport)
        buttons_frame.bind("<Configure>", lambda event: (
            canvas.configure(scrollregion=canvas.bbox('all')), update_viewport(),
        ))

        buttons_frame.grid_anchor(tk.N)
        for index, (text, command) in enumerate(menu_items):
            buttons.append(create_hover_button(
                buttons_frame, text=text,
                command=lambda action=command: self._run_settings_action(action, window=window),
                **button_style,
            ))
            buttons[-1].grid(row=index, column=0, sticky='ew',
                             pady=(0, 15 if index < len(menu_items) - 1 else 0))
        window.update_idletasks()
        max_width = max(1, self.root.winfo_screenwidth() - 32)
        max_height = max(1, self.root.winfo_screenheight() - 80)
        natural_button_width = max(button.winfo_reqwidth() for button in buttons)
        available_width = max(1, max_width - 20 - scrollbar.winfo_reqwidth())
        fit_buttons(available_width)

        # Прокрутка нужна, если все пункты не помещаются на экране при высоком DPI.
        # Привязки к окну действуют и над кнопками, не затрагивая другие диалоги.
        window.bind("<Button-4>", lambda event: canvas.yview_scroll(-1, "units"))
        window.bind("<Button-5>", lambda event: canvas.yview_scroll(1, "units"))
        window.bind("<MouseWheel>", lambda event: canvas.yview_scroll(-int(event.delta / 120), "units"))
        window.update_idletasks()
        canvas.configure(width=buttons_frame.winfo_reqwidth(), height=buttons_frame.winfo_reqheight())
        window.update_idletasks()
        if window.winfo_reqheight() > max_height:
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y, before=canvas)
            window.update_idletasks()
        width = min(window.winfo_reqwidth(), max_width)
        height = min(window.winfo_reqheight(), max_height)
        window.minsize(width, min(200, height))

        def activate_viewport():
            nonlocal layout_ready
            layout_ready = True
            update_viewport()

        window._settings_content_size = (width, height)
        window._settings_activate_viewport = activate_viewport
        window._settings_buttons = buttons
        window._settings_canvas = canvas
        window._settings_scrollbar = scrollbar
        return window

    def _show_settings_menu(self, window):
        # Центрирование обрабатывает события Tk: состояние и обработчики
        # закрытия должны быть готовы до показа, в том числе при раннем Esc.
        place_toplevel_centered_on_parent(
            window, self.root, fixed_content_size=window._settings_content_size, immediate=True,
        )
        try:
            if window.winfo_exists():
                window._settings_activate_viewport()
                window.grab_set()
                window.focus_set()
                return True
        except tk.TclError:
            pass  # Приложение могло закрыться во время центрирования.
        return False

    def _run_settings_action(self, command, window=None):
        """Возвращает тот же раздел или корневое меню после дочернего окна."""
        if window is None:
            window = getattr(self, "settings_menu", None)
        if window is None:
            return command()
        return run_child_window(window, command, on_return=self.refresh_decky_plugin_button)

    def refresh_decky_plugin_button(self):
        """Обновляет действие Decky после возврата и фоновой операции."""
        button = getattr(self, "decky_plugin_button", None)
        if button is None:
            return
        try:
            if not button.winfo_exists():
                return
            installed = self.is_decky_zapret_plugin_installed()
            self.decky_plugin_installed = installed
            command = self.remove_decky_plugin if installed else self.install_decky_plugin
            button.configure(
                text="Удалить плагин Zapret DPI" if installed else "Установить плагин Zapret DPI",
                command=lambda: self._run_settings_action(
                    command, window=getattr(self, "decky_plugin_menu", None),
                ),
            )
        except tk.TclError:
            pass

    def close_settings_menu(self):
        """Закрывает окно настроек и освобождает захват ввода."""
        window = getattr(self, "settings_menu", None)
        if getattr(window, "_navigation_child_open", False):
            return
        self.settings_menu = None
        self.settings_menu_open = False
        self._close_settings_window(window)

    @staticmethod
    def _close_settings_window(window):
        """Закрывает текущий уровень, не затрагивая скрытых предков."""
        if getattr(window, "_navigation_child_open", False):
            return
        if window is not None:
            try:
                if window.grab_current() == window:
                    window.grab_release()
                window.destroy()
            except tk.TclError:
                pass  # Если окно уже уничтожено

    def open_service_window(self):
        """Открывает окно выбора типа стратегии"""
        selector_window = StrategySelectorWindow(self.root)
        selector_window.run()
        # После выхода из приложения виджеты главного окна уже уничтожены.
        try:
            if self.root.winfo_exists():
                self.load_current_strategy()
        except tk.TclError:
            pass

    def open_game_preset_editor(self):
        try:
            GamePresetEditorWindow(self.root).run()
        except (OSError, ValueError, UnicodeError) as error:
            show_error(self.root, "Ошибка пресета", str(error))

    def open_strategy_import(self):
        StrategyImportWindow(self.root).run()

    def open_connection_check(self):
        """Открывает окно проверки соединения"""
        connection_window = ConnectionCheckWindow(self.root)
        connection_window.run()

    def open_error_log(self):
        """Открывает штатный журнал ошибок приложения в Kate."""
        try:
            self._error_log_process = open_error_log_in_kate()
        except OSError as error:
            show_error(self.root, "Ошибка открытия лога", str(error))

    def open_hostlist_settings(self):
        """Открывает окно настроек HOSTLIST"""
        hostlist_window = HostlistSettingsWindow(self.root)
        hostlist_window.run()

    def open_ipset_settings(self):
        """Сразу открывает добавление пользовательских IP-адресов."""
        ipset_window = IpsetSettingsWindow(self.root)
        ipset_window.run()

    def open_tg_ws_proxy(self):
        existing = getattr(self, "tg_ws_proxy_window", None)
        if existing is not None and existing.window.winfo_exists():
            existing.window.lift()
            existing.window.focus_set()
            existing.run()
            return
        self.tg_ws_proxy_window = TgWsProxyWindow(self.root)
        self.tg_ws_proxy_window.run()

    def open_dns_settings(self):
        """Открывает окно настроек DNS"""
        dns_window = DNSSettingsWindow(self.root)
        dns_window.run()

    def open_firewall_settings(self):
        """Открывает выбор фаервола службы."""
        FirewallSettingsWindow(self.root, main_window=self).run()

    def open_service_unlock(self):
        """Открывает окно настроек Разблокировки сервисов"""
        unlock_window = ServiceUnlockWindow(self.root)
        unlock_window.run()

    def open_update_settings(self):
        """Открывает окно обновления Zapret"""
        show_update_window(self.root)

    def uninstall_zapret(self):
        """Запускает удаление Zapret"""
        try:
            # Запускаем удаление
            result = run_zapret_uninstall(self.root)

            if result:
                # Если удаление успешно, закрываем программу
                self.show_status_message("Zapret удален. Программа закроется...", success=True)
                self.root.after(2000, self.root.destroy)
            else:
                self.show_status_message("Удаление отменено или не удалось", warning=True)

        except ImportError as e:
            self.show_status_message(f"Ошибка импорта модуля удаления: {e}", error=True)
        except Exception as e:
            self.show_status_message(f"Ошибка при удалении: {e}", error=True)
