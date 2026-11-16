"""Переходы между живыми окнами без повторного создания предыдущего экрана."""
import tkinter as tk


def run_child_window(window, open_child, *, on_return=None):
    """Скрывает экран на время дочернего ``run()``, затем возвращает его.

    ``open_child`` включает создание окна: даже ошибка конструктора должна
    вернуть предыдущий экран. Дочерний ``run()`` ожидает ``wait_window()``.
    """
    if getattr(window, "_navigation_child_open", False):
        return None
    try:
        if not window.winfo_exists():
            return None
        owns_grab = window.grab_current() == window
        grab_status = window.grab_status() if owns_grab else None
    except tk.TclError:
        return None

    window._navigation_child_open = True
    try:
        if owns_grab:
            window.grab_release()
        window.withdraw()
        return open_child()
    finally:
        window._navigation_child_open = False
        restored = False
        try:
            if window.winfo_exists():
                window.deiconify()
                window.lift()
                window.focus_set()
                if owns_grab:
                    if grab_status == "global":
                        window.grab_set_global()
                    else:
                        window.grab_set()
                restored = True
        except tk.TclError:
            # Выход или перезапуск приложения уничтожает всю иерархию Tk.
            pass
        if restored and on_return is not None:
            on_return()
