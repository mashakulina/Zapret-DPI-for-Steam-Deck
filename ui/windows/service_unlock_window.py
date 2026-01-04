#!/usr/bin/env python3
import tkinter as tk
import os
import subprocess
from ui.components.custom_messagebox import show_info, show_error
from core.service_data import SERVICE_CATEGORIES, PROXY_DOMAINS
from ui.components.button_styler import create_hover_button
from ui.windows.sudo_password_window import SudoPasswordWindow

class ServiceUnlockWindow:
    def __init__(self, parent):
        self.parent = parent
        self.window = None
        self.hosts_file = "/etc/hosts"

        # Переменные для чекбоксов сервисов
        self.service_vars = {}

        # Группируем домены по основным категориям
        self.main_categories = self.group_domains_by_main_category()

        # Создаем плоский словарь всех доменов с IP для быстрого доступа
        self.all_domains = self.create_all_domains_dict()

        # Загружаем существующие записи
        self.existing_entries = self.load_existing_entries()


    def create_all_domains_dict(self):
        """Создает плоский словарь всех доменов с IP"""
        all_domains = {}

        for category_name, category_content in SERVICE_CATEGORIES.items():
            if isinstance(category_content, dict):
                # Если это категория с подкатегориями (chatgpt, gemini и т.д.)
                if category_name != "other":
                    # Для обычных категорий (chatgpt, gemini, claude и т.д.)
                    all_domains.update(category_content)
                else:
                    # Для категории "other" - она уже плоский словарь
                    all_domains.update(category_content)

        return all_domains

    def group_domains_by_main_category(self):
        """Группирует домены по основным категориям"""
        main_categories = {
            "Искусственный интеллект": {
                "ChatGPT": SERVICE_CATEGORIES["chatgpt"],
                "Gemini": SERVICE_CATEGORIES["gemini"],
                "Claude": SERVICE_CATEGORIES["claude"],
                "Copilot": SERVICE_CATEGORIES["copilot"],
                "Grok": SERVICE_CATEGORIES["grok"],
            },
            "Соцсети": {
                "Instagram": SERVICE_CATEGORIES["instagram"],
                "Facebook": SERVICE_CATEGORIES["facebook"],
                "TikTok": SERVICE_CATEGORIES["tiktok"],
                "Twitch": SERVICE_CATEGORIES["twitch"],
            },
            "Музыка": {
                "Spotify": SERVICE_CATEGORIES["spotify"],
                "SoundCloud": SERVICE_CATEGORIES["soundcloud"],
            },
            "Торрент": {
                "Rutracker": SERVICE_CATEGORIES["rutracker"],
                "Rutor": SERVICE_CATEGORIES["rutor"],
            },
            "Discord": SERVICE_CATEGORIES["discord"],
            "Другое": SERVICE_CATEGORIES["other"]
        }
        return main_categories

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
                                if domain in self.all_domains:  # Используем self.all_domains
                                    existing_entries.add(domain)
        except Exception as e:
            print(f"Ошибка чтения файла hosts: {e}")
        return existing_entries

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        return create_hover_button(parent, text, command, **kwargs)

    def create_main_category_frame(self, parent, category_name, category_content):
        """Создает фрейм для основной категории"""
        frame = tk.Frame(parent, bg='#182030', padx=10, pady=0)

        # Проверяем, является ли категория "Другое" (без вложенных списков)
        is_other_category = category_name in ["Другое", "Discord"]

        # Фрейм для заголовка и чекбокса категории
        header_frame = tk.Frame(frame, bg='#182030')
        header_frame.pack(fill=tk.X, pady=(0, 0))

        # Подсчитываем сколько доменов уже выбрано для всей категории
        all_domains = []
        if is_other_category:
            # Для категории "Другое" берем домены напрямую
            all_domains = list(category_content.keys())
            spacer = tk.Label(
                header_frame,
                text="",
                font=("Arial", 10),
                bg='#182030',
                width=1
            )
            spacer.pack(side=tk.LEFT, padx=(0, 8))

        else:
            # Для остальных категорий собираем все домены из подкатегорий
            for subcategory in category_content.values():
                all_domains.extend(list(subcategory.keys()))

        selected_count = sum(1 for domain in all_domains if domain in self.existing_entries)
        total_count = len(all_domains)

        # Переменная для чекбокса основной категории
        category_var = tk.BooleanVar(value=selected_count == total_count)

        # Только для НЕ "Другое" создаем кнопку раскрытия
        if not is_other_category:
            # Фрейм для содержимого (изначально скрыт)
            content_frame = tk.Frame(frame, bg='#182030')

            # Кнопка для раскрытия/скрытия содержимого
            toggle_button = tk.Label(
                header_frame,
                text="▼",
                font=("Arial", 10),
                fg='#8e8e93',
                bg='#182030',
                cursor='hand2',
                width=1
            )
            toggle_button.bind("<Button-1>", lambda e, f=content_frame, b=toggle_button: self.toggle_content_frame(f, b))
            toggle_button.pack(side=tk.LEFT, padx=(0, 8))

        # Чекбокс основной категории
        category_check = tk.Checkbutton(
            header_frame,
            text=category_name,
            variable=category_var,
            font=("Arial", 12, "bold"),
            fg='#0a84ff',
            bg='#182030',
            selectcolor='#182030',
            activebackground='#182030',
            activeforeground='#0a84ff',
            highlightthickness=0,
            command=lambda: self.toggle_category_content(category_name, is_other_category, category_content),
            cursor='hand2'
        )
        category_check.pack(side=tk.LEFT)

        # Метка с количеством доменов
        count_label = tk.Label(
            header_frame,
            text=f"({selected_count}/{total_count})",
            font=("Arial", 10),
            fg='#8e8e93',
            bg='#182030'
        )
        count_label.pack(side=tk.LEFT, padx=(5, 0))

        # Сохраняем информацию о категории
        self.service_vars[category_name] = {
            'var': category_var,
            'is_other': is_other_category,
            'count_label': count_label,
            'all_domains': all_domains
        }

        if not is_other_category:
            # Для категорий с подкатегориями
            self.service_vars[category_name]['subcategories'] = {}
            self.service_vars[category_name]['content_frame'] = content_frame
            self.service_vars[category_name]['toggle_button'] = toggle_button

            # Создаем подкатегории (список сервисов)
            for subcategory_name, domains_dict in category_content.items():
                self.service_vars[category_name]['subcategories'][subcategory_name] = {
                    'domains': list(domains_dict.keys()),
                    'selected': sum(1 for domain in domains_dict.keys() if domain in self.existing_entries)
                }

                # Создаем чекбокс для подкатегории
                subcategory_frame = self.create_subcategory_checkbox(content_frame, category_name, subcategory_name, domains_dict)
                subcategory_frame.pack(fill=tk.X, pady=(5, 0), padx=(30, 0))
        else:
            # Для категории "Другое" создаем один чекбокс для всей категории
            self.service_vars[category_name]['selected'] = selected_count

        return frame

    def create_subcategory_checkbox(self, parent, category_name, subcategory_name, domains_dict):
        """Создает чекбокс для подкатегории (сервиса)"""
        frame = tk.Frame(parent, bg='#182030')

        domains = list(domains_dict.keys())
        selected_count = sum(1 for domain in domains if domain in self.existing_entries)
        total_count = len(domains)

        # Переменная для чекбокса подкатегории
        subcategory_var = tk.BooleanVar(value=selected_count == total_count)

        # Сохраняем переменную в структуре данных
        self.service_vars[category_name]['subcategories'][subcategory_name]['var'] = subcategory_var

        # Чекбокс подкатегории (сервиса)
        subcategory_check = tk.Checkbutton(
            frame,
            text=subcategory_name,
            variable=subcategory_var,
            font=("Arial", 11),
            fg='#34c759',
            bg='#182030',
            selectcolor='#182030',
            activebackground='#182030',
            activeforeground='#34c759',
            highlightthickness=0,
            command=lambda: self.update_category_count(category_name, subcategory_name),
            cursor='hand2'
        )
        subcategory_check.pack(side=tk.LEFT)

        # Метка с количеством доменов подкатегории
        sub_count_label = tk.Label(
            frame,
            text=f"({selected_count}/{total_count})",
            font=("Arial", 9),
            fg='#8e8e93',
            bg='#182030'
        )
        sub_count_label.pack(side=tk.LEFT, padx=(5, 0))

        # Сохраняем ссылку на метку
        self.service_vars[category_name]['subcategories'][subcategory_name]['count_label'] = sub_count_label

        return frame

    def toggle_content_frame(self, content_frame, toggle_button):
        """Раскрывает или скрывает фрейм с содержимым"""
        if content_frame.winfo_ismapped():
            content_frame.pack_forget()
            toggle_button.config(text='▼')
        else:
            content_frame.pack(fill=tk.X, pady=(5, 0))
            toggle_button.config(text='▲')

    def toggle_category_content(self, category_name, is_other, category_content):
        """Включает/выключает все содержимое категории"""
        category_info = self.service_vars.get(category_name)
        if category_info:
            state = category_info['var'].get()

            if is_other:
                # Для категории "Другое" просто обновляем счетчик
                selected_count = len(category_info['all_domains']) if state else 0
                category_info['count_label'].config(text=f"({selected_count}/{len(category_info['all_domains'])})")
                category_info['selected'] = selected_count
            else:
                # Для категорий с подкатегориями
                for subcategory_name, subcategory_info in category_info['subcategories'].items():
                    subcategory_info['var'].set(state)
                    selected_count = len(subcategory_info['domains']) if state else 0
                    subcategory_info['count_label'].config(text=f"({selected_count}/{len(subcategory_info['domains'])})")
                    subcategory_info['selected'] = selected_count

                # Обновляем счетчик категории
                self.update_category_total_count(category_name)

    def update_category_count(self, category_name, subcategory_name):
        """Обновляет счетчики после изменения состояния подкатегории"""
        category_info = self.service_vars.get(category_name)
        if category_info and not category_info['is_other']:
            subcategory_info = category_info['subcategories'].get(subcategory_name)
            if subcategory_info:
                # Получаем текущее состояние подкатегории
                state = subcategory_info['var'].get()
                selected_count = len(subcategory_info['domains']) if state else 0
                subcategory_info['count_label'].config(text=f"({selected_count}/{len(subcategory_info['domains'])})")
                subcategory_info['selected'] = selected_count

                # Обновляем общий счетчик категории
                self.update_category_total_count(category_name)

    def update_category_total_count(self, category_name):
        """Обновляет общий счетчик категории"""
        category_info = self.service_vars.get(category_name)
        if category_info and not category_info['is_other']:
            total_selected = 0
            total_domains = 0

            for subcategory_name, subcategory_info in category_info['subcategories'].items():
                total_domains += len(subcategory_info['domains'])
                total_selected += subcategory_info['selected']

            category_info['count_label'].config(text=f"({total_selected}/{total_domains})")

            # Обновляем состояние чекбокса категории
            if total_selected == 0:
                category_info['var'].set(False)
            elif total_selected == total_domains:
                category_info['var'].set(True)

    def select_all(self):
        """Выбирает все сервисы и домены"""
        for category_name, category_info in self.service_vars.items():
            category_info['var'].set(True)
            self.toggle_category_content(category_name, category_info['is_other'], None)

    def deselect_all(self):
        """Снимает выделение со всех сервисов и доменов"""
        for category_name, category_info in self.service_vars.items():
            category_info['var'].set(False)
            self.toggle_category_content(category_name, category_info['is_other'], None)

    def save_to_hosts(self):
        """Сохраняет выбранные сервисы в файл /etc/hosts"""
        try:
            # Собираем выбранные домены
            selected_entries = []
            selected_domains = set()

            for category_name, category_info in self.service_vars.items():
                if category_info['is_other']:
                    # Для категории "Другое"
                    if category_info['var'].get():
                        for domain in category_info['all_domains']:
                            ip = self.all_domains.get(domain)  # Используем self.all_domains
                            if ip:
                                selected_entries.append(f"{ip} {domain}")
                                selected_domains.add(domain)
                else:
                    # Для категорий с подкатегориями
                    for subcategory_name, subcategory_info in category_info['subcategories'].items():
                        if subcategory_info['var'].get():
                            for domain in subcategory_info['domains']:
                                ip = self.all_domains.get(domain)  # Используем self.all_domains
                                if ip:
                                    selected_entries.append(f"{ip} {domain}")
                                    selected_domains.add(domain)

            # Всегда показываем окно ввода пароля
            def on_password_valid(password):
                self.save_hosts_with_password(password, selected_entries, selected_domains)

            password_window = SudoPasswordWindow(self.window, on_password_valid=on_password_valid)
            password_window.run()

        except Exception as e:
            show_error(self.window, "Ошибка", f"Не удалось сохранить файл hosts: {e}")

    def save_hosts_with_password(self, password, selected_entries, selected_domains):
        """Сохраняет файл hosts с использованием введенного пароля"""
        try:
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
            service_domains = set(self.all_domains.keys())  # Используем self.all_domains

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

                # Если это наша запись (домен из наших сервисов), пропускаем ее
                if line_stripped and not line_stripped.startswith('#'):
                    parts = line_stripped.split()
                    if len(parts) >= 2:
                        domain = parts[1]
                        if domain in service_domains:  # Используем service_domains из self.all_domains
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
                        # Подсчитываем количество выбранных категорий
                        categories_selected = 0
                        for category_name, category_info in self.service_vars.items():
                            if category_info['var'].get():
                                categories_selected += 1

                        show_info(self.window, "Сохранение",
                                f"Данные успешно сохранены в {self.hosts_file}\n\n"
                                f"Добавлено записей: {total_selected}\n"
                                f"Выбранных категорий: {categories_selected}")
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
        self.window.geometry("450x500")
        self.window.configure(bg='#182030')
        # ЭТИ СТРОКИ ДЛЯ УДАЛЕНИЯ ОБВОДКИ
        try:
            self.window.wm_overrideredirect(False)
            self.window.attributes('-toolwindow', True)
        except:
            pass
        self.window.resizable(True, True)

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=10, pady=10)
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
                             text="Выберите категории сервисов для разблокировки.\n"
                                  "Разверните категорию, чтобы увидеть отдельные сервисы.\n"
                                  "Записи будут добавлены в файл /etc/hosts.",
                             font=("Arial", 10),
                             fg='#8e8e93',
                             bg='#182030',
                             justify=tk.CENTER,
                             wraplength=400)
        desc_label.pack(anchor=tk.CENTER, pady=(0, 0))

        desc_label = tk.Label(main_frame,
                             text="После добавления перезагрузите браузер",
                             font=("Arial", 10),
                             fg='#ff9500',
                             bg='#182030',
                             justify=tk.CENTER,
                             wraplength=400)
        desc_label.pack(anchor=tk.CENTER, pady=(0, 15))


        # Фрейм с прокруткой для категорий
        canvas_frame = tk.Frame(main_frame, bg='#182030')
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 0))

        # Создаем Canvas и Scrollbar
        canvas = tk.Canvas(canvas_frame, bg='#182030', highlightthickness=0, height=250)
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

        # Создаем фреймы для основных категорий
        for category_name, category_content in self.main_categories.items():
            category_frame = self.create_main_category_frame(scrollable_frame, category_name, category_content)
            category_frame.pack(fill=tk.X, pady=(0, 10))

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
