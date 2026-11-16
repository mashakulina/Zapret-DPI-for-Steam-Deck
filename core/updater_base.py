import re
import urllib.error
import urllib.request
from itertools import zip_longest

from core.app_logging import get_error_logger


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
            get_error_logger().error(
                "Проверка обновлений (%s): %s",
                self.name,
                e,
                exc_info=True,
            )
            return None, None

    def is_newer_version(self, latest, current):
        """Сравнивает числовые компоненты версий, включая четырёхчастные."""
        def components(version):
            match = re.fullmatch(r"[vV]?([0-9]+(?:\.[0-9]+)*)", version.strip())
            if not match:
                raise ValueError(f"Неверная версия: {version!r}")
            return tuple(int(part) for part in match.group(1).split('.'))

        for latest_part, current_part in zip_longest(
            components(latest), components(current), fillvalue=0
        ):
            if latest_part != current_part:
                return latest_part > current_part
        return False
