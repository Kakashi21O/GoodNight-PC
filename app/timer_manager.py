import enum
import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TimerState(enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    WARNING = "warning"
    SHUTTING_DOWN = "shutting_down"


class TimerManager:
    def __init__(self):
        self._state = TimerState.IDLE
        self._target_time: Optional[float] = None
        self._remaining_when_paused: float = 0.0
        self._session_id: int = 0
        self._on_expire: Optional[Callable] = None
        self._tick_callback: Optional[Callable] = None
        self._tick_interval_ms: int = 1000
        self._lock = threading.Lock()
        self._root = None
        self._after_id: Optional[str] = None

    def set_root(self, root) -> None:
        self._root = root

    @property
    def state(self) -> TimerState:
        return self._state

    @state.setter
    def state(self, new_state: TimerState) -> None:
        old = self._state
        self._state = new_state
        logger.info("Timer state: %s -> %s", old.value, new_state.value)

    @property
    def session_id(self) -> int:
        return self._session_id

    def get_remaining(self) -> float:
        with self._lock:
            if self._state == TimerState.PAUSED:
                return self._remaining_when_paused
            if self._state == TimerState.RUNNING and self._target_time is not None:
                remaining = self._target_time - time.time()
                return max(remaining, 0.0)
            return 0.0

    def start(self, duration_seconds: float, on_expire: Callable, tick_callback: Optional[Callable] = None) -> bool:
        with self._lock:
            if self._state not in (TimerState.IDLE,):
                logger.warning("Cannot start timer in state %s", self._state.value)
                return False

            if duration_seconds <= 0:
                logger.warning("Invalid duration: %s", duration_seconds)
                return False

            self._session_id += 1
            self._target_time = time.time() + duration_seconds
            self._on_expire = on_expire
            self._tick_callback = tick_callback
            self._state = TimerState.RUNNING
            logger.info("Timer started: %.1fs (session %d)", duration_seconds, self._session_id)

        self._schedule_tick()
        return True

    def pause(self) -> bool:
        with self._lock:
            if self._state != TimerState.RUNNING:
                return False
            self._remaining_when_paused = max(self._target_time - time.time(), 0.0)
            self._state = TimerState.PAUSED
            self._cancel_tick()
            logger.info("Timer paused: %.1fs remaining", self._remaining_when_paused)
        return True

    def resume(self) -> bool:
        with self._lock:
            if self._state != TimerState.PAUSED:
                return False
            self._target_time = time.time() + self._remaining_when_paused
            self._state = TimerState.RUNNING
            logger.info("Timer resumed: %.1fs remaining", self._remaining_when_paused)
        self._schedule_tick()
        return True

    def cancel(self) -> bool:
        with self._lock:
            if self._state == TimerState.IDLE:
                return False
            self._cancel_tick()
            self._state = TimerState.IDLE
            self._target_time = None
            self._on_expire = None
            self._tick_callback = None
            self._session_id += 1
            logger.info("Timer cancelled (session %d)", self._session_id)
        return True

    def add_time(self, seconds: float) -> bool:
        with self._lock:
            if self._state != TimerState.RUNNING:
                return False
            self._target_time += seconds
            logger.info("Added %.0fs to timer", seconds)
        return True

    def replace_timer(self, new_duration: float, on_expire: Callable, tick_callback: Optional[Callable] = None) -> bool:
        self.cancel()
        return self.start(new_duration, on_expire, tick_callback)

    def start_warning(self, duration: float, tick_callback: Optional[Callable] = None) -> bool:
        with self._lock:
            if self._state == TimerState.WARNING:
                logger.warning("Warning already active")
                return False
            self._session_id += 1
            self._target_time = time.time() + duration
            self._tick_callback = tick_callback
            self._on_expire = None
            self._state = TimerState.WARNING
            logger.info("Warning started: %.1fs (session %d)", duration, self._session_id)
        self._schedule_tick()
        return True

    def get_warning_remaining(self) -> float:
        with self._lock:
            if self._state == TimerState.WARNING and self._target_time is not None:
                remaining = self._target_time - time.time()
                return max(remaining, 0.0)
            return 0.0

    def _schedule_tick(self) -> None:
        self._cancel_tick()
        if self._root is None:
            return
        self._after_id = self._root.after(self._tick_interval_ms, self._tick)

    def _cancel_tick(self) -> None:
        if self._root is not None and self._after_id is not None:
            try:
                self._root.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _tick(self) -> None:
        with self._lock:
            current_state = self._state
            session = self._session_id

        if current_state == TimerState.RUNNING:
            remaining = self.get_remaining()
            if remaining <= 0:
                logger.info("Timer expired (session %d)", session)
                callback = self._on_expire
                if callback:
                    self._root.after(0, callback, session)
                return
            if self._tick_callback:
                self._root.after(0, self._tick_callback, remaining, session)
            self._schedule_tick()

        elif current_state == TimerState.WARNING:
            remaining = self.get_warning_remaining()
            if remaining <= 0:
                logger.info("Warning countdown expired (session %d)", session)
                return
            if self._tick_callback:
                self._root.after(0, self._tick_callback, remaining, session)
            self._schedule_tick()

    def validate_duration(self, hours: str, minutes: str, seconds: str) -> tuple:
        errors = []
        try:
            h = int(hours) if hours.strip() else 0
        except ValueError:
            errors.append("Invalid hours value")
            h = 0
        try:
            m = int(minutes) if minutes.strip() else 0
        except ValueError:
            errors.append("Invalid minutes value")
            m = 0
        try:
            s = int(seconds) if seconds.strip() else 0
        except ValueError:
            errors.append("Invalid seconds value")
            s = 0

        if not errors:
            if h < 0 or m < 0 or s < 0:
                errors.append("Values cannot be negative")
            if m >= 60:
                errors.append("Minutes must be 0-59")
            if s >= 60:
                errors.append("Seconds must be 0-59")
            if h > 23:
                errors.append("Hours cannot exceed 23")
            if h == 0 and m == 0 and s == 0:
                errors.append("Duration must be greater than zero")

        total = h * 3600 + m * 60 + s
        return total, errors
