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
from ui.windows.ipset_settings_window import IpsetMainWindow
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
from ui.windows.gamefilter_window import GameFilterWindow

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
        self.restarting = False  # Флаг перезапуска службы

        self.service_manager = ServiceManager()

        # Путь к файлу gamefilter.enable
        home_dir = os.path.expanduser("~")
        self.game_filter_file = os.path.join(home_dir, "Zapret_DPI_Manager", "utils", "gamefilter.enable")

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
        self.root.after(100, self.check_updates_on_startup)

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

    def check_updates_on_startup(self):
        """Проверяет обновления при запуске программы"""
        # Запускаем в отдельном потоке, чтобы не блокировать UI
        thread = threading.Thread(target=self._check_updates_using_updater, daemon=True)
        thread.start()

    def _check_updates_using_updater(self):
        """Проверяет обновления с использованием существующего Updater'а"""
        try:
            from core.manager_updater import ManagerUpdater
            from core.zapret_updater import ZapretUpdater

            manager_update_info = None
            zapret_update_info = None

            # Проверка обновления менеджера
            try:
                manager_updater = ManagerUpdater()
                latest_version, update_info = manager_updater.check_for_updates()

                if latest_version and update_info:
                    manager_update_info = {
                        'current': manager_updater.current_version,
                        'available': latest_version,
                        'name': 'менеджера'
                    }
                    print(f"🔄 Обновление менеджера найдено: {manager_updater.current_version} → {latest_version}")
                else:
                    print(f"✅ Версия менеджера актуальна: {manager_updater.current_version}")

            except Exception as e:
                print(f"⚠️ Не удалось проверить обновление менеджера: {e}")
                import traceback
                traceback.print_exc()

            # Проверка обновления службы Zapret
            try:
                zapret_updater = ZapretUpdater()
                latest_version, update_info = zapret_updater.check_for_updates()

                if latest_version and update_info:
                    zapret_update_info = {
                        'current': zapret_updater.current_version,
                        'available': latest_version,
                        'name': 'zapret службы'
                    }
                    print(f"🔄 Обновление службы Zapret найдено: {zapret_updater.current_version} → {latest_version}")
                else:
                    print(f"✅ Версия службы Zapret актуальна: {zapret_updater.current_version}")

            except Exception as e:
                print(f"⚠️ Не удалось проверить обновление службы Zapret: {e}")
                import traceback
                traceback.print_exc()

            # Показываем уведомление если есть обновления
            if manager_update_info or zapret_update_info:
                print(f"\n🎯 Найдены обновления! Показываю уведомление...")
                self.root.after(0, lambda: self.show_update_notification(
                    manager_update_info,
                    zapret_update_info
                ))
            else:
                print(f"\n✅ Все компоненты обновлены")

        except Exception as e:
            print(f"❌ Ошибка при проверке обновлений: {e}")
            import traceback
            traceback.print_exc()

    def show_update_notification(self, manager_update_info, zapret_update_info):
        """Показывает окно уведомления об обновлениях с номерами версий"""
        # Определяем размер окна в зависимости от количества обновлений
        if manager_update_info and zapret_update_info:
            height = 350
            width = 370
            title = "Доступны обновления"
        elif manager_update_info:
            height = 240
            width = 400
            title = "Доступно обновление менеджера"
        else:
            height = 240
            width = 440
            title = "Доступно обновление службы Zapret"

        # Создаем окно уведомления
        notification_window = tk.Toplevel(self.root)
        notification_window.title(title)
        notification_window.geometry(f"{width}x{height}")
        notification_window.configure(bg='#182030')
        notification_window.grab_set()  # Модальное окно

        # Основной контейнер
        main_frame = tk.Frame(notification_window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text=title,
            font=("Arial", 16, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 20))

        # Информационное сообщение
        info_label = tk.Label(
            main_frame,
            text="Рекомендуется обновиться для получения\nновых функций и исправлений ошибок",
            font=("Arial", 11),
            fg='#AAAAAA',
            bg='#182030',
            justify=tk.CENTER
        )
        info_label.pack(pady=(0, 20))

        # Фрейм для сообщений об обновлениях
        updates_frame = tk.Frame(main_frame, bg='#182030')
        updates_frame.pack(fill=tk.X, pady=(0, 0))

        if manager_update_info and zapret_update_info:

            manager_frame = tk.Frame(updates_frame, bg='#182030')
            manager_frame.pack(fill=tk.X, pady=(0, 12))

            # Иконка и название
            header_frame = tk.Frame(manager_frame, bg='#182030')
            header_frame.pack(fill=tk.X, pady=(0, 5))

            manager_name = tk.Label(
                header_frame,
                text="Zapret DPI Manager",
                font=("Arial", 12, "bold"),
                fg='#0a84ff',
                bg='#182030',
            )
            manager_name.pack(pady=(0, 0))

            # Версии
            versions_frame = tk.Frame(manager_frame, bg='#182030')
            versions_frame.pack(fill=tk.X, pady=5)

            # Создаем контейнер для центрирования
            center_container = tk.Frame(versions_frame, bg='#182030')
            center_container.pack(expand=True)  # Это центрирует содержимое

            current_version_label = tk.Label(
                center_container,
                text=f"Текущая версия: {manager_update_info['current']}",
                font=("Arial", 11),
                fg='#AAAAAA',
                bg='#182030'
            )
            current_version_label.pack(side=tk.LEFT, padx=(0, 10))

            arrow_label = tk.Label(
                center_container,
                text="→",
                font=("Arial", 11),
                fg='white',
                bg='#182030'
            )
            arrow_label.pack(side=tk.LEFT)

            new_version_label = tk.Label(
                center_container,
                text=f"Новая версия: {manager_update_info['available']}",
                font=("Arial", 11, "bold"),
                fg='#30d158',
                bg='#182030'
            )
            new_version_label.pack(side=tk.LEFT, padx=(10, 0))

            zapret_frame = tk.Frame(updates_frame, bg='#182030')
            zapret_frame.pack(fill=tk.X, pady=(0, 12))

            # Иконка и название
            header_frame = tk.Frame(zapret_frame, bg='#182030')
            header_frame.pack(fill=tk.X, pady=(0, 5))

            zapret_name = tk.Label(
                header_frame,
                text="Служба Zapret",
                font=("Arial", 12, "bold"),
                fg='#0a84ff',
                bg='#182030',
            )
            zapret_name.pack(pady=(0, 0))

            # Версии
            versions_frame = tk.Frame(zapret_frame, bg='#182030')
            versions_frame.pack(fill=tk.X, pady=5)

            # Создаем контейнер для центрирования
            center_container = tk.Frame(versions_frame, bg='#182030')
            center_container.pack(expand=True)  # Это центрирует содержимое

            current_version_label = tk.Label(
                center_container,
                text=f"Текущая версия: {zapret_update_info['current']}",
                font=("Arial", 11),
                fg='#AAAAAA',
                bg='#182030'
            )
            current_version_label.pack(side=tk.LEFT, padx=(0, 10))

            arrow_label = tk.Label(
                center_container,
                text="→",
                font=("Arial", 11),
                fg='white',
                bg='#182030'
            )
            arrow_label.pack(side=tk.LEFT)

            new_version_label = tk.Label(
                center_container,
                text=f"Новая версия: {zapret_update_info['available']}",
                font=("Arial", 11, "bold"),
                fg='#30d158',
                bg='#182030'
            )
            new_version_label.pack(side=tk.LEFT, padx=(10, 0))

        # Сообщение об обновлениях с версиями
        elif manager_update_info:
            manager_frame = tk.Frame(updates_frame, bg='#182030')
            manager_frame.pack(fill=tk.X, pady=(0, 12))

            # Иконка и название
            header_frame = tk.Frame(manager_frame, bg='#182030')
            header_frame.pack(fill=tk.X, pady=(0, 5))

            # Версии
            versions_frame = tk.Frame(manager_frame, bg='#182030')
            versions_frame.pack(fill=tk.X, pady=5)

            # Создаем контейнер для центрирования
            center_container = tk.Frame(versions_frame, bg='#182030')
            center_container.pack(expand=True)  # Это центрирует содержимое

            current_version_label = tk.Label(
                center_container,
                text=f"Текущая версия: {manager_update_info['current']}",
                font=("Arial", 11),
                fg='#AAAAAA',
                bg='#182030'
            )
            current_version_label.pack(side=tk.LEFT, padx=(0, 10))

            arrow_label = tk.Label(
                center_container,
                text="→",
                font=("Arial", 11),
                fg='white',
                bg='#182030'
            )
            arrow_label.pack(side=tk.LEFT)

            new_version_label = tk.Label(
                center_container,
                text=f"Новая версия: {manager_update_info['available']}",
                font=("Arial", 11, "bold"),
                fg='#30d158',
                bg='#182030'
            )
            new_version_label.pack(side=tk.LEFT, padx=(10, 0))

        elif zapret_update_info:
            zapret_frame = tk.Frame(updates_frame, bg='#182030')
            zapret_frame.pack(fill=tk.X, pady=(0, 12))

            # Иконка и название
            header_frame = tk.Frame(zapret_frame, bg='#182030')
            header_frame.pack(fill=tk.X, pady=(0, 5))

            # Версии
            versions_frame = tk.Frame(zapret_frame, bg='#182030')
            versions_frame.pack(fill=tk.X, pady=5)

            # Создаем контейнер для центрирования
            center_container = tk.Frame(versions_frame, bg='#182030')
            center_container.pack(expand=True)

            current_version_label = tk.Label(
                center_container,
                text=f"Текущая версия: {zapret_update_info['current']}",
                font=("Arial", 11),
                fg='#AAAAAA',
                bg='#182030'
            )
            current_version_label.pack(side=tk.LEFT, padx=(0, 10))

            arrow_label = tk.Label(
                center_container,
                text="→",
                font=("Arial", 11),
                fg='white',
                bg='#182030'
            )
            arrow_label.pack(side=tk.LEFT)

            new_version_label = tk.Label(
                center_container,
                text=f"Новая версия: {zapret_update_info['available']}",
                font=("Arial", 11, "bold"),
                fg='#30d158',
                bg='#182030'
            )
            new_version_label.pack(side=tk.LEFT, padx=(10, 0))

        # Фрейм для кнопок по центру
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(0, 10))

        # Центральный контейнер для кнопок
        center_frame = tk.Frame(buttons_frame, bg='#182030')
        center_frame.pack(expand=True)

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'width': 14,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка "Обновиться"
        update_button = tk.Button(
            center_frame,
            text="Обновиться",
            command=lambda: self.open_update_window(notification_window),
            **button_style
        )
        update_button.pack(side=tk.LEFT, padx=(0, 10))

        # Добавляем эффект наведения для кнопки "Обновиться"
        update_button.bind("<Enter>", lambda e: update_button.config(bg='#1e4a6a'))
        update_button.bind("<Leave>", lambda e: update_button.config(bg='#15354D'))

        # Кнопка "Пропустить"
        skip_button = tk.Button(
            center_frame,
            text="Пропустить",
            command=notification_window.destroy,
            **button_style
        )
        skip_button.pack(side=tk.LEFT)

        # Добавляем эффект наведения для кнопки "Пропустить"
        skip_button.bind("<Enter>", lambda e: skip_button.config(bg='#1e4a6a'))
        skip_button.bind("<Leave>", lambda e: skip_button.config(bg='#15354D'))

        # Связываем закрытие окна с кнопкой пропустить
        notification_window.protocol("WM_DELETE_WINDOW", notification_window.destroy)

    def open_update_window(self, notification_window):
        """Открывает окно обновления и закрывает уведомление"""
        notification_window.destroy()

        # Запускаем процесс обновления
        thread = threading.Thread(target=self._prepare_and_show_updates, daemon=True)
        thread.start()

    def _prepare_and_show_updates(self):
        """Подготавливает и показывает окно обновления"""
        try:
            from core.manager_updater import ManagerUpdater
            from core.zapret_updater import ZapretUpdater
            from ui.windows.update_window import show_update_progress_window

            # Получаем информацию об обновлениях
            update_tasks = []

            # Проверяем обновление менеджера
            try:
                manager_updater = ManagerUpdater()
                latest_manager_version, manager_update_info = manager_updater.check_for_updates()

                if latest_manager_version and manager_update_info:
                    update_tasks.append({
                        'name': 'Zapret DPI Manager',
                        'updater_class': 'ManagerUpdater',
                        'download_url': manager_update_info.get('download_url')
                    })
                    print(f"🔄 Обновление менеджера доступно")

            except Exception as e:
                print(f"⚠️ Не удалось получить информацию об обновлении менеджера: {e}")

            # Проверяем обновление службы Zapret
            try:
                zapret_updater = ZapretUpdater()
                latest_zapret_version, zapret_update_info = zapret_updater.check_for_updates()

                if latest_zapret_version and zapret_update_info:
                    update_tasks.append({
                        'name': 'Служба Zapret',
                        'updater_class': 'ZapretUpdater',
                        'download_url': zapret_update_info.get('download_url')
                    })
                    print(f"🔄 Обновление службы Zapret доступно")

            except Exception as e:
                print(f"⚠️ Не удалось получить информацию об обновлении службы Zapret: {e}")

            if not update_tasks:
                self.root.after(0, lambda: self.show_status_message("Нет доступных обновлений", warning=True))
                return

            # Показываем окно прогресса обновления
            self.root.after(0, lambda: show_update_progress_window(self.root, update_tasks))

            # После завершения обновления проверяем статус службы
            self.root.after(2000, self.check_service_status)

        except Exception as e:
            print(f"❌ Ошибка при подготовке обновления: {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: self.show_status_message(f"Ошибка обновления: {e}", error=True))

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

        # Иконка перезапуска службы
        self.restart_icon = tk.Button(
            left_status_frame,
            text="↻",
            font=("Arial",20),
            fg='#0a84ff',
            bg='#182030',
            bd=0,
            activebackground='#182030',
            activeforeground='#0a84ff',
            cursor='hand2',
            highlightthickness=0,
            relief=tk.FLAT
        )
        self.restart_icon.pack(side=tk.LEFT, padx=(0, 0))
        self.restart_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Перезапустить службу"))
        self.restart_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
        self.restart_icon.bind("<Button-1>", self.restart_zapret_service_properly)

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

        # Иконка настроек (шестеренка)
        self.settings_icon = tk.Label(icons_frame, text="⚙️", font=("Arial", 22),
                                    fg='#0a84ff', bg='#182030', cursor="hand2")
        self.settings_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.settings_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Открыть меню настроек"))
        self.settings_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
        self.settings_icon.bind("<Button-1>", self.toggle_settings_menu)

        # Иконка книги (руководство пользователя)
        self.book_icon = tk.Label(icons_frame, text="📖", font=("Arial", 18),
                                fg='#0a84ff', bg='#182030', cursor="hand2")
        self.book_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.book_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Открыть руководство пользователя"))
        self.book_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
        self.book_icon.bind("<Button-1>", self.open_user_guide)

        # Иконка информации
        self.info_icon = tk.Label(icons_frame, text="🛈︎", font=("Arial", 16),
                                fg='#0a84ff', bg='#182030', cursor="hand2")
        self.info_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.info_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Информация о программе"))
        self.info_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
        self.info_icon.bind("<Button-1>", lambda e: show_info_dialog(self.root))

        # Иконка доната
        self.donate_icon = tk.Label(icons_frame, text="💸", font=("Arial", 14),
                                fg='#ffcc00', bg='#182030', cursor="hand2")
        self.donate_icon.pack(side=tk.LEFT)
        self.donate_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Поблагодарить разработчика"))
        self.donate_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
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

        # Центральный контейнер для кнопок
        center_frame = tk.Frame(buttons_frame, bg='#182030')
        center_frame.pack(expand=True)

        # Кнопка Запуск/Остановка службы Zapret DPI
        self.zapret_button = create_hover_button(
            center_frame,
            text="Запустить Zapret DPI",
            command=self.toggle_zapret,
            **button_style
        )
        self.zapret_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка вкл/выкл Автозапуска службы Zapret
        self.autostart_button = create_hover_button(
            center_frame,
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

    def open_user_guide(self, event=None):
        """Открывает руководство пользователя в браузере"""
        import webbrowser
        url = "https://telegra.ph/Rukovodstvo-polzovatelya-Zapret-DPI-Manager-20-dlya-Steam-Deck-01-04"

        try:
            webbrowser.open(url)
            self.show_status_message("Открываю руководство пользователя...", success=True)
        except Exception as e:
            error_msg = f"Не удалось открыть руководство: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)

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


    def show_icon_tooltip(self, event, description):
        """Показывает всплывающее окошко для иконки"""
        if hasattr(self, 'icon_tooltip') and self.icon_tooltip:
            self.hide_icon_tooltip()

        # Определяем виджет-источник события
        widget = event.widget

        # Позиционируем подсказку рядом с иконкой
        x = widget.winfo_rootx() - 20
        y = widget.winfo_rooty() + widget.winfo_height() + 5

        # Создаем всплывающее окно
        self.icon_tooltip = tk.Toplevel(self.root)
        self.icon_tooltip.wm_overrideredirect(True)
        self.icon_tooltip.geometry(f"+{x}+{y}")
        self.icon_tooltip.configure(bg='#15354D', relief=tk.SOLID, bd=1)

        # Добавляем текст с заголовком и описанием
        text_frame = tk.Frame(self.icon_tooltip, bg='#15354D')
        text_frame.pack(padx=10, pady=5)

        # Описание
        desc_label = tk.Label(text_frame,
                            text=description,
                            font=("Arial", 9),
                            fg='white',
                            bg='#15354D',
                            justify=tk.LEFT)
        desc_label.pack(anchor=tk.W)

    def hide_icon_tooltip(self, event=None):
        """Скрывает всплывающее окошко для иконки"""
        if hasattr(self, 'icon_tooltip') and self.icon_tooltip:
            try:
                self.icon_tooltip.destroy()
            except:
                pass  # Если окно уже уничтожено
            self.icon_tooltip = None

    def hide_status_tooltip(self, event=None):
        """Скрывает всплывающее окошко со статусом"""
        if self.status_tooltip:
            try:
                self.status_tooltip.destroy()
            except:
                pass
            self.status_tooltip = None

    def restart_zapret_service_properly(self, event=None):
        """Правильный перезапуск службы - использует тот же механизм что и другие кнопки"""
        if self.restarting:
            return

        # 1. Проверяем пароль ЧЕРЕЗ ensure_sudo_password (как другие кнопки)
        if not self.ensure_sudo_password():
            return  # Если пароль не получен - выходим

        # 2. Запускаем перезапуск
        self._perform_restart()

    def _perform_restart(self):
        """Выполняет перезапуск службы"""
        try:
            # Сначала блокируем UI
            self.restarting = True
            self.restart_icon.config(state=tk.DISABLED)

            # Показываем сообщение
            self.show_status_message("Перезапуск службы Zapret...")

            # Обновляем окно чтобы оно было видимым
            self.root.update_idletasks()
            self.root.update()

            # Запускаем в отдельном потоке
            thread = threading.Thread(target=self._restart_zapret_thread, daemon=True)
            thread.start()

        except Exception as e:
            print(f"Ошибка при запуске перезапуска: {e}")
            self.show_status_message(f"Ошибка: {str(e)}", error=True)
            self.restarting = False
            self.restart_icon.config(state=tk.NORMAL)

    def _restart_zapret_thread(self):
        """Поток для перезапуска службы"""
        try:
            # Запускаем перезапуск службы
            success, message = self.service_manager.restart_service()

            if success:
                self.root.after(0, lambda: self.show_status_message(
                    "Служба Zapret успешно перезапущена", success=True))
            else:
                self.root.after(0, lambda: self.show_status_message(
                    f"Ошибка: {message}", error=True))

        except Exception as e:
            self.root.after(0, lambda: self.show_status_message(
                f"Ошибка перезапуска службы: {e}", error=True))
        finally:
            # Восстанавливаем UI
            self.root.after(0, lambda: self.restart_icon.config(state=tk.NORMAL))
            self.restarting = False

            # Обновляем статус службы через 1 секунду
            self.root.after(1000, self.check_service_status)

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
        """Открывает окно GameFilter при клике на иконку."""
        gamefilter_window = GameFilterWindow(self.root, self)
        gamefilter_window.run()

    def _show_game_filter_warning(self):
        """Показывает предупреждение о Game Filter с адаптацией под Steam Deck"""

        # Закрываем все всплывающие подсказки перед показом окна
        self.hide_game_filter_tooltip()
        self.hide_icon_tooltip()
        self.hide_status_tooltip()

        # Сначала делаем главное окно видимым и поднимаем его
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

        # Создаем окно предупреждения
        warning_window = tk.Toplevel(self.root)
        warning_window.title("ВНИМАНИЕ!")
        warning_window.configure(bg='#182030')

        # Определяем функцию для проверки Steam Deck
        def is_steamdeck():
            """Проверяет, работает ли приложение на Steam Deck"""
            try:
                # Проверяем системные файлы Steam Deck
                steamdeck_files = [
                    "/sys/devices/platform/steamdeck_hwmon",
                    "/sys/devices/virtual/dmi/id/product_name"
                ]

                # Проверяем наличие файлов Steam Deck
                for file in steamdeck_files:
                    if os.path.exists(file):
                        with open(file, 'r') as f:
                            content = f.read().lower()
                            if 'steam' in content or 'deck' in content:
                                return True

                # Проверяем переменные окружения
                if 'DECK' in os.path.environ.get('XDG_SESSION_DESKTOP', '').upper():
                    return True

                # Проверяем разрешение экрана (Steam Deck: 1280x800 или 1280x720)
                try:
                    screen_width = warning_window.winfo_screenwidth()
                    screen_height = warning_window.winfo_screenheight()

                    # Обычное разрешение Steam Deck
                    if (screen_width == 1280 and screen_height == 800) or \
                       (screen_width == 1280 and screen_height == 720):
                        return True
                except:
                    pass

                return False
            except:
                return False

        # Получаем размеры экрана
        screen_width = warning_window.winfo_screenwidth()
        screen_height = warning_window.winfo_screenheight()

        # Базовые размеры (оригинал)
        base_width = 450
        base_height = 310

        # --- Учёт ориентации ---
        if screen_height > screen_width:
            # Портретная ориентация (например, у Steam Deck в вертикальном режиме)
            screen_width, screen_height = screen_height, screen_width

        # --- Подстройка под Steam Deck / SteamOS ---
        on_steamdeck = is_steamdeck()

        if on_steamdeck:
            # На Steam Deck — размер окна меньше, чтобы точно влезало
            width = min(base_width - 60, screen_width - 80)  # Еще меньше для надежности
            height = min(base_height - 60, screen_height - 80)

            # Для Steam Deck делаем позиционирование относительно главного окна
            try:
                # Позиционируем относительно главного окна
                main_x = self.root.winfo_x()
                main_y = self.root.winfo_y()
                main_width = self.root.winfo_width()
                main_height = self.root.winfo_height()

                # Позиция по центру главного окна
                x = main_x + (main_width - width) // 2
                y = main_y + (main_height - height) // 2

                # Убедимся, что окно не выходит за границы экрана
                x = max(0, min(x, screen_width - width - 10))
                y = max(0, min(y, screen_height - height - 10))

                warning_window.geometry(f"{int(width)}x{int(height)}+{int(x)}+{int(y)}")
            except:
                # Если не удалось получить позицию главного окна
                width = min(base_width - 60, screen_width - 80)
                height = min(base_height - 60, screen_height - 80)
                warning_window.geometry(f"{int(width)}x{int(height)}")

            # Делаем более читаемым для Steam Deck
            font_title = ("Arial", 14, "bold")
            font_warning = ("Arial", 11)
            font_problems = ("Arial", 9)
            font_final = ("Arial", 10, "bold")
            font_buttons = ("Arial", 10)
            button_padx = 12
            button_pady = 6
            button_width = 10
            padx_main = 15  # Меньше отступы
            pady_main = 10
        else:
            # На обычных системах
            width = base_width
            height = base_height
            font_title = ("Arial", 16, "bold")
            font_warning = ("Arial", 12)
            font_problems = ("Arial", 10)
            font_final = ("Arial", 11, "bold")
            font_buttons = ("Arial", 11)
            button_padx = 20
            button_pady = 8
            button_width = 12
            padx_main = 20
            pady_main = 15

        # Основной контейнер
        main_frame = tk.Frame(warning_window, bg='#182030', padx=padx_main, pady=pady_main)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text="ВНИМАНИЕ!",
            font=font_title,
            fg='#ff9500',
            bg='#182030'
        )
        title_label.pack(pady=(0, 10))

        # Основное предупреждение
        warning_text = "Данный фильтр является экспериментальной функцией"
        warning_label = tk.Label(
            main_frame,
            text=warning_text,
            font=font_warning,
            fg='white',
            bg='#182030',
            justify=tk.CENTER,
            wraplength=width - padx_main * 2  # Автоперенос для Steam Deck
        )
        warning_label.pack(pady=(0, 15))

        # Подробности о проблемах
        problems_frame = tk.Frame(main_frame, bg='#182030')
        problems_frame.pack(fill=tk.X, pady=(0, 20))

        problems_title = tk.Label(
            problems_frame,
            text="Возможные проблемы на Steam Deck:",
            font=font_problems,
            fg='#ff3b30',
            bg='#182030',
            anchor=tk.W
        )
        problems_title.pack(fill=tk.X, pady=(0, 5))

        # Список проблем
        problems = [
            "• черный экран после перехода с рабочего стола в игровой режим. Лучше перезагрузиться",
            "• долгая загрузка после включения/перезагрузки",
            "• скорее всего не будет работать Youtube и Discord. Нужно будет отключать GameFilter",
            "• возможны другие нестабильности в работе"
        ]

        for problem in problems:
            problem_label = tk.Label(
                problems_frame,
                text=problem,
                font=font_problems,
                fg='#AAAAAA',
                bg='#182030',
                anchor=tk.W,
                justify=tk.LEFT,
                wraplength=width - padx_main * 2  # Автоперенос
            )
            problem_label.pack(fill=tk.X, pady=2, anchor=tk.W)

        # Финальное предупреждение
        final_warning = tk.Label(
            main_frame,
            text="Пользоваться данной функцией на свой страх и риск",
            font=font_final,
            fg='#ff9500',
            bg='#182030',
            justify=tk.CENTER,
            wraplength=width - padx_main * 2  # Автоперенос
        )
        final_warning.pack(pady=(0, 20))

        # Фрейм для кнопок
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X)

        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        # Стиль кнопок
        button_style = {
            'font': font_buttons,
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': button_padx,
            'pady': button_pady,
            'width': button_width,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка "Включить"
        enable_button = tk.Button(
            buttons_center_frame,
            text="Включить",
            command=lambda: self._on_warning_accept(warning_window),
            **button_style
        )
        enable_button.pack(side=tk.LEFT, padx=(0, 10))

        # Добавляем эффект наведения
        enable_button.bind("<Enter>", lambda e: enable_button.config(bg='#1e4a6a'))
        enable_button.bind("<Leave>", lambda e: enable_button.config(bg='#15354D'))

        # Кнопка "Назад"
        cancel_button = tk.Button(
            buttons_center_frame,
            text="Назад",
            command=warning_window.destroy,
            **button_style
        )
        cancel_button.pack(side=tk.LEFT)

        # Добавляем эффект наведения
        cancel_button.bind("<Enter>", lambda e: cancel_button.config(bg='#1e4a6a'))
        cancel_button.bind("<Leave>", lambda e: cancel_button.config(bg='#15354D'))

        # ОБЯЗАТЕЛЬНО для SteamOS/Wayland
        warning_window.transient(self.root)  # Делаем окно дочерним
        warning_window.grab_set()  # Делаем модальным

        # Ждем немного чтобы окно успело отобразиться
        warning_window.update_idletasks()
        warning_window.update()

        # Для Steam Deck делаем дополнительную проверку
        if on_steamdeck:
            # Поднимаем окно на самый верх
            warning_window.attributes('-topmost', True)
            warning_window.after(100, lambda: warning_window.attributes('-topmost', False))

            # Фокусируем окно
            warning_window.focus_force()

            # Обновляем несколько раз для надежности
            for _ in range(3):
                warning_window.update()
                time.sleep(0.05)

        # Связываем закрытие окна с кнопкой отмена
        warning_window.protocol("WM_DELETE_WINDOW", warning_window.destroy)

        # Ждем завершения окна
        self.root.wait_window(warning_window)

    def _on_warning_accept(self, warning_window):
        """Обработчик нажатия на кнопку 'Понятно, включить'"""
        warning_window.destroy()

        # Проверяем пароль sudo
        if not self.ensure_sudo_password():
            return

        # Выполняем включение Game Filter
        self._perform_game_filter_toggle()

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
                print("🎮🔴 Game Filter выключен")
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
            ("Настройки IPSet", self.open_ipset_settings),
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

    def ensure_sudo_password(self):
        """Проверяет и получает пароль sudo если нужно"""
        if not self.service_manager:
            self.show_status_message("Менеджер службы не инициализирован", error=True)
            return False

        if not self.service_manager.sudo_password:
            # Убедимся, что окно действительно видимо
            self.root.update_idletasks()

            # Проверяем видимость окна
            if not self.root.winfo_viewable():
                self.root.deiconify()  # Делаем окно видимым
                self.root.update_idletasks()

            # Даем время на отрисовку
            self.root.update()

            # Маленькая задержка чтобы окно стало видимым
            import time
            time.sleep(0.1)

            # Показываем окно ввода пароля
            password_window = SudoPasswordWindow(
                self.root,
                on_password_valid=lambda pwd: self.service_manager.set_sudo_password(pwd)
            )
            password = password_window.run()

            if not password:
                self.show_status_message("Требуется пароль sudo", warning=True)
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
