import tkinter as tk

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
