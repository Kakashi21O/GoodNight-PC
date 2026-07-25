import json
import os
import time
import pytest
from app.recovery import save_active_state, load_active_state, clear_active_state


@pytest.fixture(autouse=True)
def cleanup_state():
    yield
    try:
        os.unlink(os.path.expanduser(".goodnight_pc_active_state.json"))
    except OSError:
        pass


class TestSaveAndLoad:
    def test_save_and_load(self):
        target = time.time() + 3600
        save_active_state("shutdown", target, 3600)
        state = load_active_state()
        assert state is not None
        assert state["action"] == "shutdown"
        assert state["initial_duration"] == 3600
        assert state["remaining"] > 3500

    def test_load_returns_none_when_no_file(self):
        clear_active_state()
        assert load_active_state() is None

    def test_load_expired_state(self):
        target = time.time() - 100
        save_active_state("shutdown", target, 3600)
        state = load_active_state()
        assert state is None

    def test_load_corrupted_file(self):
        path = os.path.expanduser(".goodnight_pc_active_state.json")
        with open(path, "w") as f:
            f.write("{bad json!!")
        state = load_active_state()
        assert state is None


class TestClear:
    def test_clear_removes_file(self):
        save_active_state("shutdown", time.time() + 3600, 3600)
        clear_active_state()
        assert load_active_state() is None

    def test_clear_noop_when_no_file(self):
        clear_active_state()
        assert load_active_state() is None


class TestAtomicWrite:
    def test_no_temp_files_left(self):
        save_active_state("shutdown", time.time() + 3600, 3600)
        state_dir = os.path.expanduser("~")
        tmp_files = [f for f in os.listdir(state_dir)
                     if f.startswith(".goodnight_pc_active_state") and f.endswith(".tmp")]
        assert tmp_files == []
