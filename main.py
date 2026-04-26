#!/usr/bin/env python3
import os
import sys

# Добавляем текущую директорию в путь для импортов до импортов пакетов проекта
_current_dir = os.path.dirname(os.path.abspath(__file__))
if _current_dir not in sys.path:
    sys.path.insert(0, _current_dir)

from core.app_logging import get_error_logger, setup_error_logging

setup_error_logging()

from ui.windows.main_window import MainWindow

def main():
    """Точка входа в программу"""
    err_log = get_error_logger()
    try:
        app = MainWindow()
        app.run()
    except ImportError as e:
        err_log.exception("Ошибка импорта")
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что все модули установлены правильно.")
        sys.exit(1)
    except Exception as e:
        err_log.exception("Неизвестная ошибка при запуске")
        print(f"Неизвестная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
