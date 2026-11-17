"""Bounded HTTP probes and evidence-based interpretation, independent of Tk."""
from dataclasses import dataclass
import os
import subprocess
import tempfile
import time
from typing import Optional


@dataclass(frozen=True)
class Probe:
    name: str
    url: str
    method: str = "HEAD"
    expected: tuple = (200, 204)


@dataclass(frozen=True)
class ProbeResult:
    probe: Probe
    outcome: str  # success, failed, incomplete, cancelled
    diagnosis: str
    status: Optional[int] = None
    final_url: str = ""
    elapsed_ms: float = 0
    curl_code: Optional[int] = None

    @property
    def success(self):
        return self.outcome == "success"


YOUTUBE_PROBES = (
    Probe("Сайт YouTube", "https://www.youtube.com/", "HEAD", (200,)),
    Probe("YouTube generate_204", "https://www.youtube.com/generate_204", "GET", (204,)),
    Probe("Изображения YouTube", "https://i.ytimg.com/vi/dQw4w9WgXcQ/mqdefault.jpg", "GET", (200,)),
)
INTERNET_PROBES = (
    Probe("Google", "https://www.google.com/", expected=(200,)),
    Probe("Cloudflare", "https://1.1.1.1/", expected=(200,)),
    Probe("Yandex", "https://ya.ru/", expected=(200,)),
)
DISCORD_PROBES = (
    Probe("Discord Website", "https://discord.com/", "HEAD", (200,)),
    Probe("Discord API", "https://discord.com/api/v9/gateway", "GET", (200,)),
)


def interpret_results(results, expected_count, cancelled=False):
    """Availability concerns only these probes, never playback or a DPI cause."""
    if (cancelled or not results or len(results) != expected_count
            or any(r.outcome in ("incomplete", "cancelled") for r in results)):
        return "incomplete"
    successes = sum(r.success for r in results)
    if successes == len(results):
        return "available"
    return "partial" if successes else "unavailable"


def connection_summary(internet=(), youtube=(), discord=()):
    """Summarize HTTP evidence, retaining complete categories after interruption.

    A received HTTP response proves connectivity, even if access was denied.
    ICMP results deliberately do not participate in this HTTP summary.
    """
    internet, youtube, discord = tuple(internet), tuple(youtube), tuple(discord)
    state = interpret_results(internet, len(INTERNET_PROBES))
    evidence = any(r.success or (r.status is not None and 100 <= r.status <= 599)
                   for r in internet + youtube + discord)
    if state == "available":
        network = "связь есть"
    elif evidence:
        network = "частичная доступность"
    elif internet:
        network = "подтвердить не удалось"
    else:
        network = "не проверен"

    def service(results, count):
        state = interpret_results(results, count)
        if state == "incomplete":
            return "частично доступен (не завершено)" if any(r.success for r in results) else "не проверен (не завершено)"
        return {"available": "доступен", "partial": "частично доступен",
                "unavailable": "недоступен"}[state]

    return (f"Итог: Интернет: {network}; YouTube: {service(youtube, len(YOUTUBE_PROBES))}; "
            f"Discord: {service(discord, len(DISCORD_PROBES))}.")


def http_diagnosis(status):
    if status == 403:
        return "HTTP 403: сервер запретил запрос"
    if status == 404:
        return "HTTP 404: ресурс не найден"
    if status == 429:
        return "HTTP 429: ограничение частоты запросов"
    if status >= 500:
        return f"HTTP {status}: ошибка сервера"
    return f"HTTP {status}"


def parse_result(probe, returncode, output, elapsed_ms=0):
    """Parse curl write-out only; response headers (including CONNECT) are ignored."""
    status, final_url = None, ""
    lines = output.strip().splitlines()
    if len(lines) == 2 and lines[0].isdigit() and len(lines[0]) == 3:
        status = int(lines[0]) or None
        final_url = lines[1]
    diagnoses = {
        5: "DNS: не удалось разрешить имя прокси",
        6: "DNS: не удалось разрешить имя узла",
        7: "TCP: не удалось установить соединение",
        28: "Таймаут запроса или соединения",
        35: "TLS: ошибка согласования защищённого соединения",
        51: "TLS: сертификат не прошёл проверку",
        60: "TLS: сертификат не прошёл проверку",
        58: "TLS: ошибка локального сертификата",
        77: "TLS: недоступно хранилище сертификатов",
        47: "Превышено число перенаправлений",
        63: "Превышен допустимый объём ответа",
    }
    if returncode:
        incomplete = returncode in (2, 3, 4, 23, 26, 27, 48)
        return ProbeResult(probe, "incomplete" if incomplete else "failed",
                           diagnoses.get(returncode, f"Ошибка curl ({returncode})"),
                           status, final_url, elapsed_ms, returncode)
    if status is None or not 100 <= status <= 599 or not final_url.startswith(("http://", "https://")):
        return ProbeResult(probe, "incomplete", "Некорректные метаданные ответа curl", elapsed_ms=elapsed_ms, curl_code=returncode)
    success = status in probe.expected
    return ProbeResult(probe, "success" if success else "failed", http_diagnosis(status),
                       status, final_url, elapsed_ms, returncode)


def run_probe(probe, cancel=None, timeout=10, max_bytes=256 * 1024):
    """GET really downloads a bounded body; TLS validation stays enabled.

    Files avoid unbounded pipe buffers, and the poll loop enforces a size cap
    even when an older curl or chunked response cannot enforce max-filesize.
    """
    if probe.method not in ("HEAD", "GET"):
        raise ValueError("Only HEAD and GET probes are supported")
    started = time.monotonic()
    if cancel is not None and cancel.is_set():
        return ProbeResult(probe, "cancelled", "Проверка отменена")
    with tempfile.TemporaryDirectory(prefix="connection-check-") as directory:
        body = os.path.join(directory, "body")
        command = ["curl", "--disable", "--silent", "--show-error", "--location",
                   "--max-redirs", "5", "--connect-timeout", "5", "--max-time", str(timeout),
                   "--proto", "=http,https",
                   "--proto-redir", "=http,https", "--output", body,
                   "--write-out", "%{http_code}\\n%{url_effective}\\n",
                   "--user-agent", "Mozilla/5.0"]
        if probe.method == "HEAD":
            command.append("--head")
        else:
            command.extend(["--max-filesize", str(max_bytes)])
        command.extend(["--url", probe.url])
        try:
            # Metadata and error output are capped too (e.g. a malicious redirect URL).
            with tempfile.TemporaryFile() as metadata, tempfile.TemporaryFile() as errors:
                process = subprocess.Popen(command, stdout=metadata, stderr=errors)
                reason = None
                while process.poll() is None:
                    if cancel is not None and cancel.is_set():
                        reason = ("cancelled", "Проверка отменена")
                    elif time.monotonic() - started > timeout + 1:
                        reason = ("failed", "Таймаут выполнения curl")
                    elif ((os.path.exists(body) and os.path.getsize(body) > max_bytes)
                          or os.fstat(metadata.fileno()).st_size > 16384
                          or os.fstat(errors.fileno()).st_size > 16384):
                        reason = ("failed", "Превышен допустимый объём ответа")
                    if reason:
                        process.kill()
                        break
                    time.sleep(0.02)
                process.wait()
                if not reason and ((os.path.exists(body) and os.path.getsize(body) > max_bytes)
                                   or os.fstat(metadata.fileno()).st_size > 16384
                                   or os.fstat(errors.fileno()).st_size > 16384):
                    reason = ("failed", "Превышен допустимый объём ответа")
                elapsed = (time.monotonic() - started) * 1000
                if reason:
                    return ProbeResult(probe, *reason, elapsed_ms=elapsed)
                if cancel is not None and cancel.is_set():
                    return ProbeResult(probe, "cancelled", "Проверка отменена", elapsed_ms=elapsed)
                metadata.seek(0)
                return parse_result(probe, process.returncode, metadata.read(16384).decode("utf-8", "replace"), elapsed)
        except FileNotFoundError:
            return ProbeResult(probe, "incomplete", "curl не установлен")
        except OSError as error:
            return ProbeResult(probe, "incomplete", f"Не удалось запустить curl: {error}")
