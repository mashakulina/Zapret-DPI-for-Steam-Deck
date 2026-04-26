"""Настройка записи ошибок приложения в /tmp/zapterdpimanager.log."""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

LOG_FILE_PATH = Path("/tmp/zapterdpimanager.log")
_LOGGER_NAME = "zapret_dpi_manager.error"

_setup_done = False


def get_error_logger() -> logging.Logger:
    return logging.getLogger(_LOGGER_NAME)


def setup_error_logging() -> None:
    """Пишет только ERROR+ в файл; перехватывает необработанные исключения и Tk callback."""
    global _setup_done
    if _setup_done:
        return
    _setup_done = True

    log = get_error_logger()
    log.setLevel(logging.ERROR)
    log.propagate = False

    if not log.handlers:
        handler = logging.FileHandler(LOG_FILE_PATH, encoding="utf-8")
        handler.setLevel(logging.ERROR)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        log.addHandler(handler)

    _orig_sys_excepthook = sys.excepthook

    def _excepthook(exc_type, exc_value, exc_traceback):
        if exc_type is not None and issubclass(exc_type, KeyboardInterrupt):
            _orig_sys_excepthook(exc_type, exc_value, exc_traceback)
            return
        log.error("Необработанное исключение", exc_info=(exc_type, exc_value, exc_traceback))
        _orig_sys_excepthook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _excepthook

    if hasattr(threading, "excepthook"):
        _orig_threading_excepthook = threading.excepthook

        def _threading_excepthook(args):
            log.error(
                "Необработанное исключение в потоке %r",
                getattr(args.thread, "name", "?"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
            _orig_threading_excepthook(args)

        threading.excepthook = _threading_excepthook

    import tkinter as tk

    _orig_tk_report = tk.Tk.report_callback_exception

    def _report_callback_exception(self, exc, val, tb):
        log.error("Исключение в колбэке Tkinter", exc_info=(exc, val, tb))
        return _orig_tk_report(self, exc, val, tb)

    tk.Tk.report_callback_exception = _report_callback_exception  # type: ignore[method-assign]
