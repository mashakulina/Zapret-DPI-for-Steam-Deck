"""Conservative, offline Flowseal BAT import. Never executes source files."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile

from core.strategy_paths import LEGACY, LISTS


class ImportRejected(ValueError):
    """The source cannot safely be represented by the Linux starter."""


class ReplacementRequired(ImportRejected):
    pass


def manager_root():
    return Path.home() / 'Zapret_DPI_Manager'


def bin_alias(filename):
    # ARGS is intentionally expanded unquoted by the existing starter. No whitespace,
    # globbing, shell syntax, separators or placeholder punctuation is permitted.
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]*\.bin', filename):
        raise ImportRejected('Недопустимое имя BIN: используйте латинские буквы, цифры, _, - и точку; расширение .bin.')
    stem = filename[:-4]
    alias = LEGACY.get(stem, 'dbankcloud' if stem == 'quic_initial_dbankcloud_ru' else stem)
    reserved = set(LISTS.values()) | {'ipset_all_user', 'GameFilter', 'gw', 'other'}
    if alias in reserved or (alias in set(LEGACY.values()) | {'dbankcloud'} and
                              stem not in set(LEGACY) | {'quic_initial_dbankcloud_ru'}):
        raise ImportRejected(f'Имя BIN конфликтует с подстановкой: {alias}')
    return alias


def _read_regular(path, suffix):
    path = Path(path)
    if path.suffix.lower() != suffix or path.is_symlink() or not path.is_file():
        raise ImportRejected(f'Выберите обычный файл {suffix.upper()}.')
    data = path.read_bytes()
    if not data or b'\0' in data and suffix == '.bat':
        raise ImportRejected('Файл пуст или имеет неподдерживаемый формат.')
    return data


def decode_bat(data):
    # chcp is ASCII in every supported codepage; an explicit declaration wins.
    declaration = re.search(rb'(?im)^\s*@?chcp\s+(\d+)\b', data)
    if declaration and declaration[1] not in (b'65001', b'1251', b'866'):
        raise ImportRejected('Неподдерживаемая кодовая страница BAT (chcp).')
    if data.startswith(b'\xef\xbb\xbf'):
        encoding = 'utf-8-sig'
    elif declaration:
        encoding = {'65001': 'utf-8', '1251': 'cp1251', '866': 'cp866'}[declaration[1].decode()]
    else:
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            encoding = 'cp1251'
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as error:
        raise ImportRejected('Кодировка BAT не соответствует chcp/BOM.') from error


def starter_mappings(text):
    """Locate the real substitution block semantically; reject unfamiliar starters."""
    loops = list(re.finditer(r'^while IFS= read -r line[^\n]*; do\s*$', text, re.M))
    if len(loops) != 1:
        raise ImportRejected('Не найден поддерживаемый блок чтения starter.sh.')
    tail = text[loops[0].end():]
    stop = re.search(r'^done\s*<', tail, re.M)
    if not stop:
        raise ImportRejected('Не найден конец блока starter.sh.')
    block = tail[:stop.start()]
    matches = list(re.finditer(r'^    line="\$\{line//\\\{([A-Za-z0-9_.-]+)\\\}/\$TEMP_DIR/([A-Za-z0-9_.-]+)\}"[ \t]*$', block, re.M))
    if not matches or not {'list_general', 'tlsgoogle'} <= {m[1] for m in matches}:
        raise ImportRejected('Неподдерживаемый блок подстановок starter.sh.')
    mapping = {}
    for m in matches:
        if m[1] in mapping and mapping[m[1]] != m[2]:
            raise ImportRejected(f'Конфликт подстановки {m[1]} в starter.sh.')
        mapping[m[1]] = m[2]
    return mapping, loops[0].end() + matches[-1].end()


def register_bin(text, filename):
    alias = bin_alias(filename)
    mapping, offset = starter_mappings(text)
    if alias in mapping:
        if mapping[alias] != filename:
            raise ImportRejected(f'Конфликт подстановки BIN: {alias}')
        return text
    line = f'    line="${{line//\\{{{alias}\\}}/$TEMP_DIR/{filename}}}"\n'
    # matches may consume the following newline; ensure the insertion starts a line.
    prefix, suffix = text[:offset], text[offset:]
    return prefix.rstrip('\n') + '\n' + line + suffix


def convert_bat(raw, payloads, mappings):
    """Return Linux profiles, validating every placeholder and shell argument."""
    physical = raw.splitlines()
    # Count command launches, not comments, echo text or existence checks.
    launch_prefix = re.compile(r'(?i)^\s*@?(?:start\s+(?:"[^"]*"\s+)?(?:/min\s+)?)?(?:"%BIN%winws\.exe"|%BIN%winws\.exe|winws\.exe)(?:\s|$)')
    starts = [i for i, line in enumerate(physical) if launch_prefix.match(line)]
    # A second unsupported launch must also be rejected rather than ignored.
    suspicious = [line for line in physical if re.match(r'(?i)^\s*@?(?:(?:call|start)\s+|(?:"[^"]*winws\.exe"|[^\s"]*winws\.exe)(?:\s|$))', line)
                  and 'winws.exe' in line.lower() and not launch_prefix.match(line)]
    if suspicious:
        raise ImportRejected('Неподдерживаемый запуск winws.exe.')
    if len(starts) != 1:
        raise ImportRejected('BAT должен содержать ровно один запуск winws.exe.')
    i = starts[0]
    command = []
    while True:
        line = physical[i].strip()
        continued = line.endswith('^')
        command.append(line[:-1].rstrip() if continued else line)
        if not continued:
            break
        i += 1
        if i >= len(physical):
            raise ImportRejected('Незавершённое продолжение команды BAT.')
    joined = ' '.join(command)
    launcher = re.match(r'(?i)^\s*@?(?:(?:start\s+(?:"[^"]*"\s+)?(?:/min\s+)?)?)(?:"%BIN%winws\.exe"|%BIN%winws\.exe|winws\.exe)\s+(.*)$', joined)
    if not launcher:
        raise ImportRejected('Неподдерживаемый запуск winws.exe.')
    joined = launcher[1].replace('^!', '!')
    def path(match):
        kind, filename = match[1].upper(), match[2]
        if kind == 'LISTS':
            if filename not in LISTS:
                raise ImportRejected(f'Неизвестный список: {filename}')
            return '{' + LISTS[filename] + '}'
        alias = bin_alias(filename)
        if filename not in payloads:
            raise ImportRejected(f'Отсутствует BIN: {filename}. Сначала добавьте его.')
        if mappings.get(alias) != filename:
            raise ImportRejected(f'BIN не зарегистрирован в starter.sh: {filename}. Добавьте его повторно.')
        return '{' + alias + '}'
    joined = re.sub(r'"?%(LISTS|BIN)%([^"\s\\/]+)"?', path, joined, flags=re.I)
    joined = re.sub(r'%GameFilter(?:TCP|UDP)%', '{GameFilter}', joined, flags=re.I)
    tokens = joined.split()
    profiles, current = [], []
    allowed = set(LISTS.values()) | {'ipset_all_user', 'GameFilter'} | set(mappings)
    for token in tokens:
        if token.startswith('--wf-'):
            # Only simple filter values are removed, never swallow command syntax.
            if not re.fullmatch(r'--wf-[a-z-]+=[0-9,{}A-Za-z_-]+', token):
                raise ImportRejected(f'Неподдерживаемый Windows-фильтр: {token}')
            continue
        if not token.startswith('--') or re.search(r'[\s%"\'\\^$`;|&<>*?()\[\]~]', token):
            raise ImportRejected(f'Неподдерживаемый аргумент BAT: {token}')
        placeholders = re.findall(r'\{([^{}]+)\}', token)
        if set(placeholders) - allowed or re.sub(r'\{[^{}]+\}', '', token).count('{') or re.sub(r'\{[^{}]+\}', '', token).count('}'):
            raise ImportRejected(f'Неизвестная подстановка: {token}')
        for placeholder in placeholders:
            filename = mappings.get(placeholder, '')
            if filename.endswith('.bin') and filename not in payloads:
                raise ImportRejected(f'Отсутствует BIN: {filename}. Сначала добавьте его.')
        if token == '--new':
            if not current:
                raise ImportRejected('Пустой профиль BAT.')
            profiles.append(current)
            current = []
        else:
            current.append(token)
            if token == '--ipset={ipset_all}':
                current.append('--ipset={ipset_all_user}')
    if not current:
        raise ImportRejected('Пустой профиль BAT.')
    profiles.append(current)
    for profile in profiles:
        if '{GameFilter}' in ' '.join(profile) and not any(t.startswith(('--filter-tcp=', '--filter-udp=')) for t in profile):
            raise ImportRejected('GameFilter требует TCP или UDP фильтр.')
    return '\n'.join(' '.join(p) + (' --new' if i < len(profiles) - 1 else '')
                     for i, p in enumerate(profiles)) + '\n'


def _transaction(entries):
    """Stage all replacements before committing; restore originals on any failure."""
    staged, committed, created_dirs = [], [], []
    try:
        for entry in entries:
            path = Path(entry['path'])
            if path.is_symlink():
                raise ImportRejected(f'Символическая ссылка не поддерживается: {path}')
            old = path.read_bytes() if path.exists() else None
            expected = base64.b64decode(entry['old']) if entry['old'] is not None else None
            if old != expected:
                raise ImportRejected(f'Файл изменился во время импорта: {path}')
            missing = []
            directory = path.parent
            while not directory.exists():
                missing.append(directory)
                directory = directory.parent
            for directory in reversed(missing):
                directory.mkdir()
                created_dirs.append(directory)
            fd, temp = tempfile.mkstemp(prefix='.strategy-import-', dir=path.parent)
            staged.append((path, Path(temp), old, entry))
            with os.fdopen(fd, 'wb') as out:
                out.write(base64.b64decode(entry['data']))
                out.flush()
                os.fsync(out.fileno())
            os.chmod(temp, entry['mode'])
            if os.geteuid() == 0:
                os.chown(temp, entry['uid'], entry['gid'])
        for item in staged:
            os.replace(item[1], item[0])
            committed.append(item)
    except Exception:
        for path, temp, old, entry in reversed(committed):
            if old is None:
                path.unlink()
            else:
                fd, rollback = tempfile.mkstemp(prefix='.strategy-rollback-', dir=path.parent)
                with os.fdopen(fd, 'wb') as out:
                    out.write(old)
                os.chmod(rollback, entry['mode'])
                if os.geteuid() == 0:
                    os.chown(rollback, entry['uid'], entry['gid'])
                os.replace(rollback, path)
        raise
    finally:
        for _, temp, _, _ in staged:
            temp.unlink(missing_ok=True)
        for directory in reversed(created_dirs):
            try:
                directory.rmdir()
            except OSError:
                pass


_transaction_impl = _transaction


def write_transaction(outputs, password=None):
    entries = []
    for path, data in outputs.items():
        path = Path(path)
        if path.is_symlink():
            raise ImportRejected(f'Символическая ссылка не поддерживается: {path}')
        info = path.stat() if path.exists() else None
        entries.append(dict(path=str(path.resolve()), data=base64.b64encode(data).decode(),
                            old=base64.b64encode(path.read_bytes()).decode() if info else None,
                            mode=stat.S_IMODE(info.st_mode) if info else 0o644,
                            uid=info.st_uid if info else os.getuid(), gid=info.st_gid if info else os.getgid()))
    try:
        _transaction(entries)
    except PermissionError:
        if password is None:
            raise
        # Pass code as argv and password solely on stdin. No shell is involved.
        import inspect
        code = 'import os,sys,json,base64,tempfile\nfrom pathlib import Path\nclass ImportRejected(ValueError): pass\n' + inspect.getsource(_transaction_impl) + '\nwith open(sys.argv[1]) as source: _transaction(json.load(source))\n'
        # A private payload file avoids argv size limits for large user BINs.
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', prefix='strategy-import-') as payload:
            json.dump(entries, payload)
            payload.flush()
            result = subprocess.run(['sudo', '-S', '-p', '', '--', sys.executable, '-c', code, payload.name],
                                    input=password + '\n', capture_output=True, text=True)
        if result.returncode:
            raise ImportRejected('Не удалось сохранить файлы через sudo: ' + result.stderr.strip())


class StrategyImporter:
    def __init__(self, root=None, installed_starter='/opt/zapret/starter.sh', template=None):
        self.root = Path(root) if root is not None else manager_root()
        self.installed_starter = Path(installed_starter)
        self.template = Path(template) if template is not None else self.root / 'zapret/system/starter.sh'

    def _starters(self, include_template=True):
        result = {}
        # The installer removes <manager>/zapret after copying the runtime to
        # /opt/zapret. A bundled template is optional in an installed manager.
        paths = [self.installed_starter]
        if include_template and (self.template.exists() or self.template.is_symlink()):
            paths.insert(0, self.template)
        for path in dict.fromkeys(paths):
            if path.is_symlink() or not path.is_file():
                raise ImportRejected(f'Не найден обычный starter.sh: {path}')
            text = path.read_text(encoding='utf-8')
            starter_mappings(text)
            result[path] = text
        return result

    def convert(self, source, overwrite=False):
        source = Path(source)
        raw = decode_bat(_read_regular(source, '.bat'))
        if not source.stem or source.stem.startswith('.') or any(ord(c) < 32 for c in source.stem):
            raise ImportRejected('Недопустимое имя стратегии.')
        # The installed starter is the runtime authority. A manager-only update may
        # have reset the bundled template while installed custom mappings survive.
        starters = self._starters(include_template=False)
        common = starter_mappings(next(iter(starters.values())))[0]
        payloads = {p.name for p in (self.root / 'files/bin').glob('*.bin') if p.is_file() and not p.is_symlink() and p.stat().st_size}
        converted = convert_bat(raw, payloads, common)
        target = self.root / 'files/strategy' / source.stem
        if target.exists() and not overwrite:
            raise ReplacementRequired(f'Стратегия «{source.stem}» уже существует. Заменить?')
        write_transaction({target: converted.encode('utf-8')})
        return target

    def add_bin(self, source, overwrite=False, password=None):
        source = Path(source)
        data = _read_regular(source, '.bin')
        alias = bin_alias(source.name)
        for existing in (self.root / 'files/bin').glob('*.bin'):
            if existing.name == source.name:
                continue
            # Manual legacy payloads with unsafe names are unrelated to this import.
            # Still detect a reserved legacy alias shadowed by an existing filename.
            existing_alias = LEGACY.get(existing.stem, 'dbankcloud' if existing.stem == 'quic_initial_dbankcloud_ru' else existing.stem)
            if existing_alias == alias:
                raise ImportRejected(f'Коллизия BIN: {existing.name}')
        target = self.root / 'files/bin' / source.name
        if target.exists() and not overwrite:
            raise ReplacementRequired(f'BIN «{source.name}» уже существует. Заменить?')
        starters = self._starters()
        outputs = {target: data}
        for path, text in starters.items():
            updated = register_bin(text, source.name)
            if updated != text:
                outputs[path] = updated.encode('utf-8')
        write_transaction(outputs, password=password)
        return target


def starter_with_manager_bins(text, root=None):
    """Reapply custom substitutions when the service updater replaces its template."""
    root = Path(root) if root is not None else manager_root()
    for payload in sorted((root / 'files/bin').glob('*.bin')):
        if payload.is_file() and not payload.is_symlink():
            try:
                bin_alias(payload.name)
            except ImportRejected:
                continue
            text = register_bin(text, payload.name)
    return text
