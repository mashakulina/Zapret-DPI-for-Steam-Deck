import tkinter as tk
import tkinter.font as tkfont


def uniform_button_width_for_font(master, font, *texts, pad_chars=2):
    """Ширина tk.Button в символах (width) по самой длинной строке; pad_chars — запас."""
    if not texts:
        return max(1, 1 + int(pad_chars))
    try:
        f = tkfont.Font(master=master, font=font)
        zero = f.measure("0")
        if zero < 1:
            zero = 1
        mw = 0
        for t in texts:
            if t is None:
                continue
            for line in str(t).split("\n"):
                mw = max(mw, f.measure(line))
        n = (mw + zero - 1) // zero + int(pad_chars)
        return max(1, n)
    except Exception:
        longest = 1
        for t in texts:
            if t is None:
                continue
            for line in str(t).split("\n"):
                longest = max(longest, len(line))
        return max(1, longest + int(pad_chars))


def create_hover_button(parent, text, command, **kwargs):
    """Создает кнопку с эффектом наведения"""
    # Базовые стили
    default_style = {
        'font': ('Arial', 10),
        'bg': '#15354D',
        'fg': 'white',
        'bd': 0,
        'padx': 10,
        'pady': 5,
        'highlightthickness': 0,
        'cursor': 'hand2',
        'relief': 'flat'
    }

    # Обновляем стили переданными параметрами
    default_style.update(kwargs)

    # Создаем кнопку
    btn = tk.Button(parent, text=text, command=command, **default_style)

    # Добавляем эффект наведения
    apply_hover_effect(btn)

    return btn

def apply_hover_effect(button):
    """Добавляет эффект наведения для кнопки"""
    original_bg = button.cget('bg')
    hover_bg = '#1E4A6E'  # Более светлый оттенок синего

    def on_enter(event):
        button.config(bg=hover_bg)

    def on_leave(event):
        button.config(bg=original_bg)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
