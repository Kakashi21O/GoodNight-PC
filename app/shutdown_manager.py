import logging
import platform
import subprocess

logger = logging.getLogger(__name__)


class ShutdownManager:
    def __init__(self, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self._shutdown_pending = False

    @property
    def is_windows(self) -> bool:
        return platform.system() == "Windows"

    def request_shutdown(self, delay_seconds: int = 60) -> bool:
        if self.mock_mode:
            logger.info("[TEST MODE] Windows shutdown requested (delay=%ds)", delay_seconds)
            self._shutdown_pending = True
            return True

        if not self.is_windows:
            logger.error("Shutdown not supported on %s", platform.system())
            return False

        try:
            cmd = ["shutdown", "/s", "/t", str(delay_seconds)]
            subprocess.run(cmd, check=True, capture_output=True)
            self._shutdown_pending = True
            logger.info("Shutdown scheduled in %d seconds", delay_seconds)
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Shutdown command failed: %s", e)
            return False
        except FileNotFoundError:
            logger.error("shutdown command not found")
            return False

    def abort_shutdown(self) -> bool:
        if self.mock_mode:
            logger.info("[TEST MODE] Windows shutdown aborted")
            self._shutdown_pending = False
            return True

        if not self.is_windows:
            logger.error("Abort not supported on %s", platform.system())
            return False

        try:
            subprocess.run(["shutdown", "/a"], check=True, capture_output=True)
            self._shutdown_pending = False
            logger.info("Shutdown aborted")
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Abort command failed: %s", e)
            return False
        except FileNotFoundError:
            logger.error("shutdown command not found")
            return False

    def immediate_shutdown(self) -> bool:
        if self.mock_mode:
            logger.info("[TEST MODE] Immediate shutdown requested")
            self._shutdown_pending = False
            return True

        if not self.is_windows:
            logger.error("Immediate shutdown not supported on %s", platform.system())
            return False

        try:
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True, capture_output=True)
            self._shutdown_pending = False
            logger.info("Immediate shutdown initiated")
            return True
        except subprocess.CalledProcessError as e:
            logger.error("Immediate shutdown failed: %s", e)
            return False
        except FileNotFoundError:
            logger.error("shutdown command not found")
            return False

    @property
    def is_shutdown_pending(self) -> bool:
        return self._shutdown_pending

    def clear_pending(self) -> None:
        self._shutdown_pending = False
