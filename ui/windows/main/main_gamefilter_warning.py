"""Модальное предупреждение Game Filter (вынесено из MainGameFilterMixin)."""
from __future__ import annotations

import os
import time
import tkinter as tk
from typing import Protocol

from core.dpi_utils import (
    _parse_winfo_geometry,
    _place_child_centered_on_anchor,
    application_tk_root,
    center_toplevel_on_screen,
    set_window_size_to_fit_content,
)
from core.tk_scale_lab_helpers import warning_dialog_scale


class GameFilterWarningHost(Protocol):
    root: tk.Misc

    def hide_game_filter_tooltip(self, event=None) -> None: ...
    def hide_icon_tooltip(self, event=None) -> None: ...
    def hide_status_tooltip(self, event=None) -> None: ...
    def _on_warning_accept(self, warning_window: tk.Toplevel) -> None: ...


def show_game_filter_warning_dialog(host: GameFilterWarningHost) -> None:
    """Показывает предупреждение о Game Filter с адаптацией под Steam Deck"""

    # Закрываем все всплывающие подсказки перед показом окна
    host.hide_game_filter_tooltip()
    host.hide_icon_tooltip()
    host.hide_status_tooltip()

    # Сначала делаем главное окно видимым и поднимаем его
    host.root.deiconify()
    host.root.lift()
    host.root.focus_force()

    # Создаем окно предупреждения
    warning_window = tk.Toplevel(host.root)
    warning_window.title("ВНИМАНИЕ!")
    warning_window.configure(bg='#182030')
    warning_window.resizable(False, False)

    # Определяем функцию для проверки Steam Deck
    def is_steamdeck():
        """Проверяет, работает ли приложение на Steam Deck"""
        try:
            # Проверяем системные файлы Steam Deck
            steamdeck_files = [
                "/sys/devices/platform/steamdeck_hwmon",
                "/sys/devices/virtual/dmi/id/product_name"
            ]

            # Наличие hwmon — железо Steam Deck; DMI без общих подстрок «deck» (ложные срабатывания на ПК).
            for file in steamdeck_files:
                if not os.path.exists(file):
                    continue
                if "steamdeck_hwmon" in file.replace("\\", "/"):
                    return True
                with open(file, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read().lower()
                if "steam deck" in content or "jupiter" in content or "galileo" in content:
                    return True

            # Проверяем переменные окружения
            if 'DECK' in os.path.environ.get('XDG_SESSION_DESKTOP', '').upper():
                return True

            # Проверяем разрешение экрана (Steam Deck: 1280x800 или 1280x720)
            try:
                screen_width = warning_window.winfo_screenwidth()
                screen_height = warning_window.winfo_screenheight()

                # Обычное разрешение Steam Deck
                if (screen_width == 1280 and screen_height == 800) or \
                   (screen_width == 1280 and screen_height == 720):
                    return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    # Получаем размеры экрана
    screen_width = warning_window.winfo_screenwidth()
    screen_height = warning_window.winfo_screenheight()

    # --- Учёт ориентации ---
    if screen_height > screen_width:
        # Портретная ориентация (например, у Steam Deck в вертикальном режиме)
        screen_width, screen_height = screen_height, screen_width

    # Эталонные размеры окна с учётом DPI (100% ≈ 1.0, 125% ≈ 1.25). При f>1 шрифты растут сильнее
    # по вертикали — чуть больший коэффициент по ширине, меньший по высоте, чтобы пропорции не «заваливались».
    f = warning_dialog_scale(host.root)
    extra = max(0.0, float(f) - 1.0)
    base_width = int(round(470.0 * f * (1.0 + 0.22 * extra)))
    base_height = int(round(340.0 * f * (1.0 + 0.09 * extra)))
    base_width = max(380, min(base_width, int(screen_width) - 32))
    base_height = max(280, min(base_height, int(screen_height) - 48))

    # --- Подстройка под Steam Deck / SteamOS ---
    on_steamdeck = is_steamdeck()

    if on_steamdeck:
        # Целевые минимумы; итоговый размер и позиция — после сборки UI (fit + центр по главному окну)
        width = min(base_width - 60, screen_width - 80)
        height = min(base_height - 60, screen_height - 80)

        # Делаем более читаемым для Steam Deck
        font_title = ("Arial", 14, "bold")
        font_warning = ("Arial", 11)
        font_problems = ("Arial", 9)
        font_final = ("Arial", 10, "bold")
        font_buttons = ("Arial", 10)
        button_padx = 12
        button_pady = 6
        button_width = 10
        padx_main = 15  # Меньше отступы
        pady_main = 10
    else:
        # На обычных системах
        width = base_width
        height = base_height
        font_title = ("Arial", 16, "bold")
        font_warning = ("Arial", 12)
        font_problems = ("Arial", 10)
        font_final = ("Arial", 11, "bold")
        font_buttons = ("Arial", 11)
        button_padx = 20
        button_pady = 8
        button_width = 12
        padx_main = 20
        pady_main = 15

    # Фиксированный перенос по целевой ширине (не winfo_width при Configure — иначе при 1px
    # получается wraplength=120, огромная высота req и «вытянутое» окно после fit_toplevel).
    wrap_px = max(120, width - 2 * int(padx_main))

    # Внешняя колонка фиксированной ширины: перенос и высота не «плавают» с размером Toplevel (лог: 409 vs 644 px).
    outer = tk.Frame(
        warning_window,
        bg='#182030',
        width=int(width),
        height=min(max(400, int(screen_height) - 80), 900),
    )
    outer.pack(anchor=tk.N)
    outer.pack_propagate(False)

    main_frame = tk.Frame(outer, bg='#182030', padx=padx_main, pady=pady_main)
    main_frame.pack(fill=tk.X)

    # Заголовок
    title_label = tk.Label(
        main_frame,
        text="ВНИМАНИЕ!",
        font=font_title,
        fg='#ff9500',
        bg='#182030'
    )
    title_label.pack(pady=(0, 10))

    # Основное предупреждение (перенос по ширине окна, без фиксации wraplength к начальной geometry)
    warning_text = "Данный фильтр является экспериментальной функцией"
    warning_label = tk.Label(
        main_frame,
        text=warning_text,
        font=font_warning,
        fg='white',
        bg='#182030',
        justify=tk.CENTER,
        anchor=tk.CENTER,
        wraplength=wrap_px,
    )
    warning_label.pack(pady=(0, 15), fill=tk.X)

    # Подробности о проблемах
    problems_frame = tk.Frame(main_frame, bg='#182030')
    problems_frame.pack(fill=tk.X, pady=(0, 12))

    problems_title = tk.Label(
        problems_frame,
        text="Возможные проблемы на Steam Deck:",
        font=font_problems,
        fg='#ff3b30',
        bg='#182030',
        anchor=tk.W,
    )
    problems_title.pack(fill=tk.X, pady=(0, 5))

    problems = [
        "• черный экран после перехода с рабочего стола в игровой режим. Лучше перезагрузиться",
        "• долгая загрузка после включения/перезагрузки",
        "• скорее всего не будет работать Youtube и Discord. Нужно будет отключать GameFilter",
        "• возможны другие нестабильности в работе",
    ]
    problem_wrap_labels: list[tk.Label] = []
    for problem in problems:
        pl = tk.Label(
            problems_frame,
            text=problem,
            font=font_problems,
            fg='#AAAAAA',
            bg='#182030',
            anchor=tk.NW,
            justify=tk.LEFT,
            wraplength=wrap_px,
        )
        problem_wrap_labels.append(pl)
        pl.pack(fill=tk.X, pady=(0, 6), anchor=tk.NW)

    # Финальное предупреждение
    final_warning = tk.Label(
        main_frame,
        text="Пользоваться данной функцией на свой страх и риск",
        font=font_final,
        fg='#ff9500',
        bg='#182030',
        justify=tk.CENTER,
        anchor=tk.CENTER,
        wraplength=wrap_px,
    )
    final_warning.pack(pady=(0, 12), fill=tk.X)

    # Фрейм для кнопок
    buttons_frame = tk.Frame(main_frame, bg='#182030')
    buttons_frame.pack(fill=tk.X)

    buttons_center_frame = tk.Frame(buttons_frame, bg='#182030')
    buttons_center_frame.pack()

    # Стиль кнопок
    button_style = {
        'font': font_buttons,
        'bg': '#15354D',
        'fg': 'white',
        'bd': 0,
        'padx': button_padx,
        'pady': button_pady,
        'width': button_width,
        'highlightthickness': 0,
        'cursor': 'hand2'
    }

    # Кнопка "Включить"
    enable_button = tk.Button(
        buttons_center_frame,
        text="Включить",
        command=lambda: host._on_warning_accept(warning_window),
        **button_style
    )
    enable_button.pack(side=tk.LEFT, padx=(0, 10))

    # Добавляем эффект наведения
    enable_button.bind("<Enter>", lambda e: enable_button.config(bg='#1e4a6a'))
    enable_button.bind("<Leave>", lambda e: enable_button.config(bg='#15354D'))

    # Кнопка "Назад"
    cancel_button = tk.Button(
        buttons_center_frame,
        text="Назад",
        command=warning_window.destroy,
        **button_style
    )
    cancel_button.pack(side=tk.LEFT)

    # Добавляем эффект наведения
    cancel_button.bind("<Enter>", lambda e: cancel_button.config(bg='#1e4a6a'))
    cancel_button.bind("<Leave>", lambda e: cancel_button.config(bg='#15354D'))

    wrap_labels: list[tk.Label] = [warning_label, final_warning, *problem_wrap_labels]

    def _apply_wrap_for_outer(wcol: int) -> None:
        wp = max(120, int(wcol) - 2 * int(padx_main))
        for lb in wrap_labels:
            lb.config(wraplength=wp)

    outer.update_idletasks()
    outer_w = max(int(width), int(main_frame.winfo_reqwidth()))
    outer_h = max(1, int(main_frame.winfo_reqheight()))
    outer.config(width=outer_w, height=outer_h)
    outer.update_idletasks()
    # Если масштаб «потерялся» (~1.0), колонка узкая — много строк и огромная высота (лог ~473×644).
    # Только расширять outer недостаточно: нужно обновить wraplength у всех Label.
    sw_outer = int(warning_window.winfo_screenwidth())
    wrap_adjust_iters = 0
    for _ in range(6):
        if outer_h <= max(440, int(outer_w * 1.3)):
            break
        grow = min(max(24, outer_w // 8), sw_outer - outer_w - 40)
        if grow < 16:
            break
        outer_w += grow
        outer.config(width=outer_w)
        _apply_wrap_for_outer(outer_w)
        outer.update_idletasks()
        outer_h = max(1, int(main_frame.winfo_reqheight()))
        outer.config(height=outer_h)
        outer.update_idletasks()
        wrap_adjust_iters += 1

    # ОБЯЗАТЕЛЬНО для SteamOS/Wayland
    warning_window.transient(host.root)  # Делаем окно дочерним
    warning_window.grab_set()  # Делаем модальным

    warning_window.update_idletasks()
    warning_window.update()

    # Не fit_toplevel_to_content: он ставит minsize(max(min_w, req_w), …) и при min_w=580
    # раздувает ширину до 580 при низкой высоте контента → «полоска» 580×350 (см. лог post_fit/post_place).
    try:
        warning_window.minsize(1, 1)
    except tk.TclError:
        pass
    fw, fh = set_window_size_to_fit_content(
        warning_window,
        min_width=0,
        min_height=0,
        margin_width=8,
        margin_height=12,
    )
    try:
        warning_window.lift()
    except tk.TclError:
        pass
    anchor = application_tk_root(host.root)
    if anchor is not None:
        try:
            host.root.update_idletasks()
            host.root.update()
        except tk.TclError:
            pass
        _place_child_centered_on_anchor(warning_window, anchor)
    else:
        center_toplevel_on_screen(warning_window)
    warning_window.update_idletasks()
    # WM/transient иногда ужимает Toplevel ниже winfo_req+margin от set_window_size_to_fit_content.
    try:
        _parsed_geom = _parse_winfo_geometry(warning_window.winfo_geometry())
        if _parsed_geom:
            _gw0, _gh0, _gx0, _gy0 = _parsed_geom
            if _gw0 < int(fw) or _gh0 < int(fh):
                warning_window.geometry(
                    f"{int(fw)}x{int(fh)}{_gx0:+d}{_gy0:+d}"
                )
                warning_window.update_idletasks()
    except tk.TclError:
        pass

    # Для Steam Deck делаем дополнительную проверку
    if on_steamdeck:
        # Поднимаем окно на самый верх
        warning_window.attributes('-topmost', True)
        warning_window.after(100, lambda: warning_window.attributes('-topmost', False))

        # Фокусируем окно
        warning_window.focus_force()

        # Обновляем несколько раз для надежности
        for _ in range(3):
            warning_window.update()
            time.sleep(0.05)

    # Связываем закрытие окна с кнопкой отмена
    warning_window.protocol("WM_DELETE_WINDOW", warning_window.destroy)

    # Ждем завершения окна
    host.root.wait_window(warning_window)
