import tkinter as tk
import os
from ui.components.button_styler import create_hover_button
from core.strategy_data import STRATEGY_OPTIONS, save_strategy_names, load_strategy_names, get_strategy_command
from core.service_manager import ServiceManager
from ui.windows.sudo_password_window import SudoPasswordWindow

class CustomStrategyWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)

        # Используем данные из strategy_data.py
        self.strategy_options = STRATEGY_OPTIONS

        # Инициализируем переменные для радиокнопок
        self.strategy_vars = {}  # {category: StringVar}
        for category in self.strategy_options.keys():
            self.strategy_vars[category] = tk.StringVar(value="")  # По умолчанию ничего не выбрано

        # Инициализируем менеджер службы
        if ServiceManager:
            self.service_manager = ServiceManager()
        else:
            self.service_manager = None
            print("Предупреждение: ServiceManager не загружен")

        # Цвета
        self.success_color = '#4CAF50'  # Зеленый для успеха и выбранных элементов
        self.warning_color = '#FF9800'  # Оранжевый для предупреждений
        self.error_color = '#F44336'    # Красный для ошибок
        self.default_status_color = '#AAAAAA'  # Серый по умолчанию

        self.setup_window_properties()
        self.root.title("Сборка своей стратегии")
        self.setup_ui()
        self.load_saved_strategies()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("650x550")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Сборка своей стратегии",
                            font=("Arial", 16, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(0, 20))

        # Основной контейнер с двумя колонками
        content_frame = tk.Frame(main_frame, bg='#182030')
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Левая колонка - список категорий стратегий
        left_frame = tk.Frame(content_frame, bg='#182030', width=200)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, padx=(0, 15))
        left_frame.pack_propagate(False)

        tk.Label(left_frame, text="Категории трафика:",
                font=("Arial", 12, "bold"), fg='white', bg='#182030').pack(anchor=tk.W, pady=(0, 10))

        # Контейнер для списка категорий с прокруткой
        categories_container = tk.Frame(left_frame, bg='#182030')
        categories_container.pack(fill=tk.BOTH, expand=True)

        # Список категорий
        self.categories_listbox = tk.Listbox(
            categories_container,
            bg='#15354D',
            fg='white',
            selectbackground='#1E4A6E',
            selectforeground='white',
            font=("Arial", 11),
            highlightthickness=0,
            bd=0
        )
        self.categories_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Заполняем список категорий
        for category in self.strategy_options.keys():
            self.categories_listbox.insert(tk.END, category)

        # Bind событие выбора категории
        self.categories_listbox.bind('<<ListboxSelect>>', self.on_category_select)

        # Правая колонка - варианты стратегий для выбранной категории
        right_frame = tk.Frame(content_frame, bg='#182030')
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Заголовок для выбранной категории
        self.category_title = tk.Label(right_frame, text="Выберите категорию",
                            font=("Arial", 12, "bold"), fg='white', bg='#182030')
        self.category_title.pack(anchor=tk.W, pady=(0, 10))

        # Контейнер для вариантов стратегий с прокруткой
        strategies_container = tk.Frame(right_frame, bg='#182030')
        strategies_container.pack(fill=tk.BOTH, expand=True)

        # Полоса прокрутки для вариантов стратегий
        strategies_scrollbar = tk.Scrollbar(strategies_container)
        strategies_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Canvas для прокрутки чекбоксов
        self.strategies_canvas = tk.Canvas(
            strategies_container,
            bg='#182030',
            highlightthickness=0,
            yscrollcommand=strategies_scrollbar.set
        )
        self.strategies_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Привязка скроллбара
        strategies_scrollbar.config(command=self.strategies_canvas.yview)

        # Фрейм для радиокнопок внутри canvas
        self.radiobuttons_frame = tk.Frame(self.strategies_canvas, bg='#182030')
        self.canvas_window = self.strategies_canvas.create_window((0, 0), window=self.radiobuttons_frame, anchor="nw")

        # Настройка прокрутки колесом мыши
        self.strategies_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Настройка прокрутки для Linux (Button-4 и Button-5)
        self.strategies_canvas.bind_all("<Button-4>", self._on_mousewheel_linux)
        self.strategies_canvas.bind_all("<Button-5>", self._on_mousewheel_linux)

        # Обновление прокрутки при изменении размера фрейма
        self.radiobuttons_frame.bind("<Configure>", self.on_frame_configure)

        # Привязка для обновления ширины фрейма при изменении размера canvas
        self.strategies_canvas.bind("<Configure>", self.on_canvas_configure)

        # Словарь для хранения ссылок на радиокнопки для обновления цвета
        self.radio_buttons = {}  # {(category, strategy_name): tk.Radiobutton}

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

        # Кнопка Применить
        self.apply_button = create_hover_button(
            center_frame,
            text="Применить",
            command=self.apply_strategies,
            **button_style
        )
        self.apply_button.pack(side=tk.LEFT, padx=(0, 30))

        # Кнопка Назад
        back_button = create_hover_button(
            center_frame,
            text="Назад",
            command=self.close_window,
            **button_style
        )
        back_button.pack(side=tk.LEFT)

        # Выбираем первую категорию по умолчанию
        if self.strategy_options:
            first_category = list(self.strategy_options.keys())[0]
            self.categories_listbox.selection_set(0)
            self.update_strategies_for_category(first_category)

        # Bind событие изменения выбора радиокнопок
        self.setup_radio_bindings()

    def on_canvas_configure(self, event):
        """Обновляет ширину фрейма при изменении размера canvas"""
        # Устанавливаем ширину фрейма равной ширине canvas
        self.strategies_canvas.itemconfig(self.canvas_window, width=event.width)

    def setup_radio_bindings(self):
        """Настраивает отслеживание изменений в радиокнопках"""
        for category, var in self.strategy_vars.items():
            var.trace_add('write', lambda *args, cat=category: self.on_strategy_change(cat))

    def on_strategy_change(self, category):
        """Обрабатывает изменение выбора стратегии в категории"""
        selected_strategy = self.strategy_vars[category].get()

        # Обновляем цвета всех радиокнопок в этой категории
        if category in self.strategy_options:
            for strategy_name in self.strategy_options[category].keys():
                radio_key = (category, strategy_name)
                if radio_key in self.radio_buttons:
                    radio_button = self.radio_buttons[radio_key]
                    # Устанавливаем цвет текста
                    if strategy_name == selected_strategy:
                        radio_button.config(fg=self.success_color)  # Зеленый для выбранного
                    else:
                        radio_button.config(fg='white')  # Белый для невыбранных

    def _on_mousewheel(self, event):
        """Обработка прокрутки колесом мыши (Windows/Mac)"""
        # Прокрутка вниз при положительном delta, вверх при отрицательном
        self.strategies_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_mousewheel_linux(self, event):
        """Обработка прокрутки для Linux (Button-4/Button-5)"""
        if event.num == 4:
            # Button-4: прокрутка вверх
            self.strategies_canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            # Button-5: прокрутка вниз
            self.strategies_canvas.yview_scroll(1, "units")

    def on_frame_configure(self, event):
        """Обновляет область прокрутки при изменении размера фрейма"""
        # Обновляем область прокрутки canvas
        self.strategies_canvas.configure(scrollregion=self.strategies_canvas.bbox("all"))

    def on_category_select(self, event):
        """Обрабатывает выбор категории из списка"""
        selection = self.categories_listbox.curselection()
        if selection:
            selected_category = self.categories_listbox.get(selection[0])
            self.update_strategies_for_category(selected_category)

    def update_strategies_for_category(self, category_name):
        """Обновляет радиокнопки для выбранной категории"""
        # Обновляем заголовок
        self.category_title.config(text=f"Стратегии для: {category_name}")

        # Очищаем предыдущие радиокнопки
        for widget in self.radiobuttons_frame.winfo_children():
            widget.destroy()

        # Очищаем словарь радиокнопок для этой категории
        keys_to_remove = [k for k in self.radio_buttons.keys() if k[0] == category_name]
        for key in keys_to_remove:
            del self.radio_buttons[key]

        strategies = self.strategy_options.get(category_name, {})

        if not strategies:
            # Если нет стратегий для этой категории
            no_strategies_label = tk.Label(
                self.radiobuttons_frame,
                text="Нет доступных стратегий для этой категории",
                font=("Arial", 11),
                fg='#8e8e93',
                bg='#182030'
            )
            no_strategies_label.pack(pady=20)
            return

        # Создаем радиокнопки для каждого варианта стратегии
        for strategy_name in strategies.keys():
            # Фрейм для радиокнопки
            strategy_frame = tk.Frame(self.radiobuttons_frame, bg='#182030')
            strategy_frame.pack(fill=tk.X, pady=6, padx=5)

            # Определяем цвет текста: зеленый если выбрано, белый если нет
            text_color = self.success_color if self.strategy_vars[category_name].get() == strategy_name else 'white'

            radiobutton = tk.Radiobutton(
                strategy_frame,
                text=strategy_name,
                variable=self.strategy_vars[category_name],
                value=strategy_name,
                bg='#182030',
                fg=text_color,  # Устанавливаем цвет текста
                selectcolor='#15354D',
                activebackground='#182030',
                activeforeground=self.success_color,  # Зеленый при наведении
                font=("Arial", 11),
                anchor=tk.W,
                highlightthickness=0,
                bd=0,
                wraplength=500,
                cursor='hand2'
            )
            radiobutton.pack(fill=tk.X, anchor=tk.W)

            # Сохраняем ссылку на радиокнопку
            self.radio_buttons[(category_name, strategy_name)] = radiobutton

            # Добавляем разделитель
            separator = tk.Frame(strategy_frame, height=1, bg='#1e4a6a')
            separator.pack(fill=tk.X, pady=(5, 0))

        # Обновляем прокрутку
        self.radiobuttons_frame.update_idletasks()
        self.strategies_canvas.configure(scrollregion=self.strategies_canvas.bbox("all"))

    def load_saved_strategies(self):
        """Загружает сохраненные стратегии из файла"""
        try:
            selected_strategies = load_strategy_names()

            # Устанавливаем выбранные стратегии в радиокнопки
            for category, strategy_name in selected_strategies.items():
                if category in self.strategy_vars:
                    self.strategy_vars[category].set(strategy_name)

        except Exception as e:
            print(f"Ошибка загрузки сохраненных стратегий: {e}")

    def ensure_sudo_password(self):
        """Проверяет и получает пароль sudo если нужно"""
        if not self.service_manager:
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
                    return False
            else:
                self.status_label.config(text="Модуль запроса пароля не найден", fg=self.error_color)
                return False

        return True

    def restart_service(self):
        """Перезапускает службу zapret"""
        if not self.service_manager:
            return False, "Менеджер службы не инициализирован"

        success, message = self.service_manager.restart_service()
        return success, message

    def apply_strategies(self):
        """Применяет выбранные стратегии, сохраняет их и перезапускает службу"""
        try:
            # Собираем все выбранные стратегии
            selected_strategies = {}
            has_any_selection = False
            has_valid_strategy = False

            for category, var in self.strategy_vars.items():
                if var.get():  # Если что-то выбрано
                    has_any_selection = True
                    selected_strategies[category] = var.get()
                    if var.get() != "Не выбирать":
                        has_valid_strategy = True

            # Проверяем, выбраны ли стратегии
            if not has_any_selection:
                self.status_label.config(text="Не выбрано ни одной стратегии", fg=self.warning_color)
                # Сброс состояния через 2 секунды
                self.root.after(2000, lambda: self.status_label.config(text="", fg=self.default_status_color))
                return

            # Меняем состояние UI
            self.root.config(cursor="watch")
            self.apply_button.config(state=tk.DISABLED, text="Применение...")
            self.status_label.config(text="Сохранение стратегий...")
            self.root.update()

            # Сохраняем наименования в файл и команды в config.txt
            if not save_strategy_names(selected_strategies):
                self.status_label.config(text="Ошибка сохранения стратегий", fg=self.error_color)
                self.reset_ui_state()
                return

            print(f"Сохранено {len(selected_strategies)} стратегий")

            # Проверяем, есть ли хотя бы одна валидная стратегия (не "Не выбирать")
            if has_valid_strategy:
                # Проверяем возможность перезапуска службы
                if not self.service_manager:
                    self.status_label.config(
                        text="Стратегии сохранены. Перезапустите службу вручную",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
                    return

                # Запрашиваем пароль sudo для перезапуска службы
                self.status_label.config(text="Запрос прав администратора...")
                self.root.update()

                if not self.ensure_sudo_password():
                    self.status_label.config(
                        text="Стратегии сохранены. Перезапустите службу вручную",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
                    return

                # Перезапускаем службу
                self.status_label.config(text="Перезапуск службы...")
                self.apply_button.config(text="Перезапуск...")
                self.root.update()

                success, message = self.restart_service()

                if success:
                    self.status_label.config(
                        text=f"Сохранено {len(selected_strategies)} стратегий, служба перезапущена",
                        fg=self.success_color
                    )
                    # Ждем немного и закрываем окно
                    self.root.after(1500, self.close_window)
                else:
                    self.status_label.config(
                        text=f"Сохранено {len(selected_strategies)} стратегий, но служба не перезапущена",
                        fg=self.warning_color
                    )
                    # Сброс состояния через 3 секунды
                    self.root.after(3000, self.reset_ui_state)
            else:
                # Если выбраны только "Не выбирать" - очищаем стратегии
                self.status_label.config(
                    text="Все стратегии очищены",
                    fg=self.success_color
                )
                # Ждем немного и закрываем окно
                self.root.after(1500, self.close_window)

        except Exception as e:
            self.status_label.config(text=f"Ошибка: {str(e)}", fg=self.error_color)
            print(f"Ошибка применения стратегий: {e}")
            # Сброс состояния через 3 секунды
            self.root.after(3000, self.reset_ui_state)

    def reset_ui_state(self):
        """Восстанавливает состояние UI"""
        self.root.config(cursor="")
        self.apply_button.config(state=tk.NORMAL, text="Применить")
        self.status_label.config(text="", fg=self.default_status_color)

    def close_window(self):
        """Закрывает окно"""
        # Отвязываем события прокрутки перед закрытием
        self.strategies_canvas.unbind_all("<MouseWheel>")
        self.strategies_canvas.unbind_all("<Button-4>")
        self.strategies_canvas.unbind_all("<Button-5>")
        self.root.destroy()

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
