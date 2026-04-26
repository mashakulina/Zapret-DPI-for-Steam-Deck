"""Главное окно: меню настроек и действия."""
import tkinter as tk

from ui.components.button_styler import create_hover_button, uniform_button_width_for_font
from ui.windows.connection_check_window import ConnectionCheckWindow
from ui.windows.dns_settings_window import DNSSettingsWindow
from ui.windows.hostlist_settings_window import HostlistSettingsWindow
from ui.windows.ipset_settings_window import IpsetMainWindow
from ui.windows.service_unlock_window import ServiceUnlockWindow
from ui.windows.strategy_selector_window import StrategySelectorWindow
from ui.windows.update_window import show_update_window
from core.dpi_utils import fit_toplevel_to_content
from core.tk_scale_lab_helpers import logical_ui_scale
from ui.integrations.zapret_uninstall import run_zapret_uninstall


class MainUISettingsMixin:
    def open_settings_menu(self):
        """Открывает меню настроек"""
        if self.settings_menu_open:
            return

        self.settings_menu_open = True

        # Создаем выпадающее меню
        menu_x = self.settings_icon.winfo_rootx()
        menu_y = self.settings_icon.winfo_rooty() + self.settings_icon.winfo_height()

        f = logical_ui_scale(self.root)
        base_menu_w, base_menu_h = 240, 385
        menu_w = int(round(base_menu_w * f))
        menu_h = int(round(base_menu_h * f))
        fz = max(9, int(round(11 * f)))
        padx_m = int(max(8, round(12 * f)))
        pady_m = int(max(6, round(10 * f)))
        bd_m = max(1, int(round(f)))

        self.settings_menu = tk.Toplevel(self.root)
        self.settings_menu.wm_overrideredirect(True)
        self.settings_menu.geometry(f"{menu_w}x{menu_h}+{menu_x}+{menu_y}")
        self.settings_menu.configure(bg='#15354D', relief=tk.RAISED, bd=bd_m)

        # Стиль для кнопок меню (явные пиксели/pt — через коэффициент от DPI Tk, см. tk_scale_lab_helpers)
        menu_button_style = {
            'font': ('Arial', fz),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'relief': tk.FLAT,
            'padx': padx_m,
            'pady': pady_m,
            'anchor': tk.W,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        installed = self.is_decky_zapret_plugin_installed()
        plugin_label = "Удалить плагин Zapret DPI" if installed else "Установить плагин Zapret DPI"
        plugin_command = self.remove_decky_plugin if installed else self.install_decky_plugin

        # Кнопки меню
        menu_items = [
            ("Сменить стратегию", self.open_service_window),
            ("Проверка соединения", self.open_connection_check),
            ("Настройки Hostlist", self.open_hostlist_settings),
            ("Настройки IPSet", self.open_ipset_settings),
            ("Настройки DNS", self.open_dns_settings),
            ("Разблокировать сервисы", self.open_service_unlock),
            (plugin_label, plugin_command),
            ("Обновить Zapret", self.open_update_settings),
            ("Удалить Zapret", self.uninstall_zapret)
        ]
        menu_button_style["width"] = max(
            int(round(18 * f)),
            uniform_button_width_for_font(
                self.settings_menu,
                menu_button_style["font"],
                *[t for t, _ in menu_items],
            ),
        )

        for text, command in menu_items:
            menu_button = create_hover_button(self.settings_menu, text=text,
                                            command=command, **menu_button_style)
            menu_button.pack(fill=tk.X)
            menu_button.bind("<Enter>", lambda e, btn=menu_button: btn.config(bg='#1e4a6a'))
            menu_button.bind("<Leave>", lambda e, btn=menu_button: btn.config(bg='#15354D'))

        self.settings_menu.update_idletasks()
        fit_toplevel_to_content(
            self.settings_menu,
            min_width=int(round(200 * f)),
            min_height=int(round(120 * f)),
            margin_width=int(max(4, round(8 * f))),
            margin_height=int(max(8, round(12 * f))),
        )

        # Bind событие клика вне меню для закрытия
        self.settings_menu.bind("<FocusOut>", lambda e: self.close_settings_menu())
        self.root.bind("<Button-1>", self.check_close_settings_menu)

    def check_close_settings_menu(self, event):
        """Проверяет, нужно ли закрыть меню настроек при клике вне его области"""
        if (hasattr(self, 'settings_menu') and self.settings_menu and
            self.settings_menu.winfo_exists()):

            # Проверяем, был ли клик на самом меню или иконке
            menu_widget = event.widget
            while menu_widget:
                if menu_widget == self.settings_menu:
                    return  # Клик внутри меню - не закрываем
                menu_widget = menu_widget.master

            # Если клик был не в меню и не на иконке - закрываем
            if (event.widget != self.settings_icon and
                not self.is_event_in_widget(event, self.settings_icon)):
                self.close_settings_menu()
                self.hide_status_tooltip()

    def close_settings_menu(self):
        """Закрывает меню настроек"""
        if hasattr(self, 'settings_menu') and self.settings_menu:
            try:
                self.settings_menu.destroy()
            except Exception:
                pass  # Если окно уже уничтожено
        self.settings_menu_open = False
        try:
            self.root.unbind("<Button-1>")
        except Exception:
            pass

    def is_event_in_widget(self, event, widget):
        """Проверяет, находится ли событие в области виджета"""
        try:
            x, y, width, height = (widget.winfo_rootx(), widget.winfo_rooty(),
                                widget.winfo_width(), widget.winfo_height())
            return (x <= event.x_root <= x + width and
                y <= event.y_root <= y + height)
        except Exception:
            return False

    def open_service_window(self):
        """Открывает окно выбора типа стратегии"""
        selector_window = StrategySelectorWindow(self.root)
        selector_window.run()
        # После закрытия окна обновляем отображение стратегии
        self.load_current_strategy()

    def open_connection_check(self):
        """Открывает окно проверки соединения"""
        self.close_settings_menu()  # Закрываем меню
        connection_window = ConnectionCheckWindow(self.root)
        connection_window.run()

    def open_hostlist_settings(self):
        """Открывает окно настроек HOSTLIST"""
        self.close_settings_menu()  # Закрываем меню
        hostlist_window = HostlistSettingsWindow(self.root)
        hostlist_window.run()

    def open_ipset_settings(self):
        """Открывает окно настроек IPset"""
        self.close_settings_menu()  # Закрываем меню
        ipset_main_window = IpsetMainWindow(self.root)
        ipset_main_window.run()

    def open_dns_settings(self):
        """Открывает окно настроек DNS"""
        dns_window = DNSSettingsWindow(self.root)
        dns_window.run()

    def open_service_unlock(self):
        """Открывает окно настроек Разблокировки сервисов"""
        self.close_settings_menu()  # Закрываем меню
        unlock_window = ServiceUnlockWindow(self.root)
        unlock_window.run()

    def open_update_settings(self):
        """Открывает окно обновления Zapret"""
        update_window = show_update_window(self.root)
        update_window.run()

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
