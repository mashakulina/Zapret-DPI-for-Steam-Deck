"""Описание релиза с GitHub API для окна уведомления об обновлении."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from core.app_logging import get_error_logger
from core.manager_config import GITHUB_API_REPO

_USER_AGENT = "Zapret-DPI-Manager"
_MAX_NOTES_LEN = 3000

# Символы, из‑за которых Tkinter часто рисует «▯» (в т.ч. \r в конце строк CRLF).
_INVISIBLE_OR_CONTROL = (
    "\ufeff",  # BOM
    "\u200b", "\u200c", "\u200d", "\u2060",  # zero-width
    "\u00ad",  # soft hyphen
    "\u2028", "\u2029",  # line/paragraph separator
)


def sanitize_text_for_display(text: str) -> str:
    """Нормализует переносы и убирает символы, которые ломают отображение в Tk."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for ch in _INVISIBLE_OR_CONTROL:
        text = text.replace(ch, "")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def release_body_to_plain_text(body: str) -> str:
    """Упрощает Markdown из GitHub Release до текста для Tkinter."""
    text = sanitize_text_for_display(body or "")
    if not text:
        return ""

    text = re.sub(r"```[^\n]*\n(.*?)```", r"\1", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return sanitize_text_for_display(text)


def _tag_variants(version: str) -> list[str]:
    raw = version.strip()
    core = raw.lstrip("v")
    return list(dict.fromkeys([raw, f"v{core}", core]))


def _github_api_get(url: str, *, timeout: float = 10) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"GitHub API ({url}): HTTP {e.code}")
            get_error_logger().error(
                "GitHub API (%s): HTTP %s",
                url,
                e.code,
                exc_info=True,
            )
        return None
    except Exception as e:
        print(f"GitHub API ({url}): {e}")
        get_error_logger().error("GitHub API (%s): %s", url, e, exc_info=True)
        return None


def _notes_from_release_data(data: dict | None) -> str | None:
    if not data:
        return None
    plain = release_body_to_plain_text(data.get("body") or "")
    if not plain:
        return None
    if len(plain) > _MAX_NOTES_LEN:
        plain = plain[: _MAX_NOTES_LEN - 1].rstrip() + "…"
    return plain


def fetch_release_notes_for_version(
    version: str | None = None,
    *,
    timeout: float = 10,
) -> str | None:
    """
    Возвращает plain-text описание релиза.

    Сначала ищет release по тегу версии из version.txt, затем — latest.
    """
    base = f"https://api.github.com/repos/{GITHUB_API_REPO}/releases"

    if version:
        for tag in _tag_variants(version):
            encoded = urllib.parse.quote(tag, safe="")
            data = _github_api_get(f"{base}/tags/{encoded}", timeout=timeout)
            notes = _notes_from_release_data(data)
            if notes:
                return notes

    data = _github_api_get(f"{base}/latest", timeout=timeout)
    notes = _notes_from_release_data(data)
    if notes and version and data:
        tag_name = (data.get("tag_name") or "").strip().lstrip("v")
        ver = version.strip().lstrip("v")
        if tag_name and ver and tag_name != ver:
            print(
                f"Описание релиза взято с тега {data.get('tag_name')!r} "
                f"(в манифесте версия {version!r})"
            )
    return notes
