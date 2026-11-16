"""Connect Telegram without depending on the proxy bundle's pyperclip backend."""

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import urlencode

from core.tg_ws_proxy import ProxyError
from core.tg_proxy_desktop import _external_environment


def connection_link(config_file):
    try:
        with Path(config_file).open('rb') as stream:
            config = json.loads(stream.read(1024 * 1024))
        host, port, secret = config['host'], config['port'], config['secret']
        if (not isinstance(host, str) or not host or any(ord(c) < 33 for c in host)
                or type(port) is not int or not 1 <= port <= 65535
                or not isinstance(secret, str) or not re.fullmatch(r'[0-9a-fA-F]{32}', secret)):
            raise ValueError('invalid proxy settings')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ProxyError('Не удалось прочитать настройки подключения. Запустите TG WS Proxy '
                         'и завершите его первоначальную настройку.') from exc
    host = '127.0.0.1' if host in ('0.0.0.0', '::', '[::]') else host
    return 'tg://proxy?' + urlencode({'server': host, 'port': port, 'secret': 'dd' + secret})


def copy_with_desktop(text, *, env=None, which=shutil.which, runner=subprocess.run):
    """Return False for a Tk fallback; never include clipboard contents in errors."""
    env = os.environ if env is None else env
    commands = []
    if env.get('WAYLAND_DISPLAY') and (command := which('wl-copy')):
        commands.append(([command], text))
    if command := which('xclip'):
        commands.append(([command, '-selection', 'clipboard'], text))
    if command := which('xsel'):
        commands.append(([command, '--clipboard', '--input'], text))
    for name in ('qdbus6', 'qdbus'):
        if command := which(name):
            commands.append(([command, 'org.kde.klipper', '/klipper', 'setClipboardContents', text], None))
    for argv, stdin in commands:
        try:
            result = runner(argv, input=stdin, text=True, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, timeout=5, env=_external_environment(env))
            if result.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def open_in_telegram(link, *, runner=subprocess.run, which=shutil.which):
    command = which('xdg-open')
    if not command:
        raise ProxyError('Не найден xdg-open. Скопируйте ссылку и откройте её в Telegram вручную.')
    try:
        result = runner([command, link], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, timeout=15, env=_external_environment(os.environ))
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProxyError('Не удалось открыть Telegram. Скопируйте ссылку и откройте её вручную.') from exc
    if result.returncode:
        raise ProxyError('Telegram не обработал ссылку подключения. Проверьте установку Telegram '
                         'или воспользуйтесь кнопкой «Скопировать ссылку».')
