import subprocess
import os
from core.sudo_checker import SudoChecker

class ServiceManager:
    def __init__(self, sudo_password=None):
        self.sudo_password = sudo_password

    def set_sudo_password(self, password):
        """Устанавливает пароль sudo"""
        self.sudo_password = password

    def _run_sudo_command(self, command):
        """Выполняет команду с sudo"""
        if not self.sudo_password:
            return False, "Пароль sudo не установлен"

        try:
            # Формируем команду с передачей пароля
            cmd = f"echo '{self.sudo_password}' | sudo -S {command}"

            process = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            if process.returncode == 0:
                return True, process.stdout.strip()
            else:
                return False, process.stderr.strip()

        except subprocess.TimeoutExpired:
            return False, "Таймаут выполнения команды"
        except Exception as e:
            return False, str(e)

    def start_service(self):
        """Запускает службу zapret"""
        return self._run_sudo_command("systemctl start zapret")

    def stop_service(self):
        """Останавливает службу zapret"""
        return self._run_sudo_command("systemctl stop zapret")

    def restart_service(self):
        """Перезапускает службу zapret"""
        return self._run_sudo_command("systemctl restart zapret")

    def enable_autostart(self):
        """Включает автозапуск службы zapret"""
        return self._run_sudo_command("systemctl enable zapret")

    def disable_autostart(self):
        """Отключает автозапуск службы zapret"""
        return self._run_sudo_command("systemctl disable zapret")

    def get_service_status(self):
        """Получает статус службы zapret"""
        success, output = self._run_sudo_command("systemctl is-active zapret")

        if success:
            status = output.strip()
            if status in ["active", "inactive", "failed", "activating"]:
                return status
            else:
                return "unknown"
        else:
            # Пробуем получить детальный статус
            success, output = self._run_sudo_command("systemctl status zapret --no-pager | grep -E 'Active:|Loaded:'")
            if success:
                if "active (running)" in output.lower():
                    return "active"
                elif "inactive (dead)" in output.lower():
                    return "inactive"
                elif "failed" in output.lower():
                    return "failed"
            return "unknown"

    def get_autostart_status(self):
        """Проверяет, включен ли автозапуск без sudo"""
        try:
            # Пробуем получить статус без пароля
            process = subprocess.run(
                ["systemctl", "is-enabled", "zapret"],
                capture_output=True,
                text=True,
                timeout=5
            )

            output = process.stdout.strip().lower()

            if output == "enabled":
                return True
            elif output == "disabled":
                return False
            else:
                # Пробуем другой способ
                process = subprocess.run(
                    ["systemctl", "list-unit-files", "zapret.service"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if "enabled" in process.stdout.lower():
                    return True
                return False

        except subprocess.TimeoutExpired:
            print("Таймаут проверки автозапуска")
            return False
        except Exception as e:
            print(f"Ошибка проверки автозапуска: {e}")
            return False

    def check_service_exists(self):
        """Проверяет, существует ли служба zapret"""
        success, _ = self._run_sudo_command("systemctl list-unit-files | grep -w zapret.service")
        return success

    def get_service_status(self):
        """Получает статус службы zapret без sudo"""
        try:
            # Пробуем получить статус без пароля (для чтения обычно не нужен sudo)
            process = subprocess.run(
                ["systemctl", "is-active", "zapret"],
                capture_output=True,
                text=True,
                timeout=5
            )

            status = process.stdout.strip()

            if status in ["active", "inactive", "failed", "activating", "deactivating"]:
                return status
            elif process.returncode == 0:
                return status
            else:
                # Если команда вернула ошибку, пробуем получить детальный статус
                process = subprocess.run(
                    ["systemctl", "status", "zapret", "--no-pager"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                output = process.stdout.lower()
                if "active (running)" in output:
                    return "active"
                elif "inactive (dead)" in output:
                    return "inactive"
                elif "failed" in output:
                    return "failed"
                else:
                    return "unknown"

        except subprocess.TimeoutExpired:
            print("Таймаут проверки статуса службы")
            return "unknown"
        except Exception as e:
            print(f"Ошибка проверки статуса службы: {e}")
            return "unknown"

    def get_autostart_status(self):
        """Проверяет, включен ли автозапуск"""
        success, output = self._run_sudo_command("systemctl is-enabled zapret")

        if success:
            return output.strip() == "enabled"
        elif "disabled" in output.lower():
            return False
        else:
            # Если команда вернула ошибку, проверяем через list-unit-files
            success, output = self._run_sudo_command("systemctl list-unit-files zapret.service | grep zapret")
            if success:
                return "enabled" in output
            return False
