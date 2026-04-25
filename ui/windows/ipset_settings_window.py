#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import ipaddress
import re
import os
from ui.components.custom_messagebox import show_info, show_error, ask_yesno, ask_yesnocancel
from core.dpi_utils import application_tk_root, place_toplevel_centered_on_parent
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale


class IpsetSettingsWindow:
    """Пользовательские IP: базовый размер при ~100 % DPI, далее — _s / _font как у hostlist."""

    _BASE_WIN_W = 450
    _BASE_WIN_H = 480
    # Верхняя граница ширины (логические px при ~100 %), чтобы не раздуваться под reqwidth подсказок
    _MAX_WIN_W = 480

    def __init__(self, parent):
        self.parent = parent
        self.window = None

        self.blocked_text_input = None
        self.unblocked_text_input = None

        # Пути к файлам
        self.manager_dir = os.path.expanduser("~/Zapret_DPI_Manager")
        self.ipset_all_user_file = os.path.join(self.manager_dir, "files", "lists", "ipset-all_user.txt")
        self.ipset_exclude_user_file = os.path.join(self.manager_dir, "files", "lists", "ipset-exclude_user.txt")

    def validate_ip_address(self, ip_str):
        """Проверяет корректность IP-адреса, диапазона или подсети (IPv4 и IPv6)."""

        # Комментарий
        if ip_str.strip().startswith('#'):
            return True, ""

        # Проверка на пустую строку
        if not ip_str.strip():
            return True, ""

        s = ip_str.strip()

        # Диапазон только для IPv4: 172.16.0.0-172.31.255.255
        range_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}-\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if re.match(range_pattern, s):
            start_ip, end_ip = s.split('-')
            for part in start_ip.split('.'):
                if not 0 <= int(part) <= 255:
                    return False, "Неверный начальный IP в диапазоне"
            for part in end_ip.split('.'):
                if not 0 <= int(part) <= 255:
                    return False, "Неверный конечный IP в диапазоне"
            return True, ""

        # Одиночный адрес или подсеть CIDR (IPv4 и IPv6), например 2a14:7583:f14c::/46
        if '/' in s:
            try:
                ipaddress.ip_network(s, strict=False)
                return True, ""
            except ValueError:
                return False, "Некорректный адрес или префикс (IPv4/IPv6 CIDR)"

        try:
            ipaddress.ip_address(s)
            return True, ""
        except ValueError:
            return False, "Некорректный формат адреса или комментарий без #"

    def save_data(self):
        """Сохраняет данные в файлы"""
        try:
            # Сохраняем заблокированные IP
            blocked_data = self.blocked_text_input.get("1.0", tk.END).strip()

            # Проверяем заблокированные IP
            if blocked_data:
                lines = blocked_data.split('\n')
                error_lines = []

                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    is_valid, error_msg = self.validate_ip_address(line)
                    if not is_valid:
                        error_lines.append(f"Строка {i}: {line} - {error_msg}")

                if error_lines:
                    error_text = "\n".join(error_lines)
                    show_info(self.window, "Ошибка в данных",
                            f"Обнаружены ошибки в заблокированных IP. Данные не сохранены:\n\n{error_text}")
                    return

            # Сохраняем незаблокированные IP
            unblocked_data = self.unblocked_text_input.get("1.0", tk.END).strip()

            # Проверяем незаблокированные IP
            if unblocked_data:
                lines = unblocked_data.split('\n')
                error_lines = []

                for i, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    is_valid, error_msg = self.validate_ip_address(line)
                    if not is_valid:
                        error_lines.append(f"Строка {i}: {line} - {error_msg}")

                if error_lines:
                    error_text = "\n".join(error_lines)
                    show_info(self.window, "Ошибка в данных",
                            f"Обнаружены ошибки в незаблокированных IP. Данные не сохранены:\n\n{error_text}")
                    return

            # Сохраняем данные
            self.write_to_file(blocked_data, self.ipset_all_user_file)
            self.write_to_file(unblocked_data, self.ipset_exclude_user_file)

            # Считаем количество IP
            blocked_count = len([line for line in blocked_data.split('\n') if line.strip() and not line.strip().startswith('#')]) if blocked_data else 0
            unblocked_count = len([line for line in unblocked_data.split('\n') if line.strip() and not line.strip().startswith('#')]) if unblocked_data else 0

            show_info(
                self.window,
                "Сохранение",
                (
                    f"Данные успешно сохранены! "
                    f"Заблокированные IP: {blocked_count} (сохранено в ipset-all_user.txt). "
                    f"Незаблокированные IP: {unblocked_count} (сохранено в ipset-exclude_user.txt)."
                ),
            )

        except Exception as e:
            show_info(self.window, "Ошибка", f"Не удалось сохранить файлы: {e}")

    def write_to_file(self, data, file_path):
        """Записывает данные в указанный файл"""
        try:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(data)

        except Exception as e:
            raise Exception(f"Не удалось сохранить файл {file_path}: {e}")

    def load_existing_data(self):
        """Загружает существующие данные из файлов"""
        # Загружаем заблокированные IP из ipset-all_user.txt
        try:
            if os.path.exists(self.ipset_all_user_file):
                with open(self.ipset_all_user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.blocked_text_input:
                        self.blocked_text_input.delete("1.0", tk.END)
                        self.blocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла ipset-all_user.txt: {e}")

        # Загружаем незаблокированные IP из ipset-exclude_user.txt
        try:
            if os.path.exists(self.ipset_exclude_user_file):
                with open(self.ipset_exclude_user_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if self.unblocked_text_input:
                        self.unblocked_text_input.delete("1.0", tk.END)
                        self.unblocked_text_input.insert("1.0", content)
        except Exception as e:
            print(f"Ошибка загрузки файла ipset-exclude_user.txt: {e}")

    def create_hover_button(self, parent, text, command, **kwargs):
        """Создает кнопку в стиле главного меню с эффектом наведения"""
        from ui.components.button_styler import create_hover_button
        return create_hover_button(parent, text, command, **kwargs)

    def _anchor_root(self):
        return application_tk_root(self.parent) or self.parent

    def _s(self, px: float) -> int:
        f = float(getattr(self, "_ui_scale", 1.0))
        return max(1, int(round(float(px) * f)))

    def _font(self, family, size, weight=None):
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
        # Оба источника: на Wayland часть DE даёт 150 % только в logical_ui_scale,
        # а warning_dialog_scale остаётся ~1 — тогда прежняя ветка по u не срабатывала.
        u = max(
            float(warning_dialog_scale(anchor)),
            float(logical_ui_scale(anchor)),
        )

        base_h = float(self._BASE_WIN_H)
        if u >= 1.45:
            base_h *= 0.74
        elif u >= 1.22:
            base_h *= 0.86

        tw = min(int(self._s(self._BASE_WIN_W)), max(1, sw - margin))
        th = min(int(self._s(base_h)), max(1, sh - margin))

        # Потолок по экрану: иначе на Deck / низком дисплее окно почти на весь рост.
        screen_cap = max(260, int(sh * 0.70) - margin)
        if u >= 1.30 or sh <= 900:
            th = min(th, screen_cap)

        tw = min(tw, max(1, sw - margin))
        th = min(th, max(1, sh - margin))
        return tw, th

    def _place_ipset_user_window_once(self, tw, th):
        """Один вызов размещения без maxsize/minsize и отложенных повторов — меньше «прыжков» WM."""
        tw, th = int(tw), int(th)
        try:
            place_toplevel_centered_on_parent(
                self.window,
                self.parent,
                fixed_content_size=(tw, th),
                immediate=True,
            )
        except tk.TclError:
            pass

    def create_text_tab(self, parent, tab_name, description, file_name):
        """Создает вкладку с текстовым полем для ввода IP-адресов"""
        frame = tk.Frame(parent, bg='#182030')

        info = tk.Label(
            frame,
            text=description,
            font=self._font("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=self._s(260),
        )
        info.grid(row=0, column=0, sticky="ew", pady=(0, self._s(8)))

        def _sync_tab_desc_wrap(_event=None):
            try:
                aw = max(frame.winfo_width(), 1)
                info.configure(wraplength=max(self._s(100), aw - self._s(12)))
            except tk.TclError:
                pass

        frame.bind("<Configure>", lambda _e: _sync_tab_desc_wrap())
        frame.after_idle(_sync_tab_desc_wrap)

        text_frame = tk.Frame(frame, bg='#182030')
        text_frame.grid(row=1, column=0, sticky="nsew", pady=(0, self._s(6)))
        frame.grid_rowconfigure(1, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        text_label = tk.Label(
            text_frame,
            text="Введите IP-адреса:",
            font=self._font("Arial", 11),
            fg='#0a84ff',
            bg='#182030',
        )
        text_label.grid(row=0, column=0, sticky="w", pady=(0, self._s(4)))

        text_container = tk.Frame(text_frame, bg='#182030')
        text_container.grid(row=1, column=0, sticky="nsew")
        text_frame.grid_rowconfigure(1, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)

        _hi = max(
            float(getattr(self, "_ui_scale", 1.0)),
            float(getattr(self, "_logical_scale", 1.0)),
        )
        _text_lines = 4 if _hi >= 1.30 else 5

        text_input = tk.Text(
            text_container,
            font=self._font("Courier New", 10),
            bg='#1a1a2e',
            fg='#ffffff',
            insertbackground='white',
            wrap=tk.NONE,
            height=_text_lines,
        )
        text_input.grid(row=0, column=0, sticky="nsew")
        text_container.grid_rowconfigure(0, weight=1)
        text_container.grid_columnconfigure(0, weight=1)

        tab_refs = {"info": info, "text_label": text_label, "text_input": text_input}
        return frame, text_input, tab_refs

    def create_window(self):
        """Создает окно добавления пользовательских IP-адресов"""
        self.window = tk.Toplevel(self.parent)
        self.window.title("Добавление пользовательских IP-адресов")
        self.window.configure(bg='#182030')
        self.window.resizable(True, True)

        anchor = self._anchor_root()
        self._ui_scale = float(warning_dialog_scale(anchor))
        self._logical_scale = float(logical_ui_scale(anchor))

        _tw, _th = self._clamped_fixed_geometry_wh(anchor)
        shell = tk.Frame(self.window, bg="#182030", width=_tw, height=_th)
        shell.pack_propagate(False)
        shell.pack()
        self._ip_shell_frame = shell

        # Внешние отступы — внутри shell; propagate=False не даёт Toplevel раздуваться под reqheight > clamp
        main_frame = tk.Frame(shell, bg='#182030', padx=self._s(12))
        main_frame.pack(
            fill=tk.BOTH,
            expand=True,
            pady=(self._s(12), self._s(15)),
        )
        self._ip_main_frame = main_frame

        title_label = tk.Label(
            main_frame,
            text="Добавление пользовательских IP-адресов",
            font=self._font("Arial", 14, "bold"),
            fg='white',
            bg='#182030',
        )
        title_label.grid(row=0, column=0, pady=(0, self._s(10)))
        self._ip_title_label = title_label

        info_frame = tk.Frame(main_frame, bg='#182030')
        info_frame.grid(row=1, column=0, sticky="ew", pady=(0, self._s(8)))

        info_body = (
            "Вводить адреса или диапазон нужно по одному на строку.\n"
            "Примеры: IPv4 — 192.168.1.1, 10.0.0.0/8, 172.16.0.0-172.31.255.255; "
            "IPv6 — 2001:db8::1 или подсеть 2a14:7583:f14c::/46.\n"
            "Чтобы оставить комментарий, нужно сначала поставить знак «#» и только после этого писать текст комментария."
        )
        info_block = tk.Label(
            info_frame,
            text=info_body,
            font=self._font("Arial", 10),
            fg='#8e8e93',
            bg='#182030',
            justify=tk.LEFT,
            anchor=tk.NW,
            wraplength=self._s(260),
        )
        info_block.pack(anchor=tk.NW, fill=tk.X)
        self._ip_info_block = info_block

        def _sync_ip_hints_wrap(_event=None):
            try:
                aw = max(info_frame.winfo_width(), 1)
                info_block.configure(wraplength=max(self._s(100), aw - self._s(8)))
            except tk.TclError:
                pass

        info_frame.bind("<Configure>", lambda _e: _sync_ip_hints_wrap())
        info_frame.after_idle(_sync_ip_hints_wrap)

        self._ip_nb_style = "IpsetUser.TNotebook"
        style = ttk.Style()
        style.theme_use('default')
        style.configure(self._ip_nb_style, background='#182030', borderwidth=0)
        style.configure(
            f"{self._ip_nb_style}.Tab",
            background='#1a1a2e',
            foreground='#8e8e93',
            padding=[self._s(8), self._s(4)],
            font=self._font('Arial', 10),
        )
        style.map(
            f"{self._ip_nb_style}.Tab",
            background=[('selected', '#0a84ff')],
            foreground=[('selected', 'white')],
        )

        notebook = ttk.Notebook(main_frame, style=self._ip_nb_style)
        notebook.grid(row=2, column=0, sticky="nsew", pady=(0, self._s(6)))
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)  # растяжение по ширине окна

        blocked_frame, self.blocked_text_input, br = self.create_text_tab(
            notebook,
            "Заблокированный",
            "Пользовательские IP-адреса сохраняются в файле ipset-all_user.txt.",
            "ipset-all_user.txt"
        )
        notebook.add(blocked_frame, text="Заблокированный")

        unblocked_frame, self.unblocked_text_input, ur = self.create_text_tab(
            notebook,
            "Незаблокированный",
            "Пользовательские IP-адреса сохраняются в файле ipset-exclude_user.txt",
            "ipset-exclude_user.txt"
        )
        notebook.add(unblocked_frame, text="Незаблокированный")
        self._ip_tab_refs = (br, ur)

        buttons_frame = tk.Frame(main_frame, bg='#182030')
        buttons_frame.grid(row=3, column=0, sticky="ew", pady=(0, self._s(10)))
        self._ip_buttons_frame = buttons_frame

        buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
        buttons_center_frame.pack()

        button_style = {
            'font': self._font('Arial', 11),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': self._s(18),
            'pady': self._s(8),
            'width': 15,
            'highlightthickness': 0,
            'cursor': 'hand2'
        }

        self.save_button = self.create_hover_button(
            buttons_center_frame,
            text="Сохранить",
            command=self.save_data,
            **button_style
        )
        self.save_button.pack(side=tk.LEFT, padx=(0, self._s(12)))

        self.cancel_button = self.create_hover_button(
            buttons_center_frame,
            text="Назад",
            command=self.window.destroy,
            **button_style
        )
        self.cancel_button.pack(side=tk.LEFT)

        self.status_message = tk.Label(
            main_frame,
            text="",
            font=self._font("Arial", 10),
            fg='#AAAAAA',
            bg='#182030'
        )
        self.status_message.grid(row=4, column=0, sticky="ew", pady=(self._s(3), 0))
        self.status_message.grid_remove()

        self.load_existing_data()

        if self.blocked_text_input:
            self.blocked_text_input.focus_set()

        # Узкая обёртка текста до измерения reqwidth — иначе длинные подписи дают mrw > 1000 px
        _inner_w = max(self._s(72), _tw - 2 * self._s(12))
        try:
            self._ip_info_block.configure(wraplength=_inner_w)
        except tk.TclError:
            pass
        for tab in getattr(self, "_ip_tab_refs", ()) or ():
            inf = tab.get("info") if tab else None
            if inf:
                try:
                    inf.configure(wraplength=max(self._s(72), _inner_w - self._s(8)))
                except tk.TclError:
                    pass

        self.window.update_idletasks()
        try:
            mrh = int(main_frame.winfo_reqheight())
            mrw = int(main_frame.winfo_reqwidth())
        except tk.TclError:
            mrh, mrw = _th, _tw
        margin = max(8, self._s(24))
        sh_scr = max(1, int(anchor.winfo_screenheight()))
        sw_scr = max(1, int(anchor.winfo_screenwidth()))
        _w_cap = min(sw_scr - margin, int(self._s(self._MAX_WIN_W)))
        _th_fit = min(sh_scr - margin, max(_th, mrh))
        _tw_fit = min(_w_cap, max(_tw, mrw))
        shell.configure(width=_tw_fit, height=_th_fit)

        try:
            self.window.minsize(1, 1)
            _cap_h = min(int(sh_scr * 0.96), _th_fit + self._s(80))
            _cap_w = min(sw_scr - margin, _tw_fit + self._s(32))
            self.window.maxsize(max(_tw_fit, _cap_w), max(_th_fit, _cap_h))
        except tk.TclError:
            pass

        self._place_ipset_user_window_once(_tw_fit, _th_fit)

        return self.window

    def show_status_message(self, message, success=False, warning=False, error=False):
        """Показывает сообщение в статусной строке"""
        if not (message or "").strip():
            try:
                self.status_message.config(text="")
                self.status_message.grid_remove()
            except tk.TclError:
                pass
            return

        self.status_message.config(text=message)

        if success:
            self.status_message.config(fg='#30d158')  # Зеленый
        elif warning:
            self.status_message.config(fg='#ff9500')  # Оранжевый
        elif error:
            self.status_message.config(fg='#ff3b30')  # Красный
        else:
            self.status_message.config(fg='#AAAAAA')  # Серый

        try:
            self.status_message.grid(row=4, column=0, sticky="ew", pady=(self._s(3), 0))
        except tk.TclError:
            pass

        def _clear_status():
            try:
                if self.window and self.window.winfo_exists() and self.status_message.winfo_exists():
                    self.status_message.config(text="")
                    self.status_message.grid_remove()
            except tk.TclError:
                pass

        self.window.after(3000, _clear_status)

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

        self.blocked_text_input = None
        self.unblocked_text_input = None

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
        note_label = tk.Label(
            note_frame,
            text=note_text,
            font=("Arial", 10),
            fg='#ff9500',  # Оранжевый цвет для выделения
            bg='#182030',
            justify=tk.CENTER,
            wraplength=400,
        )
        note_label.pack(fill=tk.X)

        def _sync_note_wrap(_event=None):
            try:
                aw = max(main_frame.winfo_width(), 1)
                note_label.config(wraplength=max(120, aw - 40))
            except tk.TclError:
                pass

        main_frame.bind("<Configure>", lambda _e: _sync_note_wrap())
        self.window.after_idle(_sync_note_wrap)

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

        place_toplevel_centered_on_parent(
            self.window, self.parent, min_width=360, min_height=300, margin_width=8, margin_height=12
        )
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

        # Кнопка «Добавление пользовательских IP-адресов» (две строки через \n)
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

        place_toplevel_centered_on_parent(
            self.window, self.parent, min_width=260, min_height=220, margin_width=8, margin_height=12
        )
        return self.window

    def run(self):
        """Запускает главное окно выбора настроек IPSet"""
        self.create_window()
        self.window.wait_window()
