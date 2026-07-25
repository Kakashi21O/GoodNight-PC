import time
import pytest
from unittest.mock import MagicMock
from app.timer_manager import TimerManager, TimerState, MAX_DURATION_SECONDS


@pytest.fixture
def timer():
    t = TimerManager()
    root = MagicMock()
    root.after.return_value = "after_id"
    root.after_cancel = MagicMock()
    t.set_root(root)
    return t


class TestTimerState:
    def test_initial_state(self, timer):
        assert timer.state == TimerState.IDLE

    def test_session_id_starts_at_zero(self, timer):
        assert timer.session_id == 0

    def test_get_remaining_idle(self, timer):
        assert timer.get_remaining() == 0.0


class TestStart:
    def test_start_sets_running(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        assert timer.state == TimerState.RUNNING

    def test_start_increments_session(self, timer):
        cb = MagicMock()
        old = timer.session_id
        timer.start(60, on_expire=cb)
        assert timer.session_id == old + 1

    def test_start_negative_duration_rejected(self, timer):
        cb = MagicMock()
        result = timer.start(-1, on_expire=cb)
        assert result is False
        assert timer.state == TimerState.IDLE

    def test_start_zero_duration_rejected(self, timer):
        cb = MagicMock()
        result = timer.start(0, on_expire=cb)
        assert result is False

    def test_start_sets_target_time(self, timer):
        cb = MagicMock()
        before = time.time()
        timer.start(100, on_expire=cb)
        after = time.time()
        assert timer._target_time is not None
        assert before + 99 <= timer._target_time <= after + 101


class TestPauseResume:
    def test_pause_from_running(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        assert timer.pause() is True
        assert timer.state == TimerState.PAUSED

    def test_pause_stores_remaining(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        timer.pause()
        remaining = timer.get_remaining()
        assert 58 <= remaining <= 62

    def test_pause_from_idle_fails(self, timer):
        assert timer.pause() is False

    def test_resume_from_paused(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        timer.pause()
        assert timer.resume() is True
        assert timer.state == TimerState.RUNNING

    def test_resume_from_idle_fails(self, timer):
        assert timer.resume() is False

    def test_pause_resume_maintains_remaining(self, timer):
        cb = MagicMock()
        timer.start(300, on_expire=cb)
        timer.pause()
        remaining_before = timer.get_remaining()
        timer.resume()
        remaining_after = timer.get_remaining()
        assert abs(remaining_before - remaining_after) < 1


class TestCancel:
    def test_cancel_sets_idle(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        assert timer.cancel() is True
        assert timer.state == TimerState.IDLE

    def test_cancel_increments_session(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        old = timer.session_id
        timer.cancel()
        assert timer.session_id == old + 1

    def test_cancel_idle_fails(self, timer):
        assert timer.cancel() is False

    def test_cancel_clears_target(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        timer.cancel()
        assert timer._target_time is None


class TestAddTime:
    def test_add_time_extends_target(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        old_target = timer._target_time
        timer.add_time(120)
        assert timer._target_time - old_target == pytest.approx(120, abs=1)

    def test_add_time_when_paused_fails(self, timer):
        cb = MagicMock()
        timer.start(60, on_expire=cb)
        timer.pause()
        assert timer.add_time(60) is False


class TestValidateDuration:
    def test_valid_duration(self, timer):
        total, errors = timer.validate_duration("1", "30", "0")
        assert total == 5400
        assert errors == []

    def test_empty_returns_error(self, timer):
        total, errors = timer.validate_duration("", "", "")
        assert errors

    def test_invalid_hours(self, timer):
        total, errors = timer.validate_duration("abc", "0", "0")
        assert errors

    def test_minutes_out_of_range(self, timer):
        total, errors = timer.validate_duration("0", "60", "0")
        assert errors

    def test_seconds_out_of_range(self, timer):
        total, errors = timer.validate_duration("0", "0", "60")
        assert errors

    def test_negative_values(self, timer):
        total, errors = timer.validate_duration("-1", "0", "0")
        assert errors

    def test_hours_too_large(self, timer):
        total, errors = timer.validate_duration("24", "0", "0")
        assert errors

    def test_exceeds_max_duration(self, timer):
        days_in_secs = 8 * 24 * 3600
        h = days_in_secs // 3600
        total, errors = timer.validate_duration(str(h), "0", "0")
        assert errors
