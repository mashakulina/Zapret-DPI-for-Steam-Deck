#!/usr/bin/env python3
import sys
import os
import tkinter as tk
from ui.windows.main_window import MainWindow

# Добавляем текущую директорию в путь для импортов
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

def main():
    """Точка входа в программу"""
    try:
        app = MainWindow()
        app.run()
    except ImportError as e:
        print(f"Ошибка импорта: {e}")
        print("Убедитесь, что все модули установлены правильно.")
        sys.exit(1)
    except Exception as e:
        print(f"Неизвестная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
