"""User-local clipboard bridge for Flowseal's frozen Linux tray application."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile

BRIDGE_MARKER = '# Zapret DPI Manager managed clipboard bridge'


def _external_environment(env):
    """System helpers must not load shared libraries from a PyInstaller bundle."""
    clean = dict(env)
    if "LD_LIBRARY_PATH_ORIG" in clean:
        clean["LD_LIBRARY_PATH"] = clean["LD_LIBRARY_PATH_ORIG"]
    else:
        clean.pop("LD_LIBRARY_PATH", None)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        clean.pop(name, None)
    return clean


def _bridge_source(qdbus):
    # A shell trampoline cleans the dynamic-loader environment before Python
    # starts. The same file is valid Python; no manager imports are needed.
    return '#!/bin/sh\n' + BRIDGE_MARKER + '''
""":"
if [ "${LD_LIBRARY_PATH_ORIG+x}" = x ]; then
    export LD_LIBRARY_PATH="$LD_LIBRARY_PATH_ORIG"
else
    unset LD_LIBRARY_PATH
fi
unset PYTHONHOME PYTHONPATH
exec /usr/bin/env python3 "$0" "$@"
":"""
import os
import subprocess
import sys

QDBUS = ''' + repr(str(qdbus)) + '''


def main():
    # These are precisely the CLIPBOARD calls made by pyperclip's xclip
    # backend. Klipper does not provide X11 PRIMARY selection semantics.
    args = sys.argv[1:]
    if args not in (["-selection", "c"], ["-selection", "c", "-o"]):
        return 2
    env = dict(os.environ)
    if "LD_LIBRARY_PATH_ORIG" in env:
        env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
    else:
        env.pop("LD_LIBRARY_PATH", None)
    for name in ("PYTHONHOME", "PYTHONPATH"):
        env.pop(name, None)
    command = [QDBUS, "org.kde.klipper", "/klipper"]
    try:
        if args[-1] == "-o":
            result = subprocess.run(command + ["getClipboardContents"],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                                    env=env, timeout=5)
            if result.returncode:
                return 1
            text = result.stdout
            # qdbus adds one newline, even if the clipboard itself ends in one.
            sys.stdout.write(text[:-1] if text.endswith("\\n") else text)
        else:
            text = sys.stdin.read()
            result = subprocess.run(command + ["setClipboardContents", text],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, env=env, timeout=5)
            if result.returncode:
                return 1
    except (OSError, ValueError, subprocess.SubprocessError):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def prepare_clipboard_environment(data_dir, *, env=None, which=shutil.which, runner=subprocess.run):
    """Return proxy-only PATH with a KDE bridge when native backends are absent.

    The Klipper service is checked without reading or changing clipboard data.
    Missing helpers, an unavailable session bus, or unwritable user data simply
    leave the environment unchanged; manager-owned connection buttons still work.
    """
    proxy_env = dict(os.environ if env is None else env)
    if not proxy_env.get("DISPLAY") and not proxy_env.get("WAYLAND_DISPLAY"):
        return proxy_env
    search_path = proxy_env.get("PATH", os.defpath)
    if which("xclip", path=search_path) or which("xsel", path=search_path):
        return proxy_env
    if (proxy_env.get("WAYLAND_DISPLAY") and which("wl-copy", path=search_path)
            and which("wl-paste", path=search_path)):
        return proxy_env
    for name in ("qdbus6", "qdbus"):
        qdbus = which(name, path=search_path)
        if not qdbus:
            continue
        try:
            result = runner([str(qdbus), "org.kde.klipper", "/klipper"],
                            capture_output=True, text=True, timeout=5,
                            env=_external_environment(proxy_env))
        except (OSError, subprocess.SubprocessError):
            continue
        if (result.returncode or "getClipboardContents()" not in result.stdout
                or "setClipboardContents(QString" not in result.stdout):
            continue
        bridge_dir = Path(data_dir) / "clipboard-bin"
        temporary = None
        try:
            bridge_dir.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".clipboard-", dir=bridge_dir)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(_bridge_source(Path(qdbus).resolve()))
            os.chmod(temporary, 0o700)
            os.replace(temporary, bridge_dir / "xclip")
            temporary = None
        except OSError:
            return proxy_env
        finally:
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
        proxy_env["PATH"] = str(bridge_dir) + os.pathsep + search_path
        return proxy_env
    return proxy_env
