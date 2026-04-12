# -*- coding: utf-8 -*-
"""Вспомогательные функции лаборатории масштаба Tk (DPI, xrdb, отчёт при старте)."""
from __future__ import annotations

import os
import re
import subprocess
import tkinter as tk


def env_scale_hints():
    pairs = []
    for key in ("GDK_SCALE", "QT_SCALE_FACTOR", "ELM_SCALE", "WINIT_HIDPI_FACTOR"):
        raw = os.environ.get(key)
        if not raw:
            continue
        try:
            v = float(raw)
            if 0.25 <= v <= 4.0:
                pairs.append((key, v))
        except ValueError:
            continue
    return pairs


def dpi_from_xrdb():
    try:
        r = subprocess.run(
            ["xrdb", "-query"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if r.returncode != 0:
            return None
        for line in r.stdout.splitlines():
            m = re.search(r"(?i)Xft\.dpi:\s*([0-9.]+)", line)
            if m:
                return float(m.group(1))
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError):
        return None
    return None


def winfo_dpi(root: tk.Misc):
    """Пикселей на один логический дюйм по Tk (часто совпадает с DPI экрана под X)."""
    try:
        return float(root.winfo_fpixels("1i"))
    except tk.TclError:
        return None


def read_tk_scaling(root: tk.Misc) -> float:
    return float(root.tk.call("tk", "scaling", "-displayof", "."))


def pct_of_96_dpi(dpi: float | None) -> str:
    """Логический процент от эталона 96 DPI (как в настройках «100% / 125%» Windows)."""
    if dpi is None or dpi <= 0:
        return "—"
    return f"{100.0 * dpi / 96.0:.1f}%"


def build_system_scale_report_lines(root: tk.Misc) -> list[str]:
    """Сводка сигналов масштаба при старте/обновлении (тест, без привязки к конкретной DE)."""
    dpi_tk = winfo_dpi(root)
    dpi_xft = dpi_from_xrdb()
    hints = env_scale_hints()
    tk_s = f"{dpi_tk:.2f}" if dpi_tk is not None else "—"
    xf_s = f"{dpi_xft:.2f}" if dpi_xft is not None else "—"
    lines = [
        "── Определение масштаба экрана (тест при запуске / «Обновить текст») ──",
        f"  Tk  winfo_fpixels('1i'):  {tk_s}  →  от 96 DPI: {pct_of_96_dpi(dpi_tk)}",
        f"  X11 Xft.dpi (xrdb):      {xf_s}  →  от 96 DPI: {pct_of_96_dpi(dpi_xft)}",
    ]
    if hints:
        lines.append("  Переменные окружения (часто задают тулкиты/игры):")
        for key, val in hints:
            lines.append(f"    {key}={val}")
    else:
        lines.append("  Переменные GDK_SCALE / QT_SCALE_FACTOR / … — не заданы в окружении процесса.")
    lines.append(
        "  Подсказка: процент от 96 для строк выше = DPI÷96×100. Ползунок масштаба в KDE/GNOME "
        "на Wayland может расходиться с Xft.dpi; ориентир для этого окна — строка Tk."
    )
    lines.append("")
    return lines


def apply_scaling_for_dpi(root: tk.Misc, dpi: float) -> None:
    """Задать tk scaling = dpi/72 (пикселей на point)."""
    if dpi <= 0:
        return
    pxpt = dpi / 72.0
    root.tk.call("tk", "scaling", "-displayof", ".", pxpt)


def logical_ui_scale(root: tk.Misc) -> float:
    """Коэффициент масштаба виджетов относительно эталона 96 DPI (как 100% / 125% в настройках дисплея).

    Использует тот же источник, что и отчёт лаборатории масштаба: ``winfo_fpixels('1i')`` через
    :func:`winfo_dpi`. Не меняет глобальный ``tk scaling`` — только для явных размеров в пикселях.
    """
    dpi = winfo_dpi(root)
    if dpi is None or dpi <= 0:
        return 1.0
    s = dpi / 96.0
    return max(0.5, min(4.0, s))


def warning_dialog_scale(root: tk.Misc) -> float:
    """Масштаб для размеров диалога предупреждения.

    На Wayland ``logical_ui_scale`` часто остаётся ~1 при системных 125%, тогда подмешиваются
    ``tk scaling`` (как DPI/96), Xft.dpi (xrdb) и переменные GDK_SCALE / QT_SCALE_FACTOR из окружения.
    """
    f = logical_ui_scale(root)
    try:
        ts = read_tk_scaling(root)
        if ts > 0:
            f = max(f, (ts * 72.0) / 96.0)
    except (tk.TclError, ValueError, TypeError):
        pass
    dpi_x = dpi_from_xrdb()
    if dpi_x is not None and dpi_x > 1.0:
        f = max(f, dpi_x / 96.0)
    for _key, val in env_scale_hints():
        if 0.5 <= val <= 4.0:
            f = max(f, float(val))
    return max(0.85, min(4.0, f))
