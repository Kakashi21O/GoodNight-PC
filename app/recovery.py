import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE = ".goodnight_pc_active_state.json"


def _state_path() -> str:
    return str(Path.home() / STATE_FILE)


def save_active_state(action: str, target_time: float, initial_duration: float) -> None:
    data = {
        "action": action,
        "target_time": target_time,
        "initial_duration": initial_duration,
        "saved_at": time.time(),
    }
    path = _state_path()
    try:
        dir_path = os.path.dirname(path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=dir_path, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, path)
            logger.info("Active state saved")
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as e:
        logger.error("Failed to save active state: %s", e)


def load_active_state() -> Optional[dict]:
    path = _state_path()
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        target_time = data.get("target_time", 0)
        if target_time <= 0:
            return None
        remaining = target_time - time.time()
        if remaining <= 0:
            logger.info("Saved state is expired, discarding")
            clear_active_state()
            return None
        data["remaining"] = remaining
        return data
    except (json.JSONDecodeError, ValueError, OSError) as e:
        logger.warning("Could not load active state: %s", e)
        clear_active_state()
        return None


def clear_active_state() -> None:
    path = _state_path()
    try:
        if os.path.exists(path):
            os.unlink(path)
            logger.info("Active state cleared")
    except OSError as e:
        logger.warning("Could not clear active state: %s", e)
