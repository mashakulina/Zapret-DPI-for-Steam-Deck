# -*- coding: utf-8 -*-
"""Режим TCP/UDP и пользовательские диапазоны глобального GameFilter."""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from core.game_presets import get_manager_dir

GAMEFILTER_PROTOCOL_BOTH = "both"
GAMEFILTER_PROTOCOL_TCP = "tcp"
GAMEFILTER_PROTOCOL_UDP = "udp"

DEFAULT_GAME_FILTER_TCP_PORTS = "27000-27100,3074-3076"
DEFAULT_GAME_FILTER_UDP_PORTS = "3000-3010,5050-5060,27000-27100,3478-3481,3074-3076,4380,50000-50200,49152-52000"

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


def get_game_filter_ports_file(manager_dir: str | None = None) -> str:
    if manager_dir is None:
        manager_dir = get_manager_dir()
    return os.path.join(manager_dir, "utils", "gamefilter.ports.json")


def normalize_game_filter_ports(value: str) -> str:
    """Validate a port list and return its safe canonical representation."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[ \t]*[0-9]+(?:[ \t]*-[ \t]*[0-9]+)?(?:[ \t]*,[ \t]*[0-9]+(?:[ \t]*-[ \t]*[0-9]+)?)*[ \t]*", value
    ):
        raise ValueError("Укажите порты или диапазоны через запятую, например 443,27000-27100.")
    parts = []
    for item in value.split(','):
        numbers = [int(number.strip()) for number in item.split('-')]
        if any(not 1 <= number <= 65535 for number in numbers):
            raise ValueError("Порты должны быть в диапазоне от 1 до 65535.")
        if len(numbers) == 2 and numbers[0] > numbers[1]:
            raise ValueError("Начало диапазона портов должно быть не больше конца.")
        parts.append('-'.join(str(number) for number in numbers))
    return ','.join(parts)


def validate_game_filter_custom_ports(mode: str, ports: dict | None) -> dict | None:
    if mode not in _VALID_MODES:
        raise ValueError("Некорректный режим GameFilter.")
    if ports is None:
        return None
    if not isinstance(ports, dict) or any(key not in ('tcp', 'udp') for key in ports):
        raise ValueError("Некорректные настройки портов GameFilter.")
    protocols = ('tcp', 'udp') if mode == 'both' else (mode,)
    if any(protocol not in ports for protocol in protocols):
        raise ValueError("Укажите порты для каждого выбранного протокола GameFilter.")
    # Validate inactive values too: a config is data, never an opaque shell fragment.
    normalized = {key: normalize_game_filter_ports(value) for key, value in ports.items()}
    return {protocol: normalized[protocol] for protocol in protocols}


def read_game_filter_custom_ports(manager_dir: str | None = None) -> dict | None:
    path = get_game_filter_ports_file(manager_dir)
    try:
        with open(path, encoding='utf-8') as source:
            ports = json.load(source)
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("Не удалось прочитать настройки портов GameFilter: " + str(exc)) from exc
    if ports is None:
        raise ValueError("Некорректные настройки портов GameFilter: ожидается объект TCP/UDP.")
    return validate_game_filter_custom_ports(read_game_filter_protocol_mode(manager_dir), ports)


def _atomic_write(path: Path, data: bytes | None) -> None:
    if data is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    permissions = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix='.gamefilter-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, permissions)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def write_game_filter_settings(mode: str, ports: dict | None = None,
                              manager_dir: str | None = None) -> None:
    """Save mode and custom ports together, restoring both if a write fails."""
    normalized_ports = validate_game_filter_custom_ports(mode, ports)
    outputs = {
        Path(get_game_filter_mode_file(manager_dir)): (mode + '\n').encode(),
        Path(get_game_filter_ports_file(manager_dir)): (
            (json.dumps(normalized_ports, ensure_ascii=False) + '\n').encode()
            if normalized_ports is not None else None),
    }
    _write_settings_files(outputs)


def _write_settings_files(outputs: dict[Path, bytes | None]) -> None:
    originals = {}
    for path in outputs:
        if path.is_symlink():
            raise ValueError(f"Символическая ссылка не поддерживается: {path}")
        originals[path] = path.read_bytes() if path.exists() else None
    committed = []
    try:
        for path, data in outputs.items():
            if data != originals[path]:
                _atomic_write(path, data)
                committed.append(path)
    except Exception:
        for path in reversed(committed):
            _atomic_write(path, originals[path])
        raise


def remove_game_filter_custom_ports_file(manager_dir: str | None = None) -> None:
    try:
        os.remove(get_game_filter_ports_file(manager_dir))
    except OSError:
        pass


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
    """Remove all standalone settings; restore them together on failure."""
    _write_settings_files({
        Path(get_game_filter_enable_file(manager_dir)): None,
        Path(get_game_filter_mode_file(manager_dir)): None,
        Path(get_game_filter_ports_file(manager_dir)): None,
    })
