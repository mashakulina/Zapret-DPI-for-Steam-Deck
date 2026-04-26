"""Удаление Zapret с кастомными диалогами приложения."""
from __future__ import annotations

import tkinter as tk

from core.zapret_uninstaller import ZapretUninstaller
from ui.components.custom_messagebox import ask_yesno as custom_ask_yesno
from ui.components.custom_messagebox import show_info as custom_show_info


def run_zapret_uninstall(root_window: tk.Misc | None = None):
    """То же поведение, что раньше при вызове core.run_zapret_uninstall(root)."""

    def _info(title: str, message: str) -> None:
        if root_window:
            custom_show_info(root_window, title, message)
        else:
            print(f"{title}: {message}")

    def _yesno(title: str, message: str) -> bool:
        if root_window:
            return bool(custom_ask_yesno(root_window, title, message))
        return False

    uninstaller = ZapretUninstaller(
        root_window,
        show_info_fn=_info,
        ask_yesno_fn=_yesno,
    )
    return uninstaller.run_uninstall()
