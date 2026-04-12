"""DPI / window sizing helpers for Tkinter (Windows awareness + size-to-content)."""
import re
import sys
import ctypes
import tkinter as tk


def ensure_process_dpi_awareness():
    """Best-effort Per-Monitor v2 (or fallback) on Windows. No-op elsewhere. Call before tk.Tk()."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = ctypes.c_int
        if user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2):
            return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass


def set_window_size_to_fit_content(
    window,
    min_width=0,
    min_height=0,
    margin_width=0,
    margin_height=0,
):
    """Resize window to requested size of its children; optional minimums and extra margin."""
    window.update_idletasks()
    w = max(int(min_width), int(window.winfo_reqwidth()) + int(margin_width))
    h = max(int(min_height), int(window.winfo_reqheight()) + int(margin_height))
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    w = min(w, max(1, sw))
    h = min(h, max(1, sh))
    window.geometry(f"{w}x{h}")
    return w, h


def clamp_position_on_screen(window, x, y, width, height, sw=None, sh=None):
    """Keep top-left (x, y) so the window stays on-screen.

    Если заданы ``sw``/``sh``, используются они (рабочая область с учётом дробного масштаба),
    иначе — ``winfo_screen*`` у ``window``.
    """
    if sw is None:
        sw = window.winfo_screenwidth()
    if sh is None:
        sh = window.winfo_screenheight()
    sw = max(int(sw), 1)
    sh = max(int(sh), 1)
    x = int(max(0, min(x, sw - width)))
    y = int(max(0, min(y, sh - height)))
    return x, y


def center_toplevel_on_screen(window):
    """Центрирует окно на текущем экране (после задания размера)."""
    try:
        window.deiconify()
        window.lift()
    except Exception:
        pass
    window.update_idletasks()
    # Сразу после geometry("WxH") winfo_width часто ещё 1 — опираемся на req и реальный размер
    w = max(
        int(window.winfo_reqwidth()),
        int(window.winfo_width()),
    )
    h = max(
        int(window.winfo_reqheight()),
        int(window.winfo_height()),
    )
    w = max(w, 1)
    h = max(h, 1)
    sw = max(1, int(window.winfo_screenwidth()))
    sh = max(1, int(window.winfo_screenheight()))
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    x, y = clamp_position_on_screen(window, x, y, w, h)
    window.geometry(f"+{x}+{y}")


def application_tk_root(widget):
    """Находит корневое окно приложения (tk.Tk), поднимаясь по .master."""
    if widget is None:
        return None
    w = widget
    while w is not None and not isinstance(w, tk.Tk):
        w = w.master
    return w


def _parse_winfo_geometry(geom):
    """Парсит winfo_geometry(): 'WxH+X+Y' (X,Y со знаком)."""
    m = re.match(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$", (geom or "").strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def geometry_resize_keep_position(window, width, height):
    """Сменить размер окна, сохранив +x+y.

    На части WM (Steam/Linux) вызов ``geometry("WxH")`` без позиции сбрасывает Y в угол экрана.
    """
    ww = max(int(width), 1)
    hh = max(int(height), 1)
    try:
        window.update_idletasks()
    except tk.TclError:
        pass
    parsed = _parse_winfo_geometry(window.winfo_geometry())
    if parsed:
        _, _, xa, ya = parsed
        window.geometry(f"{ww}x{hh}{int(xa):+d}{int(ya):+d}")
    else:
        window.geometry(f"{ww}x{hh}")


def _effective_child_wh(child):
    """Внешние размеры дочернего окна: max(geometry, req, winfo) после полного update."""
    try:
        child.update_idletasks()
        child.update()
    except Exception:
        pass
    rw = max(int(child.winfo_reqwidth()), 1)
    rh = max(int(child.winfo_reqheight()), 1)
    parsed = _parse_winfo_geometry(child.winfo_geometry())
    if parsed:
        gw, gh, _, _ = parsed
        return max(gw, rw, int(child.winfo_width()), 1), max(gh, rh, int(child.winfo_height()), 1)
    return max(rw, int(child.winfo_width()), 1), max(rh, int(child.winfo_height()), 1)


def _wm_transient_master_path(child):
    try:
        m = child.tk.call("wm", "transient", child._w)
        if isinstance(m, bytes):
            m = m.decode("utf-8", "replace")
        return str(m) if m else ""
    except tk.TclError:
        return ""


def _anchor_outer_rect(anchor):
    """Размер и левый верх главного окна: только winfo_root* + winfo_* (без парсинга geometry)."""
    try:
        anchor.update_idletasks()
        anchor.update()
    except Exception:
        pass
    px = int(anchor.winfo_rootx())
    py = int(anchor.winfo_rooty())
    pw = max(int(anchor.winfo_width()), int(anchor.winfo_reqwidth()), 1)
    ph = max(int(anchor.winfo_height()), int(anchor.winfo_reqheight()), 1)
    return pw, ph, px, py


def _place_child_centered_on_anchor(child, anchor, fixed_wh=None):
    """Ставит child по центру главного окна (anchor), с запасом по экрану; ``geometry +x+y`` абсолютные.

    Если центр по якорю выходит за края монитора (высокая модалка при 150% и т.п.),
    по вертикали/горизонтали подставляется центр экрана, чтобы не прижимать к y=0.

    Если задан ``fixed_wh`` — размеры для geometry/clamp (окно уже собрано по размеру);
    иначе — :func:`_effective_child_wh` как у ``place_toplevel_centered_on_parent``.
    """
    try:
        # Иначе часть WM (особенно с transient) трактует +x+y как смещение от родителя
        child.wm_positionfrom("user")
    except tk.TclError:
        pass
    pw, ph, px, py = _anchor_outer_rect(anchor)
    if fixed_wh is not None:
        w = max(int(fixed_wh[0]), 1)
        h = max(int(fixed_wh[1]), 1)
    else:
        w, h = _effective_child_wh(child)
    # Размеры экрана с главного окна: у нового Toplevel child.winfo_screen* часто ложь до map,
    # clamp(child, …) без sw/sh давал sh−h≈38 и y=38 при gy0=184 (лог post_place_final).
    sw_anchor = max(1, int(anchor.winfo_screenwidth()))
    sh_anchor = max(1, int(anchor.winfo_screenheight()))
    # Сначала центр по главному окну; если модалка выше/шире области якоря (часто при 150%),
    # py + (ph−h)//2 уходит в минус или за нижний край — clamp даёт y=0 («прилипание» к верху).
    # Тогда берём центр по экрану, как раньше для высоких Toplevel.
    gx_parent = px + (pw - w) // 2
    if gx_parent < 0 or gx_parent + w > sw_anchor:
        gx0 = max(0, (sw_anchor - w) // 2) if w < sw_anchor else max(0, sw_anchor - w)
    else:
        gx0 = gx_parent
    gy_parent = py + (ph - h) // 2
    if gy_parent < 0 or gy_parent + h > sh_anchor:
        gy0 = max(0, (sh_anchor - h) // 2) if h < sh_anchor else max(0, sh_anchor - h)
    else:
        gy0 = gy_parent
    x, y = clamp_position_on_screen(
        child, gx0, gy0, w, h, sw=sw_anchor, sh=sh_anchor
    )
    transient_m = _wm_transient_master_path(child)
    needs_transient_clear = transient_m == str(anchor._w)
    gx, gy = x, y
    # Подгонка по winfo_root*: часть WM смещает окно относительно geometry (+x+y).
    _tol = 5
    rx = ry = None
    for _attempt in range(8):
        if needs_transient_clear:
            try:
                child.tk.call("wm", "transient", child._w, "")
            except tk.TclError:
                pass
        try:
            child.geometry(f"{w}x{h}+{gx}+{gy}")
        except tk.TclError:
            break
        if needs_transient_clear:
            try:
                child.tk.call("wm", "transient", child._w, anchor._w)
            except tk.TclError:
                pass
            try:
                child.update_idletasks()
                child.geometry(f"{w}x{h}+{gx}+{gy}")
            except tk.TclError:
                pass
        try:
            child.update_idletasks()
            child.update()
        except Exception:
            pass
        try:
            child.update_idletasks()
            rx = int(child.winfo_rootx())
            ry = int(child.winfo_rooty())
        except Exception:
            rx, ry = None, None
            break
        if rx is None or ry is None:
            break
        if abs(rx - x) <= _tol and abs(ry - y) <= _tol:
            break
        # Сдвиг geometry так, чтобы winfo_root совпал с целевым (x,y) — устраняет смещение WM/рамки.
        gx = gx - (rx - x)
        gy = gy - (ry - y)
        gx, gy = clamp_position_on_screen(
            child, gx, gy, w, h, sw=sw_anchor, sh=sh_anchor
        )
    try:
        child.wm_positionfrom("user")
    except tk.TclError:
        pass
    try:
        child.geometry(f"{w}x{h}+{gx}+{gy}")
    except tk.TclError:
        pass
    # Цикл выше может выйти по |ry−y|≤tol при «ложном» ry; строка winfo_geometry при этом +38 (лог).
    _prev_tail_gy = None
    for _tail in range(8):
        try:
            child.update_idletasks()
            child.update()
        except Exception:
            pass
        try:
            ry3 = int(child.winfo_rooty())
        except tk.TclError:
            break
        # Нельзя использовать ry3 >= y−tol: при слишком большой ry3 (окно ниже цели) условие тоже
        # выполняется и цикл выходит, не поднимая окно — визуально «прилипание» к верху (150% / Gamescope).
        if abs(ry3 - int(y)) <= _tol:
            break
        gy = int(gy) + (int(y) - ry3)
        gx, gy = clamp_position_on_screen(
            child, gx, gy, w, h, sw=sw_anchor, sh=sh_anchor
        )
        if _prev_tail_gy is not None and gy == _prev_tail_gy:
            break
        _prev_tail_gy = gy
        try:
            child.wm_positionfrom("user")
            child.geometry(f"{w}x{h}+{gx}+{gy}")
        except tk.TclError:
            break
    # Gamescope / HiDPI: winfo_rooty иногда отстаёт от целевого y без withdraw — несколько
    # дополнительных шагов только для fixed_wh (окно уже с финальным размером).
    if fixed_wh is not None:
        for _fin in range(4):
            try:
                child.update_idletasks()
                child.update()
                ry_f = int(child.winfo_rooty())
            except tk.TclError:
                break
            if abs(ry_f - int(y)) <= _tol * 2:
                break
            gy = int(gy) + (int(y) - ry_f)
            gx, gy = clamp_position_on_screen(
                child, gx, gy, w, h, sw=sw_anchor, sh=sh_anchor
            )
            try:
                child.wm_positionfrom("user")
                child.geometry(f"{w}x{h}+{gx}+{gy}")
            except tk.TclError:
                break


def center_toplevel_on_parent(child, parent=None):
    """Центрирует child относительно главного окна приложения (tk.Tk).

    Использует winfo_rootx/y и размеры главного окна; перед geometry вызывается
    wm positionfrom user (абсолютные координаты). Размещение после idle; внутри — повтор geometry до сходимости с WM.
    Центр со знаком; transient на якорь снимается на время каждой попытки geometry.
    """
    anchor = application_tk_root(parent) if parent is not None else None
    if anchor is None:
        try:
            child.deiconify()
            child.lift()
        except Exception:
            pass
        child.update_idletasks()
        center_toplevel_on_screen(child)
        return

    def _pass():
        try:
            if not child.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            child.deiconify()
            child.lift()
        except Exception:
            pass
        child.update_idletasks()
        try:
            anchor.update_idletasks()
            anchor.update()
        except Exception:
            pass
        _place_child_centered_on_anchor(child, anchor)

    try:
        child.after_idle(_pass)
    except Exception:
        _pass()


def center_toplevel_on_parent_with_size(
    child, parent, width, height, immediate=False
):
    """Центрирование относительно главного окна с **фиксированными** размерами окна.

    Тот же путь, что у :func:`center_toplevel_on_parent` (transient, цикл по ``winfo_root*``),
    но без :func:`_effective_child_wh` — для окон вроде «Разблокировки сервисов», где размер
    уже задан (canvas + max_h), а общий ``place_toplevel_centered_on_parent`` раздул бы высоту.

    ``immediate=True`` — без ``after_idle`` (иначе между вызовами ``geometry("WxH")`` без +x+y
    и центром окно успевает отрисоваться у верхней кромки).
    """
    w = max(int(width), 1)
    h = max(int(height), 1)
    anchor = application_tk_root(parent) if parent is not None else None
    if anchor is None:
        try:
            child.deiconify()
            child.lift()
        except Exception:
            pass
        child.update_idletasks()
        center_toplevel_on_screen(child)
        return

    def _pass():
        try:
            if not child.winfo_exists():
                return
        except tk.TclError:
            return
        try:
            child.deiconify()
            child.lift()
        except Exception:
            pass
        child.update_idletasks()
        try:
            anchor.update_idletasks()
            anchor.update()
        except Exception:
            pass
        _place_child_centered_on_anchor(child, anchor, fixed_wh=(w, h))

    if immediate:
        _pass()
    else:
        try:
            child.after_idle(_pass)
        except Exception:
            _pass()


def fit_toplevel_to_content(
    window,
    min_width=240,
    min_height=120,
    margin_width=8,
    margin_height=12,
):
    """minsize по содержимому и geometry с запасом; ограничение размером экрана."""
    window.update_idletasks()
    req_w = window.winfo_reqwidth()
    req_h = window.winfo_reqheight()
    bw = max(int(min_width), int(req_w))
    bh = max(int(min_height), int(req_h))
    window.minsize(bw, bh)
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    w = min(bw + int(margin_width), max(1, sw))
    h = min(bh + int(margin_height), max(1, sh))
    w = max(w, bw)
    h = max(h, bh)
    window.geometry(f"{w}x{h}")
    return w, h


def place_toplevel_centered_on_parent(
    child,
    parent,
    min_width=260,
    min_height=100,
    margin_width=8,
    margin_height=10,
    *,
    fixed_content_size=None,
    immediate=False,
):
    """Размер по содержимому и центрирование относительно главного окна (tk.Tk).

    ``fixed_content_size=(w, h)`` — не вызывать :func:`fit_toplevel_to_content` (у окон со
    скроллом ``winfo_reqheight`` часто завышен); выставить ``WxH`` и центрировать через
    :func:`center_toplevel_on_parent_with_size`. ``immediate=True`` — только вместе с
    ``fixed_content_size``: синхронное размещение без ``after_idle`` (меньше мигания).
    """
    try:
        child.update_idletasks()
    except tk.TclError:
        pass
    if fixed_content_size is not None:
        fw = max(1, int(fixed_content_size[0]))
        fh = max(1, int(fixed_content_size[1]))
        try:
            child.update_idletasks()
        except tk.TclError:
            pass
        try:
            child.geometry(f"{fw}x{fh}")
        except tk.TclError:
            pass
        try:
            child.update_idletasks()
        except tk.TclError:
            pass
        center_toplevel_on_parent_with_size(
            child, parent, fw, fh, immediate=bool(immediate)
        )
        return
    fit_toplevel_to_content(
        child,
        min_width=min_width,
        min_height=min_height,
        margin_width=margin_width,
        margin_height=margin_height,
    )
    center_toplevel_on_parent(child, parent)
