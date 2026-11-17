"""Validate external strategy payloads before changing a running configuration.

Also executable with python3 -I by the installed starter (no project imports).
"""
from pathlib import Path
import os
import re
import stat
import sys


class PayloadUnavailable(ValueError):
    pass


def validate_payloads(text, root=None, starter='/opt/zapret/starter.sh', payload_dir=None):
    root = Path(root) if root is not None else Path.home() / 'Zapret_DPI_Manager'
    # No external payload means no dependency on the installed alias registry.
    clean = '\n'.join(line.split('#', 1)[0] for line in text.lstrip('\ufeff').splitlines())
    values = re.findall(r'--dpi-desync-(?:fake-(?:http|tls|quic|discord|stun|syndata|unknown|unknown-udp)|split-seqovl-pattern|fakedsplit-pattern|udplen-pattern)=([^\s]+)', clean)
    external = [v for v in values if v != '!' and not re.fullmatch(r'0x[0-9a-fA-F]*', v)]
    aliases = set(re.findall(r'\{([^{}]+)\}', clean)) - {
        'list_general', 'list_general_user', 'list_exclude', 'list_exclude_user',
        'list_google', 'ipset_all', 'ipset_all_user', 'ipset_exclude', 'ipset_exclude_user',
        'GameFilter', 'gw', 'other'}
    if not external and not aliases:
        return []
    starter = Path(starter)
    if str(starter) == '/opt/zapret/starter.sh' and not starter.exists() and not starter.is_symlink():
        starter = root / 'zapret/system/starter.sh'
    if starter.is_symlink() or not starter.is_file():
        raise PayloadUnavailable(f'Не найден обычный starter.sh: {starter}')
    mapping = dict(re.findall(r'^    line="\$\{line//\\\{([A-Za-z0-9_.-]+)\\\}/\$TEMP_DIR/([A-Za-z0-9_.-]+)\}"[ \t]*$', starter.read_text(), re.M))
    paths = set()
    for alias in aliases:
        filename = mapping.get(alias)
        if not filename or not filename.endswith('.bin'):
            raise PayloadUnavailable(f'Неизвестная подстановка BIN: {{{alias}}}')
        paths.add((Path(payload_dir) if payload_dir else root / 'files/bin') / filename)
    for value in external:
        if '"' in value or "'" in value:
            raise PayloadUnavailable('Пути BIN в кавычках не поддерживаются starter.sh. Используйте зарегистрированную подстановку {alias} или путь без пробелов и кавычек.')
        if re.fullmatch(r'\{[^{}]+\}', value):
            continue
        if '{' in value or '}' in value:
            raise PayloadUnavailable(f'Некорректная ссылка BIN: {value}')
        path = Path(value)
        paths.add(path if path.is_absolute() else root / path)
    for path in sorted(paths):
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or not info.st_size or not info.st_mode & 0o444:
                raise OSError('не обычный читаемый непустой файл')
            # O_NOFOLLOW also closes the symlink race between lstat and open.
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or not os.read(fd, 1):
                    raise OSError('пустой или не обычный файл')
            finally:
                os.close(fd)
        except OSError as error:
            raise PayloadUnavailable(f'BIN недоступен: {path} ({error})') from error
    return sorted(paths)


def validate_active(root=None, starter='/opt/zapret/starter.sh'):
    root = Path(root) if root is not None else Path.home() / 'Zapret_DPI_Manager'
    return validate_payloads((root / 'config.txt').read_text(encoding='utf-8-sig'), root, starter)


if __name__ == '__main__':
    try:
        root = Path(sys.argv[1])
        text = (root / 'config.txt').read_text(encoding='utf-8-sig')
        for path in validate_payloads(text, root, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None):
            print(path)
    except (OSError, ValueError) as error:
        print(f'Error: {error}; nfqws was not started.', file=sys.stderr)
        sys.exit(1)
