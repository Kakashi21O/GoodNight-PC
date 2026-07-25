import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SETTINGS_VERSION = 2

DEFAULTS: Dict[str, Any] = {
    "schema_version": SETTINGS_VERSION,
    "warning_duration": 20,
    "alert_sound_enabled": True,
    "always_on_top_warning": True,
    "confirm_before_shutdown": True,
    "theme": "dark",
    "selected_action": "shutdown",
    "custom_presets": [],
    "postpone_minutes": [5, 10, 15, 30, 60],
    "history": [],
    "window_geometry": None,
}


class SettingsManager:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = str(Path.home() / ".goodnight_pc_settings.json")
        self._config_path = config_path
        self._settings = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    raise ValueError("Settings file is not a valid JSON object")
                self._migrate(data)
                for key in DEFAULTS:
                    if key in data:
                        self._settings[key] = data[key]
                self._settings["schema_version"] = SETTINGS_VERSION
                logger.info("Settings loaded from %s", self._config_path)
            else:
                logger.info("No settings file found, using defaults")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupted settings file, restoring defaults: %s", e)
            self._backup_corrupted()
            self._settings = dict(DEFAULTS)
            self.save()
        except Exception as e:
            logger.error("Failed to load settings: %s", e)
            self._settings = dict(DEFAULTS)

    def _migrate(self, data: dict) -> None:
        old_version = data.get("schema_version", 1)
        if old_version < 2:
            logger.info("Migrating settings from schema v%d to v%d", old_version, SETTINGS_VERSION)
            if "custom_presets" not in data:
                data["custom_presets"] = []
            if "postpone_minutes" not in data:
                data["postpone_minutes"] = [5, 10, 15, 30, 60]
            if "history" not in data:
                data["history"] = []
            if "theme" not in data:
                data["theme"] = "dark"
            if "selected_action" not in data:
                data["selected_action"] = "shutdown"
            if "window_geometry" not in data:
                data["window_geometry"] = None

    def _backup_corrupted(self) -> None:
        try:
            if os.path.exists(self._config_path):
                backup = self._config_path + ".corrupted.bak"
                os.replace(self._config_path, backup)
                logger.info("Corrupted settings backed up to %s", backup)
        except Exception:
            logger.warning("Could not backup corrupted settings file")

    def save(self) -> None:
        try:
            dir_path = os.path.dirname(self._config_path) or "."
            fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(self._settings, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, self._config_path)
                logger.info("Settings saved to %s", self._config_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
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
