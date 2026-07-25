import platform
import logging

logger = logging.getLogger(__name__)


def is_windows() -> bool:
    return platform.system() == "Windows"


def format_duration(total_seconds: int) -> str:
    if total_seconds < 0:
        total_seconds = 0
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def format_shutdown_time(target_timestamp: float) -> str:
    import time
    t = time.localtime(target_timestamp)
    hour = t.tm_hour
    minute = t.tm_min
    ampm = "AM" if hour < 12 else "PM"
    display_hour = hour % 12
    if display_hour == 0:
        display_hour = 12
    return f"Scheduled for {display_hour}:{minute:02d} {ampm}"


def play_alert_sound(enabled: bool = True) -> None:
    if not enabled:
        return
    try:
        if is_windows():
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        else:
            import subprocess
            subprocess.Popen(
                ["printf", "\a"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        logger.warning("Failed to play alert sound", exc_info=True)


def get_platform_label() -> str:
    system = platform.system()
    if system == "Windows":
        return "Windows"
    elif system == "Darwin":
        return "macOS"
    elif system == "Linux":
        return "Linux"
    return system
