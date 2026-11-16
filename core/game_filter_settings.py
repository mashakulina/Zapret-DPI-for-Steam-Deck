# -*- coding: utf-8 -*-
"""Режим протоколов для глобального Game Filter (файл utils/gamefilter.mode)."""

from __future__ import annotations

import os

from core.game_presets import get_manager_dir

GAMEFILTER_PROTOCOL_BOTH = "both"
GAMEFILTER_PROTOCOL_TCP = "tcp"
GAMEFILTER_PROTOCOL_UDP = "udp"

_VALID_MODES = frozenset(
    {GAMEFILTER_PROTOCOL_BOTH, GAMEFILTER_PROTOCOL_TCP, GAMEFILTER_PROTOCOL_UDP}
)


def get_game_filter_mode_file(manager_dir: str | None = None) -> str:
    if manager_dir is None:
        manager_dir = get_manager_dir()
    return os.path.join(manager_dir, "utils", "gamefilter.mode")


def normalize_game_filter_protocol_mode(value: str | None) -> str:
    v = (value or "").strip().lower()
    if v in _VALID_MODES:
        return v
    return GAMEFILTER_PROTOCOL_BOTH


def read_game_filter_protocol_mode(manager_dir: str | None = None) -> str:
    path = get_game_filter_mode_file(manager_dir)
    if not os.path.isfile(path):
        return GAMEFILTER_PROTOCOL_BOTH
    try:
        with open(path, "r", encoding="utf-8") as f:
            line = f.readline()
    except OSError:
        return GAMEFILTER_PROTOCOL_BOTH
    return normalize_game_filter_protocol_mode(line)


def write_game_filter_protocol_mode(mode: str, manager_dir: str | None = None) -> None:
    normalized = normalize_game_filter_protocol_mode(mode)
    path = get_game_filter_mode_file(manager_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(normalized + "\n")


def remove_game_filter_protocol_mode_file(manager_dir: str | None = None) -> None:
    path = get_game_filter_mode_file(manager_dir)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    except OSError:
        pass


def get_game_filter_enable_file(manager_dir: str | None = None) -> str:
    if manager_dir is None:
        manager_dir = get_manager_dir()
    return os.path.join(manager_dir, "utils", "gamefilter.enable")


def disable_standalone_gamefilter(manager_dir: str | None = None) -> None:
    """Выключает отдельный GameFilter (маркер и режим TCP/UDP). Без перезапуска службы."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    enable_path = get_game_filter_enable_file(manager_dir)
    try:
        os.remove(enable_path)
    except FileNotFoundError:
        pass
    except OSError:
        pass
    remove_game_filter_protocol_mode_file(manager_dir)
