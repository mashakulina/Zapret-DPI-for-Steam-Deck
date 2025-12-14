#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
import re
from ui.components.custom_messagebox import show_info, show_error, ask_yesno, ask_yesnocancel

class HostlistSettingsWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None

        # Путь к файлам
        self.manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        self.other_file = os.path.join(self.manager_dir, "files", "lists", "other.txt")
        self.other2_file = os.path.join(self.manager_dir, "files", "lists", "other2.txt")
        self.ignore_file = os.path.join(self.manager_dir, "files", "lists", "ignore.txt")

        # Данные для предустановленных сервисов
        self.services = {
            "WhatsApp": [
                "api.whatsapp.com",
                "chat.whatsapp.com",
                "w1.web.whatsapp.com",
                "w2.web.whatsapp.com",
                "w3.web.whatsapp.com",
                "w4.web.whatsapp.com",
                "w5.web.whatsapp.com",
                "w6.web.whatsapp.com",
                "w7.web.whatsapp.com",
                "w8.web.whatsapp.com",
                "wa.me",
                "web.whatsapp.com",
                "whatsapp.com",
                "whatsapp.net",
                "www.whatsapp.com"
            ],
            "Rockstar/Epic Games": [
                "cdn1.unrealengine.com",
                "cdn2.unrealengine.com",
                "epicgames-download1.akamaized.net",
                "fortnite.com",
                "rockstargames.com"
            ]
        }

        # Переменные для чекбоксов
        self.whatsapp_var = tk.BooleanVar()
        self.rockstar_var = tk.BooleanVar()

        # Переменные для текстовых полей вкладок
        self.blocked_text_input = None
        self.unblocked_text_input = None

        # Переменная для хранения существующих доменов
        self.existing_domains = []

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def load_existing_data(self):
        """Загружает существующие данные из файлов"""
        # Загружаем пользовательские домены из other2.txt (заблокированные)
        try:
            if os.path.exists(self.other2_file):
                with open(self.other2_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.blocked_text_input:
                        self.blocked_text_input.delete("1.0", tk.END)
                        self.blocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла other2.txt: {e}")

        # Загружаем пользовательские домены из ignore.txt (незаблокированные)
        try:
            if os.path.exists(self.ignore_file):
                with open(self.ignore_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.unblocked_text_input:
                        self.unblocked_text_input.delete("1.0", tk.END)
                        self.unblocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла ignore.txt: {e}")

        # Загружаем существующие домены из other.txt для проверки выбранных сервисов
        try:
            if os.path.exists(self.other_file):
                with open(self.other_file, 'r', encoding='utf-8') as f:
                    self.existing_domains = [line.strip() for line in f if line.strip()]

                    # Проверяем наличие доменов WhatsApp
                    whatsapp_selected = False
                    for domain in self.services["WhatsApp"]:
                        if domain in self.existing_domains:
                            whatsapp_selected = True
                            break
                    self.whatsapp_var.set(whatsapp_selected)

                    # Проверяем наличие доменов Rockstar/Epic Games
                    rockstar_selected = False
                    for domain in self.services["Rockstar/Epic Games"]:
                        if domain in self.existing_domains:
                            rockstar_selected = True
                            break
                    self.rockstar_var.set(rockstar_selected)

        except Exception as e:
            print(f"Ошибка загрузки файла other.txt: {e}")
            self.existing_domains = []

    def validate_domain(self, domain_str):
        """Проверяет корректность доменного имени"""

        # Комментарий
        if domain_str.strip().startswith('#'):
            return True, ""

        # Проверка на пустую строку
        if not domain_str.strip():
            return True, ""

        # Допустимые символы в доменном имени
        domain_pattern = r'^(\*\.)?([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z]{2,}$'

        if re.match(domain_pattern, domain_str):
            # Дополнительные проверки
            if len(domain_str) > 253:  # Максимальная длина домена
                return False, "Слишком длинное доменное имя"

            parts = domain_str.split('.')
            for part in parts:
                if part.startswith('-') or part.endswith('-'):
                    return False, "Часть домена не может начинаться или заканчиваться дефисом"
                if len(part) > 63:
                    return False, "Часть домена слишком длинная"

            return True, ""

        else:
            return False, "Некорректный формат домена"

    def save_custom_domains(self, text_widget, file_path, domain_type):
        """Сохраняет пользовательские домены в указанный файл"""
        try:
            custom_domains = text_widget.get("1.0", tk.END).strip()

            # Проверяем пользовательские домены перед сохранением
            if custom_domains:
                lines = custom_domains.split('\n')
                error_lines = []

                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:  # Пропускаем пустые строки
                        continue

                    # Пропускаем комментарии без проверки
                    if line.startswith('#'):
                        continue

                    is_valid, error_msg = self.validate_domain(line)
                    if not is_valid:
                        error_lines.append(f"Строка {i}: {line} - {error_msg}")

                if error_lines:
                    error_text = "\n".join(error_lines)
                    show_info(self.window, "Ошибка в данных",
                            f"Обнаружены ошибки в доменах ({domain_type}). Данные не сохранены:\n\n{error_text}")
                    return False

            # Если проверка прошла или файл пустой, продолжаем сохранение

            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(custom_domains)

            # Считаем пользовательские домены (без комментариев)
            custom_count = 0
            if custom_domains:
                custom_lines = custom_domains.split('\n')
                for line in custom_lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        custom_count += 1

            return custom_count

        except Exception as e:
            show_info(self.window, "Ошибка", f"Не удалось сохранить файл {file_path}: {e}")
            return None

    def save_data(self):
        """Сохраняет все данные"""
        try:
            # Сохраняем заблокированные домены
            blocked_count = self.save_custom_domains(
                self.blocked_text_input,
                self.other2_file,
                "Заблокированные"
            )
            if blocked_count is None:  # Если была ошибка
                return

            # Сохраняем незаблокированные домены
            unblocked_count = self.save_custom_domains(
                self.unblocked_text_input,
                self.ignore_file,
                "Незаблокированные"
            )
            if unblocked_count is None:  # Если была ошибка
                return

            # Обрабатываем other.txt: сохраняем существующие данные + добавляем/удаляем выбранные сервисы
            # Загружаем текущие домены из файла (если он существует)
            current_domains = set()
            if os.path.exists(self.other_file):
                with open(self.other_file, 'r', encoding='utf-8') as f:
                    current_domains = set([line.strip() for line in f if line.strip()])
            else:
                # Если файла нет, используем существующие домены из загрузки
                current_domains = set(self.existing_domains)

            # Удаляем все домены сервисов (чтобы потом добавить только выбранные)
            all_service_domains = set(self.services["WhatsApp"] + self.services["Rockstar/Epic Games"])
            current_domains = current_domains - all_service_domains

            # Добавляем домены выбранных сервисов
            if self.whatsapp_var.get():
                current_domains.update(self.services["WhatsApp"])

            if self.rockstar_var.get():
                current_domains.update(self.services["Rockstar/Epic Games"])

            # Сортируем и сохраняем в файл other.txt
            sorted_domains = sorted(current_domains)
            os.makedirs(os.path.dirname(self.other_file), exist_ok=True)
            with open(self.other_file, 'w', encoding='utf-8') as f:
                for domain in sorted_domains:
                    f.write(f"{domain}\n")

            # Показываем статистику
            selected_services = []
            if self.whatsapp_var.get():
                selected_services.append("WhatsApp")
            if self.rockstar_var.get():
                selected_services.append("Rockstar/Epic Games")

            services_text = ", ".join(selected_services) if selected_services else "ни одного сервиса"

            show_info(self.window, "Сохранение",
                     f"Данные успешно сохранены!\n\n"
                     f"Выбранные сервисы: {services_text}\n"
                     f"Всего доменов в other.txt: {len(sorted_domains)}\n"
                     f"Заблокированные домены: {blocked_count} (сохранено в other2.txt)\n"
                     f"Незаблокированные домены: {unblocked_count} (сохранено в ignore.txt)")

        except Exception as e:
            show_info(self.window, "Ошибка", f"Не удалось сохранить файлы: {e}")

    def create_text_tab(self, parent, tab_name, description, examples, file_name):
        """Создает вкладку с текстовым полем для ввода доменов"""
        frame = tk.Frame(parent, bg='#182030')

        # ЗАКОММЕНТИРОВАНО: Убрал заголовок вкладки
        # title = tk.Label(frame,
        #                 text=tab_name,
        #                 font=("Arial", 12, "bold"),
        #                 fg='#0a84ff',
        #                 bg='#182030')
        # title.pack(anchor=tk.W, pady=(0, 10))

        # Описание
        info = tk.Label(frame,
                    text=description,
                    font=("Arial", 10),
                    fg='#8e8e93',
                    bg='#182030',
                    justify=tk.LEFT,
                    wraplength=400)
        info.pack(anchor=tk.W, pady=(0, 15))

        # Примеры доменов
        examples_frame = tk.Frame(frame, bg='#182030')
        examples_frame.pack(fill=tk.X, pady=(0, 10))

        examples_label = tk.Label(examples_frame,
                                text="Примеры доменов:",
                                font=("Arial", 10, "italic"),
                                fg='#8e8e93',
                                bg='#182030')
        examples_label.pack(anchor=tk.W)

        examples_text = tk.Label(examples_frame,
                                text=examples,
                                font=("Courier New", 9),
                                fg='#8e8e93',
                                bg='#182030',
                                justify=tk.LEFT)
        examples_text.pack(anchor=tk.W, padx=(10, 0))

        # Фрейм для текстового поля
        text_frame = tk.Frame(frame, bg='#182030')
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Метка для текстового поля
        text_label = tk.Label(text_frame,
                            text="Введите домены:",
                            font=("Arial", 11),
                            fg='#0a84ff',
                            bg='#182030')
        text_label.pack(anchor=tk.W, pady=(0, 5))

        # Текстовое поле с прокруткой
        text_container = tk.Frame(text_frame, bg='#182030')
        text_container.pack(fill=tk.BOTH, expand=True)

        # Текстовое поле
        text_input = tk.Text(text_container,
                            font=("Courier New", 10),
                            bg='#15354D',
                            fg='#ffffff',
                            insertbackground='white',
                            wrap=tk.NONE,
                            height=6)
        text_input.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        return frame, text_input
    def create_window(self):
        """Создает окно настроек HOSTLIST"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки фильтрации доменов")
        self.window.geometry("710x650")
        self.window.configure(bg='#182030')
        self.window.resizable(True, True)

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Настройки фильтрации доменов",
                               font=("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.pack(anchor=tk.CENTER, pady=(0, 15))

        # Фрейм с двумя колонками
        columns_frame = tk.Frame(main_frame, bg='#182030')
        columns_frame.pack(fill=tk.BOTH, expand=True)

        # Левая колонка (30% ширины)
        left_frame = tk.Frame(columns_frame, bg='#182030', width=260)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=False)
        left_frame.pack_propagate(False)

        # Правая колонка (70% ширины)
        right_frame = tk.Frame(columns_frame, bg='#182030')
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(20, 0))

        # ========== ЛЕВАЯ КОЛОНКА ==========
        # Инструкция для пользовательских доменов
        instruction_title = tk.Label(left_frame,
                                    text="Пользовательские домены",
                                    font=("Arial", 12, "bold"),
                                    fg='#0a84ff',
                                    bg='#182030')
        instruction_title.pack(anchor=tk.W, pady=(0, 10))

        instruction_text = tk.Label(left_frame,
                                  text="Если с Zapret не работает заблокированный сайт, то выберите вкладку 'Заблокированный' и внесите домен в список\n\n"
                                       "Если с Zapret не работает незаблокированный сайт, то выберите вкладку 'Незаблокированный' и внесите домен в список",
                                  font=("Arial", 10),
                                  fg='#8e8e93',
                                  bg='#182030',
                                  justify=tk.LEFT,
                                  wraplength=240)
        instruction_text.pack(anchor=tk.W)


        left_title = tk.Label(left_frame,
                             text="Предустановленные сервисы",
                             font=("Arial", 12, "bold"),
                             fg='#0a84ff',
                             bg='#182030')
        left_title.pack(anchor=tk.W, pady=(20, 10))

        left_info = tk.Label(left_frame,
                           text="Выбрать предустановленные сервисы для фильтрации\n"
                                "Домены сервисов будут прописаны в файл other.txt",
                           font=("Arial", 10),
                           fg='#8e8e93',
                           bg='#182030',
                           justify=tk.LEFT,
                           wraplength=220)
        left_info.pack(anchor=tk.W, pady=(0, 20))

        # Фрейм для чекбоксов
        checkboxes_frame = tk.Frame(left_frame, bg='#182030')
        checkboxes_frame.pack(fill=tk.X, pady=(0, 20))

        # Чекбокс WhatsApp
        whatsapp_check = tk.Checkbutton(checkboxes_frame,
                                       text="WhatsApp",
                                       variable=self.whatsapp_var,
                                       font=("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        whatsapp_check.pack(anchor=tk.W, pady=(0, 10))

        # Чекбокс Rockstar/Epic Games
        rockstar_check = tk.Checkbutton(checkboxes_frame,
                                       text="Rockstar/Epic Games",
                                       variable=self.rockstar_var,
                                       font=("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        rockstar_check.pack(anchor=tk.W, pady=(0, 10))


        # ========== ПРАВАЯ КОЛОНКА ==========
        # Создаем Notebook для вкладок
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        # Стилизация Notebook
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background='#182030', borderwidth=0)
        style.configure('TNotebook.Tab',
                       background='#1a1a2e',
                       foreground='#8e8e93',
                       padding=[10, 5],
                       font=('Arial', 10))
        style.map('TNotebook.Tab',
                 background=[('selected', '#0a84ff')],
                 foreground=[('selected', 'white')])

        # Вкладка "Заблокированный"
        blocked_frame, self.blocked_text_input = self.create_text_tab(
            notebook,
            "Заблокированный",
            "Пользовательские домены сохраняются в файл other2.txt.\n"
            "Вводить домены нужно по одному на строку.\n"
            "Чтобы оставить комментарий, поставьте знак '#' в начале строки",
            "example.com\n*.example.com\nsubdomain.example.com",
            "other2.txt"
        )
        notebook.add(blocked_frame, text="Заблокированный")

        # Вкладка "Незаблокированный"
        unblocked_frame, self.unblocked_text_input = self.create_text_tab(
            notebook,
            "Незаблокированный",
            "Пользовательские домены сохраняются в файл ignore.txt.\n"
            "Вводить домены нужно по одному на строку.\n"
            "Чтобы оставить комментарий, поставьте знак '#' в начале строки",
            "example.com\n*.example.com\nsubdomain.example.com",
            "ignore.txt"
        )
        notebook.add(unblocked_frame, text="Незаблокированный")

        # ========== КНОПКИ ВНИЗУ ==========
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(20, 0))

        # Контейнер для центрирования кнопок
        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        # Стиль кнопок
        button_style = {
            'font': ('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': 25,
            'pady': 10,
            'width': 15,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

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

        # Загружаем существующие данные
        self.load_existing_data()

        # Устанавливаем фокус на первую вкладку
        self.blocked_text_input.focus_set()

        return self.window

    def run(self):
        """Запускает окно настроек HOSTLIST"""
        self.create_window()
        self.window.wait_window()
