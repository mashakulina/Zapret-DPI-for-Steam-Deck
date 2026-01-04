import tkinter as tk
from tkinter import ttk, messagebox
from core.sudo_checker import SudoChecker
from ui.components.button_styler import create_hover_button

class SudoPasswordWindow:
    def __init__(self, parent, on_password_valid=None):
        self.parent = parent
        self.on_password_valid = on_password_valid

        self.root = tk.Toplevel(parent)
        self.setup_window_properties()
        self.root.title("Требуется пароль sudo")

        self.password = None
        self.setup_ui()

        # Пробуем загрузить кэшированный пароль
        cached_password = SudoChecker.get_cached_password()
        if cached_password:
            self.password_entry.insert(0, cached_password)
            self.remember_var.set(True)

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.geometry("300x310")
        self.root.configure(bg='#182030')
        self.root.transient(self.parent)
        self.root.grab_set()

        # Блокируем родительское окно
        self.root.focus_set()

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(
            main_frame,
            text="Введите sudo пароль",
            font=("Arial", 14, "bold"),
            fg='white',
            bg='#182030'
        )
        title_label.pack(pady=(0, 20))

        # Описание
        description_label = tk.Label(
            main_frame,
            text="Для управления службой требуются\nправа администратора",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030',
            justify=tk.CENTER
        )
        description_label.pack(pady=(0, 20))

        # Поле для пароля
        password_frame = tk.Frame(main_frame, bg='#182030')
        password_frame.pack(fill=tk.X, pady=(0, 20))

        tk.Label(
            password_frame,
            text="Пароль:",
            font=("Arial", 11),
            fg='white',
            bg='#182030'
        ).pack(anchor=tk.W)

        self.password_entry = tk.Entry(
            password_frame,
            show="•",
            font=("Arial", 11),
            bg='#2A3B5C',
            fg='white',
            insertbackground='white',
            relief=tk.FLAT,
            bd=0,
            highlightthickness=2,
            highlightbackground='#3A4B6C',
            highlightcolor='#4A8FE7',
            width=25
        )
        self.password_entry.pack(fill=tk.X, pady=(5, 0))
        self.password_entry.bind('<Return>', lambda e: self.verify_password())

        # Чекбокс "Запомнить"
        self.remember_var = tk.BooleanVar(value=False)
        remember_check = tk.Checkbutton(
            main_frame,
            text="Запомнить пароль",
            variable=self.remember_var,
            font=("Arial", 9),
            highlightthickness=0,
            fg='white',
            bg='#182030',
            activebackground='#182030',
            activeforeground='white',
            selectcolor='#182030',
            cursor='hand2'
        )
        remember_check.pack(anchor=tk.W, pady=(0, 25))

        # Фрейм для кнопок
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X)

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 20,
            'pady': 8,
            'width': 10,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка Подтвердить
        confirm_button = create_hover_button(
            buttons_frame,
            text="Подтвердить",
            command=self.verify_password,
            **button_style
        )

        confirm_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка Отмена
        cancel_button = create_hover_button(
            buttons_frame,
            text="Отмена",
            command=self.cancel,
            **button_style
        )
        cancel_button.pack(side=tk.RIGHT)

    def verify_password(self):
        """Проверяет введенный пароль"""
        password = self.password_entry.get().strip()

        if not password:
            messagebox.showerror("Ошибка", "Введите пароль sudo")
            return

        # Показываем индикатор загрузки
        self.root.config(cursor="watch")
        self.root.update()

        # Проверяем пароль
        is_valid = SudoChecker.is_sudo_password_valid(password)

        # Возвращаем курсор
        self.root.config(cursor="")

        if is_valid:
            self.password = password

            # Если выбрано "запомнить" - кэшируем пароль
            if self.remember_var.get():
                SudoChecker.cache_password(password)
            else:
                SudoChecker.clear_password_cache()

            # Вызываем callback если он есть
            if self.on_password_valid:
                self.on_password_valid(password)

            # Закрываем окно
            self.root.destroy()
        else:
            messagebox.showerror("Ошибка", "Неверный пароль sudo")
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()

    def cancel(self):
        """Отмена ввода пароля"""
        self.password = None
        self.root.destroy()

    def get_password(self):
        """Возвращает введенный пароль"""
        return self.password

    def run(self):
        """Запускает окно"""
        self.root.wait_window()
        return self.password
