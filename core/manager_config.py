GITHUB_BASE_URL = "https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/mashakulina/Zapret-DPI-for-Steam-Deck/main"

RELEASES_URL = "https://github.com/mashakulina/Zapret-DPI-for-Steam-Deck/releases/latest/download/"


# Конфигурация менеджера
MANAGER_CONFIG = {
    # URL файла с версией менеджера
    "version_url": f"{GITHUB_RAW_URL}/manager_version.txt",
    # Текущая версия менеджера
    "current_version": "2.7.6"
}

# Конфигурация zapret службы
ZAPRET_CONFIG = {
    # URL файла с версией zapret
    "version_url": f"{GITHUB_RAW_URL}/zapret_version.txt",
    # Текущая версия zapret
    "current_version": "2.6.2"
}
