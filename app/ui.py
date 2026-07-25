import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Dict

from app.timer_manager import TimerManager, TimerState
from app.power_manager import PowerManager, PowerAction, ACTION_LABELS, ACTION_VERBS
from app.shutdown_manager import ShutdownManager
from app.settings_manager import SettingsManager
from app.theme import ThemeManager
from app.utils import format_duration, format_shutdown_time, play_alert_sound, is_windows
from app.version import APP_VERSION_STRING

logger = logging.getLogger(__name__)


class App(tk.Tk):
    def __init__(self, shutdown_manager: ShutdownManager, settings: SettingsManager,
                 power_manager: Optional[PowerManager] = None):
        super().__init__()
        self.shutdown_manager = shutdown_manager
        self.power_manager = power_manager or PowerManager(mock_mode=shutdown_manager.mock_mode)
        self.settings = settings
        self.theme = ThemeManager(settings.get("theme", "dark"))
        self.timer = TimerManager()
        self.timer.set_root(self)
        self._selected_action = PowerAction(settings.get("selected_action", "shutdown"))
        self._test_mode = shutdown_manager.mock_mode
        self._initial_duration: float = 0

        self.title("GoodNight PC")
        self.geometry("420x480")
        self.minsize(380, 440)
        self.configure(bg=self.theme.get("bg"))
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_styles()
        self._build_status_bar()
        self._build_idle_frame()
        self._build_running_frame()
        self._warning_window: Optional[WarningWindow] = None

        self._show_idle()
        self._update_action_labels()
        logger.info("Application started")

    def _build_styles(self) -> None:
        c = self.theme.colors
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=c["bg"], foreground=c["text"])
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"), background=c["bg"], foreground=c["text"])
        style.configure("Greeting.TLabel", font=("Segoe UI", 13), background=c["bg"], foreground=c["text_dim"])
        style.configure("Subtitle.TLabel", font=("Segoe UI", 10), background=c["bg"], foreground=c["text_dim"])
        style.configure("Big.TLabel", font=("Consolas", 42, "bold"), background=c["bg"], foreground=c["accent"])
        style.configure("Huge.TLabel", font=("Consolas", 52, "bold"), background=c["bg"], foreground=c["warning"])
        style.configure("Info.TLabel", font=("Segoe UI", 10), background=c["bg"], foreground=c["text_dim"])
        style.configure("Status.TLabel", font=("Segoe UI", 8), background=c["surface"], foreground=c["text_muted"])
        style.configure("Test.TLabel", font=("Segoe UI", 8, "italic"), background="#7c3aed", foreground="white")
        style.configure("Primary.TButton", font=("Segoe UI", 11, "bold"), background=c["primary"], foreground="white", padding=(16, 8))
        style.map("Primary.TButton", background=[("active", c["primary_hover"])])
        style.configure("Preset.TButton", font=("Segoe UI", 9), background=c["surface"], foreground=c["text"], padding=(8, 5))
        style.map("Preset.TButton", background=[("active", c["surface_hover"])])
        style.configure("Danger.TButton", font=("Segoe UI", 10, "bold"), background=c["danger"], foreground="white", padding=(12, 7))
        style.map("Danger.TButton", background=[("active", c["danger_hover"])])
        style.configure("Secondary.TButton", font=("Segoe UI", 9), background=c["surface"], foreground=c["text"], padding=(8, 5))
        style.map("Secondary.TButton", background=[("active", c["surface_hover"])])
        style.configure("Accent.TButton", font=("Segoe UI", 9, "bold"), background=c["accent"], foreground=c["bg"], padding=(8, 5))
        style.map("Accent.TButton", background=[("active", c["accent_hover"])])
        style.configure("Ghost.TButton", font=("Segoe UI", 9), background=c["bg"], foreground=c["text_dim"], padding=(6, 4))
        style.map("Ghost.TButton", background=[("active", c["surface"])])
        style.configure("Horizontal.TProgressbar", background=c["primary"], troughcolor=c["surface"], thickness=6)

    def _build_status_bar(self) -> None:
        c = self.theme.colors
        self._status_frame = tk.Frame(self, bg=c["surface"], height=24)
        self._status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self._status_frame.pack_propagate(False)
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(self._status_frame, textvariable=self._status_var, font=("Segoe UI", 8),
                 bg=c["surface"], fg=c["text_muted"]).pack(side=tk.LEFT, padx=8)
        if self._test_mode:
            tk.Label(self._status_frame, text="TEST MODE", font=("Segoe UI", 8, "bold"),
                     bg="#7c3aed", fg="white", padx=6, pady=1).pack(side=tk.RIGHT, padx=4, pady=2)

    def _build_idle_frame(self) -> None:
        c = self.theme.colors
        self._idle_frame = tk.Frame(self, bg=c["bg"])

        greeting = self._get_greeting()
        tk.Label(self._idle_frame, text=greeting, font=("Segoe UI", 13),
                 bg=c["bg"], fg=c["text_dim"]).pack(pady=(18, 2))

        tk.Label(self._idle_frame, text="When should this PC power down?",
                 font=("Segoe UI", 10), bg=c["bg"], fg=c["text_muted"]).pack(pady=(0, 12))

        time_frame = tk.Frame(self._idle_frame, bg=c["bg"])
        time_frame.pack(padx=20, pady=5)

        self._hours_var = tk.StringVar(value="00")
        self._minutes_var = tk.StringVar(value="30")
        self._seconds_var = tk.StringVar(value="00")

        for i, (var, label_text) in enumerate([(self._hours_var, "H"), (self._minutes_var, "M"), (self._seconds_var, "S")]):
            col = tk.Frame(time_frame, bg=c["bg"])
            col.pack(side=tk.LEFT, padx=4)
            e = tk.Entry(col, textvariable=var, width=3, justify=tk.CENTER,
                         font=("Consolas", 22), bg=c["input_bg"], fg=c["text"],
                         insertbackground=c["text"], relief=tk.FLAT, bd=0,
                         highlightthickness=1, highlightbackground=c["border"])
            e.pack(ipady=4)
            e.bind("<FocusIn>", lambda ev, w=e: w.select_range(0, tk.END))
            tk.Label(col, text=label_text, font=("Segoe UI", 8), bg=c["bg"], fg=c["text_muted"]).pack()
            if i < 2:
                tk.Label(time_frame, text=":", font=("Consolas", 22, "bold"),
                         bg=c["bg"], fg=c["text_dim"]).pack(side=tk.LEFT, padx=1)

        self._start_btn_var = tk.StringVar(value="Start Timer")
        ttk.Button(self._idle_frame, textvariable=self._start_btn_var,
                   style="Primary.TButton", command=self._on_start).pack(pady=(14, 10))

        sep = tk.Frame(self._idle_frame, bg=c["border"], height=1)
        sep.pack(fill=tk.X, padx=30, pady=4)

        tk.Label(self._idle_frame, text="Quick timers", font=("Segoe UI", 9),
                 bg=c["bg"], fg=c["text_muted"]).pack(pady=(4, 6))

        preset_frame = tk.Frame(self._idle_frame, bg=c["bg"])
        preset_frame.pack(padx=20)
        for text, secs in [("15m", 900), ("30m", 1800), ("1h", 3600), ("2h", 7200)]:
            ttk.Button(preset_frame, text=text, style="Preset.TButton",
                       command=lambda s=secs: self._on_preset(s)).pack(side=tk.LEFT, padx=3)

        action_frame = tk.Frame(self._idle_frame, bg=c["bg"])
        action_frame.pack(pady=(10, 2))
        tk.Label(action_frame, text="Action", font=("Segoe UI", 9),
                 bg=c["bg"], fg=c["text_muted"]).pack(side=tk.LEFT, padx=(20, 6))
        self._action_var = tk.StringVar(value=ACTION_LABELS.get(self._selected_action, "Shut Down"))
        actions_list = [ACTION_LABELS[a] for a in self.power_manager.get_available_actions()]
        self._action_menu = tk.OptionMenu(action_frame, self._action_var, *actions_list,
                                          command=self._on_action_change)
        self._action_menu.configure(font=("Segoe UI", 9), bg=c["surface"], fg=c["text"],
                                    activebackground=c["surface_hover"], highlightthickness=0,
                                    relief=tk.FLAT)
        self._action_menu["menu"].configure(font=("Segoe UI", 9), bg=c["surface"], fg=c["text"])
        self._action_menu.pack()

        self._error_var = tk.StringVar(value="")
        tk.Label(self._idle_frame, textvariable=self._error_var, font=("Segoe UI", 8),
                 bg=c["bg"], fg=c["danger"]).pack(pady=(4, 0))

        bottom = tk.Frame(self._idle_frame, bg=c["bg"])
        bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=6)
        ttk.Button(bottom, text="Settings", style="Ghost.TButton",
                   command=self._on_settings).pack(side=tk.RIGHT)

    def _build_running_frame(self) -> None:
        c = self.theme.colors
        self._running_frame = tk.Frame(self, bg=c["bg"])

        tk.Label(self._running_frame, text="GoodNight PC", font=("Segoe UI", 14, "bold"),
                 bg=c["bg"], fg=c["text"]).pack(pady=(14, 2))

        self._action_label_var = tk.StringVar(value="SHUTDOWN IN")
        tk.Label(self._running_frame, textvariable=self._action_label_var,
                 font=("Segoe UI", 10), bg=c["bg"], fg=c["text_dim"]).pack(pady=(8, 4))

        self._countdown_var = tk.StringVar(value="00:00:00")
        tk.Label(self._running_frame, textvariable=self._countdown_var,
                 font=("Consolas", 42, "bold"), bg=c["bg"], fg=c["accent"]).pack(pady=4)

        self._schedule_var = tk.StringVar(value="")
        tk.Label(self._running_frame, textvariable=self._schedule_var,
                 font=("Segoe UI", 10), bg=c["bg"], fg=c["text_dim"]).pack(pady=(2, 8))

        self._progress_var = tk.DoubleVar(value=0)
        self._progress_bar = ttk.Progressbar(self._running_frame, variable=self._progress_var,
                                             maximum=100, mode="determinate",
                                             style="Horizontal.TProgressbar")
        self._progress_bar.pack(fill=tk.X, padx=50, pady=(0, 12))

        btn_row1 = tk.Frame(self._running_frame, bg=c["bg"])
        btn_row1.pack(fill=tk.X, padx=40, pady=2)
        self._pause_var = tk.StringVar(value="Pause")
        ttk.Button(btn_row1, textvariable=self._pause_var, style="Secondary.TButton",
                   command=self._on_pause_resume).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(btn_row1, text="+30 min", style="Accent.TButton",
                   command=self._on_add_30).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(3, 0))

        btn_row2 = tk.Frame(self._running_frame, bg=c["bg"])
        btn_row2.pack(fill=tk.X, padx=40, pady=4)
        ttk.Button(btn_row2, text="Change", style="Secondary.TButton",
                   command=self._on_change_timer).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 3))
        ttk.Button(btn_row2, text="Cancel", style="Danger.TButton",
                   command=self._on_cancel).pack(side=tk.RIGHT, expand=True, fill=tk.X, padx=(3, 0))

    def _get_greeting(self) -> str:
        hour = time.localtime().tm_hour
        if hour < 6:
            return "Good night"
        elif hour < 12:
            return "Good morning"
        elif hour < 17:
            return "Good afternoon"
        elif hour < 21:
            return "Good evening"
        return "Good night"

    def _show_idle(self) -> None:
        self._running_frame.pack_forget()
        self._idle_frame.pack(fill=tk.BOTH, expand=True)
        self._error_var.set("")
        self._status_var.set("Ready")

    def _show_running(self) -> None:
        self._idle_frame.pack_forget()
        self._running_frame.pack(fill=tk.BOTH, expand=True)
        self._pause_var.set("Pause")
        self._status_var.set("Timer active")

    def _on_action_change(self, selection: str) -> None:
        for action, label in ACTION_LABELS.items():
            if label == selection:
                self._selected_action = action
                self._update_action_labels()
                self.settings.set("selected_action", action.value)
                break

    def _update_action_labels(self) -> None:
        label = ACTION_LABELS.get(self._selected_action, "Shut Down")
        self._start_btn_var.set(f"Start {label}")
        self._action_label_var.set(f"{self._selected_action.value.upper()} IN")

    def _update_progress(self, remaining: float) -> None:
        if self._initial_duration > 0:
            elapsed = self._initial_duration - remaining
            pct = max(0, min(100, (elapsed / self._initial_duration) * 100))
            self._progress_var.set(pct)

    def _on_start(self) -> None:
        total, errors = self.timer.validate_duration(
            self._hours_var.get(), self._minutes_var.get(), self._seconds_var.get()
        )
        if errors:
            self._error_var.set("; ".join(errors))
            return

        self._error_var.set("")
        self._initial_duration = total
        self.timer.start(total, on_expire=self._on_timer_expired, tick_callback=self._on_tick)
        self._show_running()
        self._update_countdown(total)
        self._update_schedule(total)
        self._update_progress(total)
        label = ACTION_LABELS.get(self._selected_action, "Shut Down")
        logger.info("Timer started: %s (%s)", format_duration(total), label)

    def _on_preset(self, seconds: int) -> None:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        self._hours_var.set(f"{h:02d}")
        self._minutes_var.set(f"{m:02d}")
        self._seconds_var.set(f"{s:02d}")
        self._on_start()

    def _on_pause_resume(self) -> None:
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
            self._pause_var.set("Resume")
            self._status_var.set("Paused")
        elif self.timer.state == TimerState.PAUSED:
            self.timer.resume()
            self._pause_var.set("Pause")
            self._status_var.set("Timer active")

    def _on_add_30(self) -> None:
        if self.timer.state == TimerState.RUNNING:
            self.timer.add_time(1800)
            self._initial_duration += 1800
            remaining = self.timer.get_remaining()
            self._update_countdown(remaining)
            self._update_schedule(remaining)
            logger.info("30 minutes added")

    def _on_change_timer(self) -> None:
        if self.timer.state in (TimerState.RUNNING, TimerState.PAUSED):
            remaining = self.timer.get_remaining()
            self.timer.cancel()
            self.power_manager.abort()
            h = int(remaining) // 3600
            m = (int(remaining) % 3600) // 60
            s = int(remaining) % 60
            self._hours_var.set(f"{h:02d}")
            self._minutes_var.set(f"{m:02d}")
            self._seconds_var.set(f"{s:02d}")
            self._show_idle()
            logger.info("Timer changed, returning to editor")

    def _on_cancel(self) -> None:
        self.timer.cancel()
        self.power_manager.abort()
        self._show_idle()
        self._error_var.set("Timer cancelled")
        logger.info("Timer cancelled")

    def _on_timer_expired(self, session_id: int) -> None:
        if session_id != self.timer.session_id:
            logger.info("Stale expiration ignored (session %d != %d)", session_id, self.timer.session_id)
            return
        self.timer.state = TimerState.WARNING
        self._show_warning()

    def _on_tick(self, remaining: float, session_id: int) -> None:
        if session_id != self.timer.session_id:
            return
        if self.timer.state == TimerState.RUNNING:
            self._update_countdown(remaining)
            self._update_progress(remaining)

    def _update_countdown(self, remaining: float) -> None:
        self._countdown_var.set(format_duration(int(remaining)))

    def _update_schedule(self, remaining: float) -> None:
        target = time.time() + remaining
        self._schedule_var.set(format_shutdown_time(target))

    def _show_warning(self) -> None:
        if self._warning_window is not None:
            return
        self._warning_window = WarningWindow(self, self.timer, self.power_manager, self.settings,
                                              on_done=self._on_warning_done)

    def _on_warning_done(self, action: str, session_id: int) -> None:
        if session_id != self.timer.session_id:
            logger.info("Stale warning callback ignored (session %d != %d)", session_id, self.timer.session_id)
            return

        self._warning_window = None

        if action == "cancel":
            self.timer.cancel()
            self.power_manager.abort()
            self._show_idle()
            self._error_var.set("Timer cancelled")
        elif action == "postpone":
            self.timer.cancel()
            self.timer.start(1800, on_expire=self._on_timer_expired, tick_callback=self._on_tick)
            self._initial_duration = 1800
            self._show_running()
            self._update_countdown(1800)
            self._update_schedule(1800)
            self._update_progress(1800)
            self._error_var.set("Postponed by 30 minutes")
        elif action == "new_timer":
            self.timer.cancel()
            self.power_manager.abort()
            self._show_idle()
        elif action == "shutdown":
            self.timer.cancel()
            self._show_idle()

    def _on_settings(self) -> None:
        SettingsDialog(self, self.settings, self.theme)

    def _on_close(self) -> None:
        if self._warning_window is not None:
            self._warning_window.destroy()
            self._warning_window = None
            self.timer.cancel()
            self.power_manager.abort()
            self._show_idle()

        if self.timer.state in (TimerState.RUNNING, TimerState.PAUSED):
            if messagebox.askyesno("Active Timer",
                                   "A timer is active. Cancel and exit?"):
                self.timer.cancel()
                self.power_manager.abort()
                logger.info("Application closed (timer cancelled)")
                self.destroy()
            return

        if self.timer.state == TimerState.WARNING:
            self.timer.cancel()
            self.power_manager.abort()

        logger.info("Application closed")
        self.destroy()


class WarningWindow(tk.Toplevel):
    def __init__(self, parent: App, timer: TimerManager, power_manager: PowerManager,
                 settings: SettingsManager, on_done):
        super().__init__(parent)
        self.parent_app = parent
        self.timer = timer
        self.power_manager = power_manager
        self.settings = settings
        self.on_done = on_done
        self._session_id = timer.session_id
        self._warning_duration = settings.get("warning_duration", 20)
        self._remaining = self._warning_duration

        c = parent.theme.colors
        action_label = ACTION_LABELS.get(parent._selected_action, "Shut Down")
        verb = ACTION_VERBS.get(parent._selected_action, "shut down")

        self.title(f"{action_label} Ready")
        self.geometry("380x420")
        self.resizable(False, False)
        self.configure(bg=c["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if settings.get("always_on_top_warning", True):
            self.attributes("-topmost", True)
        self.grab_set()
        self.focus_force()

        tk.Label(self, text=f"{action_label} Ready", font=("Segoe UI", 18, "bold"),
                 bg=c["bg"], fg=c["danger"]).pack(pady=(20, 4))
        tk.Label(self, text=f"Your PC will {verb} in", font=("Segoe UI", 11),
                 bg=c["bg"], fg=c["text"]).pack(pady=(4, 4))

        self._countdown_var = tk.StringVar(value=str(self._warning_duration))
        tk.Label(self, textvariable=self._countdown_var,
                 font=("Consolas", 52, "bold"), bg=c["bg"], fg=c["warning"]).pack(pady=4)
        tk.Label(self, text="seconds", font=("Segoe UI", 11), bg=c["bg"], fg=c["text_dim"]).pack()
        tk.Label(self, text="Save your work now.", font=("Segoe UI", 10, "italic"),
                 bg=c["bg"], fg=c["text"]).pack(pady=(8, 14))

        grid = tk.Frame(self, bg=c["bg"])
        grid.pack(fill=tk.X, padx=20, pady=(0, 14))
        grid.columnconfigure(0, weight=1)
        grid.columnconfigure(1, weight=1)

        btn_style = {"font": ("Segoe UI", 10, "bold"), "relief": "flat", "bd": 0, "padx": 8, "pady": 8}
        tk.Button(grid, text="Cancel", bg=c["success"], fg="white",
                  activebackground=c["success_hover"], command=self._on_cancel, **btn_style).grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)
        tk.Button(grid, text="+30 min", bg=c["primary"], fg="white",
                  activebackground=c["primary_hover"], command=self._on_postpone, **btn_style).grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)
        tk.Button(grid, text="New Timer", bg="#2563eb", fg="white",
                  activebackground="#1d4ed8", command=self._on_new_timer, **btn_style).grid(row=1, column=0, sticky="ew", padx=(0, 3), pady=2)
        tk.Button(grid, text=action_label + " Now", bg=c["danger"], fg="white",
                  activebackground=c["danger_hover"], command=self._on_action_now, **btn_style).grid(row=1, column=1, sticky="ew", padx=(3, 0), pady=2)

        play_alert_sound(settings.get("alert_sound_enabled", True))
        self._tick()

    def _tick(self) -> None:
        if self._remaining <= 0:
            self.power_manager.execute(self.parent_app._selected_action, delay_seconds=10)
            self.on_done("shutdown", self._session_id)
            self.destroy()
            return
        self._countdown_var.set(str(int(self._remaining)))
        self._remaining -= 1
        self.after(1000, self._tick)

    def _on_cancel(self) -> None:
        self.on_done("cancel", self._session_id)
        self.destroy()

    def _on_postpone(self) -> None:
        self.on_done("postpone", self._session_id)
        self.destroy()

    def _on_new_timer(self) -> None:
        self.on_done("new_timer", self._session_id)
        self.destroy()

    def _on_action_now(self) -> None:
        action_label = ACTION_LABELS.get(self.parent_app._selected_action, "Shut Down")
        if self.settings.get("confirm_before_shutdown", True):
            if not messagebox.askyesno(f"Confirm {action_label}", f"{action_label} your PC now?"):
                return
        self.power_manager.execute_immediate(self.parent_app._selected_action)
        self.on_done("shutdown", self._session_id)
        self.destroy()

    def _on_close(self) -> None:
        self.on_done("cancel", self._session_id)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings: SettingsManager, theme: ThemeManager):
        super().__init__(parent)
        self.settings = settings
        self.theme = theme
        c = theme.colors
        self.title("Settings")
        self.geometry("380x420")
        self.resizable(False, False)
        self.configure(bg=c["bg"])
        self.transient(parent)
        self.grab_set()

        tk.Label(self, text="Settings", font=("Segoe UI", 15, "bold"),
                 bg=c["bg"], fg=c["text"]).pack(pady=(14, 8))

        canvas = tk.Canvas(self, bg=c["bg"], highlightthickness=0)
        scrollbar = tk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=c["bg"])
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True, padx=(20, 0))
        scrollbar.pack(side="right", fill="y")

        f = scroll_frame

        tk.Label(f, text="Warning", font=("Segoe UI", 10, "bold"),
                 bg=c["bg"], fg=c["text_dim"]).pack(anchor=tk.W, pady=(8, 2))
        self._warning_var = tk.IntVar(value=settings.get("warning_duration", 20))
        tk.Label(f, text="Countdown (seconds):", bg=c["bg"], fg=c["text"],
                 font=("Segoe UI", 9)).pack(anchor=tk.W)
        tk.Spinbox(f, from_=5, to=300, textvariable=self._warning_var, width=5,
                   font=("Consolas", 11), bg=c["input_bg"], fg=c["text"],
                   insertbackground=c["text"], relief=tk.FLAT,
                   highlightthickness=1, highlightbackground=c["border"]).pack(anchor=tk.W, pady=2)

        self._sound_var = tk.BooleanVar(value=settings.get("alert_sound_enabled", True))
        tk.Checkbutton(f, text="Alert sound", variable=self._sound_var, bg=c["bg"],
                       fg=c["text"], selectcolor=c["input_bg"], font=("Segoe UI", 9),
                       activebackground=c["bg"]).pack(anchor=tk.W, pady=3)

        self._topmost_var = tk.BooleanVar(value=settings.get("always_on_top_warning", True))
        tk.Checkbutton(f, text="Always on top (warning)", variable=self._topmost_var, bg=c["bg"],
                       fg=c["text"], selectcolor=c["input_bg"], font=("Segoe UI", 9),
                       activebackground=c["bg"]).pack(anchor=tk.W, pady=3)

        self._confirm_var = tk.BooleanVar(value=settings.get("confirm_before_shutdown", True))
        tk.Checkbutton(f, text="Confirm before action", variable=self._confirm_var, bg=c["bg"],
                       fg=c["text"], selectcolor=c["input_bg"], font=("Segoe UI", 9),
                       activebackground=c["bg"]).pack(anchor=tk.W, pady=3)

        tk.Label(f, text="Appearance", font=("Segoe UI", 10, "bold"),
                 bg=c["bg"], fg=c["text_dim"]).pack(anchor=tk.W, pady=(12, 2))
        self._theme_var = tk.StringVar(value=settings.get("theme", "dark"))
        theme_frame = tk.Frame(f, bg=c["bg"])
        theme_frame.pack(anchor=tk.W, pady=2)
        for t in ["dark", "light"]:
            tk.Radiobutton(theme_frame, text=t.capitalize(), variable=self._theme_var,
                           value=t, bg=c["bg"], fg=c["text"], selectcolor=c["input_bg"],
                           font=("Segoe UI", 9), activebackground=c["bg"]).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(f, text="About", font=("Segoe UI", 10, "bold"),
                 bg=c["bg"], fg=c["text_dim"]).pack(anchor=tk.W, pady=(12, 2))
        tk.Label(f, text=APP_VERSION_STRING, bg=c["bg"], fg=c["text_dim"],
                 font=("Segoe UI", 9)).pack(anchor=tk.W)

        btn_frame = tk.Frame(self, bg=c["bg"])
        btn_frame.pack(fill=tk.X, padx=20, pady=12)
        tk.Button(btn_frame, text="Save", bg=c["primary"], fg="white",
                  font=("Segoe UI", 10, "bold"), activebackground=c["primary_hover"],
                  relief="flat", command=self._save).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="Cancel", bg=c["surface"], fg=c["text"],
                  font=("Segoe UI", 9), activebackground=c["surface_hover"],
                  relief="flat", command=self.destroy).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Reset", bg=c["danger"], fg="white",
                  font=("Segoe UI", 9), activebackground=c["danger_hover"],
                  relief="flat", command=self._reset).pack(side=tk.RIGHT)

    def _save(self) -> None:
        self.settings.set("warning_duration", self._warning_var.get())
        self.settings.set("alert_sound_enabled", self._sound_var.get())
        self.settings.set("always_on_top_warning", self._topmost_var.get())
        self.settings.set("confirm_before_shutdown", self._confirm_var.get())
        self.settings.set("theme", self._theme_var.get())
        self.destroy()

    def _reset(self) -> None:
        if messagebox.askyesno("Reset Settings", "Restore all settings to defaults?"):
            self.settings.reset()
            self._warning_var.set(20)
            self._sound_var.set(True)
            self._topmost_var.set(True)
            self._confirm_var.set(True)
            self._theme_var.set("dark")
