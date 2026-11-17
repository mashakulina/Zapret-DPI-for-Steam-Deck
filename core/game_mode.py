"""Shared disk operations for desktop and Decky game controls (no Tk dependency)."""
from pathlib import Path
import os
import json
import logging

from core.custom_game_presets import _read, _commit, _json

from core.game_presets import (
    get_game_presets, get_active_preset_id, is_custom_preset, apply_custom_preset,
    clear_custom_preset, validate_custom_preset, set_active_preset, clear_active_preset,
    remove_preset_lines_from_config, restore_gamefilter_for_preset, games_data_file,
    substitute_gamefilter_in_config, preset_switch_transaction,
)
from core.game_filter_settings import (
    disable_standalone_gamefilter, read_game_filter_custom_ports,
    read_game_filter_protocol_mode, write_game_filter_settings,
    validate_game_filter_custom_ports,
)
from core.game_filter_extras import clear_game_mode_extras_if_inactive

def _preset_read_nonempty_lines(path):
    """Читает непустые строки файла без комментариев."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]


def _preset_write_lines(path, lines):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if lines:
            f.write("\n".join(lines) + "\n")
        else:
            f.write("")


def _list_general_user_path(manager_dir):
    return os.path.join(manager_dir, "files", "lists", "list-general_user.txt")


def _ipset_all_user_path(manager_dir):
    return os.path.join(manager_dir, "files", "lists", "ipset-all_user.txt")


BUILTIN_LIST_STATE = 'builtin_game_lists.state.json'


def _list_state(root):
    path = Path(root) / 'utils' / BUILTIN_LIST_STATE
    raw = _read(path)
    data = json.loads(raw) if raw is not None else {'version': 1, 'sources': {}}
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('sources'), dict):
        raise ValueError('Повреждены сведения о списках встроенного пресета.')
    return path, data


def _preset_apply_user_list(manager_dir, source_name, target_name):
    """Append only missing game entries and remember exactly what this adds."""
    root = Path(manager_dir)
    source = games_data_file(str(root), source_name)
    additions = _preset_read_nonempty_lines(source)
    if not additions:
        raise FileNotFoundError(f'Файл не найден или пуст: {source}')
    target = root / 'files/lists' / target_name
    state_path, state = _list_state(root)
    if source_name in state['sources']:
        # Selecting the same preset is idempotent and must keep its first baseline.
        return
    before = _read(target)
    existing = set(_preset_read_nonempty_lines(target))
    owned = []
    for line in additions:
        if line not in existing:
            owned.append(line)
            existing.add(line)
    after = before or b''
    if owned:
        newline = b'\r\n' if b'\r\n' in after else b'\n'
        if after and not after.endswith((b'\r', b'\n')):
            after += newline
        after += newline.join(line.encode('utf-8') for line in owned) + newline
    state['sources'][source_name] = dict(target=target_name,
        before=before.hex() if before is not None else None, after=after.hex(), added=owned)
    _commit({target: after, state_path: _json(state)})


def _preset_remove_user_list(manager_dir, source_name, target_name):
    root = Path(manager_dir)
    state_path, state = _list_state(root)
    entry = state['sources'].get(source_name)
    if entry is None:
        # An older installation did not record ownership. Removing every source
        # match would also erase pre-existing user entries, so keep those lines.
        logging.getLogger(__name__).warning(
            'Legacy preset %s has no list journal; preserving user list %s', source_name, target_name)
        return
    if not isinstance(entry, dict) or entry.get('target') != target_name:
        raise ValueError('Повреждены сведения о списках встроенного пресета.')
    target = root / 'files/lists' / target_name
    current = _read(target)
    before = bytes.fromhex(entry['before']) if entry.get('before') is not None else None
    after = bytes.fromhex(entry['after'])
    if current == after:
        restored = before
    elif current is None:
        restored = None
    else:
        # Keep comments, ordering, duplicates and later user edits. Remove at
        # most one occurrence per entry that this preset actually appended.
        lines = current.decode('utf-8').splitlines(keepends=True)
        for owned in reversed(entry['added']):
            for index in range(len(lines) - 1, -1, -1):
                if lines[index].strip() == owned:
                    del lines[index]
                    break
        restored = ''.join(lines).encode('utf-8')
    del state['sources'][source_name]
    _commit({target: restored, state_path: _json(state) if state['sources'] else None})


def _preset_remove_list_general_user_domains(manager_dir, games_list_file):
    _preset_remove_user_list(manager_dir, games_list_file, 'list-general_user.txt')


def _preset_apply_list_general_user_domains(manager_dir, games_list_file):
    _preset_apply_user_list(manager_dir, games_list_file, 'list-general_user.txt')


def _preset_remove_ipset_user_entries(manager_dir, games_ipset_file):
    _preset_remove_user_list(manager_dir, games_ipset_file, 'ipset-all_user.txt')


def _preset_apply_ipset_user_entries(manager_dir, games_ipset_file):
    _preset_apply_user_list(manager_dir, games_ipset_file, 'ipset-all_user.txt')


def _preset_remove_roblox_domains(manager_dir):
    _preset_remove_list_general_user_domains(manager_dir, "list-general_roblox.txt")


def _preset_remove_roblox_ipset(manager_dir):
    _preset_remove_ipset_user_entries(manager_dir, "ipset-all_roblox.txt")


def _preset_remove_fallguys_domains(manager_dir):
    _preset_remove_list_general_user_domains(manager_dir, "list-general_fallguys.txt")


def _preset_remove_fallguys_ipset(manager_dir):
    _preset_remove_ipset_user_entries(manager_dir, "ipset-all_fallguys.txt")


def _preset_set_ipset_none(manager_dir):
    target_path = os.path.join(manager_dir, "files", "lists", "ipset-all.txt")
    os.makedirs(os.path.dirname(target_path), exist_ok=True)
    with open(target_path, "w", encoding="utf-8") as f:
        f.write("203.0.113.113/32")


def clear_active_game_preset_disk(manager_dir: str) -> None:
    """Снимает активный пресет с диска (без перезапуска службы и без диалогов)."""
    with preset_switch_transaction(manager_dir):
        active_before = get_active_preset_id(manager_dir)
        if active_before:
            if is_custom_preset(active_before, manager_dir):
                clear_custom_preset(active_before, manager_dir)
                clear_active_preset(manager_dir)
                return
            if active_before == "roblox":
                _preset_remove_roblox_domains(manager_dir)
                _preset_remove_roblox_ipset(manager_dir)
            elif active_before == "fall_guys":
                _preset_remove_fallguys_domains(manager_dir)
                _preset_remove_fallguys_ipset(manager_dir)
            else:
                remove_preset_lines_from_config(active_before, manager_dir)
            if active_before == "elite_dangerous":
                _preset_set_ipset_none(manager_dir)
            restore_gamefilter_for_preset(active_before, manager_dir)
        clear_active_preset(manager_dir)


def apply_game_preset_disk(manager_dir, preset_id):
    """Apply or clear a built-in/custom preset identically in either UI."""
    root = Path(manager_dir)
    presets = get_game_presets(str(root))
    if preset_id is not None and preset_id not in presets:
        raise ValueError('Пресет не найден.')
    if preset_id and is_custom_preset(preset_id, str(root)):
        validate_custom_preset(preset_id, str(root), check_config=False)
    with preset_switch_transaction(str(root)):
        previous = get_active_preset_id(str(root))
        if preset_id is None:
            clear_active_game_preset_disk(str(root))
            clear_game_mode_extras_if_inactive(str(root))
            return
        if previous and previous != preset_id:
            clear_active_game_preset_disk(str(root))
        if is_custom_preset(preset_id, str(root)):
            apply_custom_preset(preset_id, str(root))
            set_active_preset(preset_id, str(root))
            return
        disable_standalone_gamefilter(str(root))
        preset = presets[preset_id]
        tcp, udp = preset.get('game_filter_tcp'), preset.get('game_filter_udp')
        if tcp is not None and udp is not None:
            substitute_gamefilter_in_config(tcp, udp, str(root))
        game = {'roblox': 'roblox', 'fall_guys': 'fallguys'}.get(preset_id)
        if game:
            _preset_apply_list_general_user_domains(str(root), f'list-general_{game}.txt')
            _preset_apply_ipset_user_entries(str(root), f'ipset-all_{game}.txt')
        elif preset_id == 'elite_dangerous':
            source = root / 'utils/ipset-all.txt'
            (root / 'files/lists/ipset-all.txt').write_bytes(source.read_bytes())
        lines = preset.get('lines') or []
        if lines:
            path = root / 'config.txt'
            content = path.read_text(encoding='utf-8') if path.exists() else ''
            block = '\n'.join(lines)
            if content != block and not content.startswith(block + '\n'):
                path.write_text(block + '\n' + content, encoding='utf-8')
        set_active_preset(preset_id, str(root))


def toggle_gamefilter_disk(manager_dir, mode=None):
    """Preserve current custom ports when enabling; clear the full tuple when disabling."""
    root = Path(manager_dir)
    with preset_switch_transaction(str(root)):
        if (root / 'utils/gamefilter.enable').is_file():
            disable_standalone_gamefilter(str(root))
            clear_game_mode_extras_if_inactive(str(root))
            return False
        current_mode = read_game_filter_protocol_mode(str(root))
        current_ports = read_game_filter_custom_ports(str(root))
        chosen_mode = mode or current_mode
        if chosen_mode not in ('tcp', 'udp', 'both'):
            raise ValueError('Некорректный режим GameFilter.')
        # A protocol switch must not silently discard or invent user ports.
        ports = validate_game_filter_custom_ports(chosen_mode, current_ports)
        clear_active_game_preset_disk(str(root))
        write_game_filter_settings(chosen_mode, ports, str(root))
        (root / 'utils/gamefilter.enable').write_text('', encoding='utf-8')
        return True


def set_gamefilter_mode_disk(manager_dir, mode):
    root = Path(manager_dir)
    with preset_switch_transaction(str(root)):
        if not (root / 'utils/gamefilter.enable').is_file():
            raise ValueError('GameFilter выключен.')
        if mode not in ('tcp', 'udp', 'both'):
            raise ValueError('Некорректный режим GameFilter.')
        ports = read_game_filter_custom_ports(str(root))
        if ports is not None:
            protocols = ('tcp', 'udp') if mode == 'both' else (mode,)
            if any(protocol not in ports for protocol in protocols):
                raise ValueError('Сначала задайте порты выбранного протокола в «Режим и порты GameFilter».')
        write_game_filter_settings(mode, ports, str(root))
