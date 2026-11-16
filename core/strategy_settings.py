"""Single-config editing and conservative UDP payload selection.

Token spans refer to the original text, so unrelated bytes survive replacement.
"""
from __future__ import annotations
import base64
import hashlib
from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import subprocess
from core.strategy_import import bin_alias, manager_root, starter_mappings, _transaction, ImportRejected
from core.game_presets import get_game_presets, get_active_preset_id


class ConfigConflict(ValueError):
    pass


class ConfigDocument:
    def __init__(self, config_path=None, root=None):
        self.root = Path(root) if root is not None else manager_root()
        self.path = Path(config_path) if config_path is not None else self.root / 'config.txt'
        self.original = self._read()
        if not self.original.decode('utf-8-sig').strip():
            raise ValueError('Выбранный config пуст.')
        self.text = self.original.decode('utf-8')

    def _read(self):
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError(f'Не найден обычный файл config: {self.path}')
        return self.path.read_bytes()

    @property
    def active(self):
        return self.path.resolve() == (self.root / 'config.txt').resolve()

    @property
    def editor_text(self):
        return self.text.removeprefix('\ufeff').replace('\r\n', '\n').replace('\r', '\n')

    def save_editor(self, text):
        if text == self.editor_text:
            return self.save_bytes(self.original)
        newline = '\r\n' if b'\r\n' in self.original else '\n'
        data = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', newline).encode('utf-8')
        if self.original.startswith(b'\xef\xbb\xbf'):
            data = b'\xef\xbb\xbf' + data
        return self.save_bytes(data)

    def save_bytes(self, data):
        decoded = data.decode('utf-8')
        if not decoded.removeprefix('\ufeff').strip():
            raise ValueError('Пустой config не сохранён.')
        if self._read() != self.original:
            raise ConfigConflict('Config изменился на диске. Откройте его заново, чтобы не потерять внешние изменения.')
        if data == self.original:
            return False
        if not data.strip():
            raise ValueError('Пустой config не сохранён.')
        info = self.path.stat()
        entry = dict(path=str(self.path.absolute()), old=base64.b64encode(self.original).decode(),
                     data=base64.b64encode(data).decode(), mode=stat.S_IMODE(info.st_mode),
                     uid=info.st_uid, gid=info.st_gid)
        _transaction([entry])
        self.original = data
        self.text = data.decode('utf-8')
        return True


@dataclass(frozen=True)
class Payload:
    filename: str
    alias: str


def registered_payloads(root=None, installed_starter='/opt/zapret/starter.sh'):
    root = Path(root) if root is not None else manager_root()
    starter = Path(installed_starter)
    if starter.is_symlink():
        raise ValueError('Символическая ссылка starter.sh не поддерживается.')
    mapping, _ = starter_mappings(starter.read_text(encoding='utf-8'))
    result = []
    for path in sorted((root / 'files/bin').glob('*.bin')):
        if path.is_symlink() or not path.is_file() or not path.stat().st_size:
            continue
        try:
            alias = bin_alias(path.name)
        except ImportRejected:
            continue
        if mapping.get(alias) == path.name:
            result.append(Payload(path.name, alias))
    return result


def current_payload_label(alias, payloads, root=None):
    """Resolve ACTIVE contents like Flowseal, without changing their global files."""
    by_alias = {p.alias: p for p in payloads}
    payload = by_alias.get(alias)
    if payload is None:
        return '{' + alias + '} — BIN недоступен'
    if alias not in ('ACTIVE_DISCORD_UDP', 'ACTIVE_GAME_UDP'):
        return payload.filename
    root = Path(root) if root is not None else manager_root()
    active = root / 'files/bin' / payload.filename
    digest = hashlib.sha256(active.read_bytes()).digest()
    matches = []
    for path in sorted((root / 'files/bin').glob('*.bin')):
        if path.name.startswith('ACTIVE_') or path.is_symlink() or not path.is_file() or not path.stat().st_size:
            continue
        try:
            bin_alias(path.name)
        except ImportRejected:
            continue
        if hashlib.sha256(path.read_bytes()).digest() == digest:
            matches.append(path.name)
    name = ', '.join(matches) if matches else 'Пользовательский фейк'
    return name + ' (текущий ' + payload.filename + ')'


@dataclass
class FakeSlot:
    spans: list
    current_alias: str | None
    reason: str = ''

    @property
    def enabled(self):
        return bool(self.spans) and not self.reason


def fake_slots(text, root=None):
    # Comments have no arguments, even when they contain --new or fake options.
    tokens = list(re.compile(r'#[^\r\n]*|[^\s#]+').finditer(text, 1 if text.startswith('\ufeff') else 0))
    profiles, current = [], []
    for token in tokens:
        if token[0].startswith('#'):
            continue
        if token[0] == '--new':
            profiles.append(current)
            current = []
        else:
            current.append(token)
    profiles.append(current)
    preset = get_game_presets(str(root or manager_root())).get(get_active_preset_id(str(root or manager_root())), {})
    game_ports = preset.get('game_filter_udp')
    custom_game_ports = {match.group(1) for line in preset.get('lines', [])
                         if preset.get('custom') and '--ipset={ipset_all}' in line
                         for match in re.finditer(r'--filter-udp=([^\s]+)', line)}
    found = {'discord': [], 'game': []}
    for profile in profiles:
        values = [m[0] for m in profile]
        udp = [v.split('=', 1)[1] for v in values if v.startswith('--filter-udp=')]
        if len(udp) != 1 or any(v.startswith('--filter-tcp=') for v in values):
            continue
        l7 = [v.split('=', 1)[1].split(',') for v in values if v.startswith('--filter-l7=')]
        kind = None
        if len(l7) == 1 and {'discord', 'stun'} <= set(l7[0]):
            kind = 'discord'
        elif udp[0] == '{GameFilter}' or ((udp[0] in custom_game_ports or (game_ports and udp[0] == game_ports)) and '--ipset={ipset_all}' in values):
            kind = 'game'
        if kind is None:
            continue
        options = ('discord', 'stun', 'unknown-udp') if kind == 'discord' else ('unknown-udp',)
        targets = []
        for option in options:
            prefix = '--dpi-desync-fake-' + option + '='
            matching = [m for m in profile if m[0].startswith(prefix)]
            if matching:
                targets.append((matching[-1], prefix))
        found[kind].append(targets)
    result = {}
    for kind, candidates in found.items():
        reason = ''
        spans, aliases = [], []
        if not candidates:
            reason = 'Поддерживаемый UDP-профиль отсутствует.'
        elif len(candidates) != 1 or not candidates[0]:
            reason = 'Неоднозначный профиль или отсутствуют fake-параметры.'
        else:
            for token, prefix in candidates[0]:
                value = token[0][len(prefix):]
                match = re.fullmatch(r'\{([A-Za-z0-9_.-]+)\}', value)
                if not match:
                    reason = 'Fake-параметр не является зарегистрированной подстановкой.'
                    break
                aliases.append(match[1])
                spans.append((token.start() + len(prefix), token.end()))
            if len(set(aliases)) != 1:
                reason = 'Изменяемые fake-параметры используют разные BIN.'
        result[kind] = FakeSlot(spans, aliases[0] if aliases and not reason else None, reason)
    return result


def replace_fakes(text, selections, payloads, root=None):
    available = {p.alias for p in payloads}
    slots = fake_slots(text, root)
    changes = []
    for kind, alias in selections.items():
        if kind not in slots or not slots[kind].enabled:
            raise ValueError(slots[kind].reason if kind in slots else 'Неизвестный профиль.')
        if alias not in available:
            raise ValueError('BIN отсутствует, пуст или не зарегистрирован в установленном starter.sh.')
        changes.extend((start, end, '{' + alias + '}') for start, end in slots[kind].spans)
    for start, end, value in sorted(changes, reverse=True):
        text = text[:start] + value + text[end:]
    return text


def restart_zapret(password=None, runner=None):
    runner = runner or subprocess.run
    argv = ['systemctl', 'restart', 'zapret']
    kwargs = dict(capture_output=True, text=True, timeout=30)
    if os.geteuid() != 0:
        argv = ['sudo', '-S', '-p', '', '--'] + argv
        kwargs['input'] = (password or '') + '\n'
    result = runner(argv, **kwargs)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or 'Не удалось перезапустить Zapret.')
    status = runner(['systemctl', 'is-active', '--quiet', 'zapret'], capture_output=True, text=True, timeout=10)
    if status.returncode:
        raise RuntimeError('Служба Zapret не активна после перезапуска.')
