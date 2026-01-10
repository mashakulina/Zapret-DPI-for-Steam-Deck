#!/usr/bin/env python3
import tkinter as tk
import subprocess
import threading
import os
import platform
from tkinter import messagebox
from ui.components.button_styler import create_hover_button
from ui.windows.strategy_window import StrategyWindow
from ui.windows.strategy_selector_window import StrategySelectorWindow
from core.service_manager import ServiceManager
from ui.windows.sudo_password_window import SudoPasswordWindow
from ui.windows.ipset_settings_window import IpsetSettingsWindow
from ui.windows.hostlist_settings_window import HostlistSettingsWindow
from ui.windows.service_unlock_window import ServiceUnlockWindow
from ui.windows.dns_settings_window import DNSSettingsWindow
from ui.windows.connection_check_window import ConnectionCheckWindow
from ui.windows.donat_window import DonationWindow
from ui.windows.info_window import show_info_dialog
from core.dependency_checker import run_dependency_check
from core.zapret_checker import run_zapret_check
from core.file_checker import run_file_check
from core.zapret_uninstaller import run_zapret_uninstall
from ui.windows.update_window import show_update_window

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window_properties()
        self.root.title("Zapret DPI Manager")

        # Переменные для состояния кнопок
        self.zapret_running = False
        self.autostart_enabled = False
        self.service_running = False  # Статус службы
        self.settings_menu_open = False  # Флаг для меню настроек

        self.service_manager = ServiceManager()

        # Путь к файлу gamefilter.enable
        self.game_filter_file = "/home/deck/Zapret_DPI_Manager/utils/gamefilter.enable"

        self.setup_ui()
        # Сначала проверяем зависимости
        self.check_dependencies_on_startup()
        # Затем проверяем zapret
        self.check_zapret_on_startup()
        # Проверяем целостность файлов
        # self.check_files_on_startup()
        self.load_current_strategy()
        self.check_service_status()  # Проверяем статус службы при запуске
        self.schedule_status_update()  # Запускаем периодическую проверку
        self.status_tooltip = None  # Всплывающее окошко для статуса

        # Bind событий фокус
        self.root.bind("<FocusIn>", self.on_focus_in)
        self.root.bind("<FocusOut>", self.on_focus_out)

    def check_dependencies_on_startup(self):
        """Проверяет зависимости при запуске программы"""
        print("=== НАЧАЛО ПРОВЕРКИ ЗАВИСИМОСТЕЙ ===")

        # ВАЖНО: Не скрываем окно, а делаем его видимым
        # Обновляем окно, чтобы оно было готово к отображению диалогов
        self.root.update()
        print("Главное окно обновлено")

        # Запускаем проверку зависимостей (окно видимо)
        print("Запуск run_dependency_check...")
        try:
            dependencies_ok = run_dependency_check(self.root)
            print(f"Результат проверки зависимостей: {dependencies_ok}")
        except Exception as e:
            print(f"ОШИБКА при проверке зависимостей: {e}")
            import traceback
            traceback.print_exc()
            dependencies_ok = False

        print("=== КОНЕЦ ПРОВЕРКИ ЗАВИСИМОСТЕЙ ===")

        return dependencies_ok

    def check_zapret_on_startup(self):
        """Проверяет наличие zapret при запуске программы"""
        print("=== НАЧАЛО ПРОВЕРКИ ZAPRET ===")

        # Делаем окно видимым
        self.root.update()

        # Запускаем проверку zapret
        print("Запуск проверки Zapret...")
        try:
            zapret_ok = run_zapret_check(self.root)
            print(f"Результат проверки Zapret: {zapret_ok}")
        except Exception as e:
            print(f"ОШИБКА при проверке Zapret: {e}")
            import traceback
            traceback.print_exc()
            zapret_ok = False

        print("=== КОНЕЦ ПРОВЕРКИ ZAPRET ===")

        return zapret_ok

    # def check_files_on_startup(self):
    #     """Проверяет наличие zapret при запуске программы"""
    #     print("=== НАЧАЛО ПРОВЕРКИ ФАЙЛОВ ===")
    #
    #     # Делаем окно видимым
    #     self.root.update()
    #
    #     # Запускаем проверку zapret
    #     print("Запуск проверки файлов...")
    #     try:
    #         files_ok = run_file_check(self.root)
    #         print(f"Результат проверки файлов: {files_ok}")
    #     except Exception as e:
    #         print(f"ОШИБКА при проверке файлов: {e}")
    #         import traceback
    #         traceback.print_exc()
    #         files_ok = False
    #
    #     print("=== КОНЕЦ ПРОВЕРКИ ФАЙЛОВ ===")
    #
    #     return files_ok

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("460x230")
        self.root.configure(bg='#182030')

        # Устанавливаем WM_CLASS
        try:
            self.root.wm_class("ZapretDPIManager")
        except:
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

    def on_focus_in(self, event):
        """Обрабатывает получение фокуса окном"""
        self.load_current_strategy()  # Обновляем стратегию при получении фокуса

    def on_focus_out(self, event):
        """Обрабатывает потерю фокуса окном - закрываем меню"""
        self.close_all_menus()

    def close_all_menus(self):
        """Закрывает все открытые выпадающие меню"""
        if self.settings_menu_open:
            self.close_settings_menu()

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Первая строка - иконка настроек и статус службы (теперь разделены: статус слева, иконки справа)
        top_row_frame = tk.Frame(main_frame, bg='#182030')
        top_row_frame.pack(fill=tk.X, pady=(0, 0))

        # ЛЕВАЯ СТОРОНА - Статус службы
        left_status_frame = tk.Frame(top_row_frame, bg='#182030')
        left_status_frame.pack(side=tk.LEFT)

        # Индикатор статуса службы (кружок)
        self.status_indicator = tk.Label(left_status_frame, text="🔴", font=("Arial", 12),
                                        fg='#ff3b30', bg='#182030', cursor='hand2')
        self.status_indicator.pack(side=tk.LEFT)
        self.status_indicator.bind("<Enter>", self.show_status_tooltip)
        self.status_indicator.bind("<Leave>", self.hide_status_tooltip)

        # ПРАВАЯ СТОРОНА - Иконки настроек
        icons_frame = tk.Frame(top_row_frame, bg='#182030')
        icons_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Иконка Game Filter
        self.game_filter_icon = tk.Label(icons_frame, text=self.get_game_filter_icon(), font=("Arial", 12), fg='white', bg='#182030', cursor='hand2')
        self.game_filter_icon.pack(side=tk.LEFT, padx=(0, 10))

        # Обработчик клика
        self.game_filter_icon.bind("<Button-1>", self.toggle_game_filter)

        # Всплывающая подсказка при наведении
        self.game_filter_icon.bind("<Enter>", self.show_game_filter_tooltip)
        self.game_filter_icon.bind("<Leave>", self.hide_game_filter_tooltip)

        # Иконка настроек (справа)
        self.settings_icon = tk.Label(icons_frame, text="⚙️", font=("Arial", 22),
                                    fg='#0a84ff', bg='#182030', cursor="hand2")
        self.settings_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.settings_icon.bind("<Enter>", lambda e: self.settings_icon.config(fg='#30d158'))
        self.settings_icon.bind("<Leave>", lambda e: self.settings_icon.config(fg='#0a84ff'))
        self.settings_icon.bind("<Button-1>", self.toggle_settings_menu)

        # Иконка информации
        self.info_icon = tk.Label(icons_frame, text="🛈︎", font=("Arial", 16),
                                fg='#0a84ff', bg='#182030', cursor="hand2")
        self.info_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.info_icon.bind("<Enter>", lambda e: self.info_icon.config(fg='#30d158'))
        self.info_icon.bind("<Leave>", lambda e: self.info_icon.config(fg='#0a84ff'))
        self.info_icon.bind("<Button-1>", lambda e: show_info_dialog(self.root))

        # Иконка доната
        self.donate_icon = tk.Label(icons_frame, text="💸", font=("Arial", 14),
                                fg='#ffcc00', bg='#182030', cursor="hand2")
        self.donate_icon.pack(side=tk.LEFT)
        self.donate_icon.bind("<Enter>", lambda e: self.donate_icon.config(fg='#ffdd44'))
        self.donate_icon.bind("<Leave>", lambda e: self.donate_icon.config(fg='#ffcc00'))
        self.donate_icon.bind("<Button-1>", self.open_donate_link)

        # Вторая строка - заголовок
        title_row_frame = tk.Frame(main_frame, bg='#182030')
        title_row_frame.pack(fill=tk.X, pady=(0, 10))

        # Заголовок
        title_label = tk.Label(title_row_frame, text="Zapret DPI Manager",
                            font=("Arial", 18, "bold"), fg='white', bg='#182030')
        title_label.pack()

        # Третья строка с информацией о стратегии
        info_frame = tk.Frame(main_frame, bg='#182030')
        info_frame.pack(fill=tk.X, pady=(0, 10))

        # Стратегия
        strategy_frame = tk.Frame(info_frame, bg='#182030')
        strategy_frame.pack()

        strategy_label = tk.Label(strategy_frame, text="Стратегия:",
                                font=("Arial", 11), fg='#8e8e93', bg='#182030')
        strategy_label.pack(side=tk.LEFT, padx=(0, 5))

        self.strategy_value = tk.Label(strategy_frame, text="Загрузка...",
                                    font=("Arial", 11, "bold"), fg='#0a84ff', bg='#182030')
        self.strategy_value.pack(side=tk.LEFT)

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 15,
            'pady': 10,
            'width': 22,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Основные кнопки управления в две строки
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Первая строка кнопок
        first_row_frame = tk.Frame(buttons_frame, bg='#182030')
        first_row_frame.pack(fill=tk.X, pady=(0, 0))

        # Кнопка Запуск/Остановка Zapret DPI
        self.zapret_button = create_hover_button(
            first_row_frame,
            text="Запустить Zapret DPI",
            command=self.toggle_zapret,
            **button_style
        )
        self.zapret_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка Автозапуск
        self.autostart_button = create_hover_button(
            first_row_frame,
            text="Включить автозапуск",
            command=self.toggle_autostart,
            **button_style
        )
        self.autostart_button.pack(side=tk.LEFT)

        # Добавляем статусную строку для сообщений
        self.status_message = tk.Label(
            main_frame,
            text="",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.status_message.pack(pady=(0, 0))

    def load_current_strategy(self):
        """Загружает и отображает текущую стратегию из файла name_strategy.txt"""
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")
            config_file = os.path.join(manager_dir, "config.txt")

            # Проверяем оба файла
            name_strategy_exists = os.path.exists(name_strategy_file)
            config_exists = os.path.exists(config_file)

            strategy_name = "Не выбрано"  # Значение по умолчанию

            if name_strategy_exists and config_exists:
                # Читаем имя стратегии
                with open(name_strategy_file, 'r', encoding='utf-8') as f:
                    name_content = f.read().strip()

                # Читаем config.txt
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_content = f.read().strip()

                # Если оба файла не пустые - показываем имя стратегии
                if name_content and config_content:
                    strategy_name = name_content
                else:
                    # Если один из файлов пустой - показываем "Не выбрано"
                    strategy_name = "Не выбрано"
                    # Очищаем name_strategy.txt если config.txt пустой
                    if not config_content and name_content:
                        with open(name_strategy_file, 'w', encoding='utf-8') as f:
                            f.write("")
            elif name_strategy_exists:
                # Если есть только name_strategy_file, проверяем его содержимое
                with open(name_strategy_file, 'r', encoding='utf-8') as f:
                    name_content = f.read().strip()
                    strategy_name = name_content if name_content else "Не выбрано"
            else:
                # Если файла нет - создаем его
                os.makedirs(os.path.dirname(name_strategy_file), exist_ok=True)
                with open(name_strategy_file, 'w', encoding='utf-8') as f:
                    f.write("")
                strategy_name = "Не выбрано"

            self.strategy_value.config(text=strategy_name)

        except Exception as e:
            print(f"Ошибка загрузки стратегии: {e}")
            self.strategy_value.config(text="Не выбрано")

    def toggle_settings_menu(self, event=None):
        """Открывает/закрывает меню настроек"""
        if self.settings_menu_open:
            self.close_settings_menu()
        else:
            self.open_settings_menu()

    def open_donate_link(self, event=None):
        """Показывает окно доната"""
        donation_window = DonationWindow(self.root)
        donation_window.run()

    def show_status_tooltip(self, event=None):
        """Показывает всплывающее окошко со статусом службы"""
        if self.status_tooltip:
            return

        # Определяем текст в зависимости от цвета индикатора
        status_text = ""
        indicator_status = self.status_indicator.cget("text")

        if indicator_status == '🟢':  # Зеленый
            status_text = "Статус службы: активен"
        elif indicator_status == '🔴':  # Красный
            status_text = "Статус службы: неактивен"
        elif indicator_status == '🟠':  # Оранжевый
            status_text = "Статус службы: неизвестный"
        else:
            status_text = "Статус службы: неопределен"

        # Позиционируем подсказку рядом с индикатором
        x = self.status_indicator.winfo_rootx() - 20
        y = self.status_indicator.winfo_rooty() + self.status_indicator.winfo_height() + 5

        # Создаем всплывающее окно
        self.status_tooltip = tk.Toplevel(self.root)
        self.status_tooltip.wm_overrideredirect(True)
        self.status_tooltip.geometry(f"+{x}+{y}")
        self.status_tooltip.configure(bg='#15354D', relief=tk.SOLID, bd=1)

        # Добавляем текст
        label = tk.Label(self.status_tooltip,
                        text=status_text,
                        font=("Arial", 10),
                        fg='white',
                        bg='#15354D',
                        padx=10,
                        pady=5)
        label.pack()

    def hide_status_tooltip(self, event=None):
        """Скрывает всплывающее окошко со статусом"""
        if self.status_tooltip:
            try:
                self.status_tooltip.destroy()
            except:
                pass
            self.status_tooltip = None

    def get_game_filter_icon(self):
        """Получает иконку Game Filter"""
        return "🎮🟢" if self.is_game_filter_enabled() else "🎮🔴"

    def is_game_filter_enabled(self):
        """Проверяет, включен ли Game Filter"""
        return os.path.exists(self.game_filter_file)

    def show_game_filter_tooltip(self, event=None):
        """Показывает всплывающее окошко со статусом Game Filter"""
        # Не показываем если уже есть
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            return

        # Определяем текст в зависимости от состояния
        if self.is_game_filter_enabled():
            status_text = "GameFilter включен\nНажмите для выключения"
        else:
            status_text = "GameFilter выключен\nНажмите для включения"

        # Позиционируем подсказку рядом с иконкой
        x = self.game_filter_icon.winfo_rootx() - 20
        y = self.game_filter_icon.winfo_rooty() + self.game_filter_icon.winfo_height() + 5

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
                        justify=tk.LEFT)
        label.pack()

    def hide_game_filter_tooltip(self, event=None):
        """Скрывает всплывающее окошко Game Filter"""
        if hasattr(self, 'game_filter_tooltip') and self.game_filter_tooltip:
            self.game_filter_tooltip.destroy()
            self.game_filter_tooltip = None

    def toggle_game_filter(self, event=None):
        """Переключает Game Filter при клике на иконку"""
        # Используем асинхронный подход через after с небольшой задержкой
        self.root.after(100, self._toggle_game_filter_async)

    def _toggle_game_filter_async(self):
        """Асинхронное переключение Game Filter"""
        try:
            # Проверяем пароль sudo через стандартный метод
            if not self.ensure_sudo_password():
                return

            # Теперь выполняем переключение Game Filter
            self._perform_game_filter_toggle()

        except Exception as e:
            error_msg = f"Ошибка переключения Game Filter: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)

    def _perform_game_filter_toggle(self):
        """Выполняет фактическое переключение Game Filter"""
        try:
            # Получаем текущее состояние
            was_enabled = self.is_game_filter_enabled()

            if was_enabled:
                # Удаляем файл (выключаем)
                os.remove(self.game_filter_file)
                new_icon = "🎮🔴"
                status_message = "Game Filter выключен"
                print("🎮🟢 Game Filter выключен")
            else:
                # Создаем файл (включаем)
                # Сначала создаем директорию если не существует
                directory = os.path.dirname(self.game_filter_file)
                if directory and not os.path.exists(directory):
                    os.makedirs(directory, exist_ok=True)

                # Создаем файл
                with open(self.game_filter_file, 'w') as f:
                    pass  # Просто создаем пустой файл

                new_icon = "🎮🟢"
                status_message = "Game Filter включен"
                print("🎮🟢 Game Filter включен")

            # Меняем иконку
            self.game_filter_icon.config(text=new_icon)

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
        self.game_filter_icon.config(state=tk.DISABLED)

        # Показываем анимацию загрузки
        loading_icon = "🎮⚪"
        self.game_filter_icon.config(text=loading_icon)
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
                # Восстанавливаем UI
                self.root.after(0, lambda: self.game_filter_icon.config(
                    text=self.get_game_filter_icon(), state=tk.NORMAL))

                # Обновляем статус службы через 1 секунду
                self.root.after(1000, self.check_service_status)

        # Запускаем в отдельном потоке
        thread = threading.Thread(target=restart_service_thread, daemon=True)
        thread.start()

    def open_settings_menu(self):
        """Открывает меню настроек"""
        if self.settings_menu_open:
            return

        self.settings_menu_open = True

        # Создаем выпадающее меню
        menu_x = self.settings_icon.winfo_rootx()
        menu_y = self.settings_icon.winfo_rooty() + self.settings_icon.winfo_height()

        self.settings_menu = tk.Toplevel(self.root)
        self.settings_menu.wm_overrideredirect(True)
        self.settings_menu.geometry(f"200x340+{menu_x}+{menu_y}")
        self.settings_menu.configure(bg='#15354D', relief=tk.RAISED, bd=1)

        # Стиль для кнопок меню
        menu_button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'relief': tk.FLAT,
            'padx': 12,
            'pady': 10,
            'anchor': tk.W,
            'width': 18,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопки меню
        menu_items = [
            ("Сменить стратегию", self.open_service_window),
            ("Проверка соединения", self.open_connection_check),
            ("Настройки Hostlist", self.open_hostlist_settings),
            ("Настройки IPset", self.open_ipset_settings),
            ("Настройки DNS", self.open_dns_settings),
            ("Разблокировать сервисы", self.open_service_unlock),
            ("Обвноить Zapret", self.open_update_settings),
            ("Удалить Zapret", self.uninstall_zapret)
        ]

        for text, command in menu_items:
            menu_button = create_hover_button(self.settings_menu, text=text,
                                            command=command, **menu_button_style)
            menu_button.pack(fill=tk.X)
            menu_button.bind("<Enter>", lambda e, btn=menu_button: btn.config(bg='#1e4a6a'))
            menu_button.bind("<Leave>", lambda e, btn=menu_button: btn.config(bg='#15354D'))

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
            except:
                pass  # Если окно уже уничтожено
        self.settings_menu_open = False
        try:
            self.root.unbind("<Button-1>")
        except:
            pass

    def is_event_in_widget(self, event, widget):
        """Проверяет, находится ли событие в области виджета"""
        try:
            x, y, width, height = (widget.winfo_rootx(), widget.winfo_rooty(),
                                widget.winfo_width(), widget.winfo_height())
            return (x <= event.x_root <= x + width and
                y <= event.y_root <= y + height)
        except:
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
        ipset_window = IpsetSettingsWindow(self.root)
        ipset_window.run()

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

    def ensure_sudo_password(self):
        """Проверяет и получает пароль sudo если нужно"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return False

        if not self.service_manager.sudo_password:
            # Показываем окно ввода пароля
            if SudoPasswordWindow:
                password_window = SudoPasswordWindow(
                    self.root,
                    on_password_valid=lambda pwd: self.service_manager.set_sudo_password(pwd)
                )
                password = password_window.run()

                if not password:
                    self.show_status_message("Требуется пароль sudo", warning=True)
                    return False
            else:
                self.show_status_message("Модуль запроса пароля не найден", error=True)
                return False

        return True

    def check_service_status(self):
        """Проверяет статус службы Zapret"""
        try:
            # Проверяем статус службы
            result = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True
            )

            status_output = result.stdout.strip()

            if result.returncode == 0 and status_output == "active":
                # Служба активна
                self.service_running = True
                self.status_indicator.config(text="🟢")
                self.zapret_button.config(text="Остановить Zapret DPI")
            elif result.returncode == 3 and status_output == "inactive":
                # Служба неактивна
                self.service_running = False
                self.status_indicator.config(text="🔴")
                self.zapret_button.config(text="Запустить Zapret DPI")
            elif result.returncode == 4:  # Код возврата 4 означает "неактивен" или "не существует"
                self.service_running = False
                self.status_indicator.config(text="🔴")
                self.zapret_button.config(text="Запустить Zapret DPI")
            else:
                # Неизвестный статус
                self.service_running = False
                self.status_indicator.config(text="🟠")
                self.zapret_button.config(text="Запустить Zapret DPI")

            # Теперь проверяем автозапуск ОТДЕЛЬНО
            self.check_autostart_status()

        except Exception as e:
            print(f"Ошибка проверки статуса службы: {e}")
            self.service_running = False
            self.status_indicator.config(text="🟠")
            # Все равно проверяем автозапуск
            self.check_autostart_status()

    def check_autostart_status(self):
        """Проверяет и обновляет статус автозапуска"""
        try:
            # Проверяем статус автозапуска
            result = subprocess.run(
                ["systemctl", "is-enabled", "zapret"],
                capture_output=True,
                text=True
            )

            # systemctl is-enabled возвращает:
            # - 0: enabled (включен)
            # - 1: disabled (отключен)
            # - другие коды: ошибка или не существует

            if result.returncode == 0:
                # Автозапуск включен
                self.autostart_enabled = True
                self.autostart_button.config(text="Отключить автозапуск")
                # print("DEBUG: Автозапуск включен")
            elif result.returncode == 1:
                # Автозапуск отключен
                self.autostart_enabled = False
                self.autostart_button.config(text="Включить автозапуск")
                # print("DEBUG: Автозапуск отключен")
            else:
                # Неизвестный статус (служба может не существовать)
                self.autostart_enabled = False
                self.autostart_button.config(text="Включить автозапуск")
                # print(f"DEBUG: Статус автозапуска неизвестен, код возврата: {result.returncode}")
                # print(f"DEBUG: Вывод: {result.stdout.strip()}")
                # print(f"DEBUG: Ошибка: {result.stderr.strip()}")

        except Exception as e:
            print(f"Ошибка проверки автозапуска: {e}")
            self.autostart_enabled = False
            self.autostart_button.config(text="Включить автозапуск")

    def schedule_status_update(self):
        """Периодически обновляет статус службы"""
        try:
            self.check_service_status()
        except Exception as e:
            print(f"Ошибка при обновлении статуса: {e}")
        finally:
            self.root.after(5000, self.schedule_status_update)  # Проверка каждые 5 секунд

    def toggle_zapret(self):
        """Переключает состояние Zapret (запуск/остановка)"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Меняем состояние UI
        self.zapret_button.config(state=tk.DISABLED)
        if self.service_running:
            self.zapret_button.config(text="Остановка...")
            self.show_status_message("Остановка службы...")
        else:
            self.zapret_button.config(text="Запуск...")
            self.show_status_message("Запуск службы...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_zapret_thread)
        thread.daemon = True
        thread.start()

    def _toggle_zapret_thread(self):
        """Поток для переключения состояния службы"""
        try:
            if self.service_running:
                # Останавливаем службу
                success, message = self.service_manager.stop_service()
                if success:
                    self.show_status_message("Служба остановлена", success=True)
                else:
                    self.show_status_message(f"Ошибка остановки: {message}", error=True)
            else:
                # Запускаем службу
                success, message = self.service_manager.start_service()
                if success:
                    self.show_status_message("Служба запущена", success=True)
                else:
                    self.show_status_message(f"Ошибка запуска: {message}", error=True)

            # Обновляем статус после операции
            self.root.after(1000, self.check_service_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку
            self.root.after(100, lambda: self.zapret_button.config(state=tk.NORMAL))

    def toggle_autostart(self):
        """Переключает автозапуск"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return

        # Сначала проверяем текущий статус
        self.check_autostart_status()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Меняем состояние UI
        self.autostart_button.config(state=tk.DISABLED)
        if self.autostart_enabled:
            self.autostart_button.config(text="Отключение...")
            self.show_status_message("Отключение автозапуска...")
        else:
            self.autostart_button.config(text="Включение...")
            self.show_status_message("Включение автозапуска...")
        self.root.update()

        # Запускаем операцию в отдельном потоке
        thread = threading.Thread(target=self._toggle_autostart_thread)
        thread.daemon = True
        thread.start()

    def _toggle_autostart_thread(self):
        """Поток для переключения автозапуска"""
        try:
            # Двойная проверка состояния перед выполнением
            current_state = self.autostart_enabled

            if current_state:
                # Отключаем автозапуск
                success, message = self.service_manager.disable_autostart()
                if success:
                    self.show_status_message("Автозапуск отключен", success=True)
                    self.autostart_enabled = False
                else:
                    self.show_status_message(f"Ошибка отключения: {message}", error=True)
            else:
                # Включаем автозапуск
                success, message = self.service_manager.enable_autostart()
                if success:
                    self.show_status_message("Автозапуск включен", success=True)
                    self.autostart_enabled = True
                else:
                    self.show_status_message(f"Ошибка включения: {message}", error=True)

            # Обновляем статус после операции
            self.root.after(1000, self.check_autostart_status)

        except Exception as e:
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
        finally:
            # Восстанавливаем кнопку и обновляем текст
            self.root.after(100, lambda: self.autostart_button.config(state=tk.NORMAL))
            self.root.after(100, self.check_autostart_status)  # Еще раз проверяем состояние

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        self.root.after(0, lambda: self._update_status_message(message, success, warning, error))

    def _update_status_message(self, message, success, warning, error):
        """Обновляет статусное сообщение в основном потоке"""
        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg='#30d158')  # Зеленый
        elif warning:
            self.status_message.config(fg='#ff9500')  # Оранжевый
        elif error:
            self.status_message.config(fg='#ff3b30')  # Красный
        else:
            self.status_message.config(fg='#AAAAAA')  # Серый

        # Автоматически очищаем сообщение через 3 секунды (кроме ошибок)
        if message and not error:
            self.root.after(3000, lambda: self.status_message.config(text=""))

    def run(self):
        """Запускает главное окно"""
        self.root.mainloop()

if __name__ == "__main__":
    app = MainWindow()
    app.run()
