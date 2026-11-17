"""Переходы между живыми окнами и отмена цепочки через рамку окна."""
import tkinter as tk


def _application_root(window):
    current = window
    while vars(current).get('master') is not None:
        current = current.master
    return current


def _cancel_owned_callbacks(window):
    """Отменяет after уничтожаемых виджетов, сохраняя таймеры главного окна."""
    commands = set(getattr(window, '_tclCommands', None) or ())
    for identifier in window.tk.call('after', 'info'):
        try:
            script = window.tk.call('after', 'info', identifier)[0]
            if window.tk.splitlist(script)[0] in commands:
                window.after_cancel(identifier)
        except (tk.TclError, IndexError):
            pass
    for child in window.winfo_children():
        _cancel_owned_callbacks(child)


def _close_original(window):
    if not window.winfo_exists():
        return
    script = getattr(window, '_navigation_original_close', '')
    # Сначала родной обработчик: он останавливает потоки/опрос или отклоняет
    # закрытие во время уже выполняемого применения настроек.
    if script:
        window.tk.eval(script)
    else:
        window.destroy()


def close_window_chain(window):
    """Закрывает окно и отменяет его активную цепочку до главного окна.

    Отмена распространяется только после успешного закрытия: родной обработчик
    вправе оставить окно открытым, пока завершает необратимую операцию.
    """
    frames = getattr(window, '_navigation_frames', ())
    try:
        _close_original(window)
        if window.winfo_exists():
            return
    except tk.TclError:
        return
    for frame in frames:
        frame['cancelled'] = True


def prepare_window_navigation(window):
    """Идемпотентно настраивает закрытие рамкой; возвращает ``None``.

    Вызывать после назначения собственного WM_DELETE_WINDOW и до обработки
    событий (не позднее ``wait_window``). «Назад»/Escape сохраняют свои команды.
    Обычное окно закрывается само; окно внутри ``run_child_window`` отменяет
    активные шаги цепочки, не возвращая скрытые экраны. Повторный вызов обновляет
    цепочку, но не добавляет callback или привязку. Главное Tk не перехватывается.
    """
    root = _application_root(window)
    if root is window:
        return
    window._navigation_frames = tuple(getattr(root, '_navigation_stack', ()))
    if getattr(window, '_navigation_close_prepared', False):
        return
    window._navigation_close_prepared = True
    window._navigation_original_close = window.protocol('WM_DELETE_WINDOW')
    window.protocol('WM_DELETE_WINDOW', lambda: close_window_chain(window))

    def cleanup(event):
        # События потомков также проходят через bindtag Toplevel. Отменяем
        # их after до того, как Tk удалит зарегистрированные Python-команды.
        try:
            _cancel_owned_callbacks(event.widget)
        except tk.TclError:
            pass
        if event.widget == window:
            window._navigation_frames = ()

    window.bind('<Destroy>', cleanup, add='+')
    original_destroy = window.destroy

    def destroy():
        try:
            _cancel_owned_callbacks(window)
            grab = window.grab_current()
            current = grab
            while current is not None:
                if current == window:
                    grab.grab_release()
                    break
                current = getattr(current, 'master', None)
        except tk.TclError:
            pass
        original_destroy()

    window.destroy = destroy


def run_child_window(window, open_child, *, on_return=None):
    """Скрывает шаг; «Назад» возвращает его, рамка отменяет всю цепочку.

    ``open_child`` включает создание окна: даже ошибка конструктора должна
    вернуть предыдущий экран. Дочернее окно вызывает prepare_window_navigation.
    """
    if getattr(window, '_navigation_child_open', False):
        return None
    try:
        if not window.winfo_exists():
            return None
        owns_grab = window.grab_current() == window
        grab_status = window.grab_status() if owns_grab else None
    except tk.TclError:
        return None

    root = _application_root(window)
    stack = getattr(root, '_navigation_stack', None)
    if stack is None:
        stack = root._navigation_stack = []
    frame = {'window': window, 'cancelled': False}
    stack.append(frame)
    window._navigation_child_open = True
    try:
        if owns_grab:
            window.grab_release()
        window.withdraw()
        return open_child()
    finally:
        stack.remove(frame)
        window._navigation_child_open = False
        restored = False
        try:
            if frame['cancelled'] and window is not root:
                _close_original(window)
            elif window.winfo_exists():
                window.deiconify()
                window.lift()
                window.focus_set()
                if owns_grab:
                    if grab_status == 'global':
                        window.grab_set_global()
                    else:
                        window.grab_set()
                restored = True
        except tk.TclError:
            # Выход или перезапуск приложения уничтожает всю иерархию Tk.
            pass
        if restored and on_return is not None:
            on_return()
