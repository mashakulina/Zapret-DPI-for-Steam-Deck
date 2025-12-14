import tkinter as tk
import webbrowser
import subprocess
import urllib.parse
import re
import os
from urllib.request import urlopen
from ui.components.button_styler import create_hover_button
from core.manager_config import MANAGER_CONFIG, ZAPRET_CONFIG
_last_available_site = None
_last_check_time = 0


def setup_window_properties(self):
    """Настройка свойств окна для корректного отображения"""
    self.root.title("Zapret DPI Manager")

    # Устанавливаем WM_CLASS (БЕЗ ПРОБЕЛОВ!)
    try:
        self.root.wm_class("ZapretDPIManager")
    except:
        pass

    # Устанавливаем иконку
    try:
        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        icon_path = os.path.join(manager_dir, "ico/adguard.png")
        if os.path.exists(icon_path):
            # Для PNG файлов в tkinter
            icon = tk.PhotoImage(file=icon_path)
            self.root.iconphoto(True, icon)
    except Exception as e:
        print(f"Не удалось установить иконку: {e}")

def get_manager_version():
    """Получает версию менеджера"""
    return MANAGER_CONFIG.get("current_version", "Неизвестно")

def get_zapret_version():
    """Получает версию менеджера"""
    return ZAPRET_CONFIG.get("current_version", "Неизвестно")

def clean_ansi_codes(text):
    """Очищает текст от ANSI escape sequences"""
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def show_info_dialog(parent):
    """Показывает диалоговое окно с информацией"""
    dialog = tk.Toplevel(parent)

    # Применяем настройки окна
    try:
        dialog.title("Zapret_DPI_Manager")
        dialog.wm_class("ZapretDPIManager")

        manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        icon_path = os.path.join(manager_dir, "ico/adguard.png")
        if os.path.exists(icon_path):
            icon = tk.PhotoImage(file=icon_path)
            dialog.iconphoto(True, icon)
    except Exception as e:
        print(f"Не удалось установить свойства окна: {e}")

    dialog.title("Информация о Zapret DPI Manager")

    dialog.configure(bg='#182030')
    dialog.transient(parent)

    """Настройка свойств окна"""
    dialog.geometry("380x270")
    dialog.configure(bg='#182030')

    # Заголовок
    title_frame = tk.Frame(dialog, bg='#182030', pady=15)
    title_frame.pack(fill=tk.X)

    tk.Label(title_frame, text="Информация",
             font=("Arial", 14, "bold"), bg='#182030', fg='white').pack()

    # Основное содержимое
    content_frame = tk.Frame(dialog, bg='#182030', padx=20)
    content_frame.pack(fill=tk.BOTH, expand=True)

    # Информационное сообщение
    info_text = (
        "Zapret DPI Manager помогает получить доступ к Youtube и Discord на Steam Deck"
    )

    info_frame = tk.Frame(content_frame, bg='#182030')
    info_frame.pack(fill=tk.X, pady=(0, 20))

    # Автоматический расчет wraplength
    window_width = 395
    padding = 50
    auto_wraplength = window_width - padding

    info_label = tk.Label(info_frame, text=info_text,
                        font=('Arial', 11),
                        bg='#182030',
                        fg='#ff9500',
                        wraplength=auto_wraplength,
                        justify=tk.CENTER
                        )
    info_label.pack(fill=tk.X)

    # Сначала объявляем функции для ссылок
    def open_official_page(event):
        available_site = get_available_site()
        webbrowser.open(available_site)

    def open_github_page(event):
        webbrowser.open("https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck")

    # Функция для создания ссылки с разделенной иконкой и текстом
    def create_link_with_icon(parent, icon, text, command_func):
        link_frame = tk.Frame(parent, bg='#182030')
        link_frame.pack(anchor=tk.W, pady=(0, 8), fill=tk.X)

        # Иконка (без подчеркивания)
        icon_label = tk.Label(link_frame, text=icon, font=('Arial', 11),
                            bg='#182030', fg='#3CAA3C', cursor='hand2')
        icon_label.pack(side=tk.LEFT)
        icon_label.bind("<Button-1>", command_func)
        icon_label.bind("<Enter>", lambda e: (icon_label.config(fg='#4d8058'),
                                            text_label.config(fg='#4d8058', font=('Arial', 11, 'underline'))))
        icon_label.bind("<Leave>", lambda e: (icon_label.config(fg='#3CAA3C'),
                                            text_label.config(fg='#3CAA3C', font=('Arial', 11))))

        # Текст (с подчеркиванием при наведении)
        text_label = tk.Label(link_frame, text=text, font=('Arial', 11),
                            bg='#182030', fg='#3CAA3C', cursor='hand2')
        text_label.pack(side=tk.LEFT)
        text_label.bind("<Button-1>", command_func)
        text_label.bind("<Enter>", lambda e: (icon_label.config(fg='#4d8058'),
                                            text_label.config(fg='#4d8058', font=('Arial', 11, 'underline'))))
        text_label.bind("<Leave>", lambda e: (icon_label.config(fg='#3CAA3C'),
                                            text_label.config(fg='#3CAA3C', font=('Arial', 11))))

        return link_frame

    # Создаем ссылки с разделенными иконками и текстом
    create_link_with_icon(content_frame, "💻", "Страница Zapret DPI Manager на GitHub", open_github_page)

    # Отображаем версии в одну строку по центру
    versions_frame = tk.Frame(content_frame, bg='#182030')
    versions_frame.pack(fill=tk.X, pady=(10,0))

    # Версия zapret и менеджера в одну строку
    zapret_version = get_zapret_version()
    manager_version = get_manager_version()

    version_text = f"Zapret DPI Manager: {manager_version} | Zapret DPI: {zapret_version}"
    version_label = tk.Label(versions_frame, text=version_text,
                           font=("Arial", 9), fg='#5BA06A', bg='#182030')
    version_label.pack(anchor=tk.CENTER)

    # Кнопка закрытия
    button_frame = tk.Frame(dialog, bg='#182030')
    button_frame.pack(fill=tk.X, pady=(0,15))

    close_style = {
        'font': ('Arial', 10),
        'bg': '#15354D',
        'fg': 'white',
        'bd': 0,
        'padx': 20,
        'pady': 8,
        'width': 10,
        'highlightthickness': 0,
        'cursor': 'hand2'
    }

    close_btn = create_hover_button(button_frame, text="Закрыть",
                                  command=dialog.destroy, **close_style)
    close_btn.pack()

    # Обработка клавиш
    dialog.bind('<Escape>', lambda e: dialog.destroy())
    dialog.bind('<Return>', lambda e: dialog.destroy())

    # Устанавливаем фокус на диалоговое окно
    dialog.focus_set()

    # Ждем закрытия окна
    dialog.wait_window()
