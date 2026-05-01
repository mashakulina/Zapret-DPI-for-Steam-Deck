import tkinter as tk
import webbrowser
import subprocess
import urllib.parse
import re
import os
from urllib.request import urlopen
from ui.components.button_styler import create_hover_button
from core.dpi_utils import (
    center_toplevel_on_parent,
    fit_toplevel_to_content,
    place_toplevel_centered_on_parent,
)
from core.tk_scale_lab_helpers import logical_ui_scale, warning_dialog_scale, winfo_dpi
from core.manager_config import VERSION_CONFIG
_last_available_site = None
_last_check_time = 0


def setup_window_properties(self):
    """Настройка свойств окна для корректного отображения"""
    self.root.title("Zapret DPI Manager")

    # Устанавливаем WM_CLASS (БЕЗ ПРОБЕЛОВ!)
    try:
        self.root.wm_class("ZapretDPIManager")
    except Exception:
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
    dialog.configure(bg='#182030')

    # Заголовок
    title_frame = tk.Frame(dialog, bg='#182030', pady=15)
    title_frame.pack(fill=tk.X)

    tk.Label(title_frame, text="Информация",
             font=("Arial", 14, "bold"), bg='#182030', fg='white').pack()

    # Основное содержимое
    content_frame = tk.Frame(dialog, bg='#182030', padx=20)
    # Без expand: иначе min_height окна даёт «резиновый» зазор между контентом и кнопкой
    # при каждом пересчёте wraplength по <Configure>.
    content_frame.pack(fill=tk.X)

    # Информационное сообщение
    info_text = (
        "Zapret DPI Manager помогает получить доступ к Youtube и Discord на Steam Deck"
    )

    info_frame = tk.Frame(content_frame, bg='#182030')
    info_frame.pack(fill=tk.X)

    def _info_layout_u():
        return max(0.85, min(4.0, float(logical_ui_scale(parent))))

    def _scaled_info_wraplength():
        u = _info_layout_u()
        ww = int(round(395 * u))
        pd = int(round(50 * u))
        return max(120, ww - pd)

    info_label = tk.Label(info_frame, text=info_text,
                        font=('Arial', 11),
                        bg='#182030',
                        fg='#ff9500',
                        wraplength=_scaled_info_wraplength(),
                        justify=tk.CENTER
                        )
    info_label.pack(fill=tk.X)

    links_shell = tk.Frame(content_frame, bg='#182030')
    links_shell.pack(fill=tk.X)

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
    create_link_with_icon(
        links_shell, "💻", "Страница Zapret DPI Manager на GitHub", open_github_page
    )

    # Отображаем версии в одну строку по центру
    versions_frame = tk.Frame(content_frame, bg='#182030')
    versions_frame.pack(fill=tk.X)

    program_version = VERSION_CONFIG.get("current_version", "Неизвестно")
    version_text = f"Zapret DPI Manager · {program_version}"
    version_label = tk.Label(versions_frame, text=version_text,
                           font=("Arial", 9), fg='#5BA06A', bg='#182030')
    version_label.pack(anchor=tk.CENTER)

    def _apply_info_vertical_spacing():
        u = _info_layout_u()
        top_btn = max(10, int(round(14 * u)))
        try:
            info_label.pack_configure(pady=(0, max(4, int(round(6 * u)))))
            info_frame.pack_configure(pady=(0, max(16, int(round(20 * u)))))
            links_shell.pack_configure(pady=(max(6, int(round(8 * u))), 0))
            versions_frame.pack_configure(pady=(max(8, int(round(10 * u))), 0))
            button_frame.pack_configure(pady=(top_btn, 15))
        except tk.TclError:
            pass

    def _sync_info_wrap_from_width(_event=None):
        try:
            cw = max(int(content_frame.winfo_width()), 1)
        except tk.TclError:
            return
        try:
            u = _info_layout_u()
            margin = max(24, int(round(32 * u)))
            base = _scaled_info_wraplength()
            wl = int(min(base, max(120, cw - margin)))
            try:
                cur = int(info_label.cget("wraplength"))
            except tk.TclError:
                cur = None
            if cur is not None and abs(cur - wl) < 8:
                return
            info_label.config(wraplength=wl)
        except tk.TclError:
            pass

    content_frame.bind("<Configure>", lambda _e: _sync_info_wrap_from_width(), add="+")

    # Кнопка закрытия
    button_frame = tk.Frame(dialog, bg='#182030')
    button_frame.pack(fill=tk.X, pady=(max(10, int(round(14 * _info_layout_u()))), 15))
    _apply_info_vertical_spacing()

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

    place_toplevel_centered_on_parent(
        dialog, parent, min_width=340, min_height=280, margin_width=8, margin_height=12
    )

    try:
        dialog.after_idle(_sync_info_wrap_from_width)
    except tk.TclError:
        pass

    def _current_scale_tuple():
        nu = float(warning_dialog_scale(parent))
        nl = float(logical_ui_scale(parent))
        try:
            ntk = float(dialog.tk.call("tk", "scaling", "-displayof", dialog))
        except Exception:
            ntk = None
        try:
            dtk = winfo_dpi(parent)
            ndpi = round(float(dtk), 2) if dtk is not None and dtk > 0 else None
        except (tk.TclError, TypeError, ValueError):
            ndpi = None
        return nu, nl, ntk, ndpi

    def _scale_tuple_changed(prev, cur):
        if abs(cur[0] - prev[0]) >= 0.02:
            return True
        if abs(cur[1] - prev[1]) >= 0.02:
            return True
        if cur[2] is None or prev[2] is None:
            if cur[2] != prev[2]:
                return True
        else:
            if abs(cur[2] - prev[2]) >= 0.02:
                return True
        if (cur[3] is None) != (prev[3] is None):
            return True
        if cur[3] is not None and prev[3] is not None:
            if abs(cur[3] - prev[3]) >= 0.9:
                return True
        return False

    _info_scale_snap = list(_current_scale_tuple())

    _poll_after_id = [None]
    _POLL_MS = 450

    def _cancel_info_scale_poll():
        if _poll_after_id[0] is not None:
            try:
                dialog.after_cancel(_poll_after_id[0])
            except tk.TclError:
                pass
            _poll_after_id[0] = None

    def _try_refit_info_for_scale():
        try:
            if not dialog.winfo_exists():
                return False
        except tk.TclError:
            return False
        cur_scale = _current_scale_tuple()
        if not _scale_tuple_changed(_info_scale_snap, cur_scale):
            return False
        _info_scale_snap[:] = list(cur_scale)
        try:
            info_label.config(wraplength=_scaled_info_wraplength())
        except tk.TclError:
            pass
        _apply_info_vertical_spacing()
        _sync_info_wrap_from_width()
        try:
            dialog.update_idletasks()
        except tk.TclError:
            pass
        try:
            fit_toplevel_to_content(
                dialog,
                min_width=340,
                min_height=280,
                margin_width=8,
                margin_height=12,
            )
            center_toplevel_on_parent(dialog, parent)
        except tk.TclError:
            pass
        return True

    def _poll_info_dpi_tick():
        _poll_after_id[0] = None
        _try_refit_info_for_scale()
        try:
            if dialog.winfo_exists():
                _poll_after_id[0] = dialog.after(_POLL_MS, _poll_info_dpi_tick)
        except tk.TclError:
            pass

    def _schedule_info_scale_probe(_evt=None):
        def _go():
            try:
                if not dialog.winfo_exists():
                    return
            except tk.TclError:
                return
            _try_refit_info_for_scale()

        try:
            dialog.after(200, _go)
        except tk.TclError:
            pass

    for _ev in ("<Map>", "<FocusIn>"):
        dialog.bind(_ev, lambda _e: _schedule_info_scale_probe(), add="+")

    try:
        dialog.bind("<Destroy>", lambda _e: _cancel_info_scale_poll(), add="+")
    except tk.TclError:
        pass
    try:
        _poll_after_id[0] = dialog.after(_POLL_MS, _poll_info_dpi_tick)
    except tk.TclError:
        pass

    # Устанавливаем фокус на диалоговое окно
    dialog.focus_set()

    # Ждем закрытия окна
    dialog.wait_window()
