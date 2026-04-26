"""Запуск проверки файлов менеджера с кастомными диалогами."""
from __future__ import annotations

import tkinter as tk

from core.file_checker import ZapretFileChecker
from ui.components.custom_messagebox import show_info as custom_show_info


def run_file_check(root_window: tk.Misc | None = None) -> bool:
    """Проверка и восстановление файлов с тем же UI, что раньше в core."""

    def _show(title: str, message: str) -> None:
        if root_window:
            custom_show_info(root_window, title, message)
        else:
            print(f"{title}: {message}")

    checker = ZapretFileChecker(root_window, show_info_fn=_show)
    return checker.run_check()
