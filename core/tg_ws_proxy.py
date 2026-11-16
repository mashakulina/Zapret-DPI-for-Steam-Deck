"""Official Flowseal GUI installation; no Telegram secrets or sudo cache here."""

import ctypes
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import select
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from core import platform_info
from core.tg_proxy_desktop import BRIDGE_MARKER, prepare_clipboard_environment

PROJECT_URL = "https://github.com/Flowseal/tg-ws-proxy"
RELEASE_API = "https://api.github.com/repos/Flowseal/tg-ws-proxy/releases/latest"
ASSET_BASE = "TgWsProxy_linux_amd64"
OWNER = "X-Zapret-Manager=true"
MAX_ASSET_SIZE = 512 * 1024 * 1024
_INSTALL_LOCK = threading.Lock()


class ProxyError(Exception):
    """An actionable error safe to display without command output/passwords."""


@dataclass(frozen=True)
class InstallPlan:
    distro: str
    architecture: str
    backend: str | None

    @property
    def asset_name(self):
        suffix = ".deb" if self.backend == "apt" else ".rpm" if self.backend else ""
        return ASSET_BASE + suffix

    @property
    def description(self):
        return f"Системный пакет ({self.backend})" if self.backend else "Standalone в каталоге пользователя (без sudo)"


def detect_plan(machine=None, system=None, release=None, backend=None, ostree=None):
    machine = platform.machine() if machine is None else machine
    if (platform.system() if system is None else system) != "Linux":
        raise ProxyError("TG WS Proxy доступен здесь только для Linux.")
    if machine.lower() not in ("x86_64", "amd64"):
        raise ProxyError(f"Нет официальной Linux-сборки для архитектуры {machine}; требуется x86_64/amd64.")
    release = platform_info.parse_os_release() if release is None else release
    backend = platform_info.detect_package_backend() if backend is None else backend
    ostree = platform_info.is_ostree_boot() if ostree is None else ostree
    ids = {release.get("ID", "").lower(), *release.get("ID_LIKE", "").lower().split()}
    native = None
    if not ostree and not ids.intersection({"steamos", "arch"}):
        if ids.intersection({"debian", "ubuntu", "linuxmint"}) and backend == "apt":
            native = backend
        elif ids.intersection({"fedora", "rhel", "centos"}) and backend in ("dnf", "yum"):
            native = backend
    return InstallPlan(release.get("PRETTY_NAME") or release.get("ID") or "Linux", machine, native)


def _atomic_write(path, data, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tg-ws-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def desktop_exec(path):
    """Escape Exec quoting first, then Desktop Entry string escaping (spec)."""
    value = str(path)
    if "=" in value or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ProxyError("Путь содержит недопустимые символы для автозапуска.")
    return _desktop_argument(value)


def _desktop_argument(value):
    if any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ProxyError("Путь содержит недопустимые символы для автозапуска.")
    value = value.replace("%", "%%")
    value = re.sub(r'([\\"`$])', r'\\\1', value)
    return '"' + value.replace("\\", "\\\\") + '"'


class TgWsProxy:
    def __init__(self, *, home=None, env=None, plan=None, opener=urlopen,
                 runner=subprocess.run, launcher=subprocess.Popen, runtime_loader=ctypes.CDLL,
                 proc_root="/proc", pidfd_opener=None, process_signaler=None, process_waiter=None):
        env = os.environ if env is None else env
        self.environment = dict(env)
        home = Path.home() if home is None else Path(home)
        def xdg(key, fallback):
            value = Path(env.get(key) or fallback)
            return value if value.is_absolute() else home / fallback.relative_to(home)
        self.data_dir = xdg("XDG_DATA_HOME", home / ".local/share") / "zapret-dpi-manager/tg-ws-proxy"
        self.autostart = xdg("XDG_CONFIG_HOME", home / ".config") / "autostart/zapret-tg-ws-proxy.desktop"
        self.flowseal_dir = xdg("XDG_CONFIG_HOME", home / ".config") / "TgWsProxy"
        self.receipt = self.data_dir / "installed.json"
        self.plan = detect_plan() if plan is None else plan
        self.binary = Path("/usr/bin/tg-ws-proxy") if self.plan.backend else self.data_dir / ASSET_BASE
        self.opener, self.runner, self.launcher = opener, runner, launcher
        self.runtime_loader = runtime_loader
        self.proc_root = Path(proc_root)
        self.pidfd_opener = pidfd_opener or getattr(os, "pidfd_open", None)
        self.process_signaler = process_signaler or getattr(signal, "pidfd_send_signal", None)
        self.process_waiter = process_waiter or self._wait_for_exit

    def installed(self):
        if not self.binary.is_file() or not os.access(self.binary, os.X_OK):
            return False
        if not self.plan.backend:
            return True
        return self._native_package_owns_binary()

    def _native_package_owns_binary(self):
        """Package file lists also identify a damaged installation with a missing GUI."""
        try:
            if self.plan.backend == "apt":
                argv = ["dpkg-query", "-S", str(self.binary)]
            else:
                argv = ["rpm", "-qf", "--qf", "%{NAME}", "--", str(self.binary)]
            result = self.runner(argv, capture_output=True, text=True, timeout=15)
            if result.returncode != 0:
                return False
            if self.plan.backend == "apt":
                return any(line == f"tg-ws-proxy: {self.binary}" or line == f"tg-ws-proxy:amd64: {self.binary}"
                           for line in result.stdout.splitlines())
            return result.stdout.strip() == "tg-ws-proxy"
        except (OSError, subprocess.SubprocessError):
            return False

    def version(self):
        if not self.installed():
            return "не установлен"
        try:
            data = json.loads(self.receipt.read_text(encoding="utf-8"))
            if (isinstance(data, dict) and isinstance(data.get("version"), str)
                    and data.get("binary") == str(self.binary) and data.get("sha256") == self._binary_hash()):
                return data["version"]
        except (OSError, ValueError, KeyError):
            pass
        return "неизвестна (найден GUI по ожидаемому пути)"

    def _binary_hash(self):
        digest = hashlib.sha256()
        with self.binary.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _open(self, url):
        return self.opener(Request(url, headers={"User-Agent": "Zapret-DPI-Manager", "Accept": "application/vnd.github+json"}), timeout=30)

    def latest(self):
        try:
            with self._open(RELEASE_API) as response:
                release = json.loads(response.read(2 * 1024 * 1024 + 1))
            tag = release["tag_name"]
            if release.get("draft") or release.get("prerelease") or not re.fullmatch(r"v?\d+\.\d+\.\d+(?:\.\d+)?", tag):
                raise ValueError("not stable")
            assets = [a for a in release["assets"] if a["name"] == self.plan.asset_name]
            if len(assets) != 1:
                raise ValueError("asset absent")
            asset = assets[0]
            parsed = urlparse(asset["browser_download_url"])
            if (parsed.scheme != "https" or parsed.netloc != "github.com" or parsed.query or parsed.fragment
                    or parsed.path != f"/Flowseal/tg-ws-proxy/releases/download/{tag}/{self.plan.asset_name}"):
                raise ValueError("untrusted URL")
            if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", asset.get("digest", "")):
                raise ValueError("missing SHA-256")
            if type(asset["size"]) is not int or not 0 < asset["size"] <= MAX_ASSET_SIZE:
                raise ValueError("invalid size")
            return tag, asset
        except Exception as exc:
            raise ProxyError("Не удалось получить проверенный стабильный релиз GitHub. Проверьте сеть, лимит API и наличие Linux asset с SHA-256.") from exc

    def _download(self, asset, target, progress):
        digest, size = hashlib.sha256(), 0
        try:
            with self._open(asset["browser_download_url"]) as response, target.open("wb") as stream:
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > asset["size"]:
                        raise ValueError("oversized")
                    stream.write(chunk)
                    digest.update(chunk)
                    progress(f"Загрузка: {size * 100 // asset['size']}%")
            if size != asset["size"] or digest.hexdigest() != asset["digest"].split(":")[1].lower():
                raise ValueError("checksum/size")
        except Exception as exc:
            raise ProxyError("Загрузка не прошла проверку размера/SHA-256 либо прервана. Установка отменена.") from exc

    def check_runtime(self):
        for name in ("libc.so.6", "libdl.so.2", "libpthread.so.0"):
            try:
                self.runtime_loader(name)
            except OSError as exc:
                raise ProxyError(f"Для standalone требуется системная библиотека {name}. Установите совместимое glibc-окружение и повторите.") from exc

    def install(self, password=None, progress=lambda text: None):
        # Also covers reopening a window while its previous worker still installs.
        if not _INSTALL_LOCK.acquire(blocking=False):
            raise ProxyError("Другая операция TG WS Proxy ещё выполняется. Дождитесь её завершения.")
        try:
            return self._install(password, progress)
        finally:
            _INSTALL_LOCK.release()

    def _install(self, password, progress):
        if self.plan.backend and self.binary.exists() and not self.installed():
            raise ProxyError("Ожидаемый путь GUI занят файлом другого происхождения. Автоматическая замена отменена.")
        if self.plan.backend and password is None:
            raise ProxyError("Системная установка отменена: пароль sudo не получен.")
        if not self.plan.backend:
            self.check_runtime()
        progress("Получение последнего стабильного релиза…")
        version, asset = self.latest()
        # Same filesystem for atomic standalone replacement; never touch upstream config.
        self.data_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".install-", dir=self.data_dir) as temp:
            package = Path(temp) / self.plan.asset_name
            self._download(asset, package, progress)
            progress("Установка…")
            if self.plan.backend:
                argv = platform_info.install_command_for_package(self.plan.backend, str(package.resolve()))
                try:
                    result = self.runner(["sudo", "-S", "-p", "", "--", *argv], input=password + "\n",
                                         capture_output=True, text=True, timeout=600)
                except (OSError, subprocess.SubprocessError) as exc:
                    raise ProxyError("Не удалось выполнить установку пакета (sudo/пакетный менеджер/таймаут).") from exc
                if result.returncode != 0:
                    raise ProxyError("Пакетный менеджер завершился с ошибкой. Проверьте доступность репозиториев и права sudo.")
                if not self.installed():
                    raise ProxyError("Пакет установлен без ожидаемого GUI /usr/bin/tg-ws-proxy.")
                self._write_receipt(version, self._binary_hash())
            else:
                backup = Path(temp) / "previous-binary"
                had_binary = self.binary.exists()
                if had_binary:
                    shutil.copy2(self.binary, backup)
                package.chmod(0o755)
                os.replace(package, self.binary)
                try:
                    self._write_receipt(version, asset["digest"].split(":")[1].lower())
                except Exception:
                    if had_binary:
                        os.replace(backup, self.binary)
                    else:
                        self.binary.unlink()
                    raise
        return version

    def _write_receipt(self, version, digest):
        _atomic_write(self.receipt, json.dumps({"version": version, "binary": str(self.binary),
                                               "sha256": digest}).encode())

    def autostart_enabled(self):
        try:
            return self.autostart.read_text(encoding="utf-8") == self._desktop()
        except OSError:
            return False

    def _desktop(self):
        clipboard = self.data_dir / "clipboard-bin"
        environment = ""
        if (clipboard / "xclip").is_file():
            environment = _desktop_argument(f"PATH={clipboard}{os.pathsep}{os.defpath}") + " "
        return ("[Desktop Entry]\nType=Application\nName=TG WS Proxy by Flowseal\n"
                f"Exec=/usr/bin/env -- {environment}{desktop_exec(self.binary)}\nTerminal=false\n{OWNER}\n")

    def set_autostart(self, enabled):
        if self.autostart.exists():
            text = self.autostart.read_text(encoding="utf-8")
            if OWNER not in text.splitlines():
                raise ProxyError("Ярлык автозапуска с этим именем принадлежит другой программе; он сохранён.")
        if enabled:
            if not self.installed():
                raise ProxyError("Сначала установите TG WS Proxy.")
            prepare_clipboard_environment(self.data_dir, env=self.environment, runner=self.runner)
            _atomic_write(self.autostart, self._desktop().encode())
        elif self.autostart.exists():
            self.autostart.unlink()

    def launch(self):
        if not self.installed():
            raise ProxyError("GUI TG WS Proxy не найден. Сначала установите его.")
        if self.is_running():
            raise ProxyError("TG WS Proxy уже запущен. Используйте его значок в системном трее.")
        update_autostart = self.autostart_enabled()
        environment = prepare_clipboard_environment(self.data_dir, env=self.environment, runner=self.runner)
        if update_autostart:
            _atomic_write(self.autostart, self._desktop().encode())
        try:
            self.launcher([str(self.binary)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True, env=environment)
        except OSError as exc:
            raise ProxyError("Не удалось запустить GUI TG WS Proxy. Проверьте окружение рабочего стола.") from exc

    def is_running(self):
        for lock in self.flowseal_dir.glob("*.lock"):
            try:
                pid = int(lock.stem)
                identity = self._process_identity(pid) if pid > 1 else None
                if identity and identity[0] == os.getuid() and identity[1] == self.binary.resolve():
                    return True
            except (OSError, ValueError, IndexError, StopIteration):
                continue
        return False

    @staticmethod
    def _wait_for_exit(fd, timeout):
        return bool(select.select([fd], [], [], timeout)[0])

    def _process_identity(self, pid):
        """Read a Linux process fingerprint; no matching by name or command line."""
        directory = self.proc_root / str(pid)
        uid = directory.stat().st_uid
        fields = (directory / "stat").read_text().rsplit(")", 1)[1].split()
        if fields[0] in ("Z", "X"):
            return None
        start_ticks = int(fields[19])  # Field 22, after the parenthesized comm.
        boot_time = next(int(line.split()[1]) for line in (self.proc_root / "stat").read_text().splitlines()
                         if line.startswith("btime "))
        created = boot_time + start_ticks / os.sysconf("SC_CLK_TCK")
        executable = os.readlink(directory / "exe")
        if executable.endswith(" (deleted)"):
            executable = executable[:-10]
        return uid, Path(executable).resolve(), created

    def stop_running(self, timeout=5):
        """Stop verified GUI children from upstream locks; bootloader parents then exit.

        pidfds bind each signal to the verified process even if its PID is reused.
        Stale lock files and unrelated processes are never signalled or removed.
        """
        descriptors = []
        try:
            for lock in self.flowseal_dir.glob("*.lock"):
                try:
                    pid = int(lock.stem)
                except ValueError:
                    continue
                if pid <= 1:
                    continue
                try:
                    identity = self._process_identity(pid)
                except FileNotFoundError:
                    continue
                except (OSError, ValueError, IndexError, StopIteration) as exc:
                    raise ProxyError("Не удалось проверить процесс TG WS Proxy. Закройте его через трэй и повторите удаление.") from exc
                if identity is None:
                    continue
                try:
                    metadata = json.loads(lock.read_text(encoding="utf-8"))
                    created = float(metadata["create_time"])
                    if not math.isfinite(created) or created <= 0:
                        raise ValueError("invalid process timestamp")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    raise ProxyError("Не удалось проверить файл блокировки TG WS Proxy. Закройте GUI вручную и повторите удаление.") from exc
                if abs(identity[2] - created) > 1:
                    continue  # PID was reused; the lock belongs to an exited GUI.
                if identity[0] != os.getuid() or identity[1] != self.binary.resolve():
                    raise ProxyError("Файл блокировки относится к другому процессу. Он сохранён; закройте TG WS Proxy вручную.")
                if self.pidfd_opener is None or self.process_signaler is None:
                    raise ProxyError("Система не поддерживает безопасную остановку процесса. Закройте TG WS Proxy через трэй и повторите удаление.")
                try:
                    fd = self.pidfd_opener(pid, 0)
                except ProcessLookupError:
                    continue
                descriptors.append(fd)
                # The PID might have changed between reading /proc and opening its pidfd.
                try:
                    confirmed = self._process_identity(pid)
                except FileNotFoundError:
                    confirmed = None
                if confirmed != identity:
                    raise ProxyError("Процесс TG WS Proxy изменился во время проверки. Повторите удаление.")
            for fd in descriptors:
                try:
                    self.process_signaler(fd, signal.SIGTERM, None, 0)
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + timeout
            for fd in descriptors:
                if not self.process_waiter(fd, max(0, deadline - time.monotonic())):
                    raise ProxyError("TG WS Proxy не завершился после запроса остановки. Закройте его через трэй и повторите удаление.")
        except OSError as exc:
            raise ProxyError("Не удалось безопасно остановить TG WS Proxy. Закройте его через трэй и повторите удаление.") from exc
        finally:
            for fd in descriptors:
                os.close(fd)

    def _owns_receipt(self):
        try:
            data = json.loads(self.receipt.read_text(encoding="utf-8"))
            return (isinstance(data, dict) and data.get("binary") == str(self.binary)
                    and isinstance(data.get("version"), str)
                    and re.fullmatch(r"[0-9a-fA-F]{64}", data.get("sha256", "")) is not None)
        except (OSError, ValueError, TypeError):
            return False

    def uninstall(self, password=None, progress=lambda text: None):
        """Remove this integration's GUI and autostart, preserving Flowseal settings."""
        if not _INSTALL_LOCK.acquire(blocking=False):
            raise ProxyError("Другая операция TG WS Proxy ещё выполняется. Дождитесь её завершения.")
        try:
            present = self.binary.exists() or self.binary.is_symlink()
            owns_receipt = self._owns_receipt()
            package_present = self._native_package_owns_binary() if self.plan.backend else False
            if self.plan.backend:
                if present and not package_present:
                    raise ProxyError("Ожидаемый путь GUI занят чужим файлом или пакетом. Удаление отменено.")
                if package_present and password is None:
                    raise ProxyError("Удаление отменено: пароль sudo не получен.")
            elif present and (self.binary.is_symlink() or not owns_receipt):
                raise ProxyError("Не подтверждено происхождение standalone. Чужой файл сохранён; удаление отменено.")
            # Check access before changing installation state. Foreign launchers are preserved.
            own_autostart = False
            if self.autostart.exists():
                try:
                    own_autostart = OWNER in self.autostart.read_text(encoding="utf-8").splitlines()
                except (OSError, ValueError) as exc:
                    raise ProxyError("Не удалось проверить ярлык автозапуска. Удаление отменено.") from exc
            progress("Остановка TG WS Proxy…")
            self.stop_running()
            if present or package_present:
                progress("Удаление TG WS Proxy…")
                if self.plan.backend:
                    argv = platform_info.remove_command_for_package(self.plan.backend, "tg-ws-proxy")
                    try:
                        result = self.runner(["sudo", "-S", "-p", "", "--", *argv],
                                             input=password + "\n", capture_output=True, text=True, timeout=600)
                    except (OSError, subprocess.SubprocessError) as exc:
                        raise ProxyError("Не удалось удалить пакет TG WS Proxy (sudo/пакетный менеджер/таймаут).") from exc
                    if result.returncode != 0:
                        raise ProxyError("Пакетный менеджер не удалил TG WS Proxy. Проверьте права sudo и повторите.")
                    if self.binary.exists():
                        raise ProxyError("Пакетный менеджер завершился, но GUI остался на месте. Проверьте установленный пакет.")
                else:
                    self.binary.unlink()
            if own_autostart:
                self.autostart.unlink()
            if owns_receipt:
                self.receipt.unlink(missing_ok=True)
            bridge = self.data_dir / "clipboard-bin/xclip"
            try:
                bridge_owned = (bridge.is_file() and not bridge.is_symlink()
                                and BRIDGE_MARKER in bridge.read_text(encoding="utf-8").splitlines())
            except (OSError, UnicodeError):
                bridge_owned = False
            if bridge_owned:
                bridge.unlink()
                try:
                    bridge.parent.rmdir()
                except OSError:
                    pass  # Other files in this directory do not belong to us.
            progress("TG WS Proxy удалён. Настройки подключения сохранены.")
            return True
        except OSError as exc:
            raise ProxyError("Удаление не завершено: нет доступа к файлам TG WS Proxy. Проверьте права и повторите.") from exc
        finally:
            _INSTALL_LOCK.release()
