#!/usr/bin/env python3
import tkinter as tk

from core.dpi_utils import place_toplevel_centered_on_parent

def show_info(parent, title, message):
    """Показывает информационное сообщение в стиле приложения"""
    return _show_dialog(parent, title, message, "info")

def show_error(parent, title, message):
    """Показывает сообщение об ошибке в стиле приложения"""
    return _show_dialog(parent, title, message, "error")

def show_warning(parent, title, message):
    """Показывает предупреждение в стиле приложения"""
    return _show_dialog(parent, title, message, "warning")

def ask_yesno(parent, title, message):
    """Показывает диалог с вопросом Да/Нет в стиле приложения"""
    return _show_question(parent, title, message)

def ask_yesnocancel(parent, title, message):
    """Показывает диалог с вопросом Да/Нет/Отмена в стиле приложения"""
    return _show_question_cancel(parent, title, message)


def _attach_resizing_message_wrap(dialog, message_label, horizontal_pad=60):
    """Обновляет wraplength текста сообщения при изменении ширины диалога."""
    def _sync(_event=None):
        try:
            if not dialog.winfo_exists():
                return
            w = dialog.winfo_width()
            if w <= 1:
                return
            message_label.config(wraplength=max(120, w - horizontal_pad))
        except tk.TclError:
            pass

    dialog.resizable(True, False)
    dialog.minsize(280, 120)
    dialog.bind("<Configure>", lambda _e: _sync())
    dialog.after_idle(_sync)


def prepare_modal_window(window):
    """Map a fully built window before grabbing input; tolerate WM/close races."""
    try:
        if not window.winfo_exists():
            return False
        window.deiconify()
        window.update_idletasks()
        if not window.winfo_viewable():
            window.wait_visibility()
        if not window.winfo_exists():
            return False
        try:
            window.grab_set()
        except tk.TclError:
            # A compositor may briefly unmap the newly displayed window.
            window.update_idletasks()
            if not window.winfo_viewable():
                window.wait_visibility()
            if not window.winfo_exists():
                return False
            try:
                window.grab_set()
            except tk.TclError:
                # A complete visible message is still useful without a grab.
                if not window.winfo_viewable():
                    _close_dialog(window)
                    return False
        window.lift()
        window.focus_set()
        return True
    except tk.TclError:
        _close_dialog(window)
        return False

def _run_modal(parent, title, build, cancelled):
    dialog = None
    previous_grab = None
    try:
        previous_grab = parent.grab_current()
        dialog = tk.Toplevel(parent)
        # Build all controls before mapping, so failures cannot leave an empty window.
        dialog.withdraw()
        dialog.title(title)
        dialog.configure(bg='#182030')
        if parent.winfo_viewable():
            dialog.transient(parent)
        return build(dialog)
    except tk.TclError:
        # Closing the app during construction or a WM transition is cancellation.
        return cancelled
    finally:
        if dialog is not None:
            _close_dialog(dialog)
        try:
            if previous_grab is not None and previous_grab.winfo_exists() and previous_grab.winfo_viewable():
                previous_grab.grab_set()
        except tk.TclError:
            pass


def _wait_modal(parent, dialog):
    dialog.update_idletasks()
    width = min(max(280, dialog.winfo_reqwidth()), max(1, dialog.winfo_screenwidth() - 16))
    height = min(max(120, dialog.winfo_reqheight()), max(1, dialog.winfo_screenheight() - 40))
    place_toplevel_centered_on_parent(
        dialog, parent, fixed_content_size=(width, height), immediate=True,
    )
    if not prepare_modal_window(dialog):
        return False
    parent.wait_window(dialog)
    return True


def _show_dialog(parent, title, message, dialog_type):
    return _run_modal(parent, title,
                      lambda dialog: _build_dialog(parent, title, message, dialog_type, dialog), False)


def _show_question(parent, title, message):
    return _run_modal(parent, title, lambda dialog: _build_question(parent, title, message, dialog), False)


def _show_question_cancel(parent, title, message):
    return _run_modal(parent, title, lambda dialog: _build_question_cancel(parent, title, message, dialog), None)


def _build_dialog(parent, title, message, dialog_type, dialog):
    """Базовый метод для показа диалогового окна"""

    # Определяем цвета в зависимости от типа
    if dialog_type == "error":
        title_color = 'white'  # Красный
        button_color = '#ff3b30'
    elif dialog_type == "warning":
        title_color = 'white'  # Оранжевый
        button_color = '#ff9500'
    else:  # info
        title_color = 'white'  # Синий
        button_color = '#0a84ff'

    # Основной фрейм
    main_frame = tk.Frame(dialog, bg='#182030', padx=30, pady=25)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Заголовок
    title_label = tk.Label(main_frame,
                          text=title,
                          font=("Arial", 14, "bold"),
                          fg=title_color,
                          bg='#182030')
    title_label.pack(pady=(0, 15))

    # Сообщение
    message_label = tk.Label(main_frame,
                            text=message,
                            font=("Arial", 11),
                            fg='white',
                            bg='#182030',
                            justify=tk.LEFT,
                            wraplength=400)
    message_label.pack(pady=(0, 25), fill=tk.X)
    _attach_resizing_message_wrap(dialog, message_label)

    # Кнопка
    button_frame = tk.Frame(main_frame, bg='#182030')
    button_frame.pack()

    button = tk.Button(button_frame,
                      text="OK",
                      font=("Arial", 11),
                      bg='#15354D',
                      fg='white',
                      bd=0,
                      padx=25,
                      pady=8,
                      cursor='hand2',
                      highlightthickness=0,
                      command=lambda: _close_dialog(dialog))

    # Добавляем эффект наведения
    def on_enter(event):
        button.config(bg='#1E4A6E')

    def on_leave(event):
        button.config(bg='#15354D')

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    button.pack()

    return _wait_modal(parent, dialog)

def _build_question(parent, title, message, dialog):
    """Метод для показа вопроса Да/Нет"""
    result = {"value": False}


    # Основной фрейм
    main_frame = tk.Frame(dialog, bg='#182030', padx=30, pady=25)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Заголовок
    title_label = tk.Label(main_frame,
                          text=title,
                          font=("Arial", 14, "bold"),
                          fg='#0a84ff',  # Синий для вопросов
                          bg='#182030')
    title_label.pack(pady=(0, 15))

    # Сообщение
    message_label = tk.Label(main_frame,
                            text=message,
                            font=("Arial", 11),
                            fg='white',
                            bg='#182030',
                            justify=tk.LEFT,
                            wraplength=400)
    message_label.pack(pady=(0, 25), fill=tk.X)
    _attach_resizing_message_wrap(dialog, message_label)

    # Кнопки
    button_frame = tk.Frame(main_frame, bg='#182030')
    button_frame.pack()

    def set_result(value):
        result["value"] = value
        dialog.destroy()

    # Кнопка Да
    yes_button = tk.Button(button_frame,
                          text="Да",
                          font=("Arial", 11),
                          bg='#15354D',
                          fg='white',
                          bd=0,
                          padx=20,
                          pady=8,
                          cursor='hand2',
                          highlightthickness=0,
                          command=lambda: set_result(True))

    # Кнопка Нет
    no_button = tk.Button(button_frame,
                         text="Нет",
                         font=("Arial", 11),
                         bg='#15354D',
                         fg='white',
                         bd=0,
                         padx=20,
                         pady=8,
                         cursor='hand2',
                         highlightthickness=0,
                         command=lambda: set_result(False))

    # Добавляем эффект наведения
    def on_enter_yes(event):
        yes_button.config(bg='#34c759')

    def on_leave_yes(event):
        yes_button.config(bg='#15354D')

    def on_enter_no(event):
        no_button.config(bg='#ff453a')

    def on_leave_no(event):
        no_button.config(bg='#15354D')

    yes_button.bind("<Enter>", on_enter_yes)
    yes_button.bind("<Leave>", on_leave_yes)
    no_button.bind("<Enter>", on_enter_no)
    no_button.bind("<Leave>", on_leave_no)

    yes_button.pack(side=tk.LEFT, padx=(0, 40))
    no_button.pack(side=tk.LEFT)

    _wait_modal(parent, dialog)
    return result["value"]

def _build_question_cancel(parent, title, message, dialog):
    """Метод для показа вопроса Да/Нет/Отмена"""
    result = {"value": None}  # True=Да, False=Нет, None=Отмена


    # Основной фрейм
    main_frame = tk.Frame(dialog, bg='#182030', padx=30, pady=25)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Заголовок
    title_label = tk.Label(main_frame,
                          text=title,
                          font=("Arial", 14, "bold"),
                          fg='white',
                          bg='#182030')
    title_label.pack(pady=(0, 15))

    # Сообщение
    message_label = tk.Label(main_frame,
                            text=message,
                            font=("Arial", 11),
                            fg='white',
                            bg='#182030',
                            justify=tk.LEFT,
                            wraplength=400)
    message_label.pack(pady=(0, 25), fill=tk.X)
    _attach_resizing_message_wrap(dialog, message_label)

    # Кнопки
    button_frame = tk.Frame(main_frame, bg='#182030')
    button_frame.pack()

    def set_result(value):
        result["value"] = value
        dialog.destroy()

    # Кнопка Да
    yes_button = tk.Button(button_frame,
                          text="Да",
                          font=("Arial", 11),
                          bg='#15354D',
                          fg='white',
                          bd=0,
                          padx=15,
                          pady=8,
                          cursor='hand2',
                          command=lambda: set_result(True))

    # Кнопка Нет
    no_button = tk.Button(button_frame,
                         text="Нет",
                         font=("Arial", 11),
                         bg='#15354D',
                         fg='white',
                         bd=0,
                         padx=15,
                         pady=8,
                         cursor='hand2',
                         command=lambda: set_result(False))

    # Кнопка Отмена
    cancel_button = tk.Button(button_frame,
                            text="Отмена",
                            font=("Arial", 11),
                            bg='#15354D',
                            fg='white',
                            bd=0,
                            padx=15,
                            pady=8,
                            cursor='hand2',
                            command=lambda: set_result(None))

    # Добавляем эффект наведения
    def on_enter_yes(event):
        yes_button.config(bg='#34c759')

    def on_leave_yes(event):
        yes_button.config(bg='#30d158')

    def on_enter_no(event):
        no_button.config(bg='#ff453a')

    def on_leave_no(event):
        no_button.config(bg='#ff3b30')

    def on_enter_cancel(event):
        cancel_button.config(bg='#98989d')

    def on_leave_cancel(event):
        cancel_button.config(bg='#8e8e93')

    yes_button.bind("<Enter>", on_enter_yes)
    yes_button.bind("<Leave>", on_leave_yes)
    no_button.bind("<Enter>", on_enter_no)
    no_button.bind("<Leave>", on_leave_no)
    cancel_button.bind("<Enter>", on_enter_cancel)
    cancel_button.bind("<Leave>", on_leave_cancel)

    yes_button.pack(side=tk.LEFT, padx=(0, 5))
    no_button.pack(side=tk.LEFT, padx=(0, 5))
    cancel_button.pack(side=tk.LEFT)

    _wait_modal(parent, dialog)
    return result["value"]

def _close_dialog(dialog):
    """Закрывает диалог, в том числе уже уничтоженный оконным менеджером."""
    try:
        if dialog.winfo_exists():
            dialog.destroy()
    except tk.TclError:
        pass
