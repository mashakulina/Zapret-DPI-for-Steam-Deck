"""Главное окно: разметка и верхняя зона."""
import os
import tkinter as tk
import webbrowser

from ui.components.button_styler import create_hover_button
from ui.windows.donat_window import DonationWindow
from ui.windows.info_window import show_info_dialog
from core.dpi_utils import fit_toplevel_to_content


class MainUILayoutMixin:
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
        self.status_indicator = tk.Label(left_status_frame, text="⬤", font=("Arial", 12),
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

        # Иконка Game Filter с индикатором
        game_filter_container = tk.Frame(icons_frame, bg='#182030')
        game_filter_container.pack(side=tk.LEFT, padx=(0, 10))

        # Индикатор Game Filter
        self.game_filter_indicator = tk.Label(game_filter_container, text="⌨", font=("Arial", 14),
                                            fg='#ff3b30', bg='#182030', cursor='hand2')
        self.game_filter_indicator.pack(side=tk.LEFT, padx=(0, 0))

        # Обработчик клика
        self.game_filter_indicator.bind("<Button-1>", self.toggle_game_filter)
        # Всплывающая подсказка при наведении
        self.game_filter_indicator.bind("<Enter>", self.show_game_filter_tooltip)
        self.game_filter_indicator.bind("<Leave>", self.hide_game_filter_tooltip)

        # Иконка настроек (шестеренка)
        self.settings_icon = tk.Label(icons_frame, text="⚙️", font=("Arial", 22),
                                    fg='#0a84ff', bg='#182030', cursor="hand2")
        self.settings_icon.pack(side=tk.LEFT, padx=(0, 10))
        self.settings_icon.bind("<Enter>", lambda e: self.show_icon_tooltip(e, "Открыть меню настроек"))
        self.settings_icon.bind("<Leave>", lambda e: self.hide_icon_tooltip())
        self.settings_icon.bind("<Button-1>", self.toggle_settings_menu)

        # Иконка книги (руководство пользователя)
        self.book_icon = tk.Label(icons_frame, text="🗏", font=("Arial", 18),
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
        self.donate_icon = tk.Label(icons_frame, text="$", font=("Arial", 18),
                                fg='#0a84ff', bg='#182030', cursor="hand2")
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
        url = "https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/blob/main/docs/user-guide-zapret-dpi-manager-steam-deck-ru.md"

        try:
            webbrowser.open(url)
            self.show_status_message("Открываю руководство пользователя...", success=True)
        except Exception as e:
            error_msg = f"Не удалось открыть руководство: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)
