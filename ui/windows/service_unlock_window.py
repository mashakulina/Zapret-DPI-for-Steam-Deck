#!/usr/bin/env python3
import tkinter as tk
import os
import subprocess
from ui.components.custom_messagebox import show_info, show_error
from core.service_data import PROXY_DOMAINS
from ui.components.button_styler import create_hover_button
from ui.windows.sudo_password_window import SudoPasswordWindow

class ServiceUnlockWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.hosts_file = "/etc/hosts"

        # Переменные для чекбоксов сервисов
        self.service_vars = {}

        # Группируем домены по сервисам
        self.services_groups = self.group_domains_by_service()

        # Загружаем существующие записи
        self.existing_entries = self.load_existing_entries()

    def group_domains_by_service(self):
        """Группирует домены по сервисам"""
        services = {
            "ChatGPT / OpenAI": [],
            "Google AI (Gemini)": [],
            "Microsoft Copilot": [],
            "Социальные сети": [],
            "Spotify": [],
            "GitHub": [],
            "Разработка": [],
            "Rutracker":[],
            "Другие сервисы": []
        }

        for domain in PROXY_DOMAINS.keys():
            domain_lower = domain.lower()
            if any(x in domain_lower for x in ['openai', 'chatgpt', 'oai']):
                services["ChatGPT / OpenAI"].append(domain)
            elif any(x in domain_lower for x in ['gemini', 'google', 'generativelanguage']):
                services["Google AI (Gemini)"].append(domain)
            elif any(x in domain_lower for x in ['microsoft', 'bing', 'copilot', 'xbox']):
                services["Microsoft Copilot"].append(domain)
            elif any(x in domain_lower for x in ['facebook', 'instagram', 'tiktok', 'truthsocial', 'threads']):
                services["Социальные сети"].append(domain)
            elif 'spotify' in domain_lower:
                services["Spotify"].append(domain)
            elif any(x in domain_lower for x in ['github', 'jetbrains']):
                services["GitHub"].append(domain)
            elif any(x in domain_lower for x in ['codeium', 'elevenlabs', 'nvidia', 'intel', 'dell', 'autodesk', 'notion', 'protonmail', 'deeplearning.ai']):
                services["Разработка"].append(domain)
            elif any(x in domain_lower for x in ['rutracker']):
                services["Rutracker"].append(domain)
            else:
                services["Другие сервисы"].append(domain)

        # Удаляем пустые группы
        services = {k: v for k, v in services.items() if v}

        return services

    def load_existing_entries(self):
        """Загружает существующие записи из файла /etc/hosts"""
        existing_entries = set()
        try:
            if os.path.exists(self.hosts_file):
                with open(self.hosts_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            parts = line.split()
                            if len(parts) >= 2:
                                domain = parts[1]
                                if domain in PROXY_DOMAINS:
                                    existing_entries.add(domain)
        except Exception as e:
            print(f"Ошибка чтения файла hosts: {e}")

        return existing_entries

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        return create_hover_button(parent, text, command, **kwargs)

    def update_service_count_label(self, service_name, count_label):
        """Обновляет метку с количеством выбранных доменов"""
        service_info = self.service_vars.get(service_name)
        if service_info:
            selected_count = sum(1 for var in service_info['domain_vars'].values() if var.get())
            total_count = len(service_info['domains'])
            count_label.config(text=f"({selected_count}/{total_count})")

            # Обновляем состояние чекбокса сервиса
            if selected_count == 0:
                service_info['var'].set(False)
            elif selected_count == total_count:
                service_info['var'].set(True)
            else:
                # Частичный выбор - устанавливаем чекбокс в неопределенное состояние
                # В tkinter нет встроенного состояния "частично", но мы можем использовать другое отображение
                pass

    def create_service_frame(self, parent, service_name, domains):
        """Создает фрейм для сервиса с чекбоксами"""
        frame = tk.Frame(parent, bg='#182030', padx=10, pady=5)

        # Подсчитываем сколько доменов уже выбрано
        selected_count = sum(1 for domain in domains if domain in self.existing_entries)
        total_count = len(domains)

        # Переменная для чекбокса сервиса
        service_var = tk.BooleanVar(value=selected_count == total_count)
        self.service_vars[service_name] = {
            'var': service_var,
            'domains': domains,
            'domain_vars': {}
        }

        # Фрейм для заголовка и чекбокса сервиса
        header_frame = tk.Frame(frame, bg='#182030')
        header_frame.pack(fill=tk.X, pady=(0, 5))

        # Фрейм для доменов (изначально скрыт)
        domains_frame = tk.Frame(frame, bg='#182030')

        # Кнопка для раскрытия/скрытия доменов (ПЕРЕД ЧЕКБОКСОМ) - уменьшенная и без подсветки
        toggle_button = tk.Label(
            header_frame,
            text="▼",
            font=("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            cursor='hand2',
            width=1  # Фиксированная ширина
        )
        # Обработка кликов по метке
        toggle_button.bind("<Button-1>", lambda e, f=domains_frame, b=toggle_button: self.toggle_domains_frame(f, b))
        toggle_button.pack(side=tk.LEFT, padx=(0, 8))

        # Чекбокс сервиса
        service_check = tk.Checkbutton(
            header_frame,
            text=service_name,
            variable=service_var,
            font=("Arial", 11, "bold"),
            fg='#0a84ff',
            bg='#182030',
            selectcolor='#182030',
            activebackground='#182030',
            activeforeground='#0a84ff',
            highlightthickness=0,
            command=lambda: self.toggle_service_domains(service_name),
            cursor='hand2'
        )
        service_check.pack(side=tk.LEFT)

        # Метка с количеством доменов
        count_label = tk.Label(
            header_frame,
            text=f"({selected_count}/{total_count})",
            font=("Arial", 9),
            fg='#8e8e93',
            bg='#182030'
        )
        count_label.pack(side=tk.LEFT, padx=(5, 0))

        # Теперь создаем домены
        for domain in sorted(domains):
            # Переменная для чекбокса домена
            domain_var = tk.BooleanVar(value=domain in self.existing_entries)
            self.service_vars[service_name]['domain_vars'][domain] = domain_var

            domain_frame = tk.Frame(domains_frame, bg='#182030')
            domain_frame.pack(fill=tk.X, pady=1)

            # Чекбокс домена
            domain_check = tk.Checkbutton(
                domain_frame,
                text=domain,
                variable=domain_var,
                font=("Courier New", 9),
                fg='white',
                bg='#182030',
                selectcolor='#182030',
                activebackground='#182030',
                activeforeground='white',
                highlightthickness=0,
                cursor='hand2',
                command=lambda sn=service_name, cl=count_label: self.update_service_count_label(sn, cl)
            )
            domain_check.pack(side=tk.LEFT, anchor='w')

        return frame

    def toggle_domains_frame(self, domains_frame, toggle_button):
        """Раскрывает или скрывает фрейм с доменами"""
        if domains_frame.winfo_ismapped():
            domains_frame.pack_forget()
            toggle_button.config(text='▼')
        else:
            domains_frame.pack(fill=tk.X, padx=(30, 0), pady=(5, 0))
            toggle_button.config(text='▲')

    def toggle_service_domains(self, service_name):
        """Включает/выключает все домены сервиса"""
        service_info = self.service_vars.get(service_name)
        if service_info:
            state = service_info['var'].get()
            for domain_var in service_info['domain_vars'].values():
                domain_var.set(state)

            # Находим и обновляем метку с количеством
            for widget in self.window.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if hasattr(child, 'winfo_children'):
                            for frame in child.winfo_children():
                                if hasattr(frame, 'winfo_children'):
                                    for header_frame in frame.winfo_children():
                                        if isinstance(header_frame, tk.Frame):
                                            for w in header_frame.winfo_children():
                                                if isinstance(w, tk.Label) and '(' in w.cget('text'):
                                                    # Обновляем все метки с количеством
                                                    self.update_all_count_labels()

    def update_all_count_labels(self):
        """Обновляет все метки с количеством выбранных доменов"""
        for service_name, service_info in self.service_vars.items():
            selected_count = sum(1 for var in service_info['domain_vars'].values() if var.get())
            total_count = len(service_info['domains'])

            # Находим метку для этого сервиса и обновляем ее
            for widget in self.window.winfo_children():
                if hasattr(widget, 'winfo_children'):
                    for child in widget.winfo_children():
                        if hasattr(child, 'winfo_children'):
                            for frame in child.winfo_children():
                                if hasattr(frame, 'winfo_children'):
                                    for header_frame in frame.winfo_children():
                                        if isinstance(header_frame, tk.Frame):
                                            for w in header_frame.winfo_children():
                                                if isinstance(w, tk.Label) and service_name in header_frame.winfo_children()[0].cget('text'):
                                                    w.config(text=f"({selected_count}/{total_count})")

    def select_all(self):
        """Выбирает все сервисы и домены"""
        for service_name, service_info in self.service_vars.items():
            service_info['var'].set(True)
            for domain_var in service_info['domain_vars'].values():
                domain_var.set(True)
        self.update_all_count_labels()

    def deselect_all(self):
        """Снимает выделение со всех сервисов и доменов"""
        for service_name, service_info in self.service_vars.items():
            service_info['var'].set(False)
            for domain_var in service_info['domain_vars'].values():
                domain_var.set(False)
        self.update_all_count_labels()

    def save_to_hosts(self):
        """Сохраняет выбранные сервисы в файл /etc/hosts"""
        try:
            # Сначала собираем выбранные домены
            selected_entries = []
            selected_domains = set()

            for service_name, service_info in self.service_vars.items():
                for domain, domain_var in service_info['domain_vars'].items():
                    if domain_var.get():  # Только если чекбокс установлен
                        ip = PROXY_DOMAINS.get(domain)
                        if ip:
                            selected_entries.append(f"{ip} {domain}")
                            selected_domains.add(domain)

            # Всегда показываем окно ввода пароля (даже если ничего не выбрано)
            # Потому что нам нужно обновить файл hosts

            def on_password_valid(password):
                # Пароль валидный, сохраняем файл
                self.save_hosts_with_password(password, selected_entries, selected_domains)

            # Создаем окно с callback-функцией
            password_window = SudoPasswordWindow(self.window, on_password_valid=on_password_valid)
            # Запускаем окно (оно само вызовет on_password_valid при успешном вводе)
            password_window.run()

        except Exception as e:
            show_error(self.window, "Ошибка", f"Не удалось сохранить файл hosts: {e}")

    def save_hosts_with_password(self, password, selected_entries, selected_domains):
        """Сохраняет файл hosts с использованием введенного пароля"""
        try:
            # Читаем существующий файл hosts с sudo
            import subprocess
            import tempfile

            # 1. Читаем текущий /etc/hosts
            read_process = subprocess.Popen(
                ['sudo', '-S', 'cat', self.hosts_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            stdout, stderr = read_process.communicate(input=password + '\n')

            if read_process.returncode != 0:
                show_error(self.window, "Ошибка", f"Не удалось прочитать файл hosts:\n{stderr}")
                return

            existing_lines = stdout.splitlines(keepends=True) if stdout else []

            # 2. Обрабатываем содержимое - УДАЛЯЕМ ВСЕ наши старые записи
            new_lines = []
            service_domains = set(PROXY_DOMAINS.keys())

            # Флаг, чтобы знать, был ли наш раздел в файле
            our_section_exists = False
            section_start_index = -1

            for line in existing_lines:
                # Проверяем, не начинается ли строка с комментария нашего раздела
                line_stripped = line.strip()

                if "Разблокировка сервисов (добавлено Zapret_DPI_Manager)" in line:
                    our_section_exists = True
                    section_start_index = len(new_lines)
                    # Оставляем заголовок раздела, но будем заменять содержимое
                    new_lines.append("# Разблокировка сервисов (добавлено Zapret_DPI_Manager)\n")
                    continue

                # Если это наша запись (домен из PROXY_DOMAINS), пропускаем ее
                if line_stripped and not line_stripped.startswith('#'):
                    parts = line_stripped.split()
                    if len(parts) >= 2:
                        domain = parts[1]
                        if domain in service_domains:
                            continue  # Пропускаем эту строку

                # Сохраняем все остальные строки
                new_lines.append(line)

            # 3. Если у нас есть выбранные записи, добавляем их
            if selected_entries:
                if not our_section_exists:
                    # Добавляем новый раздел в конец
                    new_lines.append("\n# Разблокировка сервисов (добавлено Zapret_DPI_Manager)\n")
                    for entry in sorted(selected_entries):
                        new_lines.append(f"{entry}\n")
                else:
                    # Заменяем содержимое существующего раздела
                    # Находим где заканчивается наш раздел (первые не-комментарии после заголовка)
                    after_section_index = section_start_index + 1
                    while (after_section_index < len(new_lines) and
                        new_lines[after_section_index].strip() and
                        not new_lines[after_section_index].startswith('#')):
                        # Удаляем старые записи из раздела
                        new_lines.pop(after_section_index)

                    # Вставляем новые записи
                    for entry in sorted(selected_entries):
                        new_lines.insert(after_section_index, f"{entry}\n")
                        after_section_index += 1
            else:
                # Если ничего не выбрано, удаляем весь наш раздел
                if our_section_exists:
                    # Удаляем заголовок раздела
                    new_lines.pop(section_start_index)
                    # Удаляем пустые строки после раздела, если есть
                    if section_start_index < len(new_lines) and not new_lines[section_start_index].strip():
                        new_lines.pop(section_start_index)

            # 4. Создаем временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as temp_file:
                temp_file.writelines(new_lines)
                temp_path = temp_file.name

            try:
                # 5. Записываем обратно в /etc/hosts
                write_process = subprocess.Popen(
                    ['sudo', '-S', 'cp', temp_path, self.hosts_file],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                stdout, stderr = write_process.communicate(input=password + '\n')

                if write_process.returncode == 0:
                    # Обновляем кеш существующих записей
                    self.existing_entries = selected_domains

                    # Показываем статистику
                    total_selected = len(selected_entries)

                    if total_selected > 0:
                        services_selected = sum(1 for s in self.service_vars.values()
                                            if any(var.get() for var in s['domain_vars'].values()))

                        show_info(self.window, "Сохранение",
                                f"Данные успешно сохранены в {self.hosts_file}\n\n"
                                f"Добавлено записей: {total_selected}\n"
                                f"Выбранных сервисов: {services_selected}")
                    else:
                        show_info(self.window, "Сохранение",
                                f"Все записи разблокировки удалены из {self.hosts_file}")

                    # Обновляем системный DNS кеш
                    self.update_dns_cache()
                else:
                    show_error(self.window, "Ошибка", f"Не удалось записать файл hosts:\n{stderr}")

            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_path)
                except:
                    pass

        except Exception as e:
            show_error(self.window, "Ошибка", f"Ошибка при сохранении: {e}")

    def update_dns_cache(self):
        """Обновляет DNS кеш системы"""
        try:
            # Для Linux систем (systemd-resolved)
            if os.path.exists('/run/systemd/system'):
                result = subprocess.run(['systemd-resolve', '--flush-caches'],
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    show_info(self.window, "Информация",
                             "DNS кеш обновлен.\nИзменения вступят в силу немедленно.")
                    return

            # Для систем с nscd
            if os.path.exists('/etc/nscd.conf'):
                result = subprocess.run(['nscd', '-i', 'hosts'],
                                     capture_output=True, text=True)
                if result.returncode == 0:
                    show_info(self.window, "Информация",
                             "DNS кеш обновлен.\nИзменения вступят в силу немедленно.")
                    return

            # Если не удалось обновить кеш
            show_info(self.window, "Информация",
                     "Файл hosts обновлен.\nДля применения изменений может потребоваться перезагрузка или очистка DNS кеша.")

        except Exception as e:
            print(f"Ошибка обновления DNS кеша: {e}")
            show_info(self.window, "Информация",
                     "Файл hosts обновлен.\nДля применения изменений может потребоваться перезагрузка.")

    def create_window(self):
        """Создает окно разблокировки сервисов"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Разблокировка сервисов")
        self.window.geometry("460x625")
        self.window.configure(bg='#182030')
        # ЭТИ СТРОКИ ДЛЯ УДАЛЕНИЯ ОБВОДКИ
        try:
            self.window.wm_overrideredirect(False)
            self.window.attributes('-toolwindow', True)
        except:
            pass
        self.window.resizable(True, True)

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Разблокировка сервисов",
                               font=("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.pack(anchor=tk.CENTER, pady=(0, 15))

        # Описание
        desc_label = tk.Label(main_frame,
                             text="Выберите сервисы для разблокировки. Записи будут добавлены в файл /etc/hosts\n"
                                  "Разверните группу, чтобы увидеть отдельные домены",
                             font=("Arial", 10),
                             fg='#8e8e93',
                             bg='#182030',
                             justify=tk.LEFT,
                             wraplength=350)
        desc_label.pack(anchor=tk.W, pady=(0, 15))

        # Фрейм с прокруткой для сервисов
        canvas_frame = tk.Frame(main_frame, bg='#182030')
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))

        # Создаем Canvas и Scrollbar
        canvas = tk.Canvas(canvas_frame, bg='#182030', highlightthickness=0)
        scrollbar = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='#182030')

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Функция для обработки колесика мыши
        def on_mouse_wheel(event):
            # Для Windows и macOS
            if event.num == 5 or event.delta == -120:
                canvas.yview_scroll(1, "units")
            if event.num == 4 or event.delta == 120:
                canvas.yview_scroll(-1, "units")

        # Привязываем колесико мыши
        canvas.bind_all("<MouseWheel>", on_mouse_wheel)
        canvas.bind_all("<Button-4>", on_mouse_wheel)
        canvas.bind_all("<Button-5>", on_mouse_wheel)
        scrollable_frame.bind("<MouseWheel>", on_mouse_wheel)
        scrollable_frame.bind("<Button-4>", on_mouse_wheel)
        scrollable_frame.bind("<Button-5>", on_mouse_wheel)

        # Размещаем Canvas и Scrollbar
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        # scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Создаем фреймы для сервисов
        for service_name, domains in self.services_groups.items():
            service_frame = self.create_service_frame(scrollable_frame, service_name, domains)
            service_frame.pack(fill=tk.X, pady=(0, 0))

        # ========== КНОПКИ ВНИЗУ ==========
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.pack(fill=tk.X, pady=(0, 0))

        # Контейнер для центрирования кнопок
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
            'width': 12,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        # Первая строка кнопок
        row1_frame = tk.Frame(buttons_center_frame, bg='#182030')
        row1_frame.pack(pady=(0, 10))

        # Кнопка "Выбрать все"
        select_all_btn = self.create_hover_button(
            row1_frame,
            text="Выбрать все",
            command=self.select_all,
            **button_style
        )
        select_all_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка "Снять выделение"
        deselect_all_btn = self.create_hover_button(
            row1_frame,
            text="Снять выделение",
            command=self.deselect_all,
            **button_style
        )
        deselect_all_btn.pack(side=tk.LEFT)

        # Вторая строка кнопок
        row2_frame = tk.Frame(buttons_center_frame, bg='#182030')
        row2_frame.pack()

        # Кнопка "Сохранить"
        save_btn = self.create_hover_button(
            row2_frame,
            text="Сохранить",
            command=self.save_to_hosts,
            **button_style
        )
        save_btn.pack(side=tk.LEFT, padx=(0, 15))

        # Кнопка "Назад"
        back_btn = self.create_hover_button(
            row2_frame,
            text="Назад",
            command=self.window.destroy,
            **button_style
        )
        back_btn.pack(side=tk.LEFT)

        return self.window

    def run(self):
        """Запускает окно разблокировки сервисов"""
        self.create_window()
        self.window.wait_window()
