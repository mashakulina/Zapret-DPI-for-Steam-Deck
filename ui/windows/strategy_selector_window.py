import tkinter as tk
import os
from tkinter import messagebox
from ui.components.button_styler import create_hover_button
from ui.windows.strategy_window import StrategyWindow
from ui.windows.custom_strategy_window import CustomStrategyWindow
from ui.windows.strategy_tester_window import StrategyTesterWindow

class AutoSelectionWindow:
    """Окно автоподбора стратегий"""
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Автоподбор стратегий")

        self.setup_ui()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        window_width = 250
        window_height = 250

        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

        # Обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Автоподбор стратегий",
                              font=("Arial", 14, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(15, 30))

        # Стиль кнопок
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

        # Кнопка "Автоподбор по всем стратегиям"
        all_button = create_hover_button(
            main_frame,
            text="Тестировать все стратегии",
            command=self.test_all_strategies,
            **button_style
        )
        all_button.pack(pady=(0, 10))

        # Кнопка "Выбрать стратегии для автоподбора"
        select_button = create_hover_button(
            main_frame,
            text="Выбрать стратегии для теста",
            command=self.show_strategy_selection,
            **button_style
        )
        select_button.pack(pady=(0, 10))

        # Кнопка "Назад"
        back_button = create_hover_button(
            main_frame,
            text="Назад",
            command=self.on_close,
            **button_style
        )
        back_button.pack(pady=(10, 0))

    def test_all_strategies(self):
        """Запускает тестирование всех стратегий"""
        self.on_close()
        try:
            tester_window = StrategyTesterWindow(self.parent)
            tester_window.run()
        except Exception as e:
            print(f"Ошибка открытия тестировщика: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть тестировщика: {str(e)}")

    def show_strategy_selection(self):
        """Показывает отдельное окно выбора стратегий"""
        self.on_close()

        # Открываем новое окно выбора стратегий
        selection_window = StrategySelectionWindow(self.parent)
        selection_window.run()

    def on_close(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()


class StrategySelectionWindow:
    """Окно выбора стратегий для тестирования"""
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()

        self.selected_strategies = []  # Для хранения выбранных стратегий
        self.strategy_vars = {}  # Для хранения переменных чекбоксов
        self.strategy_items = []  # Список всех стратегий

        self.setup_ui()
        self.load_strategies()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.title("Выбор стратегий для тестирования")

        # Устанавливаем размер окна (уменьшили высоту)
        window_width = 770
        window_height = 360

        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

        # Обработчик закрытия окна
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=10, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Выберите стратегии для тестирования",
                              font=("Arial", 14, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(5, 10))

        # Фрейм для списка стратегий с тремя колонками
        list_frame = tk.Frame(main_frame, bg='#182030', height=250)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Контейнер для трех колонок
        columns_container = tk.Frame(list_frame, bg='#182030')
        columns_container.pack(fill=tk.BOTH, expand=True)

        # Создаем три колонки
        self.column_frames = []
        for i in range(3):
            column_frame = tk.Frame(columns_container, bg='#182030', padx=10)
            column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.column_frames.append(column_frame)

            # Добавляем разделитель между колонками (кроме последней)
            if i < 2:
                separator = tk.Frame(columns_container, width=1, bg='#1E4A6E')
                separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Панель управления внизу
        control_frame = tk.Frame(main_frame, bg='#182030')
        control_frame.pack(fill=tk.X, pady=(5, 0))  # Подняли выше

        # Статусная строка
        self.status_label = tk.Label(
            control_frame,
            text="Выберите стратегии для тестирования",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.status_label.pack(pady=(0, 8))

        # Фрейм для кнопок
        buttons_frame = tk.Frame(control_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X)

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
            'pady': 10,
            'width': 15,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка Запустить подбор
        apply_button = create_hover_button(
            center_frame,
            text="Запустить подбор",
            command=self.apply_selection,
            **button_style
        )
        apply_button.pack(side=tk.LEFT, padx=(0, 30))

        # Кнопка Назад
        back_button = create_hover_button(
            center_frame,
            text="Назад",
            command=self.on_close,
            **button_style
        )
        back_button.pack(side=tk.LEFT)

    def load_strategies(self):
        """Загружает список стратегий из папки"""
        try:
            # Путь к папке со стратегиями
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager/files")
            strategy_dir = os.path.join(manager_dir, "strategy")

            # Создаем папку если ее нет
            if not os.path.exists(strategy_dir):
                os.makedirs(strategy_dir)
                print(f"Создана папка для стратегий: {strategy_dir}")

            # Загружаем пользовательские стратегии из файлов
            if os.path.exists(strategy_dir):
                # Получаем все файлы, которые не являются папками
                strategy_files = [f for f in os.listdir(strategy_dir)
                                if os.path.isfile(os.path.join(strategy_dir, f))]

                # Сортируем и фильтруем
                sorted_files = []
                for file in sorted(strategy_files):
                    if not file.startswith('.'):
                        sorted_files.append(file)

                self.strategy_items = sorted_files

                if not self.strategy_items:
                    # Нет стратегий - показываем сообщение
                    for column_frame in self.column_frames:
                        no_strategies_label = tk.Label(
                            column_frame,
                            text="Стратегии не найдены",
                            font=("Arial", 11),
                            fg='white',
                            bg='#182030'
                        )
                        no_strategies_label.pack(pady=20)
                else:
                    # Распределяем стратегии по трем колонкам
                    items_per_column = (len(self.strategy_items) + 2) // 3

                    for i, strategy in enumerate(self.strategy_items):
                        col_index = i // items_per_column
                        if col_index < 3:
                            column_frame = self.column_frames[col_index]

                            # Создаем переменную для чекбокса
                            var = tk.BooleanVar(value=False)
                            self.strategy_vars[strategy] = var

                            # Создаем чекбокс
                            checkbox = tk.Checkbutton(
                                column_frame,
                                text=strategy,
                                variable=var,
                                font=("Arial", 11),
                                fg='white',
                                bg='#182030',
                                selectcolor='#1E4A6E',
                                activebackground='#182030',
                                activeforeground='#4fc3f7',
                                highlightthickness=0,
                                cursor='hand2',
                                command=self.update_selection_status
                            )
                            checkbox.pack(anchor='w', pady=1)  # Уменьшили расстояние между строками

                    print(f"Загружено {len(self.strategy_items)} стратегий")
                    self.update_selection_status()

        except Exception as e:
            print(f"Ошибка загрузки стратегий: {e}")
            error_label = tk.Label(
                self.column_frames[0],
                text=f"Ошибка: {str(e)}",
                font=("Arial", 11),
                fg='#ff7043',
                bg='#182030'
            )
            error_label.pack(pady=20)

    def update_selection_status(self):
        """Обновляет статусную строку выбора"""
        if self.strategy_vars:
            selected_count = sum(1 for var in self.strategy_vars.values() if var.get())

            if selected_count == 0:
                self.status_label.config(
                    text="Выберите стратегии для тестирования или оставьте все пустым для теста всех стратегий",
                    fg='#AAAAAA'
                )
            else:
                self.status_label.config(
                    text=f"Выбрано стратегий: {selected_count} из {len(self.strategy_items)}",
                    fg='#4fc3f7'
                )

    def apply_selection(self):
        """Применяет выбранные стратегии и открывает тестировщик"""
        # Получаем выбранные стратегии
        selected_strategies = []
        if self.strategy_vars:
            selected_strategies = [
                strategy for strategy, var in self.strategy_vars.items()
                if var.get()
            ]

        # Если ничего не выбрано, тестируем все стратегии
        if not selected_strategies and self.strategy_items:
            selected_strategies = self.strategy_items.copy()
            print(f"Не выбрано конкретных стратегий. Будет протестировано все: {len(selected_strategies)} стратегий")
        else:
            print(f"Выбрано стратегий для тестирования: {len(selected_strategies)}")

        # Закрываем это окно
        self.on_close()

        # Открываем окно тестирования
        try:
            tester_window = StrategyTesterWindow(self.parent, strategies_to_test=selected_strategies)
            tester_window.run()
        except Exception as e:
            print(f"Ошибка открытия тестировщика: {e}")
            messagebox.showerror("Ошибка", f"Не удалось открыть тестировщик: {str(e)}")

    def on_close(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()


class StrategySelectorWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Выбор типа стратегии")

        self.setup_ui()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        window_width = 250
        window_height = 340

        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Сменить стратегию",
                              font=("Arial", 14, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(15, 30))

        # Стиль кнопок
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

        # Кнопка "Автоподбор стратегии"
        test_button = create_hover_button(
            main_frame,
            text="Автоподбор стратегии",
            command=self.show_autoselect_menu,
            **button_style
        )
        test_button.pack(pady=(0, 10))

        # Кнопка "Использовать готовые стратегии"
        ready_button = create_hover_button(
            main_frame,
            text="Выбрать готовую стратегию",
            command=self.open_ready_strategies,
            **button_style
        )
        ready_button.pack(pady=(0, 10))

        # Кнопка "Собрать свою стратегию"
        custom_button = create_hover_button(
            main_frame,
            text="Собрать свой пресет",
            command=self.open_custom_strategy,
            **button_style
        )
        custom_button.pack(pady=(0, 10))

        # Кнопка "Назад"
        back_button = create_hover_button(
            main_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_button.pack(pady=(10, 0))

    def show_autoselect_menu(self):
        """Показывает отдельное окно автоподбора"""
        self.close_window()

        # Открываем новое окно автоподбора
        autoselect_window = AutoSelectionWindow(self.parent)
        autoselect_window.run()

    def open_ready_strategies(self):
        """Открывает окно готовых стратегий"""
        self.close_window()
        strategy_window = StrategyWindow(self.parent)
        strategy_window.run()

    def open_custom_strategy(self):
        """Открывает окно сборки своей стратегии"""
        self.close_window()
        custom_window = CustomStrategyWindow(self.parent)
        custom_window.run()

    def close_window(self):
        """Закрывает окно"""
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
