import os
import tempfile
import tarfile
import shutil
import urllib.request
import urllib.error

class BaseUpdater:
    def __init__(self, version_url, current_version, name="Объект"):
        self.version_url = version_url
        self.current_version = current_version
        self.name = name

    def check_for_updates(self):
        """Проверяет наличие обновлений через простой txt файл"""
        try:
            with urllib.request.urlopen(self.version_url, timeout=10) as response:
                content = response.read().decode('utf-8').strip()

            lines = content.split('\n')
            if len(lines) >= 2:
                latest_version = lines[0].strip()
                download_url = lines[1].strip()

                if self.is_newer_version(latest_version, self.current_version):
                    return latest_version, {
                        'download_url': download_url,
                        'description': f'Доступна новая версия {self.name}: {latest_version}'
                    }

            return None, None

        except Exception as e:
            print(f"Error checking updates for {self.name}: {e}")
            return None, None

    def is_newer_version(self, latest, current):
        """Простое сравнение версий"""
        latest_clean = latest.replace('v', '')
        current_clean = current.replace('v', '')
        return latest_clean > current_clean
