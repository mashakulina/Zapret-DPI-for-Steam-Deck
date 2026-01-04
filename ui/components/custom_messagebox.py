#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk

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

def _show_dialog(parent, title, message, dialog_type):
    """Базовый метод для показа диалогового окна"""
    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg='#182030')
    dialog.resizable(False, False)

    # Центрируем окно
    dialog.transient(parent)
    dialog.grab_set()

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
    main_frame.pack()

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
    message_label.pack(pady=(0, 25))

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

    # Устанавливаем размеры и центрируем
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)


    # Ждем закрытия окна
    parent.wait_window(dialog)
    return True

def _show_question(parent, title, message):
    """Метод для показа вопроса Да/Нет"""
    result = {"value": False}

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg='#182030')
    dialog.resizable(False, False)

    # Центрируем окно
    dialog.transient(parent)
    dialog.grab_set()

    # Основной фрейм
    main_frame = tk.Frame(dialog, bg='#182030', padx=30, pady=25)
    main_frame.pack()

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
    message_label.pack(pady=(0, 25))

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

    # Устанавливаем размеры и центрируем
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)

    # Ждем закрытия окна
    parent.wait_window(dialog)
    return result["value"]

def _show_question_cancel(parent, title, message):
    """Метод для показа вопроса Да/Нет/Отмена"""
    result = {"value": None}  # True=Да, False=Нет, None=Отмена

    dialog = tk.Toplevel(parent)
    dialog.title(title)
    dialog.configure(bg='#182030')
    dialog.resizable(False, False)

    # Центрируем окно
    dialog.transient(parent)
    dialog.grab_set()

    # Основной фрейм
    main_frame = tk.Frame(dialog, bg='#182030', padx=30, pady=25)
    main_frame.pack()

    # Заголовок
    title_label = tk.Label(main_frame,
                          text=title,
                          font=("Arial", 14, "bold"),
                          fg='#white',  # Синий для вопросов
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
    message_label.pack(pady=(0, 25))

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

    # Устанавливаем размеры и центрируем
    dialog.update_idletasks()
    width = dialog.winfo_width()
    height = dialog.winfo_height()
    x = parent.winfo_rootx() + (parent.winfo_width() // 2) - (width // 2)
    y = parent.winfo_rooty() + (parent.winfo_height() // 2) - (height // 2)
    dialog.geometry(f"{width}x{height}+{x}+{y}")

    # Ждем закрытия окна
    parent.wait_window(dialog)
    return result["value"]

def _close_dialog(dialog):
    """Закрывает диалоговое окно"""
    dialog.destroy()
