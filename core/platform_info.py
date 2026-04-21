"""Определение дистрибутива и бэкенда установки пакетов."""

import os
import shutil


def parse_os_release():
    data = {}
    try:
        with open("/etc/os-release", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    data[key.strip()] = val.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def os_release_id_normalized():
    """Поле ID из /etc/os-release (нижний регистр), без подстановок по подстрокам."""
    return (parse_os_release().get("ID") or "").lower()


def is_valve_steamos():
    """
    Только официальная SteamOS от Valve (поле ID=steamos).

    Не полагаемся на steamos-readonly, подстроки во всём os-release и /home/deck:
    Bazzite и др. образы могут это иметь при своём ID.
    """
    return os_release_id_normalized() == "steamos"


def distro_log_label():
    """Краткая строка для логов (PRETTY_NAME / NAME / ID)."""
    data = parse_os_release()
    return (
        data.get("PRETTY_NAME")
        or data.get("NAME")
        or data.get("ID")
        or "Linux"
    )


def is_ostree_boot():
    return os.path.isfile("/run/ostree-booted")


def detect_package_backend():
    """
    Бэкенд для установки пакетов на текущей системе.

    Порядок: Valve SteamOS → pacman; иначе Fedora Atomic (booted ostree + rpm-ostree);
    затем dnf, apt, zypper, yum, произвольный pacman.

    rpm-ostree без /run/ostree-booted не выбираем первым (на обычном Fedora пакет
    rpm-ostree может быть без immutable корня).
    """
    if is_valve_steamos():
        return "pacman"

    if is_ostree_boot() and shutil.which("rpm-ostree"):
        return "rpm-ostree"

    if shutil.which("dnf"):
        return "dnf"

    if shutil.which("apt"):
        return "apt"

    if shutil.which("zypper"):
        return "zypper"

    if shutil.which("yum"):
        return "yum"

    if shutil.which("pacman"):
        return "pacman"

    return None


def dependency_package_name(logical_name, backend):
    """
    Имя пакета в репозитории. logical_name — как в списке зависимостей приложения.
    """
    ln = (logical_name or "").lower()
    if ln == "nft":
        if backend in (
            "pacman",
            "apt",
            "dnf",
            "rpm-ostree",
            "zypper",
            "yum",
        ):
            return "nftables"
    return logical_name


def install_command_for_package(backend, package_name):
    """Команда: список argv для установки одного пакета с sudo."""
    if backend == "pacman":
        return ["pacman", "-S", "--noconfirm", package_name]
    if backend == "apt":
        return ["apt", "install", "-y", package_name]
    if backend == "dnf":
        return ["dnf", "install", "-y", package_name]
    if backend == "rpm-ostree":
        return ["rpm-ostree", "install", "--assumeyes", package_name]
    if backend == "zypper":
        return ["zypper", "--non-interactive", "install", package_name]
    if backend == "yum":
        return ["yum", "install", "-y", package_name]
    return None


def remove_command_for_package(backend, package_name):
    """Команда удаления одного пакета (для деинсталлятора и т.п.)."""
    if backend == "pacman":
        return ["pacman", "-Rns", "--noconfirm", package_name]
    if backend == "apt":
        return ["apt", "remove", "-y", package_name]
    if backend == "dnf":
        return ["dnf", "remove", "-y", package_name]
    if backend == "rpm-ostree":
        return ["rpm-ostree", "uninstall", "--assumeyes", package_name]
    if backend == "zypper":
        return ["zypper", "--non-interactive", "remove", package_name]
    if backend == "yum":
        return ["yum", "remove", "-y", package_name]
    return None


# Локальный unit Zapret (менеджер): /etc — доступна запись на immutable-/usr системах (Bazzite, Silverblue и т.д.).
ZAPRET_SYSTEMD_UNIT_DIR = "/etc/systemd/system"
ZAPRET_SYSTEMD_UNIT_PATH = "/etc/systemd/system/zapret.service"
# Ранее использовался путь в образе; учитываем при проверке «установлено» и удаляем при деинсталляции.
ZAPRET_SYSTEMD_UNIT_PATH_LEGACY = "/usr/lib/systemd/system/zapret.service"


def zapret_systemd_unit_is_present():
    """Файл unit в /etc (текущий) или legacy в /usr."""
    return os.path.isfile(ZAPRET_SYSTEMD_UNIT_PATH) or os.path.isfile(
        ZAPRET_SYSTEMD_UNIT_PATH_LEGACY
    )
