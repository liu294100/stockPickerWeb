from core.config_manager import ConfigManager


class SettingsService:
    def __init__(self):
        self.config_manager = ConfigManager()

    def get_config(self):
        return self.config_manager.config

    def update_settings(self, data: dict):
        for key, value in data.items():
            if key == "settings.data_sources" and isinstance(value, str):
                value = [item.strip() for item in value.split(",") if item.strip()]
            self.config_manager.set(key, value)
