import tkinter as tk
import os
from tkinter import messagebox
from ui.components.button_styler import create_hover_button
from core.service_manager import ServiceManager
from ui.windows.sudo_password_window import SudoPasswordWindow

class StrategyWindow:
    def __init__(self, parent):
        self.parent = parent
        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Смена стратегии")

        self.selected_strategy = None
        self.strategy_var = tk.StringVar()
        self.strategy_items = []  # Храним названия стратегий

        # Цвета
        self.success_color = '#4CAF50'  # Зеленый для успеха и выбранных элементов
        self.warning_color = '#FF9800'  # Оранжевый для предупреждений
        self.error_color = '#F44336'    # Красный для ошибок
        self.default_status_color = '#AAAAAA'  # Серый по умолчанию

        # Инициализируем менеджер службы
        self.service_manager = ServiceManager()
        self.sudo_password = None

        self.setup_ui()
        self.load_strategies()
        self.load_current_strategy()

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("770x505")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame, text="Выберите готовый пресет",
                              font=("Arial", 16, "bold"), fg='white', bg='#182030')
        title_label.pack(pady=(5, 20))

        # Фрейм для списка стратегий с тремя колонками
        list_frame = tk.Frame(main_frame, bg='#182030')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Контейнер для трех колонок
        columns_container = tk.Frame(list_frame, bg='#182030')
        columns_container.pack(fill=tk.BOTH, expand=True)

        # Создаем три колонки
        self.column_frames = []
        self.column_listboxes = []

        for i in range(3):
            column_frame = tk.Frame(columns_container, bg='#182030', padx=5)
            column_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.column_frames.append(column_frame)

            # Listbox для колонки
            listbox = tk.Listbox(
                column_frame,
                bg='#182030',
                fg='white',
                selectbackground='#1E4A6E',
                selectforeground='white',
                font=("Arial", 11),
                highlightthickness=0,
                bd=0,
                relief=tk.FLAT,
                activestyle='none',
                selectmode=tk.SINGLE
            )
            listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.column_listboxes.append(listbox)

            # Bind события выбора для каждого Listbox
            listbox.bind('<<ListboxSelect>>', lambda e, lb=listbox: self.on_strategy_select_listbox(lb))
            listbox.bind('<Button-1>', lambda e, lb=listbox: self.on_listbox_click_listbox(e, lb))

            # Добавляем разделитель между колонками (кроме последней)
            if i < 2:
                separator = tk.Frame(columns_container, width=1, bg='#1E4A6E')
                separator.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        # Символ радиокнопки для отображения
        self.radio_selected = "◉"  # Заполненный кружок
        self.radio_unselected = "○"  # Пустой кружок

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
        """Подсвечивает текущую стратегию в списке"""
        if not self.current_strategy:
            return

        # Ищем индекс текущей стратегии
        try:
            if self.current_strategy in self.strategy_items:
                index = self.strategy_items.index(self.current_strategy)

                # Выделяем стратегию
                self.selected_strategy = self.current_strategy

                # Сбрасываем все радиокнопки
                self.reset_radio_buttons()

                # Находим в какой колонке и какой индекс внутри колонки
                col_index, item_index = self.get_column_and_index(index)

                if col_index is not None and item_index is not None:
                    listbox = self.column_listboxes[col_index]

                    # Устанавливаем выбранную радиокнопку
                    current_text = listbox.get(item_index)
                    if self.radio_unselected in current_text:
                        listbox.delete(item_index)
                        listbox.insert(item_index, f"  {self.radio_selected}  {self.current_strategy}")

                    # Выделяем строку в Listbox
                    listbox.selection_clear(0, tk.END)
                    listbox.selection_set(item_index)
                    listbox.activate(item_index)

                    # Прокручиваем чтобы было видно
                    listbox.see(item_index)

                # Активируем кнопку Применить
                self.apply_button.config(state=tk.NORMAL, bg='#15354D')

                print(f"Подсвечена текущая стратегия: {self.current_strategy}")
        except Exception as e:
            print(f"Ошибка подсветки текущей стратегии: {e}")

    def get_column_and_index(self, global_index):
        """Возвращает номер колонки и индекс внутри колонки по глобальному индексу"""
        if not self.strategy_items or global_index >= len(self.strategy_items):
            return None, None

        # Распределяем стратегии по колонкам равномерно
        items_per_column = (len(self.strategy_items) + 2) // 3  # Округление вверх

        col_index = global_index // items_per_column
        if col_index >= 3:  # На всякий случай
            col_index = 2

        item_index = global_index % items_per_column

        # Проверяем что в этой колонке есть столько элементов
        listbox = self.column_listboxes[col_index]
        if item_index >= listbox.size():
            # Ищем последний элемент в этой колонке
            item_index = listbox.size() - 1

        return col_index, item_index

    def get_global_index(self, col_index, item_index):
        """Возвращает глобальный индекс по номеру колонки и индексу внутри колонки"""
        if col_index >= len(self.column_listboxes):
            return None

        # Подсчитываем количество элементов в предыдущих колонках
        total_before = 0
        for i in range(col_index):
            total_before += self.column_listboxes[i].size()

        return total_before + item_index

    def load_strategies(self):
        """Загружает список стратегий из папки и распределяет по трем колонкам"""
        try:
            # Путь к папке со стратегиями
            manager_dir = os.path.expanduser("~/Zapret_DPI_Manager/files")
            strategy_dir = os.path.join(manager_dir, "strategy")

            # Создаем папку если ее нет
            if not os.path.exists(strategy_dir):
                os.makedirs(strategy_dir)
                print(f"Создана папка для стратегий: {strategy_dir}")

            # Очищаем списки
            for listbox in self.column_listboxes:
                listbox.delete(0, tk.END)
            self.strategy_items.clear()

            # Загружаем пользовательские стратегии из файлов (без расширения)
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
                    # Нет стратегий - показываем сообщение в первой колонке
                    self.column_listboxes[0].insert(tk.END, "  Стратегии не найдены")
                    self.column_listboxes[0].config(state=tk.DISABLED)
                else:
                    # Распределяем стратегии по трем колонкам
                    items_per_column = (len(self.strategy_items) + 2) // 3  # Округление вверх

                    for i, strategy in enumerate(self.strategy_items):
                        col_index = i // items_per_column
                        if col_index < 3:  # Убеждаемся что не выходим за пределы
                            listbox = self.column_listboxes[col_index]
                            listbox.insert(tk.END, f"  {self.radio_unselected}  {strategy}")

                    # После загрузки всех стратегий подсвечиваем текущую
                    self.root.after(100, self.highlight_current_strategy)

        except Exception as e:
            print(f"Ошибка загрузки стратегий: {e}")
            self.column_listboxes[0].insert(tk.END, f"  Ошибка: {str(e)}")
            self.column_listboxes[0].config(state=tk.DISABLED)

    def on_listbox_click_listbox(self, event, listbox):
        """Обрабатывает клик в конкретном Listbox для имитации радиокнопок"""
        # Получаем индекс кликнутого элемента
        index = listbox.nearest(event.y)

        # Находим какой это Listbox и получаем его содержимое
        col_index = self.column_listboxes.index(listbox)

        # Получаем текст элемента
        if index < listbox.size():
            item_text = listbox.get(index)

            # Извлекаем имя стратегии из текста
            if "  " in item_text:
                parts = item_text.split("  ")
                if len(parts) >= 3:
                    strategy_name = parts[2].strip()

                    # Находим глобальный индекс
                    global_index = self.get_global_index(col_index, index)

                    if strategy_name in self.strategy_items and global_index is not None:
                        # Сбрасываем все радиокнопки
                        self.reset_radio_buttons()

                        # Устанавливаем выбранную радиокнопку
                        listbox.delete(index)
                        listbox.insert(index, f"  {self.radio_selected}  {strategy_name}")

                        # Выделяем строку
                        listbox.selection_clear(0, tk.END)
                        listbox.selection_set(index)
                        listbox.activate(index)

                        # Сохраняем выбранную стратегию
                        self.selected_strategy = strategy_name
                        self.apply_button.config(state=tk.NORMAL, bg='#15354D')

        return "break"  # Предотвращаем стандартную обработку

    def on_strategy_select_listbox(self, listbox):
        """Обрабатывает выбор стратегии через клавиатуру в конкретном Listbox"""
        selection = listbox.curselection()
        if selection:
            index = selection[0]

            # Находим какой это Listbox
            col_index = self.column_listboxes.index(listbox)

            # Получаем текст элемента
            item_text = listbox.get(index)

            # Извлекаем имя стратегии из текста
            if "  " in item_text:
                parts = item_text.split("  ")
                if len(parts) >= 3:
                    strategy_name = parts[2].strip()

                    if strategy_name in self.strategy_items:
                        # Сбрасываем все радиокнопки
                        self.reset_radio_buttons()

                        # Устанавливаем выбранную радиокнопку
                        listbox.delete(index)
                        listbox.insert(index, f"  {self.radio_selected}  {strategy_name}")

                        self.selected_strategy = strategy_name
                        self.apply_button.config(state=tk.NORMAL, bg='#15354D')

    def reset_radio_buttons(self):
        """Сбрасывает все радиокнопки к пустому состоянию во всех колонках"""
        for i, strategy in enumerate(self.strategy_items):
            # Находим в какой колонке и какой индекс внутри колонки
            col_index, item_index = self.get_column_and_index(i)

            if col_index is not None and item_index is not None:
                listbox = self.column_listboxes[col_index]

                # Проверяем что элемент существует
                if item_index < listbox.size():
                    current_text = listbox.get(item_index)
                    # Проверяем что это действительно стратегия (а не сообщение об ошибке)
                    if strategy in current_text:
                        listbox.delete(item_index)
                        listbox.insert(item_index, f"  {self.radio_unselected}  {strategy}")

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
                messagebox.showerror("Ошибка", f"Файл стратегии не найден:\n{self.selected_strategy}")
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
