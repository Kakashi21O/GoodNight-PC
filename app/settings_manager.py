import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

DEFAULTS: Dict[str, Any] = {
    "warning_duration": 20,
    "alert_sound_enabled": True,
    "always_on_top_warning": True,
    "confirm_before_shutdown": True,
}


class SettingsManager:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = str(Path.home() / ".goodnight_pc_settings.json")
        self._config_path = config_path
        self._settings = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Settings file is not a valid JSON object")
                for key in DEFAULTS:
                    if key in data:
                        self._settings[key] = data[key]
                logger.info("Settings loaded from %s", self._config_path)
            else:
                logger.info("No settings file found, using defaults")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupted settings file, restoring defaults: %s", e)
            self._settings = dict(DEFAULTS)
            self.save()
        except Exception as e:
            logger.error("Failed to load settings: %s", e)
            self._settings = dict(DEFAULTS)

    def save(self) -> None:
        try:
            with open(self._config_path, "w") as f:
                json.dump(self._settings, f, indent=2)
            logger.info("Settings saved to %s", self._config_path)
        except Exception as e:
            logger.error("Failed to save settings: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._settings[key] = value
        self.save()

    def get_all(self) -> Dict[str, Any]:
        return dict(self._settings)

    def reset(self) -> None:
        self._settings = dict(DEFAULTS)
        self.save()
        logger.info("Settings reset to defaults")
