# -*- coding: utf-8 -*-
"""Доп. настройки Game Filter: отключение основного обхода и Discord (маркеры + фильтр строк)."""

from __future__ import annotations

import os

from core.game_filter_settings import get_game_filter_enable_file
from core.game_presets import get_game_presets, get_active_preset_id, get_manager_dir

MAIN_BYPASS_DISABLE_MARKER = "gamefilter.main_bypass.disable"
DISCORD_DISABLE_MARKER = "gamefilter.discord.disable"


def _utils_path(filename: str, manager_dir: str | None = None) -> str:
    if manager_dir is None:
        manager_dir = get_manager_dir()
    return os.path.join(manager_dir, "utils", filename)


def _marker_exists(filename: str, manager_dir: str | None = None) -> bool:
    return os.path.isfile(_utils_path(filename, manager_dir))


def _set_marker(filename: str, disabled: bool, manager_dir: str | None = None) -> None:
    path = _utils_path(filename, manager_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if disabled:
        with open(path, "w", encoding="utf-8") as f:
            f.write("")
    else:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except OSError:
            pass


def read_main_bypass_enabled(manager_dir: str | None = None) -> bool:
    """Основной обход включён, если нет маркера отключения."""
    return not _marker_exists(MAIN_BYPASS_DISABLE_MARKER, manager_dir)


def set_main_bypass_enabled(enabled: bool, manager_dir: str | None = None) -> None:
    _set_marker(MAIN_BYPASS_DISABLE_MARKER, disabled=not enabled, manager_dir=manager_dir)


def read_discord_enabled(manager_dir: str | None = None) -> bool:
    return not _marker_exists(DISCORD_DISABLE_MARKER, manager_dir)


def set_discord_enabled(enabled: bool, manager_dir: str | None = None) -> None:
    _set_marker(DISCORD_DISABLE_MARKER, disabled=not enabled, manager_dir=manager_dir)


def is_game_mode_active(manager_dir: str | None = None) -> bool:
    """Отдельный GameFilter или активный пресет игры."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    if os.path.isfile(get_game_filter_enable_file(manager_dir)):
        return True
    return get_active_preset_id(manager_dir) is not None


def apply_game_mode_defaults(manager_dir: str | None = None) -> None:
    """Игровой режим по умолчанию: без основного обхода, с Discord."""
    set_main_bypass_enabled(False, manager_dir)
    set_discord_enabled(True, manager_dir)


def clear_game_mode_extras(manager_dir: str | None = None) -> None:
    """Вне игрового режима — полная стратегия, маркеры сняты."""
    set_main_bypass_enabled(True, manager_dir)
    set_discord_enabled(True, manager_dir)


def clear_game_mode_extras_if_inactive(manager_dir: str | None = None) -> None:
    if not is_game_mode_active(manager_dir):
        clear_game_mode_extras(manager_dir)


def is_filtering_active(manager_dir: str | None = None) -> bool:
    """Фильтрация при игровом режиме, если не включены и основной обход, и Discord."""
    if not is_game_mode_active(manager_dir):
        return False
    if read_main_bypass_enabled(manager_dir) and read_discord_enabled(manager_dir):
        return False
    return True


def _preset_line_set(manager_dir: str | None = None) -> frozenset[str]:
    preset_id = get_active_preset_id(manager_dir)
    if not preset_id:
        return frozenset()
    raw = get_game_presets(manager_dir).get(preset_id, {}).get("lines") or []
    return frozenset(line.strip() for line in raw if line.strip())


def is_preset_line(line: str, manager_dir: str | None = None) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    return stripped in _preset_line_set(manager_dir)


def is_gamefilter_line(line: str, manager_dir: str | None = None) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if "{GameFilter}" in stripped:
        return True

    preset_id = get_active_preset_id(manager_dir)
    if preset_id:
        preset = get_game_presets(manager_dir).get(preset_id, {})
        tcp = preset.get("game_filter_tcp")
        udp = preset.get("game_filter_udp")
        if tcp and stripped.startswith(f"--filter-tcp={tcp}"):
            return True
        if udp and stripped.startswith(f"--filter-udp={udp}"):
            return True

    if "list_general" in stripped or "list_google" in stripped:
        return False
    if "--dpi-desync-any-protocol=1" not in stripped:
        return False
    has_ipset = "{ipset_all}" in stripped or "ipset-all" in stripped
    if not has_ipset:
        return False
    return stripped.startswith("--filter-tcp=") or stripped.startswith("--filter-udp=")


def is_discord_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    markers = (
        "--filter-l7=discord",
        "hostlist-domains=discord.media",
        "hostlist={discord}",
        "{ipset_discord}",
        "dpi-desync-fake-discord",
    )
    return any(m in stripped for m in markers)


def should_include_config_line(
    line: str,
    *,
    main_bypass_enabled: bool,
    discord_enabled: bool,
    manager_dir: str | None = None,
) -> bool:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return False
    if is_preset_line(stripped, manager_dir):
        return True
    if is_gamefilter_line(stripped, manager_dir):
        return True
    if is_discord_line(stripped):
        return discord_enabled
    return main_bypass_enabled


def filter_config_lines(
    lines: list[str],
    manager_dir: str | None = None,
) -> list[str]:
    """Фильтрует строки config; без маркеров возвращает вход без изменений."""
    if not is_filtering_active(manager_dir):
        return [line.rstrip("\n") for line in lines]

    main_on = read_main_bypass_enabled(manager_dir)
    discord_on = read_discord_enabled(manager_dir)
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            result.append(stripped)
            continue
        if should_include_config_line(
            line,
            main_bypass_enabled=main_on,
            discord_enabled=discord_on,
            manager_dir=manager_dir,
        ):
            result.append(stripped)
    return result
