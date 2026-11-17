"""Persistent declarative game presets and reversible application journals."""
from __future__ import annotations

from contextlib import contextmanager
import difflib
import json
import os
from pathlib import Path
import re
import tempfile
import unicodedata


class PresetExistsError(ValueError):
    """A custom name already exists and needs explicit overwrite consent."""

    def __init__(self, preset_id, name):
        self.preset_id = preset_id
        self.name = self.preset_name = name
        super().__init__(f'Пресет «{name}» уже существует.')


class PresetConflict(ValueError):
    """A saved edit cannot safely be applied to the current strategy."""


def _root(manager_dir):
    if manager_dir is None:
        from core.game_presets import get_manager_dir
        manager_dir = get_manager_dir()
    return Path(manager_dir)


def _registry(root):
    path = root / 'utils/for games/presets.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if (not isinstance(data, dict) or data.get('version') != 1
            or not isinstance(data.get('presets'), dict)):
        raise ValueError('Некорректный реестр пользовательских пресетов.')
    return data['presets']


def get_custom_presets(manager_dir=None):
    return _registry(_root(manager_dir))


def _json(data):
    return (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def _read(path):
    if path.is_symlink():
        raise ValueError(f'Символическая ссылка не поддерживается: {path}')
    return path.read_bytes() if path.exists() else None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.unlink(missing_ok=True)
        return
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    owner = path.stat() if path.exists() else path.parent.stat()
    fd, temp = tempfile.mkstemp(prefix='.game-preset-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temp, mode)
        if os.geteuid() == 0:
            os.chown(temp, owner.st_uid, owner.st_gid)
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def _commit(outputs):
    originals = {path: _read(path) for path in outputs}
    committed = []
    try:
        for path, data in outputs.items():
            if _read(path) != originals[path]:
                raise PresetConflict(f'Файл изменился во время сохранения: {path}')
            if data != originals[path]:
                _write(path, data)
                committed.append(path)
    except Exception:
        for path in reversed(committed):
            _write(path, originals[path])
        raise


def _patches(before, after):
    a, b = before.splitlines(keepends=True), after.splitlines(keepends=True)
    result = []
    for group in difflib.SequenceMatcher(None, a, b, autojunk=False).get_grouped_opcodes(2):
        first, last = group[0], group[-1]
        result.append({
            'old': ''.join(a[first[1]:last[2]]),
            'new': ''.join(b[first[3]:last[4]]),
        })
    if result:
        result[0]['config_before'] = before
        result[0]['config_after'] = after
    return result


def _patch(text, patches, reverse=False):
    if patches and 'config_before' in patches[0]:
        source = patches[0]['config_after' if reverse else 'config_before']
        target = patches[0]['config_before' if reverse else 'config_after']
        if text == source:
            return target
        if text == target:
            return text
    for patch in patches:
        old, new = (patch['new'], patch['old']) if reverse else (patch['old'], patch['new'])
        if old == new:
            continue
        if not old:
            # A patch for an empty draft is only safe on an empty config.
            if text == new:
                continue
            if text:
                raise PresetConflict('Изменения пресета несовместимы с текущей стратегией.')
            text = new
        else:
            # Count overlapping matches too: repeated adjacent lines otherwise
            # resemble an already-applied insertion in a changed strategy.
            old_count = len(list(re.finditer('(?=' + re.escape(old) + ')', text)))
            new_count = (len(list(re.finditer('(?=' + re.escape(new) + ')', text)))
                         if new else 0)
            if old_count > 1 or new_count > 1:
                raise PresetConflict('Изменения пресета неоднозначны в текущей стратегии.')
            if new_count == 1 and (not old_count or (old in new and new not in old)):
                continue
            if old_count == 1:
                text = text.replace(old, new, 1)
            else:
                raise PresetConflict(
                    'Изменения пресета несовместимы с текущей стратегией. '
                    'Создайте пресет для этой стратегии.'
                )
    return text


def _filter_values(game_filter):
    if game_filter is None:
        return {'enabled': False, 'mode': 'both', 'main_bypass_enabled': True, 'discord_enabled': True}
    if not isinstance(game_filter, dict) or game_filter.get('mode', 'both') not in ('both', 'tcp', 'udp'):
        raise ValueError('Некорректные настройки GameFilter.')
    result = dict(enabled=True, mode='both', main_bypass_enabled=True, discord_enabled=True)
    result.update({key: game_filter[key] for key in result if key in game_filter})
    if any(not isinstance(result[key], bool) for key in result if key != 'mode'):
        raise ValueError('Некорректные настройки GameFilter.')
    from core.game_filter_settings import validate_game_filter_custom_ports
    if 'custom_ports' in game_filter:
        result['custom_ports'] = validate_game_filter_custom_ports(result['mode'], game_filter['custom_ports'])
    return result


def read_current_filter_settings(manager_dir=None):
    root = _root(manager_dir)
    from core.game_filter_settings import read_game_filter_protocol_mode, read_game_filter_custom_ports
    content = _read(root / 'files/lists/ipset-all.txt')
    text = (content or b'').decode('utf-8').strip()
    game_filter = {
        'enabled': (root / 'utils/gamefilter.enable').is_file(),
        'mode': read_game_filter_protocol_mode(str(root)),
        'main_bypass_enabled': not (root / 'utils/gamefilter.main_bypass.disable').exists(),
        'discord_enabled': not (root / 'utils/gamefilter.discord.disable').exists(),
    }
    ports = read_game_filter_custom_ports(str(root))
    if ports is not None:
        game_filter['custom_ports'] = ports
    ipset_filter = 'none' if content is None or text == '203.0.113.113/32' else ('any' if not text else 'loaded')
    return {'game_filter': game_filter, 'ipset_filter': ipset_filter}


def save_custom_preset(name, *, config_before, config_after, include_ipset=False,
                       include_hostlist=False, game_filter=None, ipset_filter=None,
                       manager_dir=None, overwrite=False):
    root = _root(manager_dir)
    if (not isinstance(name, str) or not name.strip() or len(name.strip()) > 100
            or re.search(r'[/\\\x00-\x1f\x7f]', name) or name.strip() in ('.', '..')):
        raise ValueError('Укажите безопасное название игры без разделителей пути.')
    name = name.strip()
    from core.game_presets import GAME_PRESETS
    presets = _registry(root)
    if any(p['name'].casefold() == name.casefold() for p in GAME_PRESETS.values()):
        raise ValueError('Нельзя заменить встроенный игровой пресет.')
    existing_id = next((pid for pid, p in presets.items()
                        if p['name'].casefold() == name.casefold()), None)
    if existing_id is not None and not overwrite:
        raise PresetExistsError(existing_id, presets[existing_id]['name'])
    slug = re.sub(r'[^\w-]+', '_', unicodedata.normalize('NFKC', name).casefold()).strip('_-')
    if not slug:
        raise ValueError('Название должно содержать буквы или цифры.')
    # Leave room for the longest basename: game_preset_custom_<slug>.
    if len(slug.encode('utf-8')) > 220:
        raise ValueError('Название слишком длинное для имени файла пресета.')
    preset_id = 'custom_' + slug
    if existing_id is not None:
        preset_id = existing_id
        slug = preset_id.removeprefix('custom_')
    elif preset_id in presets:
        raise ValueError('Пресет с таким идентификатором уже существует.')
    previous = presets.get(preset_id)
    if ipset_filter not in (None, 'none', 'loaded', 'any'):
        raise ValueError('Некорректный режим IPSetFilter.')
    gf = _filter_values(game_filter)
    if not isinstance(config_before, str) or not isinstance(config_after, str) or not config_after.strip():
        raise ValueError('Config пресета не должен быть пустым.')
    if previous is not None:
        config_before = _overwrite_config_base(root, preset_id, config_before)
    patches = _patches(config_before, config_after)
    before_lines, after_lines = config_before.splitlines(), config_after.splitlines()
    edits = difflib.SequenceMatcher(None, before_lines, after_lines, autojunk=False)
    lines = [line for tag, _, _, j, k in edits.get_opcodes()
             if tag in ('insert', 'replace') for line in after_lines[j:k]]
    preset = dict(name=name, custom=True, patches=patches, lines=lines,
                  game_filter=gf, ipset_filter=ipset_filter, files={},
                  revision=1 if previous is None else previous.get('revision', 1) + 1)
    outputs = {}
    list_sources = (
        (include_ipset, 'ipset-all_user.txt', f'ipset-all_{slug}.txt'),
        (include_hostlist, 'list-general_user.txt', f'list-general_{slug}.txt'),
    )
    for include, source, dest in list_sources:
        if include:
            data = _read(root / 'files/lists' / source)
            if data is None:
                raise FileNotFoundError(f'Не найден файл {source}')
            target = root / 'utils/for games' / dest
            owned = previous is not None and dest in previous.get('files', {}).values()
            if target.exists() and not owned:
                raise ValueError(f'Файл пресета уже существует: {dest}')
            outputs[target] = data
            preset['files'][source] = dest
    if previous is not None:
        for stale in set(previous.get('files', {}).values()) - set(preset['files'].values()):
            if Path(stale).name != stale:
                raise ValueError('Некорректный путь данных пресета.')
            outputs[root / 'utils/for games' / stale] = None
    presets[preset_id] = preset
    outputs[root / 'utils/for games/presets.json'] = _json(dict(version=1, presets=presets))
    _commit(outputs)
    return preset_id


def _overwrite_config_base(root, preset_id, config_before):
    """Remove the old active definition from an editor's starting draft."""
    state_path = _state_path(root, preset_id)
    if not state_path.exists():
        return config_before
    state = json.loads(state_path.read_text(encoding='utf-8'))
    saved = state['files']['config.txt']
    before = bytes.fromhex(saved['before']).decode('utf-8')
    after = bytes.fromhex(saved['after']).decode('utf-8')
    live = _read(root / 'config.txt')
    if config_before == after or (live is not None and config_before == live.decode('utf-8')):
        return _patch(config_before, _patches(before, after), reverse=True)
    return config_before


def _state_path(root, preset_id):
    if not re.fullmatch(r'custom_[\w-]+', preset_id):
        raise ValueError('Некорректный идентификатор пресета.')
    return root / 'utils' / (preset_id + '.state.json')


def _plan(preset_id, root, check_config=True):
    preset = _registry(root).get(preset_id)
    if preset is None:
        raise ValueError('Пользовательский пресет не найден.')
    config = root / 'config.txt'
    content = _read(config)
    if content is None:
        raise FileNotFoundError(config)
    updated = (_patch(content.decode('utf-8'), preset['patches']).encode('utf-8')
               if check_config else content)
    outputs = {config: updated}
    additions = {}
    for filename, data_file in preset['files'].items():
        # Registry is data, never allow it to address arbitrary paths.
        if (filename not in ('ipset-all_user.txt', 'list-general_user.txt')
                or Path(data_file).name != data_file):
            raise ValueError('Некорректный путь данных пресета.')
        path = root / 'files/lists' / filename
        current = (_read(path) or b'').decode('utf-8')
        source = root / 'utils/for games' / data_file
        entries = source.read_text(encoding='utf-8').splitlines()
        known = set(line.strip() for line in current.splitlines())
        added = []
        for line in entries:
            line = line.strip()
            if line and line not in known:
                known.add(line)
                added.append(line)
        separator = '\n' if current and not current.endswith('\n') and added else ''
        outputs[path] = (current + separator + ''.join(line + '\n' for line in added)).encode('utf-8')
        additions[filename] = added
    outputs.update(_filter_outputs(preset, root))
    return outputs, additions


def _filter_outputs(preset, root):
    gf = _filter_values(preset['game_filter'])
    custom_ports = gf.get('custom_ports') if gf['enabled'] else None
    marker_values = {'gamefilter.enable': b'' if gf['enabled'] else None,
                     'gamefilter.mode': (gf['mode'] + '\n').encode() if gf['enabled'] else None,
                     'gamefilter.ports.json': _json(custom_ports) if custom_ports is not None else None,
                     'gamefilter.main_bypass.disable': None if gf['main_bypass_enabled'] else b'',
                     'gamefilter.discord.disable': None if gf['discord_enabled'] else b''}
    outputs = {root / 'utils' / key: value for key, value in marker_values.items()}
    mode = preset['ipset_filter']
    if mode is not None:
        if mode == 'loaded':
            data = _read(root / 'utils/ipset-all.txt')
            if data is None:
                raise FileNotFoundError(root / 'utils/ipset-all.txt')
        else:
            data = b'' if mode == 'any' else b'203.0.113.113/32'
        outputs[root / 'files/lists/ipset-all.txt'] = data
    return outputs


def validate_custom_preset(preset_id, manager_dir=None, *, check_config=True):
    _plan(preset_id, _root(manager_dir), check_config=check_config)
    return True


def _saved_bytes(data):
    return None if data is None else data.hex()


def apply_custom_preset(preset_id, manager_dir=None):
    root = _root(manager_dir)
    state_path = _state_path(root, preset_id)
    if state_path.exists():
        preset = _registry(root)[preset_id]
        state = json.loads(state_path.read_text(encoding='utf-8'))
        if state.get('definition_revision', 1) != preset.get('revision', 1):
            with preset_switch_transaction(root):
                clear_custom_preset(preset_id, root)
                return apply_custom_preset(preset_id, root)
        # Selecting the active preset reapplies saved filter options. Keep the
        # original pre-activation values so clearing still restores them.
        outputs = _filter_outputs(preset, root)
        changed = False
        for path, value in outputs.items():
            current = _read(path)
            changed |= current != value
            relative = str(path.relative_to(root))
            saved = state['files'].setdefault(relative, {'before': _saved_bytes(current)})
            changed |= saved.get('after') != _saved_bytes(value)
            saved['after'] = _saved_bytes(value)
        if not changed:
            return False
        outputs[state_path] = _json(state)
        _commit(outputs)
        return True

    outputs, additions = _plan(preset_id, root)
    files = {}
    for path, value in outputs.items():
        files[str(path.relative_to(root))] = {
            'before': _saved_bytes(_read(path)), 'after': _saved_bytes(value),
        }
    preset = _registry(root)[preset_id]
    state = {'version': 1, 'additions': additions, 'files': files,
             'definition_revision': preset.get('revision', 1)}
    outputs[state_path] = _json(state)
    _commit(outputs)
    return True


def clear_custom_preset(preset_id, manager_dir=None):
    root = _root(manager_dir)
    state_path = _state_path(root, preset_id)
    if not state_path.exists():
        return False
    state = json.loads(state_path.read_text(encoding='utf-8'))
    outputs = {}
    # Mode and ports form one setting. Preserve both when the user changed
    # either one, so restoring the other cannot invalidate the remaining ports.
    filter_pair = {'utils/gamefilter.mode', 'utils/gamefilter.ports.json'}
    preserve_filter_pair = any(
        relative in state['files'] and _read(root / relative) != (
            None if state['files'][relative]['after'] is None
            else bytes.fromhex(state['files'][relative]['after']))
        for relative in filter_pair
    )
    for relative, saved in state['files'].items():
        path = root / relative
        if Path(relative).is_absolute() or '..' in Path(relative).parts:
            raise ValueError('Некорректный журнал пресета.')
        before = None if saved['before'] is None else bytes.fromhex(saved['before'])
        after = None if saved['after'] is None else bytes.fromhex(saved['after'])
        current = _read(path)
        if preserve_filter_pair and relative in filter_pair:
            continue
        if current == after:
            outputs[path] = before
        elif relative == 'config.txt':
            patches = _patches((before or b'').decode('utf-8'), (after or b'').decode('utf-8'))
            restored = _patch((current or b'').decode('utf-8'), patches, reverse=True)
            outputs[path] = restored.encode('utf-8')
        elif path.name in state['additions']:
            added = set(state['additions'][path.name])
            lines = (current or b'').decode('utf-8').splitlines(keepends=True)
            outputs[path] = ''.join(line for line in lines if line.strip() not in added).encode('utf-8')
        # Changed filter settings belong to the user; preserve them.
    outputs[state_path] = None
    _commit(outputs)
    return True


def reapply_custom_preset(preset_id, manager_dir=None):
    root = _root(manager_dir)
    state_path = _state_path(root, preset_id)
    if not state_path.exists():
        return apply_custom_preset(preset_id, str(root))
    preset = _registry(root)[preset_id]
    state = json.loads(state_path.read_text(encoding='utf-8'))
    if state.get('definition_revision', 1) != preset.get('revision', 1):
        return apply_custom_preset(preset_id, root)
    path = root / 'config.txt'
    original = _read(path)
    if original is None:
        raise FileNotFoundError(path)
    updated = _patch(original.decode('utf-8'), preset['patches']).encode('utf-8')
    prior = state['files']['config.txt']
    if updated != original:
        prior.update(before=original.hex(), after=updated.hex())
    _commit({path: updated, state_path: _json(state)})
    return True


def _switch_paths(root):
    """Files touched by built-in/custom preset clearing, for atomic UI switching."""
    paths = {root / 'config.txt'}
    paths.update(root / 'files/lists' / name for name in
                 ('ipset-all_user.txt', 'list-general_user.txt', 'ipset-all.txt'))
    paths.update(root / 'utils' / name for name in
                 ('gamefilter.enable', 'gamefilter.mode', 'gamefilter.ports.json', 'gamefilter.main_bypass.disable',
                  'gamefilter.discord.disable', 'chosen_strategies.txt',
                  'name_strategy.txt', 'working_strategies.txt', 'builtin_game_lists.state.json'))
    paths.update((root / 'utils').glob('game_preset_*'))
    paths.update((root / 'utils').glob('custom_*.state.json'))
    return paths


@contextmanager
def preset_switch_transaction(manager_dir=None):
    """Roll back all preset side effects when switching fails."""
    root = _root(manager_dir)
    from core.config_lock import manager_settings_lock
    with manager_settings_lock(root):
        paths = _switch_paths(root)
        snapshot = {path: _read(path) for path in paths}
        try:
            yield
        except Exception:
            _commit({path: snapshot.get(path) for path in paths | _switch_paths(root)})
            raise
