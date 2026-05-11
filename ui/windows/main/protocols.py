"""Типы для зависимостей миксинов (без циклических импортов с MainWindow)."""
from __future__ import annotations

from typing import Protocol


class MainWindowActions(Protocol):
    """Минимальный контракт главного окна для GameFilter и пресетов."""

    def is_game_filter_enabled(self) -> bool: ...

    def ensure_sudo_password(self) -> bool: ...

    def _show_game_filter_warning(self, protocol_mode: str = "both") -> None: ...

    def _perform_game_filter_toggle(self, protocol_mode_for_enable: str | None = None) -> None: ...

    def show_status_message(
        self,
        message: str,
        success: bool = False,
        warning: bool = False,
        error: bool = False,
    ) -> None: ...

    def update_game_filter_indicator(self) -> None: ...

    def restart_zapret_after_preset(self, status_message: str) -> None: ...
