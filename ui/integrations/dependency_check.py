"""Проверка зависимостей при старте с UI приложения."""
from __future__ import annotations

import tkinter as tk

from core.dependency_checker import DependencyChecker
from ui.components.custom_messagebox import show_info as custom_show_info
from ui.windows.sudo_password_window import SudoPasswordWindow


def run_dependency_check(root_window: tk.Misc | None = None) -> bool:
    """Поведение как у прежнего вызова core.run_dependency_check(root)."""

    def _show(title: str, message: str) -> None:
        if root_window:
            custom_show_info(root_window, title, message)
        else:
            print(f"{title}: {message}")

    def _sudo_pwd() -> str | None:
        if not root_window:
            return None
        w = SudoPasswordWindow(
            root_window,
            on_password_valid=lambda _pwd: None,
        )
        return w.run()

    checker = DependencyChecker(
        root_window,
        show_info_fn=_show,
        sudo_password_provider=_sudo_pwd if root_window else None,
    )
    return checker.check_and_install_dependencies()
