#!/usr/bin/env python3
import tkinter as tk
from tkinter import messagebox
import re
import os
from ui.components.custom_messagebox import show_info, show_error, ask_yesno, ask_yesnocancel


class IpsetSettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None

        # Путь к файлу с IP-адресами
        self.manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        self.ipset_file = os.path.join(self.manager_dir, "files", "lists", "ipset-all2.txt")

    def validate_ip_address(self, ip_str):
        """Проверяет корректность IP-адреса, диапазона или подсети"""

        # Комментарий
        if ip_str.strip().startswith('#'):
            return True, ""

        # Проверка на пустую строку
        if not ip_str.strip():
            return True, ""

        # Регулярные выражения для различных форматов
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        cidr_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$'
        range_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'

        # Проверка простого IP-адреса
        if re.match(ip_pattern, ip_str):
            parts = ip_str.split('.')
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False, "Неверный IP-адрес"
            return True, ""

        # Проверка CIDR нотации
        elif re.match(cidr_pattern, ip_str):
            ip_part, cidr_part = ip_str.split('/')
            parts = ip_part.split('.')

            # Проверка IP части
            for part in parts:
                if not 0 <= int(part) <= 255:
                    return False, "Неверный IP в CIDR"

            # Проверка CIDR части
            cidr = int(cidr_part)
            if not 0 <= cidr <= 32:
                return False, "Неверная маска CIDR"

            return True, ""

        # Проверка диапазона
        elif re.match(range_pattern, ip_str):
            start_ip, end_ip = ip_str.split('-')

            # Проверка начального IP
            start_parts = start_ip.split('.')
            for part in start_parts:
                if not 0 <= int(part) <= 255:
                    return False, "Неверный начальный IP в диапазоне"

            # Проверка конечного IP
            end_parts = end_ip.split('.')
            for part in end_parts:
                if not 0 <= int(part) <= 255:
                    return False, "Неверный конечный IP в диапазоне"

            return True, ""

        else:
            # Проверяем, не является ли это комментарием без #
            if ip_str.strip() and not ip_str.strip().startswith('#'):
                return False, "Некорректный формат или комментарий без #"
            return False, "Некорректный формат"

    def validate_data(self):
        """Проверяет введенные данные"""
        data = self.text_input.get("1.0", tk.END).strip()
        if not data:
            show_info(self.window, "Проверка данных", "Нет данных для проверки")
            return

        lines = data.split('\n')
        error_lines = []

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:  # Пропускаем пустые строки
                continue

            is_valid, error_msg = self.validate_ip_address(line)
            if not is_valid:
                error_lines.append(f"Строка {i}: {line} - {error_msg}")

        if error_lines:
            error_text = "\n".join(error_lines)
            show_info(self.window, "Ошибка в данных", f"Обнаружены ошибки:\n\n{error_text}")
        else:
            show_info(self.window, "Проверка данных", "Все данные введены корректно!")

    def save_data(self):
        """Сохраняет данные в файл"""
        data = self.text_input.get("1.0", tk.END).strip()

        # Проверяем данные перед сохранением
        if data:  # Если есть данные, проверяем их
            lines = data.split('\n')
            error_lines = []

            for i, line in enumerate(lines, 1):
                line = line.strip()
                if not line:  # Пропускаем пустые строки
                    continue

                is_valid, error_msg = self.validate_ip_address(line)
                if not is_valid:
                    error_lines.append(f"Строка {i}: {line} - {error_msg}")

            if error_lines:
                error_text = "\n".join(error_lines)
                # Просто показываем ошибки и не сохраняем
                show_info(self.window, "Ошибка в данных",
                        f"Обнаружены ошибки. Данные не сохранены:\n\n{error_text}")
                return

        # Сохраняем данные (даже если файл пустой)
        self.write_to_file(data)

    def write_to_file(self, data):
        """Записывает данные в файл"""
        try:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(self.ipset_file), exist_ok=True)

            with open(self.ipset_file, 'w', encoding='utf-8') as f:
                f.write(data)

            if data:
                show_info(self.window, "Сохранение", "Данные успешно сохранены!")
            else:
                show_info(self.window, "Сохранение", "Файл очищен (сохранен как пустой)")

        except Exception as e:
            show_info(self.window, "Ошибка", f"Не удалось сохранить файл: {e}")

    def load_existing_data(self):
        """Загружает существующие данные из файла"""
        try:
            if os.path.exists(self.ipset_file):
                with open(self.ipset_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    self.text_input.delete("1.0", tk.END)
                    self.text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла: {e}")

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def create_window(self):
        """Создает окно добавления пользовательских IP-адресов"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Добавление пользовательских IP-адресов")
        self.window.geometry("460x530")
        self.window.configure(bg='#182030')
        self.window.resizable(True, True)

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Добавление пользовательских IP-адресов",
                               font=("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.pack(anchor=tk.CENTER, pady=(0, 15))

        # Информационный текст
        info_frame = tk.Frame(main_frame, bg='#182030')
        info_frame.pack(fill=tk.X, pady=(0, 15))

        info_text = [
            "Пользовательские IP-адреса будут сохраняться в файле ipset-all2.txt",
            "Вводить адреса или диапазон нужно по одному на строку",
            "Примеры ввода адресов: 192.168.1.1, 10.0.0.0/8 или 172.16.0.0-172.31.255.255",
            "Чтобы оставить комментарий, нужно сначала поставить знак '#' и только после этого писать текст комментария"
        ]

        for text in info_text:
            info_label = tk.Label(info_frame,
                                 text=text,
                                 font=("Arial", 10),
                                 fg='#8e8e93',
                                 bg='#182030',
                                 justify=tk.LEFT,
                                 wraplength=400)
            info_label.pack(anchor=tk.W, pady=(0, 5))

        # Фрейм для текстового поля
        text_frame = tk.Frame(main_frame, bg='#182030')
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Метка для текстового поля
        text_label = tk.Label(text_frame,
                             text="Введите IP-адреса:",
                             font=("Arial", 11),
                             fg='#0a84ff',
                             bg='#182030')
        text_label.pack(anchor=tk.W, pady=(0, 5))

        # Текстовое поле с прокруткой
        text_container = tk.Frame(text_frame, bg='#182030')
        text_container.pack(fill=tk.BOTH, expand=True)

        # Вертикальная прокрутка
        scrollbar = tk.Scrollbar(text_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Текстовое поле
        self.text_input = tk.Text(text_container,
                                 font=("Courier New", 10),
                                 bg='#1a1a2e',
                                 fg='#ffffff',
                                 insertbackground='white',
                                 wrap=tk.NONE,
                                 yscrollcommand=scrollbar.set,
                                 height=8)
        self.text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar.config(command=self.text_input.yview)

        # Фрейм для кнопок
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(10, 0))

        # Контейнер для центрирования кнопок
        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        # Стиль кнопок для остальных
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 10,
            'pady': 8,
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Стиль кнопки длч Проверить данные
        button_style_1 = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 25,
            'pady': 8,
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка проверки
        self.check_button = self.create_hover_button(
            buttons_center_frame,
            text="Проверить данные",
            command=self.validate_data,
            **button_style_1
        )
        self.check_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка сохранения
        self.save_button = self.create_hover_button(
            buttons_center_frame,
            text="Сохранить",
            command=self.save_data,
            **button_style
        )
        self.save_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка отмены
        self.cancel_button = self.create_hover_button(
            buttons_center_frame,
            text="Назад",
            command=self.window.destroy,
            **button_style
        )
        self.cancel_button.pack(side=tk.LEFT)

        # Добавляем статусную строку для сообщений
        self.status_message = tk.Label(
            main_frame,
            text="",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.status_message.pack(pady=(10, 0))

        # Загружаем существующие данные
        self.load_existing_data()

        # Устанавливаем фокус на текстовое поле
        self.text_input.focus_set()

        return self.window

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg='#30d158')  # Зеленый
        elif warning:
            self.status_message.config(fg='#ff9500')  # Оранжевый
        elif error:
            self.status_message.config(fg='#ff3b30')  # Красный
        else:
            self.status_message.config(fg='#AAAAAA')  # Серый

        # Автоматически очищаем сообщение через 3 секунды
        if message:
            self.window.after(3000, lambda: self.status_message.config(text=""))

    def run(self):
        """Запускает окно добавления пользовательских IP-адресов"""
        self.create_window()
        self.window.wait_window()


class IpsetFilterWindow:
    """Окно настройки IPSet Filter"""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

        # Пути к файлам
        self.manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        self.ipset_all_file = os.path.join(self.manager_dir, "files", "lists", "ipset-all.txt")
        self.ipset_utils_file = os.path.join(self.manager_dir, "utils", "ipset-all.txt")

        # Переменная для радиокнопок
        self.filter_mode = tk.StringVar(value="none")

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def load_current_mode(self):
        """Загружает текущий режим фильтрации из файла"""
        try:
            if os.path.exists(self.ipset_all_file):
                with open(self.ipset_all_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()

                # Проверяем размер файла
                file_size = os.path.getsize(self.ipset_all_file)

                # Если файл пустой - режим any
                if file_size == 0 or not content:
                    self.filter_mode.set("any")
                    return

                # Проверяем, содержит ли файл только одну строку 203.0.113.113/32
                if content == "203.0.113.113/32":
                    self.filter_mode.set("none")
                    return

                # Если файл содержит данные из utils/ipset-all.txt
                # Загружаем данные из utils файла для сравнения
                if os.path.exists(self.ipset_utils_file):
                    with open(self.ipset_utils_file, 'r', encoding='utf-8') as f:
                        utils_content = f.read().strip()

                    # Сравниваем содержимое (игнорируем пустые строки)
                    content_lines = [line.strip() for line in content.split('\n') if line.strip()]
                    utils_lines = [line.strip() for line in utils_content.split('\n') if line.strip()]

                    # Если содержимое совпадает - режим loaded
                    if set(content_lines) == set(utils_lines):
                        self.filter_mode.set("loaded")
                        return

                # Если ни одно из условий не подошло, ставим loaded по умолчанию
                self.filter_mode.set("loaded")

        except Exception as e:
            print(f"Ошибка загрузки текущего режима: {e}")
            # По умолчанию ставим none
            self.filter_mode.set("none")

    def apply_filter(self):
        """Применяет выбранный режим фильтрации"""
        mode = self.filter_mode.get()

        try:
            # Показываем сообщение о применении изменений
            self.show_status_message("Применение изменений...", warning=False)
            self.window.update()

            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(self.ipset_all_file), exist_ok=True)

            if mode == "any":
                # Файл должен быть пустым
                with open(self.ipset_all_file, 'w', encoding='utf-8') as f:
                    f.write("")
                message = "Режим 'any' применен"

            elif mode == "loaded":
                # Копируем содержимое из utils/ipset-all.txt
                if os.path.exists(self.ipset_utils_file):
                    with open(self.ipset_utils_file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    with open(self.ipset_all_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                    message = "Режим 'loaded' применен"
                else:
                    show_info(self.window, "Ошибка",
                             f"Файл {self.ipset_utils_file} не найден")
                    return

            elif mode == "none":
                # Записываем только 203.0.113.113/32
                with open(self.ipset_all_file, 'w', encoding='utf-8') as f:
                    f.write("203.0.113.113/32")
                message = "Режим 'none' применен"

            # Показываем сообщение об успехе
            self.show_status_message(message, success=True)

        except Exception as e:
            error_msg = f"Ошибка применения режима: {e}"
            print(f"❌ {error_msg}")
            self.show_status_message(error_msg, error=True)

    def create_window(self):
        """Создает окно настройки IPSet Filter"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройка IPSet Filter")
        self.window.geometry("420x350")  # Увеличил высоту для статусной строки
        self.window.configure(bg='#182030')

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Настройка IPSet Filter",
                               font=("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.pack(anchor=tk.CENTER, pady=(0, 15))

        # Примечание
        note_frame = tk.Frame(main_frame, bg='#182030')
        note_frame.pack(fill=tk.X, pady=(0, 10))

        note_text = "Данная настройка полезна, если не работает ресурс, который без Zapret работает"
        note_label = tk.Label(note_frame,
                             text=note_text,
                             font=("Arial", 10),
                             fg='#ff9500',  # Оранжевый цвет для выделения
                             bg='#182030',
                             justify=tk.CENTER,
                             wraplength=400)
        note_label.pack()

        # Фрейм для радиокнопок
        radio_frame = tk.Frame(main_frame, bg='#182030')
        radio_frame.pack(fill=tk.X, pady=(0, 10))

        # Заголовок для радиокнопок
        radio_title = tk.Label(radio_frame,
                              text="Текущие статусы:",
                              font=("Arial", 11, "bold"),
                              fg='#0a84ff',
                              bg='#182030')
        radio_title.pack(anchor=tk.W, pady=(0, 10))

        # Радиокнопка none
        none_frame = tk.Frame(radio_frame, bg='#182030')
        none_frame.pack(fill=tk.X, pady=(0, 8))

        none_radio = tk.Radiobutton(none_frame,
                                   text="none",
                                   variable=self.filter_mode,
                                   value="none",
                                   font=("Arial", 11),
                                   fg='white',
                                   bg='#182030',
                                   selectcolor='#182030',
                                   activebackground='#182030',
                                   activeforeground='white',
                                   highlightthickness=0)
        none_radio.pack(side=tk.LEFT)

        none_desc = tk.Label(none_frame,
                            text="    - никакие айпи не попадают под проверку",
                            font=("Arial", 10),
                            fg='#8e8e93',
                            bg='#182030')
        none_desc.pack(side=tk.LEFT, padx=(10, 0))

        # Радиокнопка loaded
        loaded_frame = tk.Frame(radio_frame, bg='#182030')
        loaded_frame.pack(fill=tk.X, pady=(0, 8))

        loaded_radio = tk.Radiobutton(loaded_frame,
                                     text="loaded",
                                     variable=self.filter_mode,
                                     value="loaded",
                                     font=("Arial", 11),
                                     fg='white',
                                     bg='#182030',
                                     selectcolor='#182030',
                                     activebackground='#182030',
                                     activeforeground='white',
                                     highlightthickness=0)
        loaded_radio.pack(side=tk.LEFT)

        loaded_desc = tk.Label(loaded_frame,
                              text="- айпи проверяется на вхождение в список",
                              font=("Arial", 10),
                              fg='#8e8e93',
                              bg='#182030')
        loaded_desc.pack(side=tk.LEFT, padx=(10, 0))

        # Радиокнопка any
        any_frame = tk.Frame(radio_frame, bg='#182030')
        any_frame.pack(fill=tk.X, pady=(0, 8))

        any_radio = tk.Radiobutton(any_frame,
                                  text="any",
                                  variable=self.filter_mode,
                                  value="any",
                                  font=("Arial", 11),
                                  fg='white',
                                  bg='#182030',
                                  selectcolor='#182030',
                                  activebackground='#182030',
                                  activeforeground='white',
                                  highlightthickness=0)
        any_radio.pack(side=tk.LEFT)

        any_desc = tk.Label(any_frame,
                           text="       - любой айпи попадает под фильтр",
                           font=("Arial", 10),
                           fg='#8e8e93',
                           bg='#182030')
        any_desc.pack(side=tk.LEFT, padx=(10, 0))

        # Фрейм для кнопок
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(5, 0))

        # Контейнер для центрирования кнопок
        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 10,
            'pady': 8,
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка Применить
        self.apply_button = self.create_hover_button(
            buttons_center_frame,
            text="Применить",
            command=self.apply_filter,
            **button_style
        )
        self.apply_button.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка Назад
        self.back_button = self.create_hover_button(
            buttons_center_frame,
            text="Назад",
            command=self.window.destroy,
            **button_style
        )
        self.back_button.pack(side=tk.LEFT)

        # Статусная строка (как в главном окне)
        self.status_message = tk.Label(
            main_frame,
            text="",
            font=("Arial", 10),
            fg='#AAAAAA',
            bg='#182030',
            height=1
        )
        self.status_message.pack(fill=tk.X, pady=(15, 0))

        # Загружаем текущий режим
        self.load_current_mode()

        # Показываем текущий статус при загрузке
        current_mode = self.filter_mode.get()
        if current_mode == "none":
            self.show_status_message("Текущий режим: none (тестовый IP)", warning=False)
        elif current_mode == "loaded":
            self.show_status_message("Текущий режим: loaded (проверка по списку)", warning=False)
        elif current_mode == "any":
            self.show_status_message("Текущий режим: any (любой IP)", warning=False)

        return self.window

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg='#30d158')  # Зеленый
        elif warning:
            self.status_message.config(fg='#ff9500')  # Оранжевый
        elif error:
            self.status_message.config(fg='#ff3b30')  # Красный
        else:
            self.status_message.config(fg='#AAAAAA')  # Серый

        # Автоматически очищаем сообщение через 3 секунды (кроме ошибок)
        if message and not error:
            self.window.after(3000, lambda: self.status_message.config(text=""))

    def run(self):
        """Запускает окно настройки IPSet Filter"""
        self.create_window()
        self.window.wait_window()

class IpsetMainWindow:
    """Главное окно выбора настроек IPSet"""

    def __init__(self, parent):
        self.parent = parent
        self.window = None

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def open_filter_settings(self):
        """Открывает окно настройки IPSet Filter"""
        self.window.destroy()  # Закрываем текущее окно
        filter_window = IpsetFilterWindow(self.parent)
        filter_window.run()

    def open_custom_ips(self):
        """Открывает окно добавления пользовательских IP-адресов"""
        self.window.destroy()  # Закрываем текущее окно
        ip_window = IpsetSettingsWindow(self.parent)
        ip_window.run()

    def create_window(self):
        """Создает главное окно выбора настроек IPSet"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки IPSet")
        self.window.geometry("300x260")
        self.window.configure(bg='#182030')

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Настройки IPSet",
                               font=("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.pack(anchor=tk.CENTER, pady=(0, 30))

        # Фрейм для кнопок
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.BOTH, expand=True)

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 10,
            'pady': 8,
            'width': 32,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Кнопка "Настройка IPSet Filter"
        filter_button = self.create_hover_button(
            buttons_frame,
            text="Настройка IPSet Filter",
            command=self.open_filter_settings,
            **button_style
        )
        filter_button.pack(pady=(0, 15))

        # Кнопка "Добавление пользовательских IP-адресов" (в две строки)
        ip_button = self.create_hover_button(
            buttons_frame,
            text="Добавление пользовательских\nIP-адресов",
            command=self.open_custom_ips,
            **button_style
        )
        ip_button.pack(pady=(0, 15))

        # Кнопка "Назад"
        back_button_style = button_style.copy()
        back_button_style['width'] = 20
        back_button_style['font'] = ('Arial', 11)

        back_button = self.create_hover_button(
            buttons_frame,
            text="Назад",
            command=self.window.destroy,
            **back_button_style
        )
        back_button.pack(pady=(10, 0))

        return self.window

    def run(self):
        """Запускает главное окно выбора настроек IPSet"""
        self.create_window()
        self.window.wait_window()
