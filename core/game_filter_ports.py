"""Installed starter helper: emit validated TCP and UDP values as two lines."""
from __future__ import annotations

from pathlib import Path
import sys

# Direct execution, including python -I, must work without development folders.
if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.game_filter_settings import (
    DEFAULT_GAME_FILTER_TCP_PORTS,
    DEFAULT_GAME_FILTER_UDP_PORTS,
    get_game_filter_enable_file,
    read_game_filter_custom_ports,
    read_game_filter_protocol_mode,
)


def resolve_game_filter_ports(manager_dir: str) -> tuple[str, str]:
    if not Path(get_game_filter_enable_file(manager_dir)).is_file():
        return '12', '12'
    mode = read_game_filter_protocol_mode(manager_dir)
    custom = read_game_filter_custom_ports(manager_dir)
    ports = custom if custom is not None else {
        'tcp': DEFAULT_GAME_FILTER_TCP_PORTS,
        'udp': DEFAULT_GAME_FILTER_UDP_PORTS,
    }
    return (ports['tcp'] if mode in ('both', 'tcp') else '12',
            ports['udp'] if mode in ('both', 'udp') else '12')


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: game_filter_ports.py MANAGER_DIR', file=sys.stderr)
        return 2
    try:
        tcp, udp = resolve_game_filter_ports(sys.argv[1])
    except (ValueError, OSError) as exc:
        print(f'Error: invalid GameFilter port settings: {exc}', file=sys.stderr)
        return 1
    print(tcp)
    print(udp)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
