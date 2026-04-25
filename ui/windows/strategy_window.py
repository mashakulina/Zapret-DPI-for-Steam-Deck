import tkinter as tk
import os
from tkinter import messagebox
from ui.components.button_styler import create_hover_button
from core.service_manager import ServiceManager
from core.game_presets import reapply_active_preset_to_config
from ui.windows.sudo_password_window import SudoPasswordWindow
from core.dpi_utils import place_toplevel_centered_on_parent

class StrategyWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Смена стратегии")

        self.selected_strategy = None
        self.strategy_items = []  # Храним названия стратегий

        # Цвета
        self.success_color = '#4CAF50'  # Зеленый для успеха и выбранных элементов
        self.warning_color = '#FF9800'  # Оранжевый для предупреждений
        self.error_color = '#F44336'    # Красный для ошибок
        self.default_status_color = '#AAAAAA'  # Серый по умолчанию

        # Инициализируем менеджер службы
        self.service_manager = ServiceManager()
        self.sudo_password = None

        # Путь к файлу с рабочими стратегиями
        self.working_strategies_file = os.path.join(
            os.path.expanduser("~/Zapret_DPI_Manager"),
            "utils",
            "working_strategies.txt"
        )
        self.working_strategies = set()  # Множество для быстрого поиска

        self.setup_ui()
        self.load_working_strategies()  # Загружаем рабочие стратегии перед загрузкой всех
        self.load_strategies()
        self.load_current_strategy()
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass
        place_toplevel_centered_on_parent(
            self.root, self.parent, min_width=720, min_height=280, margin_width=8, margin_height=12
        )

    def load_working_strategies(self):
        """Загружает список рабочих стратегий из файла"""
        try:
            if os.path.exists(self.working_strategies_file):
                with open(self.working_strategies_file, 'r', encoding='utf-8') as f:
                    strategies = []
                    for line in f:
                        s = line.strip()
                        if not s:
                            continue
                        if s.startswith("\ufeff"):
                            s = s.lstrip("\ufeff").strip()
                        if s:
                            strategies.append(s)
                    self.working_strategies = set(strategies)
                    print(f"Загружено {len(self.working_strategies)} рабочих стратегий")
            else:
                self.working_strategies = set()
        except Exception as e:
            print(f"Ошибка загрузки рабочих стратегий: {e}")
            self.working_strategies = set()


    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Выберите готовую стратегию",
                              font=("Arial", 16, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(5, 20))

        # Три колонки — как в окне выбора стратегий для теста: фреймы + строки (радио + ⭐ + имя)
        list_frame = tk.Frame(main_frame, bg='#182030', height=250)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns_container = tk.Frame(list_frame, bg='#182030')
        columns_container.pack(fill=tk.BOTH, expand=True)

        self.radio_selected = "◉"
        self.radio_unselected = "○"

        self.column_frames = []
        self.column_strategies = [[], [], []]
        self.labels_by_strategy = {}
        self.row_widgets = {}

        for i in range(3):
            column_frame = tk.Frame(columns_container, bg='#182030', padx=10)
            column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.column_frames.append(column_frame)
            column_frame.bind("<Configure>", lambda e, c=i: self._on_column_configure(c, e))

            if i < 2:
                separator = tk.Frame(columns_container, width=1, bg='#1E4A6E')
                separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Статусная строка
        self.status_label = tk.Label(
            main_frame,
            text="",
            font=("Arial", 10),
            fg=self.default_status_color,
            bg='#182030'
        )
        self.status_label.pack(pady=(0, 10))

        # Фрейм для кнопок по центру
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(0, 0))

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
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка Назад
        self.apply_button = create_hover_button(
            center_frame,
            text="Применить",
            command=self.apply_strategy,
            **button_style
        )
        self.apply_button.pack(side=tk.LEFT, padx=(0, 30))
        self.apply_button.config(state=tk.DISABLED, bg='#2a4d6a')

        # Кнопка Применить
        back_button = create_hover_button(
            center_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_button.pack(side=tk.LEFT)

    def _prefix_text(self, strategy, selected=False):
        radio = self.radio_selected if selected else self.radio_unselected
        star = "⭐ " if strategy in self.working_strategies else ""
        return f"  {radio}  {star}"

    def _set_row_visual(self, strategy, selected):
        w = self.row_widgets.get(strategy)
        if not w:
            return
        w["prefix"].config(text=self._prefix_text(strategy, selected))

    def _on_column_configure(self, col_index, event):
        if event.widget is not self.column_frames[col_index]:
            return
        wrap = max(72, event.width - 16)
        for s in self.column_strategies[col_index]:
            lbl = self.labels_by_strategy.get(s)
            if lbl is not None:
                lbl.config(wraplength=wrap)

    def _create_strategy_row(self, col_index, strategy):
        col_frame = self.column_frames[col_index]
        self.column_strategies[col_index].append(strategy)
        row = tk.Frame(col_frame, bg="#182030", cursor="hand2")
        row.pack(fill=tk.X, anchor="nw", pady=1)
        lbl_font = ("Arial", 11)
        prefix_lbl = tk.Label(
            row,
            text=self._prefix_text(strategy, selected=False),
            font=lbl_font,
            fg="white",
            bg="#182030",
            anchor="nw",
        )
        prefix_lbl.pack(side=tk.LEFT, anchor="nw")
        name_lbl = tk.Label(
            row,
            text=strategy,
            font=lbl_font,
            fg="white",
            bg="#182030",
            justify="left",
            anchor="nw",
            wraplength=200,
        )
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True, anchor="nw")

        def select_row(_event=None, s=strategy):
            self._on_row_select(s)

        for w in (prefix_lbl, name_lbl, row):
            w.bind("<Button-1>", select_row)
        self.labels_by_strategy[strategy] = name_lbl
        self.row_widgets[strategy] = {"prefix": prefix_lbl, "name": name_lbl}

    def _on_row_select(self, strategy_name):
        if strategy_name not in self.strategy_items:
            return
        self.reset_radio_buttons()
        self._set_row_visual(strategy_name, selected=True)
        self.selected_strategy = strategy_name
        self.apply_button.config(state=tk.NORMAL, bg="#15354D")

    def load_current_strategy(self):
        """Загружает текущую стратегию из файла name_strategy.txt"""
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")

            if os.path.exists(name_strategy_file):
                with open(name_strategy_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    if first_line:
                        self.current_strategy = first_line
                    else:
                        self.current_strategy = None
            else:
                self.current_strategy = None

            print(f"Текущая стратегия из файла: {self.current_strategy}")

        except Exception as e:
            print(f"Ошибка загрузки текущей стратегии: {e}")
            self.current_strategy = None

    def highlight_current_strategy(self):
        """Подсвечивает текущую стратегию (◉ / ○) в строках-колонках."""
        if not self.current_strategy:
            return
        try:
            if self.current_strategy in self.strategy_items:
                self.selected_strategy = self.current_strategy
                self.reset_radio_buttons()
                self._set_row_visual(self.current_strategy, selected=True)
                self.apply_button.config(state=tk.NORMAL, bg='#15354D')
                print(f"Подсвечена текущая стратегия: {self.current_strategy}")
        except Exception as e:
            print(f"Ошибка подсветки текущей стратегии: {e}")

    def load_strategies(self):
        """Загружает стратегии в три колонки (распределение как в окне для теста)."""
        try:
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager/files")
            strategy_dir = os.path.join(manager_dir, "strategy")

            if not os.path.exists(strategy_dir):
                os.makedirs(strategy_dir)
                print(f"Создана папка для стратегий: {strategy_dir}")

            for cf in self.column_frames:
                for w in cf.winfo_children():
                    w.destroy()
            self.labels_by_strategy.clear()
            self.row_widgets.clear()
            self.column_strategies = [[], [], []]
            self.strategy_items.clear()
            self.selected_strategy = None
            self.apply_button.config(state=tk.DISABLED, bg='#2a4d6a')

            if os.path.exists(strategy_dir):
                strategy_files = [f for f in os.listdir(strategy_dir)
                                if os.path.isfile(os.path.join(strategy_dir, f))]

                sorted_files = []
                for file in sorted(strategy_files):
                    if not file.startswith('.'):
                        sorted_files.append(file)

                self.strategy_items = sorted_files

                if not self.strategy_items:
                    empty_label = tk.Label(
                        self.column_frames[0],
                        text="Стратегии не найдены",
                        font=("Arial", 11),
                        fg="white",
                        bg="#182030",
                    )
                    empty_label.pack(pady=20)
                else:
                    items_per_column = (len(self.strategy_items) + 2) // 3

                    for i, strategy in enumerate(self.strategy_items):
                        col_index = i // items_per_column
                        if col_index < 3:
                            self._create_strategy_row(col_index, strategy)

                    print(f"Загружено {len(self.strategy_items)} стратегий")
                    self.root.after(100, self.highlight_current_strategy)

        except Exception as e:
            print(f"Ошибка загрузки стратегий: {e}")
            err = tk.Label(
                self.column_frames[0],
                text=f"Ошибка: {str(e)}",
                font=("Arial", 11),
                fg="#ff7043",
                bg="#182030",
            )
            err.pack(pady=20)

    def reset_radio_buttons(self):
        """Все строки снова с ○; звезда у рабочих — только в префиксе."""
        for strategy in self.strategy_items:
            self._set_row_visual(strategy, selected=False)

    def ensure_sudo_password(self):
        """Проверяет и получает пароль sudo если нужно"""
        if not self.service_manager.sudo_password:
            # Показываем окно ввода пароля
            password_window = SudoPasswordWindow(
                self.root,
                on_password_valid=lambda pwd: self.service_manager.set_sudo_password(pwd)
            )
            password = password_window.run()

            if not password:
                return False

        return True

    def apply_strategy(self):
        """Применяет выбранную стратегию и перезапускает службу"""
        if not self.selected_strategy:
            return

        # Проверяем, выбрана ли та же стратегия что уже активна
        if self.current_strategy == self.selected_strategy:
            self.status_label.config(text="Эта стратегия уже активна", fg=self.warning_color)
            # Сброс через 2 секунды
            self.root.after(2000, lambda: self.status_label.config(text="", fg=self.default_status_color))
            return

        # Проверяем наличие пароля sudo
        if not self.ensure_sudo_password():
            messagebox.showwarning("Отменено", "Для применения стратегии требуется пароль sudo")
            return

        # Меняем состояние UI
        self.root.config(cursor="watch")
        self.apply_button.config(state=tk.DISABLED, text="Применение...")
        self.status_label.config(text="Применение стратегии...")
        self.root.update()

        try:
            # Пути к файлам
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
            strategy_dir = os.path.join(manager_dir, "files", "strategy")
            config_file = os.path.join(manager_dir, "config.txt")
            name_strategy_file = os.path.join(manager_dir, "utils", "name_strategy.txt")

            # Ищем файл стратегии (без добавления .txt)
            strategy_file = os.path.join(strategy_dir, self.selected_strategy)

            if not os.path.exists(strategy_file):
                messagebox.showerror("Ошибка", f"Файл стратегии не найден: {self.selected_strategy}")
                self.reset_ui_state()
                return

            # Читаем содержимое файла стратегии
            with open(strategy_file, 'r', encoding='utf-8') as f:
                strategy_content = f.read().strip()

            # Проверяем, не пустой ли файл стратегии
            if not strategy_content:
                # Если файл стратегии пустой, очищаем оба файла
                with open(name_strategy_file, 'w', encoding='utf-8') as f:
                    f.write("")
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write("")
                strategy_name = "Не выбрано"
            else:
                # Записываем имя стратегии в name_strategies.txt
                with open(name_strategy_file, 'w', encoding='utf-8') as f:
                    f.write(f"{self.selected_strategy}")

                # Записываем содержимое стратегии в config.txt
                with open(config_file, 'w', encoding='utf-8') as f:
                    f.write(strategy_content)

                # Если активен игровой пресет, применяем его к новому config.txt.
                reapply_active_preset_to_config(manager_dir)

                strategy_name = self.selected_strategy

            print(f"Стратегия '{strategy_name}' применена успешно")

            # Обновляем текущую стратегию
            self.current_strategy = strategy_name

            # Перезапускаем службу zapret
            self.status_label.config(text="Перезапуск службы...")
            self.apply_button.config(text="Перезапуск...")
            self.root.update()

            success, message = self.service_manager.restart_service()

            if success:
                self.status_label.config(text="Стратегия применена, служба перезапущена", fg=self.success_color)
                # Ждем немного, чтобы пользователь увидел сообщение
                self.root.after(1500, self.close_window)
            else:
                self.status_label.config(text=f"Стратегия применена, но служба не перезапущена: {message}", fg=self.warning_color)
                # Сброс состояния через 3 секунды
                self.root.after(3000, self.reset_ui_state)

        except Exception as e:
            self.status_label.config(text=f"Ошибка: {str(e)}", fg=self.error_color)
            print(f"Ошибка применения стратегии: {e}")
            # Сброс состояния через 3 секунды
            self.root.after(3000, self.reset_ui_state)

    def save_working_strategies(self, strategies):
        """Сохраняет список рабочих стратегий в файл"""
        try:
            # Создаем папку если её нет
            os.makedirs(os.path.dirname(self.working_strategies_file), exist_ok=True)

            with open(self.working_strategies_file, 'w', encoding='utf-8') as f:
                for strategy in strategies:
                    f.write(strategy + '\n')

            self.working_strategies = set(strategies)
            print(f"Сохранено {len(strategies)} рабочих стратегий")
            return True
        except Exception as e:
            print(f"Ошибка сохранения рабочих стратегий: {e}")
            return False

    def reset_ui_state(self):
        """Восстанавливает состояние UI"""
        self.root.config(cursor="")
        self.apply_button.config(state=tk.NORMAL, text="Применить")
        self.status_label.config(text="", fg=self.default_status_color)

    def close_window(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
