import enum
import logging
import platform
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


class PowerAction(enum.Enum):
    SHUTDOWN = "shutdown"
    SLEEP = "sleep"
    HIBERNATE = "hibernate"
    RESTART = "restart"
    LOCK = "lock"
    SIGN_OUT = "sign_out"


ACTION_LABELS = {
    PowerAction.SHUTDOWN: "Shut Down",
    PowerAction.SLEEP: "Sleep",
    PowerAction.HIBERNATE: "Hibernate",
    PowerAction.RESTART: "Restart",
    PowerAction.LOCK: "Lock",
    PowerAction.SIGN_OUT: "Sign Out",
}

ACTION_VERBS = {
    PowerAction.SHUTDOWN: "shut down",
    PowerAction.SLEEP: "put to sleep",
    PowerAction.HIBERNATE: "hibernate",
    PowerAction.RESTART: "restart",
    PowerAction.LOCK: "lock",
    PowerAction.SIGN_OUT: "sign out",
}


class PowerManager:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._pending_action: Optional[PowerAction] = None
        self._execution_guard: int = 0

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    def get_available_actions(self) -> list:
        actions = [PowerAction.SHUTDOWN, PowerAction.RESTART, PowerAction.LOCK, PowerAction.SIGN_OUT]
        if self._can_hibernate():
            actions.append(PowerAction.HIBERNATE)
        if self._can_sleep():
            actions.append(PowerAction.SLEEP)
        return actions

    def _can_sleep(self) -> bool:
        if self.mock_mode:
            return True
        if not self.is_windows:
            return False
        try:
            result = subprocess.run(
                ["powercfg", "/a"], capture_output=True, text=True, timeout=5
            )
            return "Standby (S)" in result.stdout
        except Exception:
            logger.debug("Could not detect sleep support", exc_info=True)
            return True

    def _can_hibernate(self) -> bool:
        if self.mock_mode:
            return True
        if not self.is_windows:
            return False
        try:
            result = subprocess.run(
                ["powercfg", "/a"], capture_output=True, text=True, timeout=5
            )
            return "Hibernate" in result.stdout and "Disabled" not in result.stdout.split("Hibernate")[1][:50]
        except Exception:
            logger.debug("Could not detect hibernate support", exc_info=True)
            return False

    def execute(self, action: PowerAction, delay_seconds: int = 10) -> bool:
        self._execution_guard += 1
        guard = self._execution_guard

        if self.mock_mode:
            label = ACTION_LABELS.get(action, action.value)
            logger.info("[TEST MODE] %s requested (delay=%ds)", label, delay_seconds)
            self._pending_action = action
            return True

        if not self.is_windows:
            logger.error("Power action %s not supported on %s", action.value, platform.system())
            return False

        try:
            cmd = self._build_command(action, delay_seconds)
            if cmd is None:
                logger.error("No command available for action: %s", action.value)
                return False
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            self._pending_action = action
            label = ACTION_LABELS.get(action, action.value)
            logger.info("%s scheduled (delay=%ds)", label, delay_seconds)
            return True
        except subprocess.TimeoutExpired:
            logger.error("Power command timed out for %s", action.value)
            return False
        except subprocess.CalledProcessError as e:
            logger.error("Power command failed for %s: %s", action.value, e)
            return False
        except FileNotFoundError:
            logger.error("Power command not found for %s", action.value)
            return False

    def _build_command(self, action: PowerAction, delay_seconds: int) -> Optional[list]:
        if action == PowerAction.SHUTDOWN:
            return ["shutdown", "/s", "/t", str(delay_seconds)]
        elif action == PowerAction.RESTART:
            return ["shutdown", "/r", "/t", str(delay_seconds)]
        elif action == PowerAction.SLEEP:
            return ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"]
        elif action == PowerAction.HIBERNATE:
            return ["rundll32.exe", "powrprof.dll,SetSuspendState", "hibernate"]
        elif action == PowerAction.LOCK:
            return ["rundll32.exe", "user32.dll,LockWorkStation"]
        elif action == PowerAction.SIGN_OUT:
            return ["shutdown", "/l"]
        return None

    def abort(self, action: Optional[PowerAction] = None) -> bool:
        if self.mock_mode:
            logger.info("[TEST MODE] Power action aborted")
            self._pending_action = None
            return True

        if not self.is_windows:
            return False

        try:
            subprocess.run(["shutdown", "/a"], check=True, capture_output=True, timeout=10)
            self._pending_action = None
            logger.info("Power action aborted")
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Abort command failed: %s", e)
            return False
        except FileNotFoundError:
            logger.error("shutdown command not found")
            return False
        except subprocess.TimeoutExpired:
            logger.error("Abort command timed out")
            return False

    def execute_immediate(self, action: PowerAction) -> bool:
        if action in (PowerAction.SHUTDOWN, PowerAction.RESTART):
            return self.execute(action, delay_seconds=0)
        elif action == PowerAction.LOCK:
            return self.execute(action, delay_seconds=0)
        elif action == PowerAction.SIGN_OUT:
            return self.execute(action, delay_seconds=0)
        elif action in (PowerAction.SLEEP, PowerAction.HIBERNATE):
            return self.execute(action, delay_seconds=0)
        return False

    @property
    def pending_action(self) -> Optional[PowerAction]:
        return self._pending_action

    @property
    def is_action_pending(self) -> bool:
        return self._pending_action is not None

    def clear_pending(self) -> None:
        self._pending_action = None
