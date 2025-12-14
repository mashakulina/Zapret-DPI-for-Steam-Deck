import subprocess
import os
from tkinter import messagebox

class SudoChecker:
    @staticmethod
    def is_sudo_password_valid(password):
        """
        Проверяет валидность пароля sudo
        Возвращает True если пароль правильный, False если нет
        """
        try:
            # Создаем команду для проверки пароля
            cmd = f"echo '{password}' | sudo -S true"

            # Запускаем процесс
            process = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )

            # Если команда выполнена успешно (код возврата 0) - пароль верный
            return process.returncode == 0

        except subprocess.TimeoutExpired:
            print("Таймаут проверки пароля")
            return False
        except Exception as e:
            print(f"Ошибка проверки пароля: {e}")
            return False

    @staticmethod
    def get_cached_password():
        """Получает кэшированный пароль (если есть)"""
        try:
            cache_file = os.path.expanduser("~/.zapret_sudo_cache")
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return f.read().strip()
        except:
            pass
        return None

    @staticmethod
    def cache_password(password):
        """Кэширует пароль (только на время сессии)"""
        try:
            cache_file = os.path.expanduser("~/.zapret_sudo_cache")
            with open(cache_file, 'w') as f:
                f.write(password)
        except:
            pass

    @staticmethod
    def clear_password_cache():
        """Очищает кэш пароля"""
        try:
            cache_file = os.path.expanduser("~/.zapret_sudo_cache")
            if os.path.exists(cache_file):
                os.remove(cache_file)
        except:
            pass
