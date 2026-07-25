import logging
import logging.handlers
import os
import sys
import socket
import traceback

from app.shutdown_manager import ShutdownManager
from app.power_manager import PowerManager
from app.settings_manager import SettingsManager
from app.version import APP_VERSION_STRING

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_lock_socket = None


def setup_logging(debug: bool = False) -> None:
    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "goodnight_pc.log")
    level = logging.DEBUG if debug else logging.INFO
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    console_handler = logging.StreamHandler(sys.stdout)
    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        handlers=[file_handler, console_handler],
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
    debug_mode = "--debug" in sys.argv
    setup_logging(debug=debug_mode)
    logger = logging.getLogger(__name__)
    logger.info("%s starting", APP_VERSION_STRING)

    if not acquire_instance_lock():
        from tkinter import messagebox, Tk
        root = Tk()
        root.withdraw()
        messagebox.showwarning("GoodNight PC", "Another instance is already running.")
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
    power_manager = PowerManager(mock_mode=mock_mode)

    def handle_exception(exc_type, exc_value, exc_tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.error("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
        from tkinter import messagebox, Tk
        try:
            root = Tk()
            root.withdraw()
            messagebox.showerror(
                "GoodNight PC",
                f"An unexpected error occurred.\n\n{exc_type.__name__}: {exc_value}\n\nCheck the log file for details."
            )
            root.destroy()
        except Exception:
            pass

    sys.excepthook = handle_exception

    from app.ui import App
    app = App(shutdown_manager, settings, power_manager=power_manager)
    app.mainloop()

    logger.info("Application exited")
    global _lock_socket
    if _lock_socket:
        _lock_socket.close()
        _lock_socket = None


if __name__ == "__main__":
    main()
