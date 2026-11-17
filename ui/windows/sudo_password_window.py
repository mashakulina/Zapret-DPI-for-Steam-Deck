from ui.components.window_navigation import prepare_window_navigation
import tkinter as tk
from core.sudo_checker import SudoChecker
from ui.components.button_styler import create_hover_button
from ui.components.custom_messagebox import prepare_modal_window, show_error
from core.dpi_utils import application_tk_root, place_toplevel_centered_on_parent

class SudoPasswordWindow:
    def __init__(self, parent, on_password_valid=None):
        self.parent = parent
        self.anchor = application_tk_root(parent) or parent
        self.on_password_valid = on_password_valid
        self._layout_ready = False

        self.root = tk.Toplevel(parent)
        self.root.withdraw()
        self.setup_window_properties()
        self.root.title("Требуется пароль sudo")

        self.password = None
        self.setup_ui()

        # Пробуем загрузить кэшированный пароль
        cached_password = SudoChecker.get_cached_password()
        if cached_password:
            self.password_entry.insert(0, cached_password)
            self.remember_var.set(True)
        self._place_compact_window()
        self._layout_ready = True
        if prepare_modal_window(self.root):
            self.password_entry.focus_set()

    def _place_compact_window(self):
        self.root.update_idletasks()
        width = min(max(280, self.main_frame.winfo_reqwidth() + 8),
                    max(1, self.anchor.winfo_screenwidth() - 32))
        # Set the final wrap before measuring height; hidden frames still report 1px.
        self.description_label.configure(wraplength=max(120, width - 40))
        self.root.update_idletasks()
        height = min(max(240, self.main_frame.winfo_reqheight() + 12),
                     max(1, self.anchor.winfo_screenheight() - 80))
        self.root.minsize(width, height)
        place_toplevel_centered_on_parent(
            self.root, self.anchor, fixed_content_size=(width, height), immediate=True,
        )

    def setup_window_properties(self):
        """Настройка свойств окна"""
        self.root.configure(bg='#182030')
        if self.anchor.winfo_viewable():
            self.root.transient(self.anchor)

    def setup_ui(self):
        """Настройка интерфейса"""
        main_frame = tk.Frame(self.root, bg='#182030', padx=20, pady=15)
        self.main_frame = main_frame
        main_frame.pack(fill=tk.X)

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
            text="Для управления службой требуются права администратора",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030',
            justify=tk.LEFT,
            wraplength=360,
        )
        self.description_label = description_label
        description_label.pack(pady=(0, 20), fill=tk.X)

        def _sync_desc_wrap(_event=None):
            try:
                if not self._layout_ready:
                    return
                aw = main_frame.winfo_width()
                if aw <= 1:
                    return
                description_label.config(wraplength=max(120, aw - 40))
            except tk.TclError:
                pass

        main_frame.bind("<Configure>", lambda _e: _sync_desc_wrap())

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
        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

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
            buttons_center_frame,
            text="Подтвердить",
            command=self.verify_password,
            **button_style
        )

        confirm_button.pack(side=tk.LEFT, padx=(0, 10))

        # Кнопка Отмена
        cancel_button = create_hover_button(
            buttons_center_frame,
            text="Отмена",
            command=self.cancel,
            **button_style
        )
        cancel_button.pack(side=tk.LEFT)

    def verify_password(self):
        """Проверяет введенный пароль"""
        # Пробелы — часть пароля, в том числе пароль из одного пробела.
        password = self.password_entry.get()

        if not password:
            show_error(self.root, "Ошибка", "Введите пароль sudo")
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
            show_error(self.root, "Ошибка", "Неверный пароль sudo")
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
        try:
            if self.root.winfo_exists():
                prepare_window_navigation(self.root)
                self.root.wait_window()
        except tk.TclError:
            return None
        return self.password
