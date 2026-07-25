import json
import os
import tempfile
import pytest
from app.settings_manager import SettingsManager, DEFAULTS, SETTINGS_VERSION


@pytest.fixture
def tmp_settings(tmp_path):
    path = str(tmp_path / "test_settings.json")
    return SettingsManager(config_path=path)


@pytest.fixture
def empty_settings(tmp_path):
    path = str(tmp_path / "empty_settings.json")
    return SettingsManager(config_path=path)


class TestDefaults:
    def test_loads_defaults_when_no_file(self, empty_settings):
        assert empty_settings.get("warning_duration") == 20
        assert empty_settings.get("alert_sound_enabled") is True
        assert empty_settings.get("theme") == "dark"
        assert empty_settings.get("selected_action") == "shutdown"
        assert empty_settings.get("custom_presets") == []
        assert empty_settings.get("postpone_minutes") == [5, 10, 15, 30, 60]

    def test_schema_version(self, empty_settings):
        assert empty_settings.get("schema_version") == SETTINGS_VERSION


class TestGetSet:
    def test_set_and_get(self, tmp_settings):
        tmp_settings.set("warning_duration", 30)
        assert tmp_settings.get("warning_duration") == 30

    def test_get_nonexistent_returns_none(self, tmp_settings):
        assert tmp_settings.get("nonexistent_key") is None

    def test_get_with_default(self, tmp_settings):
        assert tmp_settings.get("nonexistent", "fallback") == "fallback"

    def test_set_persists(self, tmp_path):
        path = str(tmp_path / "persist.json")
        s = SettingsManager(config_path=path)
        s.set("warning_duration", 45)
        s2 = SettingsManager(config_path=path)
        assert s2.get("warning_duration") == 45

    def test_get_all_returns_copy(self, tmp_settings):
        all_settings = tmp_settings.get_all()
        all_settings["warning_duration"] = 999
        assert tmp_settings.get("warning_duration") == 20


class TestCorruptedFile:
    def test_corrupted_file_restores_defaults(self, tmp_path):
        path = str(tmp_path / "corrupt.json")
        with open(path, "w") as f:
            f.write("{invalid json!!")
        s = SettingsManager(config_path=path)
        assert s.get("warning_duration") == 20

    def test_non_dict_file_restores_defaults(self, tmp_path):
        path = str(tmp_path / "list.json")
        with open(path, "w") as f:
            json.dump([1, 2, 3], f)
        s = SettingsManager(config_path=path)
        assert s.get("warning_duration") == 20

    def test_corrupted_file_backed_up(self, tmp_path):
        path = str(tmp_path / "backed.json")
        with open(path, "w") as f:
            f.write("{bad}")
        SettingsManager(config_path=path)
        assert os.path.exists(path + ".corrupted.bak")


class TestReset:
    def test_reset_restores_defaults(self, tmp_settings):
        tmp_settings.set("warning_duration", 999)
        tmp_settings.reset()
        assert tmp_settings.get("warning_duration") == 20
        assert tmp_settings.get("theme") == "dark"


class TestMigration:
    def test_v1_migration_adds_missing_keys(self, tmp_path):
        path = str(tmp_path / "v1.json")
        with open(path, "w") as f:
            json.dump({"schema_version": 1, "warning_duration": 25}, f)
        s = SettingsManager(config_path=path)
        assert s.get("custom_presets") == []
        assert s.get("postpone_minutes") == [5, 10, 15, 30, 60]
        assert s.get("theme") == "dark"

    def test_v1_migration_upgrades_version(self, tmp_path):
        path = str(tmp_path / "v1v2.json")
        with open(path, "w") as f:
            json.dump({"schema_version": 1}, f)
        s = SettingsManager(config_path=path)
        assert s.get("schema_version") == SETTINGS_VERSION


class TestAtomicWrites:
    def test_no_temp_files_left_on_save(self, tmp_path):
        path = str(tmp_path / "atomic.json")
        s = SettingsManager(config_path=path)
        s.set("test_key", "test_value")
        files = [f for f in os.listdir(tmp_path) if f.endswith(".tmp")]
        assert files == []
