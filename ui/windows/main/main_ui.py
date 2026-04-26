"""Сборка главного UI (композиция layout + settings)."""
from ui.windows.main.main_ui_layout import MainUILayoutMixin
from ui.windows.main.main_ui_settings import MainUISettingsMixin


class MainUIMixin(MainUILayoutMixin, MainUISettingsMixin):
    """Пункты меню и корневой layout."""
