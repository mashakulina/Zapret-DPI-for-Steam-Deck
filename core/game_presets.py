# -*- coding: utf-8 -*-
"""Пресеты игр для GameFilter: строки для добавления в начало config.txt."""

import os

# Префикс файла-маркера в utils: наличие utils/game_preset_{preset_id} = пресет применён
PRESET_FILE_PREFIX = "game_preset_"

# Ключ — идентификатор пресета, значение — список строк для config.txt
GAME_PRESETS = {
    "guild_wars_2": {
        "name": "Guild Wars 2",
        "lines": [
            "--filter-tcp=443 --hostlist-domains=ncplatform.net,privacy.xboxlive.com,guildwars2.com,staticwars.com,catalog.gamepass.com --dpi-desync=hostfakesplit --dpi-desync-hostfakesplit-mod=host=amd.com --dpi-desync-fooling=ts --new",
            "--filter-tcp=443 --ipset-ip=104.21.26.0/24,172.67.0.0/16,4.225.11.0/24,185.199.108.0/24,35.156.125.0/24 --dpi-desync=hostfakesplit --dpi-desync-hostfakesplit-mod=host=amd.com --dpi-desync-fooling=ts --new",
            "--filter-tcp=80 --hostlist-domains=assetcdn.101.ArenaNetworks.com --dpi-desync=fake --dpi-desync-fake-http={tlsmax} --dpi-desync-fooling=ts --dpi-desync-cutoff=d2 --new",
            "--filter-tcp=6112 --ipset={gw} --dpi-desync=fake --dpi-desync-fake-unknown={tlsmax} --dpi-desync-any-protocol --dpi-desync-fooling=badseq --dpi-desync-repeats=1 --dpi-desync-cutoff=d3 --new",
        ],
    },
}

def get_manager_dir():
    """Каталог менеджера (Zapret_DPI_Manager)."""
    return os.path.expanduser("~/Zapret_DPI_Manager")


def get_preset_marker_path(preset_id, manager_dir=None):
    """Путь к файлу-маркеру пресета в utils. Файл есть — пресет применён."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    return os.path.join(manager_dir, "utils", f"{PRESET_FILE_PREFIX}{preset_id}")


def get_active_preset_id(manager_dir=None):
    """Возвращает preset_id применённого пресета или None, если ни один не применён."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    for preset_id in GAME_PRESETS:
        if os.path.exists(get_preset_marker_path(preset_id, manager_dir)):
            return preset_id
    return None


def set_active_preset(preset_id, manager_dir=None):
    """Помечает пресет как активный: создаёт его файл в utils, удаляет файлы остальных."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    utils_dir = os.path.join(manager_dir, "utils")
    if not os.path.isdir(utils_dir):
        os.makedirs(utils_dir, exist_ok=True)
    path = get_preset_marker_path(preset_id, manager_dir)
    with open(path, "w") as f:
        f.write("")
    for pid in GAME_PRESETS:
        if pid != preset_id:
            other = get_preset_marker_path(pid, manager_dir)
            if os.path.isfile(other):
                try:
                    os.remove(other)
                except OSError:
                    pass


def clear_active_preset(manager_dir=None):
    """Снимает применение пресетов: удаляет все файлы-маркеры в utils."""
    if manager_dir is None:
        manager_dir = get_manager_dir()
    for preset_id in GAME_PRESETS:
        path = get_preset_marker_path(preset_id, manager_dir)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def remove_preset_lines_from_config(preset_id, manager_dir=None):
    """Удаляет строки пресета из начала config.txt (блок, добавленный при применении)."""
    if preset_id not in GAME_PRESETS:
        return
    if manager_dir is None:
        manager_dir = get_manager_dir()
    config_path = os.path.join(manager_dir, "config.txt")
    if not os.path.isfile(config_path):
        return
    preset_lines = [line.strip() for line in GAME_PRESETS[preset_id]["lines"]]
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    config_lines = content.splitlines()
    i = 0
    for p_line in preset_lines:
        if i < len(config_lines) and config_lines[i].strip() == p_line:
            i += 1
        else:
            break
    if i == 0:
        return
    new_content = "\n".join(config_lines[i:])
    if config_lines[i:]:
        new_content += "\n"
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)
