import pytest
from app.power_manager import PowerManager, PowerAction, ACTION_LABELS, ACTION_VERBS


@pytest.fixture
def mock_pm():
    return PowerManager(mock_mode=True)


@pytest.fixture
def real_pm():
    return PowerManager(mock_mode=False)


class TestPowerAction:
    def test_enum_values(self):
        assert PowerAction.SHUTDOWN.value == "shutdown"
        assert PowerAction.SLEEP.value == "sleep"
        assert PowerAction.HIBERNATE.value == "hibernate"
        assert PowerAction.RESTART.value == "restart"
        assert PowerAction.LOCK.value == "lock"
        assert PowerAction.SIGN_OUT.value == "sign_out"

    def test_action_labels_exist(self):
        for action in PowerAction:
            assert action in ACTION_LABELS

    def test_action_verbs_exist(self):
        for action in PowerAction:
            assert action in ACTION_VERBS


class TestMockMode:
    def test_execute_mock(self, mock_pm):
        result = mock_pm.execute(PowerAction.SHUTDOWN, delay_seconds=10)
        assert result is True
        assert mock_pm.is_action_pending

    def test_execute_mock_sets_pending(self, mock_pm):
        mock_pm.execute(PowerAction.SHUTDOWN)
        assert mock_pm.pending_action == PowerAction.SHUTDOWN

    def test_abort_mock(self, mock_pm):
        mock_pm.execute(PowerAction.SHUTDOWN)
        assert mock_pm.abort() is True
        assert not mock_pm.is_action_pending

    def test_execute_immediate_mock(self, mock_pm):
        result = mock_pm.execute_immediate(PowerAction.SHUTDOWN)
        assert result is True

    def test_execute_increments_guard(self, mock_pm):
        mock_pm.execute(PowerAction.SHUTDOWN)
        mock_pm.execute(PowerAction.RESTART)
        assert mock_pm.execution_guard == 2

    def test_guard_valid(self, mock_pm):
        mock_pm.execute(PowerAction.SHUTDOWN)
        guard = mock_pm.execution_guard
        assert mock_pm.is_guard_valid(guard)
        assert not mock_pm.is_guard_valid(guard - 1)


class TestAvailableActions:
    def test_mock_has_all_actions(self, mock_pm):
        actions = mock_pm.get_available_actions()
        assert PowerAction.SHUTDOWN in actions
        assert PowerAction.RESTART in actions
        assert PowerAction.LOCK in actions
        assert PowerAction.SIGN_OUT in actions
        assert PowerAction.SLEEP in actions
        assert PowerAction.HIBERNATE in actions


class TestBuildCommand:
    def test_shutdown_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.SHUTDOWN, 10)
        assert cmd == ["shutdown", "/s", "/t", "10"]

    def test_restart_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.RESTART, 30)
        assert cmd == ["shutdown", "/r", "/t", "30"]

    def test_lock_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.LOCK, 0)
        assert cmd == ["rundll32.exe", "user32.dll,LockWorkStation"]

    def test_sign_out_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.SIGN_OUT, 0)
        assert cmd == ["shutdown", "/l"]

    def test_sleep_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.SLEEP, 0)
        assert "powrprof.dll" in cmd[0] or "rundll32.exe" in cmd[0]

    def test_hibernate_command(self, mock_pm):
        cmd = mock_pm._build_command(PowerAction.HIBERNATE, 0)
        assert "powrprof.dll" in cmd[0] or "rundll32.exe" in cmd[0]


class TestClearPending:
    def test_clear_pending(self, mock_pm):
        mock_pm.execute(PowerAction.SHUTDOWN)
        mock_pm.clear_pending()
        assert not mock_pm.is_action_pending
        assert mock_pm.pending_action is None
