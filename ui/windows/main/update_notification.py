"""Окно уведомления об обновлениях (вынесено из MainUpdatesMixin)."""
from __future__ import annotations

import tkinter as tk
from typing import Any, Protocol

from core.dpi_utils import center_toplevel_on_parent, fit_toplevel_to_content
from core.tk_scale_lab_helpers import (
    dampened_hi_dpi_factor,
    logical_ui_scale,
    warning_dialog_scale,
    winfo_dpi,
)


class UpdateNotificationHost(Protocol):
    root: tk.Misc

    def open_update_window(self, notification_window: tk.Toplevel) -> None: ...


def show_update_notification_dialog(
    host: UpdateNotificationHost,
    bundle_update_info: dict[str, Any] | None,
) -> None:
    """Показывает окно уведомления о доступном полном обновлении"""
    if not bundle_update_info:
        return

    _d_layout = float(dampened_hi_dpi_factor(warning_dialog_scale(host.root)))
    _d_font = float(dampened_hi_dpi_factor(logical_ui_scale(host.root)))
    scale_layout = [_d_layout]
    scale_font = [_d_font]
    f = scale_layout[0]

    title = "Доступно полное обновление"

    font_targets: list[tuple[tk.Misc, float, bool]] = []

    def _fz(pt: float) -> int:
        return max(7, int(round(float(pt) * float(scale_font[0]))))

    def _reg_font(widget: tk.Misc, pt: float, bold: bool = False) -> None:
        font_targets.append((widget, float(pt), bool(bold)))

    p_block = int(max(8, round(12 * f)))
    p_small = int(max(4, round(5 * f)))
    p_title_gap = int(max(12, round(20 * f)))
    p_info_gap = int(max(12, round(20 * f)))
    p_btn_frame = int(max(8, round(10 * f)))
    pad_main = int(max(8, round(10 * f)))

    notification_window = tk.Toplevel(host.root)
    notification_window.title(title)
    notification_window.configure(bg='#182030')
    notification_window.resizable(True, True)
    try:
        notification_window.transient(host.root)
    except tk.TclError:
        pass

    main_frame = tk.Frame(notification_window, bg='#182030', padx=pad_main, pady=pad_main)
    main_frame.pack(fill=tk.BOTH, expand=True)

    title_label = tk.Label(
        main_frame,
        text=title,
        font=("Arial", _fz(16), "bold"),
        fg='white',
        bg='#182030',
    )
    _reg_font(title_label, 16.0, True)
    title_label.pack(pady=(0, p_title_gap))

    info_label = tk.Label(
        main_frame,
        text="Рекомендуется обновиться для получения новых функций и исправлений ошибок",
        font=("Arial", _fz(11)),
        fg='#AAAAAA',
        bg='#182030',
        justify=tk.CENTER,
        wraplength=max(120, int(round(330 * f))),
    )
    _reg_font(info_label, 11.0, False)
    info_label.pack(pady=(0, p_info_gap), fill=tk.X)

    def _sync_info_wrap(_event=None):
        try:
            ff_l = float(scale_layout[0])
            aw = max(main_frame.winfo_width(), 1)
            margin = int(max(24, round(40 * ff_l)))
            info_label.config(wraplength=max(120, aw - margin))
        except tk.TclError:
            pass

    main_frame.bind("<Configure>", lambda _e: _sync_info_wrap(), add="+")
    notification_window.after_idle(_sync_info_wrap)

    updates_frame = tk.Frame(main_frame, bg='#182030')
    updates_frame.pack(fill=tk.X, pady=(0, 0))

    bundle_frame = tk.Frame(updates_frame, bg='#182030')
    bundle_frame.pack(fill=tk.X, pady=(0, p_block))

    header_frame = tk.Frame(bundle_frame, bg='#182030')
    header_frame.pack(fill=tk.X, pady=(0, p_small))

    bundle_name = tk.Label(
        header_frame,
        text="Менеджер и служба Zapret",
        font=("Arial", _fz(12), "bold"),
        fg='#0a84ff',
        bg='#182030',
    )
    _reg_font(bundle_name, 12.0, True)
    bundle_name.pack(pady=(0, 0))

    versions_frame = tk.Frame(bundle_frame, bg='#182030')
    versions_frame.pack(fill=tk.X, pady=p_small)

    center_container = tk.Frame(versions_frame, bg='#182030')
    center_container.pack(expand=True)

    current_version_label = tk.Label(
        center_container,
        text=f"{bundle_update_info['current']}",
        font=("Arial", _fz(11)),
        fg='#AAAAAA',
        bg='#182030',
    )
    _reg_font(current_version_label, 11.0, False)
    current_version_label.pack(side=tk.LEFT, padx=(0, 10))

    arrow_label = tk.Label(
        center_container,
        text="→",
        font=("Arial", _fz(11)),
        fg='white',
        bg='#182030',
    )
    _reg_font(arrow_label, 11.0, False)
    arrow_label.pack(side=tk.LEFT)

    new_version_label = tk.Label(
        center_container,
        text=f"Новая версия: {bundle_update_info['available']}",
        font=("Arial", _fz(11), "bold"),
        fg='#30d158',
        bg='#182030',
    )
    _reg_font(new_version_label, 11.0, True)
    new_version_label.pack(side=tk.LEFT, padx=(10, 0))

    buttons_frame = tk.Frame(main_frame, bg='#182030')
    buttons_frame.pack(fill=tk.X, pady=(0, p_btn_frame))

    center_frame = tk.Frame(buttons_frame, bg='#182030')
    center_frame.pack(expand=True)

    def _button_style(ff_l: float, ff_t: float) -> dict:
        fz_btn = max(8, int(round(10 * ff_t)))
        return {
            'font': ('Arial', fz_btn),
            'bg': '#15354D',
            'fg': 'white',
            'bd': 0,
            'padx': int(max(12, round(20 * ff_l))),
            'pady': int(max(6, round(8 * ff_l))),
            'width': max(8, int(round(14 * ff_l))),
            'highlightthickness': 0,
            'cursor': 'hand2',
        }

    button_style = _button_style(f, scale_font[0])

    update_button = tk.Button(
        center_frame,
        text="Обновиться",
        command=lambda: host.open_update_window(notification_window),
        **button_style,
    )
    update_button.pack(side=tk.LEFT, padx=(0, 10))

    update_button.bind("<Enter>", lambda e: update_button.config(bg='#1e4a6a'))
    update_button.bind("<Leave>", lambda e: update_button.config(bg='#15354D'))

    skip_button = tk.Button(
        center_frame,
        text="Пропустить",
        command=notification_window.destroy,
        **button_style,
    )
    skip_button.pack(side=tk.LEFT)

    skip_button.bind("<Enter>", lambda e: skip_button.config(bg='#1e4a6a'))
    skip_button.bind("<Leave>", lambda e: skip_button.config(bg='#15354D'))

    def _apply_update_scale(ff_l: float) -> None:
        ff_t = float(dampened_hi_dpi_factor(logical_ui_scale(host.root)))
        scale_layout[0] = float(ff_l)
        scale_font[0] = ff_t
        for w, pt, bold in font_targets:
            try:
                sz = max(7, int(round(pt * ff_t)))
                w.config(font=("Arial", sz, "bold") if bold else ("Arial", sz))
            except tk.TclError:
                pass
        pm = int(max(8, round(10 * ff_l)))
        try:
            main_frame.config(padx=pm, pady=pm)
        except tk.TclError:
            pass
        try:
            notification_window.minsize(
                max(280, int(round(320 * ff_l))),
                max(160, int(round(200 * ff_l))),
            )
        except tk.TclError:
            pass
        bs = _button_style(ff_l, ff_t)
        for btn in (update_button, skip_button):
            try:
                btn.config(**bs)
            except tk.TclError:
                pass
        _sync_info_wrap()
        try:
            notification_window.update_idletasks()
        except tk.TclError:
            pass
        try:
            fit_toplevel_to_content(
                notification_window,
                min_width=max(280, int(round(320 * ff_l))),
                min_height=max(160, int(round(200 * ff_l))),
                margin_width=int(max(4, round(8 * ff_l))),
                margin_height=int(max(8, round(12 * ff_l))),
            )
            center_toplevel_on_parent(notification_window, host.root)
        except tk.TclError:
            pass

    def _current_scale_tuple():
        nu = float(warning_dialog_scale(host.root))
        nl = float(logical_ui_scale(host.root))
        try:
            ntk = float(notification_window.tk.call("tk", "scaling", "-displayof", notification_window))
        except Exception:
            ntk = None
        try:
            dtk = winfo_dpi(host.root)
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

    _upd_scale_snap = list(_current_scale_tuple())

    def _try_refit_update_for_scale() -> bool:
        try:
            if not notification_window.winfo_exists():
                return False
        except tk.TclError:
            return False
        cur = _current_scale_tuple()
        if not _scale_tuple_changed(_upd_scale_snap, cur):
            return False
        _upd_scale_snap[:] = list(cur)
        _ff_ap = float(dampened_hi_dpi_factor(warning_dialog_scale(host.root)))
        _apply_update_scale(_ff_ap)
        return True

    _poll_after_id = [None]
    _POLL_MS = 450

    def _cancel_update_scale_poll():
        if _poll_after_id[0] is not None:
            try:
                notification_window.after_cancel(_poll_after_id[0])
            except tk.TclError:
                pass
            _poll_after_id[0] = None

    def _poll_update_dpi_tick():
        _poll_after_id[0] = None
        _try_refit_update_for_scale()
        try:
            if notification_window.winfo_exists():
                _poll_after_id[0] = notification_window.after(_POLL_MS, _poll_update_dpi_tick)
        except tk.TclError:
            pass

    def _schedule_update_scale_probe(_evt=None):
        def _go():
            try:
                if not notification_window.winfo_exists():
                    return
            except tk.TclError:
                return
            _try_refit_update_for_scale()

        try:
            notification_window.after(200, _go)
        except tk.TclError:
            pass

    for _ev in ("<Map>", "<FocusIn>"):
        notification_window.bind(_ev, lambda _e: _schedule_update_scale_probe(), add="+")

    try:
        notification_window.bind("<Destroy>", lambda _e: _cancel_update_scale_poll(), add="+")
    except tk.TclError:
        pass

    notification_window.update_idletasks()
    try:
        fit_toplevel_to_content(
            notification_window,
            min_width=max(280, int(round(320 * f))),
            min_height=max(160, int(round(200 * f))),
            margin_width=int(max(4, round(8 * f))),
            margin_height=int(max(8, round(12 * f))),
        )
        center_toplevel_on_parent(notification_window, host.root)
    except tk.TclError:
        pass

    notification_window.grab_set()

    try:
        _poll_after_id[0] = notification_window.after(_POLL_MS, _poll_update_dpi_tick)
    except tk.TclError:
        pass

    notification_window.protocol("WM_DELETE_WINDOW", notification_window.destroy)
