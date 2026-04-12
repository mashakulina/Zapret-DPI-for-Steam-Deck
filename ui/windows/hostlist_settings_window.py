#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
import re
from ui.components.custom_messagebox import show_info, show_error, ask_yesno, ask_yesnocancel
from core.dpi_utils import (
    application_tk_root,
    center_toplevel_on_parent_with_size,
    place_toplevel_centered_on_parent,
)
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale

class HostlistSettingsWindow:
    # Эталон размера окна: ширина как раньше, высота чуть меньше (масштабируется через _s)
    _BASE_WIN_W = 710
    _BASE_WIN_H = 630

    def __init__(self, parent):
        self.parent = parent
        self.window = None

        # Путь к файлам
        self.manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        self.list_general_file = os.path.join(self.manager_dir, "files", "lists", "list-general.txt")
        self.list_general_user_file_file = os.path.join(self.manager_dir, "files", "lists", "list-general_user.txt")
        self.list_exclude_user_file = os.path.join(self.manager_dir, "files", "lists", "list-exclude_user.txt")
        self.roblox_file = os.path.join(self.manager_dir, "utils", "roblox.txt")

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
            ],
            "Github": [
                "github.com",
                "raw.githubusercontent.com",
                "gist.githubusercontent.com",
                "githubusercontent.com",
                "gitlab.com",
                "raw.gitlab.com",
                "snippets.gitlab.com",
                "git.sr.ht"
            ],
            "Roblox": self.load_roblox_domains()
        }

        # Переменные для чекбоксов
        self.whatsapp_var = tk.BooleanVar()
        self.rockstar_var = tk.BooleanVar()
        self.github_var = tk.BooleanVar()
        # ДОБАВЛЕНО: Переменная для чекбокса Roblox
        self.roblox_var = tk.BooleanVar()

        # Переменные для текстовых полей вкладок
        self.blocked_text_input = None
        self.unblocked_text_input = None

        # Переменная для хранения существующих доменов
        self.existing_domains = []
        self._scale_refresh_pending = False

    def _anchor_root(self):
        return application_tk_root(self.parent) or self.parent

    def _s(self, px: float) -> int:
        """Пиксели/отступы с учётом масштаба (как warning_dialog_scale в других окнах)."""
        f = float(getattr(self, "_ui_scale", 1.0))
        return max(1, int(round(float(px) * f)))

    def _font(self, family, size, weight=None):
        """Шрифт без двойного DPI: только logical_ui_scale (Tk уже тянет pt при своём scaling)."""
        f = float(getattr(self, "_logical_scale", 1.0))
        s = max(8, int(round(float(size) * f)))
        if weight:
            return (family, s, weight)
        return (family, s)

    def _clamped_fixed_geometry_wh(self, anchor=None):
        anchor = anchor or self._anchor_root()
        sw = max(1, int(anchor.winfo_screenwidth()))
        sh = max(1, int(anchor.winfo_screenheight()))
        margin = max(8, self._s(24))
        tw = min(int(self._s(self._BASE_WIN_W)), max(1, sw - margin))
        th = min(int(self._s(self._BASE_WIN_H)), max(1, sh - margin))
        return tw, th

    def _apply_fixed_window_bounds(self, tw, th):
        """Сброс minsize → maxsize → центр: иначе дети дают reqheight ~988 при max 720."""
        tw, th = int(tw), int(th)

        def _apply_once(_tw, _th):
            try:
                self.window.minsize(1, 1)
            except tk.TclError:
                pass
            try:
                self.window.maxsize(_tw, _th)
            except tk.TclError:
                pass
            try:
                center_toplevel_on_parent_with_size(
                    self.window, self.parent, _tw, _th, immediate=True
                )
            except tk.TclError:
                pass

        _apply_once(tw, th)

        def bump(_tw=tw, _th=th):
            try:
                if self.window.winfo_exists():
                    _apply_once(_tw, _th)
            except tk.TclError:
                pass

        try:
            self.window.after_idle(bump)
            self.window.after(100, bump)
        except tk.TclError:
            pass

    def _schedule_hostlist_scale_refresh(self, _event=None):
        """Смена масштаба монитора / возврат из настроек дисплея — перечитать DPI и подогнать окно."""
        if not self.window:
            return
        if self._scale_refresh_pending:
            return
        self._scale_refresh_pending = True

        def _go():
            self._scale_refresh_pending = False
            try:
                if self.window.winfo_exists():
                    self._reapply_hostlist_scale()
            except tk.TclError:
                pass

        try:
            self.window.after(150, _go)
        except tk.TclError:
            self._scale_refresh_pending = False

    def _reapply_hostlist_scale(self):
        """Повторное применение отступов/шрифтов/размера окна, если изменился системный масштаб."""
        if not self.window:
            return
        anchor = self._anchor_root()
        nu = float(warning_dialog_scale(anchor))
        nl = float(logical_ui_scale(anchor))
        if (
            abs(nu - float(getattr(self, "_ui_scale", 1.0))) < 0.02
            and abs(nl - float(getattr(self, "_logical_scale", 1.0))) < 0.02
        ):
            return
        self._ui_scale = nu
        self._logical_scale = nl

        mf = getattr(self, "_hl_main_frame", None)
        if mf:
            mf.configure(padx=self._s(20), pady=self._s(20))

        lf = getattr(self, "_hl_left_frame", None)
        if lf:
            lf.configure(width=self._s(260))

        rf = getattr(self, "_hl_right_frame", None)
        if rf:
            rf.grid_configure(padx=(self._s(15), 0))

        tl = getattr(self, "_hl_title_label", None)
        if tl:
            tl.configure(
                font=self._font("Arial", 14, "bold"),
                pady=(0, self._s(15)),
            )

        for w in (getattr(self, "_hl_instruction_title", None), getattr(self, "_hl_left_title", None)):
            if w:
                w.configure(font=self._font("Arial", 12, "bold"))

        for w in (
            getattr(self, "_hl_instruction_text", None),
            getattr(self, "_hl_left_info", None),
        ):
            if w:
                w.configure(font=self._font("Arial", 10))

        for cb in getattr(self, "_hl_checkbuttons", ()) or ():
            if cb:
                cb.configure(font=self._font("Arial", 11))

        for tab in getattr(self, "_hl_tab_refs", ()) or ():
            if not tab:
                continue
            info = tab.get("info")
            if info:
                info.configure(font=self._font("Arial", 10))
            el = tab.get("examples_label")
            if el:
                el.configure(font=self._font("Arial", 10, "italic"))
            et = tab.get("examples_text")
            if et:
                et.configure(font=self._font("Courier New", 9))
            tlab = tab.get("text_label")
            if tlab:
                tlab.configure(font=self._font("Arial", 11))
            ti = tab.get("text_input")
            if ti:
                ti.configure(font=self._font("Courier New", 10))

        style = ttk.Style()
        nb_style = getattr(self, "_hl_nb_style", "Hostlist.TNotebook")
        try:
            style.configure(
                f"{nb_style}.Tab",
                background="#1a1a2e",
                foreground="#8e8e93",
                padding=[self._s(10), self._s(5)],
                font=self._font("Arial", 10),
            )
        except tk.TclError:
            pass

        for b in (
            getattr(self, "save_button", None),
            getattr(self, "cancel_button", None),
        ):
            if b:
                b.configure(
                    font=self._font("Arial", 11),
                    padx=self._s(25),
                    pady=self._s(10),
                )

        bf = getattr(self, "_hl_buttons_frame", None)
        if bf:
            bf.grid_configure(pady=(self._s(20), 0))

        sb = getattr(self, "save_button", None)
        if sb:
            sb.pack_configure(padx=(0, self._s(15)))

        tw, th = self._clamped_fixed_geometry_wh(anchor)
        self._apply_fixed_window_bounds(tw, th)

    def load_roblox_domains(self):
        """Загружает домены Roblox из файла roblox.txt"""
        domains = []
        try:
            if os.path.exists(self.roblox_file):
                with open(self.roblox_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):  # Пропускаем пустые строки и комментарии
                            domains.append(line)
                print(f"Загружено {len(domains)} доменов Roblox из {self.roblox_file}")
            else:
                print(f"Файл {self.roblox_file} не найден")
        except Exception as e:
            print(f"Ошибка загрузки файла roblox.txt: {e}")
        return domains

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def load_existing_data(self):
        """Загружает существующие данные из файлов"""
        # Загружаем пользовательские домены из list-general_user.txt (заблокированные)
        try:
            if os.path.exists(self.list_general_user_file_file):
                with open(self.list_general_user_file_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.blocked_text_input:
                        self.blocked_text_input.delete("1.0", tk.END)
                        self.blocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла list-general_user.txt: {e}")

        # Загружаем пользовательские домены из list-exclude_user.txt (незаблокированные)
        try:
            if os.path.exists(self.list_exclude_user_file):
                with open(self.list_exclude_user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.unblocked_text_input:
                        self.unblocked_text_input.delete("1.0", tk.END)
                        self.unblocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла list-exclude_user.txt: {e}")

        # Загружаем существующие домены из list-general.txt для проверки выбранных сервисов
        try:
            if os.path.exists(self.list_general_file):
                with open(self.list_general_file, 'r', encoding='utf-8') as f:
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

                    # Проверяем наличие доменов Github
                    github_selected = False
                    for domain in self.services["Github"]:
                        if domain in self.existing_domains:
                            github_selected = True
                            break
                    self.github_var.set(github_selected)

                    # ДОБАВЛЕНО: Проверяем наличие доменов Roblox
                    roblox_selected = False
                    for domain in self.services["Roblox"]:
                        if domain in self.existing_domains:
                            roblox_selected = True
                            break
                    self.roblox_var.set(roblox_selected)

        except Exception as e:
            print(f"Ошибка загрузки файла list-general.txt: {e}")
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

    def clean_domain(self, domain_str):
        """Очищает домен от протоколов и слешей в конце"""
        if not domain_str or domain_str.strip().startswith('#'):
            return domain_str

        # Убираем пробелы по краям
        cleaned = domain_str.strip()

        # Удаляем протоколы http://, https://, ftp:// и т.д.
        cleaned = re.sub(r'^[a-zA-Z]+://', '', cleaned)

        # Удаляем все после первого слеша (пути и параметры)
        cleaned = cleaned.split('/')[0]

        # Удаляем порты если есть (например :8080)
        cleaned = cleaned.split(':')[0]

        return cleaned

    def on_paste(self, text_widget, event=None):
        """Обрабатывает вставку текста и очищает домены"""
        try:
            # Получаем текст из буфера обмена
            clipboard_text = text_widget.clipboard_get()

            # Разбиваем на строки и очищаем каждую
            lines = clipboard_text.split('\n')
            cleaned_lines = []

            for line in lines:
                if line.strip():
                    # Очищаем каждую непустую строку
                    cleaned_line = self.clean_domain(line)
                    if cleaned_line:  # Добавляем только если не пусто
                        cleaned_lines.append(cleaned_line)
                else:
                    # Сохраняем пустые строки для форматирования
                    cleaned_lines.append('')

            # Объединяем обратно
            cleaned_text = '\n'.join(cleaned_lines)

            # Вставляем очищенный текст
            text_widget.insert(tk.INSERT, cleaned_text)

            # Возвращаем "break", чтобы предотвратить стандартную вставку
            return "break"
        except:
            # Если не удалось получить из буфера обмена, разрешаем стандартную вставку
            return None

    def save_custom_domains(self, text_widget, file_path, domain_type):
        """Сохраняет пользовательские домены в указанный файл"""
        try:
            custom_domains = text_widget.get("1.0", tk.END).strip()

            # Проверяем пользовательские домены перед сохранением
            if custom_domains:
                lines = custom_domains.split('\n')
                error_lines = []

                # Очищаем каждую строку перед проверкой
                cleaned_lines = []
                for line in lines:
                    if line.strip() and not line.strip().startswith('#'):
                        cleaned_line = self.clean_domain(line)
                        cleaned_lines.append(cleaned_line)
                    else:
                        cleaned_lines.append(line)

                # Обновляем текст в виджете (опционально)
                if lines != cleaned_lines:
                    text_widget.delete("1.0", tk.END)
                    text_widget.insert("1.0", '\n'.join(cleaned_lines))

                # Используем очищенные строки для проверки
                lines = cleaned_lines

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
                self.list_general_user_file_file,
                "Заблокированные"
            )
            if blocked_count is None:  # Если была ошибка
                return

            # Сохраняем незаблокированные домены
            unblocked_count = self.save_custom_domains(
                self.unblocked_text_input,
                self.list_exclude_user_file,
                "Незаблокированные"
            )
            if unblocked_count is None:  # Если была ошибка
                return

            # Обрабатываем list-general.txt: сохраняем существующие данные + добавляем/удаляем выбранные сервисы
            # Загружаем текущие домены из файла (если он существует)
            current_domains = set()
            if os.path.exists(self.list_general_file):
                with open(self.list_general_file, 'r', encoding='utf-8') as f:
                    current_domains = set([line.strip() for line in f if line.strip()])
            else:
                # Если файла нет, используем существующие домены из загрузки
                current_domains = set(self.existing_domains)

            # Удаляем все домены сервисов (чтобы потом добавить только выбранные)
            all_service_domains = set(self.services["WhatsApp"] +
                                      self.services["Rockstar/Epic Games"] +
                                      self.services["Github"] +
                                      self.services["Roblox"])  # ДОБАВЛЕНО: Roblox
            current_domains = current_domains - all_service_domains

            # Добавляем домены выбранных сервисов
            if self.whatsapp_var.get():
                current_domains.update(self.services["WhatsApp"])

            if self.rockstar_var.get():
                current_domains.update(self.services["Rockstar/Epic Games"])

            if self.github_var.get():
                current_domains.update(self.services["Github"])

            # ДОБАВЛЕНО: Добавляем домены Roblox, если выбран чекбокс
            if self.roblox_var.get():
                current_domains.update(self.services["Roblox"])

            # Сортируем и сохраняем в файл list-general.txt
            sorted_domains = sorted(current_domains)
            os.makedirs(os.path.dirname(self.list_general_file), exist_ok=True)
            with open(self.list_general_file, 'w', encoding='utf-8') as f:
                for domain in sorted_domains:
                    f.write(f"{domain}\n")

            # Показываем статистику
            selected_services = []
            if self.whatsapp_var.get():
                selected_services.append("WhatsApp")
            if self.rockstar_var.get():
                selected_services.append("Rockstar/Epic Games")
            if self.github_var.get():
                selected_services.append("Github")
            # ДОБАВЛЕНО: Roblox в статистику
            if self.roblox_var.get():
                selected_services.append("Roblox")

            services_text = ", ".join(selected_services) if selected_services else "ни одного сервиса"

            # ДОБАВЛЕНО: Информация о количестве доменов Roblox
            roblox_count_info = ""
            if self.roblox_var.get():
                roblox_count_info = (
                    f" Доменов Roblox добавлено: {len(self.services['Roblox'])}."
                )

            show_info(
                self.window,
                "Сохранение",
                (
                    f"Данные успешно сохранены! Выбранные сервисы: {services_text}. "
                    f"Всего доменов в list-general.txt: {len(sorted_domains)}. "
                    f"Заблокированные домены: {blocked_count} (сохранено в list-general_user.txt). "
                    f"Незаблокированные домены: {unblocked_count} (сохранено в list-exclude_user.txt)."
                    f"{roblox_count_info}"
                ),
            )

        except Exception as e:
            show_info(self.window, "Ошибка", f"Не удалось сохранить файлы: {e}")

    def create_text_tab(self, parent, tab_name, description, examples, file_name):
        """Создает вкладку с текстовым полем для ввода доменов"""
        frame = tk.Frame(parent, bg='#182030')

        # Описание
        info = tk.Label(
            frame,
            text=description,
            font=self._font("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=self._s(400),
        )
        info.grid(row=0, column=0, sticky="ew", pady=(0, self._s(15)))

        def _sync_tab_info_wrap(_event=None):
            try:
                aw = max(frame.winfo_width(), 1)
                info.configure(wraplength=max(self._s(120), aw - self._s(24)))
            except tk.TclError:
                pass

        frame.bind("<Configure>", lambda _e: _sync_tab_info_wrap())
        frame.after_idle(_sync_tab_info_wrap)

        # Примеры доменов
        examples_frame = tk.Frame(frame, bg='#182030')
        examples_frame.grid(row=1, column=0, sticky="ew", pady=(0, self._s(10)))

        examples_label = tk.Label(examples_frame,
                                text="Примеры доменов:",
                                font=self._font("Arial", 10, "italic"),
                                fg='#8e8e93',
                                bg='#182030')
        examples_label.pack(anchor=tk.W)

        examples_text = tk.Label(
            examples_frame,
            text=examples,
            font=self._font("Courier New", 9),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=0,
        )
        examples_text.pack(anchor=tk.NW)

        # Блок ввода: строка с weight=1 — занимает оставшуюся высоту вкладки (не выталкивает кнопки окна)
        text_frame = tk.Frame(frame, bg='#182030')
        text_frame.grid(row=2, column=0, sticky="nsew", pady=(0, self._s(10)))
        frame.grid_rowconfigure(2, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        # Метка для текстового поля
        text_label = tk.Label(text_frame,
                            text="Введите домены:",
                            font=self._font("Arial", 11),
                            fg='#0a84ff',
                            bg='#182030')
        text_label.grid(row=0, column=0, sticky="w", pady=(0, self._s(5)))

        # Текстовое поле с прокруткой
        text_container = tk.Frame(text_frame, bg='#182030')
        text_container.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(1, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        # Текстовое поле
        text_input = tk.Text(text_container,
                            font=self._font("Courier New", 10),
                            bg='#1a1a2e',
                            fg='#ffffff',
                            insertbackground='white',
                            wrap=tk.NONE,
                            height=6)
        text_input.grid(row=0, column=0, sticky="nsew")
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)
        text_input.bind('<Control-v>', lambda e: self.on_paste(text_input, e))

        tab_refs = {
            "info": info,
            "examples_label": examples_label,
            "examples_text": examples_text,
            "text_label": text_label,
            "text_input": text_input,
        }
        return frame, text_input, tab_refs

    def create_window(self):
        """Создает окно настроек HOSTLIST"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Настройки фильтрации доменов")
        self.window.configure(bg='#182030')
        self.window.resizable(True, True)

        anchor = self._anchor_root()
        self._ui_scale = float(warning_dialog_scale(anchor))
        self._logical_scale = float(logical_ui_scale(anchor))

        # Основной фрейм
        main_frame = tk.Frame(self.window, bg='#182030', padx=self._s(20), pady=self._s(20))
        main_frame.pack(fill=tk.BOTH, expand=True)
        self._hl_main_frame = main_frame

        # Заголовок
        title_label = tk.Label(main_frame,
                               text="Настройки фильтрации доменов",
                               font=self._font("Arial", 14, "bold"),
                               fg='white',
                               bg='#182030')
        title_label.grid(row=0, column=0, pady=(0, self._s(15)))
        self._hl_title_label = title_label

        # Фрейм с двумя колонками (строка с weight=1 — сжимается по высоте окна)
        columns_frame = tk.Frame(main_frame, bg='#182030')
        columns_frame.grid(row=1, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Левая колонка (30% ширины)
        left_frame = tk.Frame(columns_frame, bg='#182030', width=self._s(260))
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.pack_propagate(False)
        self._hl_left_frame = left_frame

        # Правая колонка (70% ширины)
        right_frame = tk.Frame(columns_frame, bg='#182030')
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(self._s(15), 0))
        self._hl_right_frame = right_frame
        columns_frame.grid_columnconfigure(1, weight=1)
        columns_frame.grid_rowconfigure(0, weight=1)

        # ========== ЛЕВАЯ КОЛОНКА ==========
        # Инструкция для пользовательских доменов
        instruction_title = tk.Label(left_frame,
                                    text="Пользовательские домены",
                                    font=self._font("Arial", 12, "bold"),
                                    fg='#0a84ff',
                                    bg='#182030')
        instruction_title.pack(anchor=tk.W, pady=(0, self._s(10)))
        self._hl_instruction_title = instruction_title

        instruction_text = tk.Label(
            left_frame,
            text=(
                "Если с Zapret не работает заблокированный сайт, то выберите вкладку «Заблокированный» "
                "и внесите домен в список.\n\nЕсли с Zapret не работает незаблокированный сайт, то выберите "
                "вкладку «Незаблокированный» и внесите домен в список."
            ),
            font=self._font("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=self._s(240),
        )
        instruction_text.pack(anchor=tk.NW, fill=tk.X)
        self._hl_instruction_text = instruction_text


        left_title = tk.Label(left_frame,
                             text="Предустановленные сервисы",
                             font=self._font("Arial", 12, "bold"),
                             fg='#0a84ff',
                             bg='#182030')
        left_title.pack(anchor=tk.W, pady=(self._s(20), self._s(10)))
        self._hl_left_title = left_title

        left_info = tk.Label(
            left_frame,
            text=(
                "Выбрать предустановленные сервисы для фильтрации. "
                "Домены сервисов будут прописаны в файл list-general.txt."
            ),
            font=self._font("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=self._s(220),
        )
        left_info.pack(anchor=tk.NW, pady=(0, self._s(20)), fill=tk.X)
        self._hl_left_info = left_info

        def _sync_left_column_wrap(_event=None):
            try:
                aw = max(left_frame.winfo_width(), 1)
                wl = max(self._s(80), aw - self._s(8))
                instruction_text.configure(wraplength=wl)
                left_info.configure(wraplength=wl)
            except tk.TclError:
                pass

        left_frame.bind("<Configure>", lambda _e: _sync_left_column_wrap())
        left_frame.after_idle(_sync_left_column_wrap)

        # Фрейм для чекбоксов
        checkboxes_frame = tk.Frame(left_frame, bg='#182030')
        checkboxes_frame.pack(fill=tk.X, pady=(0, 0))

        # Чекбокс WhatsApp
        whatsapp_check = tk.Checkbutton(checkboxes_frame,
                                       text="WhatsApp",
                                       variable=self.whatsapp_var,
                                       font=self._font("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        whatsapp_check.pack(anchor=tk.W, pady=(0, self._s(5)))

        # Чекбокс Rockstar/Epic Games
        rockstar_check = tk.Checkbutton(checkboxes_frame,
                                       text="Rockstar/Epic Games",
                                       variable=self.rockstar_var,
                                       font=self._font("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        rockstar_check.pack(anchor=tk.W, pady=(0, self._s(5)))

        # Чекбокс Github
        github_check = tk.Checkbutton(checkboxes_frame,
                                       text="Github",
                                       variable=self.github_var,
                                       font=self._font("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        github_check.pack(anchor=tk.W, pady=(0, self._s(5)))

        # Чекбокс Roblox
        roblox_check = tk.Checkbutton(checkboxes_frame,
                                       text="Roblox",
                                       variable=self.roblox_var,
                                       font=self._font("Arial", 11),
                                       fg='white',
                                       bg='#182030',
                                       selectcolor='#182030',
                                       activebackground='#182030',
                                       highlightthickness=0,
                                       activeforeground='white')
        roblox_check.pack(anchor=tk.W, pady=(0, self._s(5)))
        self._hl_checkbuttons = (
            whatsapp_check,
            rockstar_check,
            github_check,
            roblox_check,
        )


        # ========== ПРАВАЯ КОЛОНКА ==========
        # Создаем Notebook для вкладок (свой стиль — не трогаем глобальный TNotebook других окон)
        self._hl_nb_style = "Hostlist.TNotebook"
        style = ttk.Style()
        style.theme_use('default')
        style.configure(self._hl_nb_style, background='#182030', borderwidth=0)
        style.configure(
            f"{self._hl_nb_style}.Tab",
            background='#1a1a2e',
            foreground='#8e8e93',
            padding=[self._s(10), self._s(5)],
            font=self._font('Arial', 10),
        )
        style.map(
            f"{self._hl_nb_style}.Tab",
            background=[('selected', '#0a84ff')],
            foreground=[('selected', 'white')],
        )

        notebook = ttk.Notebook(right_frame, style=self._hl_nb_style)
        notebook.grid(row=0, column=0, sticky="nsew")
        right_frame.grid_rowconfigure(0, weight=1)
        right_frame.grid_columnconfigure(0, weight=1)

        # Вкладка "Заблокированный"
        blocked_frame, self.blocked_text_input, blocked_tab_refs = self.create_text_tab(
            notebook,
            "Заблокированный",
            "Пользовательские домены сохраняются в файл list-general_user.txt.\n"
            "Вводить домены нужно по одному на строку.\n"
            "Чтобы оставить комментарий, поставьте знак «#» в начале строки.",
            "example.com\n*.example.com\nsubdomain.example.com",
            "list-general_user.txt"
        )
        notebook.add(blocked_frame, text="Заблокированный")

        # Вкладка "Незаблокированный"
        unblocked_frame, self.unblocked_text_input, unblocked_tab_refs = self.create_text_tab(
            notebook,
            "Незаблокированный",
            "Пользовательские домены сохраняются в файл list-exclude_user.txt.\n"
            "Вводить домены нужно по одному на строку.\n"
            "Чтобы оставить комментарий, поставьте знак «#» в начале строки.",
            "example.com\n*.example.com\nsubdomain.example.com",
            "list-exclude_user.txt"
        )
        notebook.add(unblocked_frame, text="Незаблокированный")
        self._hl_tab_refs = (blocked_tab_refs, unblocked_tab_refs)

        # ========== КНОПКИ ВНИЗУ ==========
        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.grid(row=2, column=0, sticky="ew", pady=(self._s(20), 0))
        self._hl_buttons_frame = buttons_frame

        # Контейнер для центрирования кнопок
        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        # Стиль кнопок
        button_style = {
            'font': self._font('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': self._s(25),
            'pady': self._s(10),
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
        self.save_button.pack(side=tk.LEFT, padx=(0, self._s(15)))

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

        _tw, _th = self._clamped_fixed_geometry_wh(anchor)
        place_toplevel_centered_on_parent(
            self.window,
            self.parent,
            fixed_content_size=(_tw, _th),
            immediate=True,
        )
        self._apply_fixed_window_bounds(_tw, _th)

        # Map / FocusIn: возврат с экрана настроек дисплея или другого монитора — перечитать масштаб
        self.window.bind("<Map>", self._schedule_hostlist_scale_refresh, add="+")
        self.window.bind("<FocusIn>", self._schedule_hostlist_scale_refresh, add="+")

        return self.window

    def run(self):
        """Запускает окно настроек HOSTLIST"""
        self.create_window()
        self.window.wait_window()
