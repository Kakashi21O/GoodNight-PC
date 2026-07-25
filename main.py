import logging
import os
import sys
import socket

from app.shutdown_manager import ShutdownManager
from app.settings_manager import SettingsManager
from app.ui import App

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_lock_socket = None


def setup_logging() -> None:
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goodnight_pc.log")
    logging.basicConfig(
        level=logging.INFO,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def acquire_instance_lock() -> bool:
    global _lock_socket
    try:
        _lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _lock_socket.bind(("127.0.0.1", 47821))
        _lock_socket.listen(1)
        return True
    except OSError:
        return False


def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    if not acquire_instance_lock():
        from tkinter import messagebox, Tk
        root = Tk()
        root.withdraw()
        messagebox.showwarning("Auto Shutdown Timer", "Another instance is already running.")
        root.destroy()
        return

    mock_mode = "--test" in sys.argv
    if mock_mode:
        logger.info("Running in TEST MODE - no real shutdown will occur")

    from app.utils import is_windows
    if not is_windows():
        logger.warning("Running on non-Windows platform. Shutdown functionality may not work.")

    settings = SettingsManager()
    shutdown_manager = ShutdownManager(mock_mode=mock_mode)

    app = App(shutdown_manager, settings)
    app.mainloop()

    logger.info("Application exited")
    global _lock_socket
    if _lock_socket:
        _lock_socket.close()
        _lock_socket = None


if __name__ == "__main__":
    main()
