import logging
import time
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from app.timer_manager import TimerManager, TimerState
from app.power_manager import PowerManager, PowerAction, ACTION_LABELS, ACTION_VERBS
from app.shutdown_manager import ShutdownManager
from app.settings_manager import SettingsManager
from app.utils import format_duration, format_shutdown_time, play_alert_sound, is_windows

logger = logging.getLogger(__name__)


class App(tk.Tk):
    def __init__(self, shutdown_manager: ShutdownManager, settings: SettingsManager,
                 power_manager: Optional[PowerManager] = None):
        super().__init__()
        self.shutdown_manager = shutdown_manager
        self.power_manager = power_manager or PowerManager(mock_mode=shutdown_manager.mock_mode)
        self.settings = settings
        self.timer = TimerManager()
        self.timer.set_root(self)
        self._selected_action = PowerAction(settings.get("selected_action", "shutdown"))

        self.title("Auto Shutdown Timer")
        self.geometry("400x420")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_styles()
        self._build_idle_frame()
        self._build_running_frame()
        self._warning_window: Optional[WarningWindow] = None

        self._test_mode = shutdown_manager.mock_mode

        self._show_idle()
        self._update_action_labels()
        logger.info("Application started")

    def _build_styles(self) -> None:
        self.colors = {
            "bg": "#1e1e2e",
            "surface": "#2a2a3e",
            "primary": "#7c3aed",
            "primary_hover": "#6d28d9",
            "danger": "#dc2626",
            "danger_hover": "#b91c1c",
            "success": "#16a34a",
            "text": "#e2e8f0",
            "text_dim": "#94a3b8",
            "accent": "#f59e0b",
        }
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Title.TLabel", font=("Segoe UI", 18, "bold"), background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("Subtitle.TLabel", font=("Segoe UI", 12), background=self.colors["bg"], foreground=self.colors["text_dim"])
        style.configure("Big.TLabel", font=("Consolas", 48, "bold"), background=self.colors["bg"], foreground=self.colors["accent"])
        style.configure("Info.TLabel", font=("Segoe UI", 11), background=self.colors["bg"], foreground=self.colors["text_dim"])
        style.configure("Input.TSpinbox", font=("Consolas", 24), fieldbackground=self.colors["surface"], foreground=self.colors["text"], insertcolor=self.colors["text"])
        style.configure("Primary.TButton", font=("Segoe UI", 12, "bold"), background=self.colors["primary"], foreground="white", padding=(20, 10))
        style.map("Primary.TButton", background=[("active", self.colors["primary_hover"])])
        style.configure("Preset.TButton", font=("Segoe UI", 10), background=self.colors["surface"], foreground=self.colors["text"], padding=(10, 6))
        style.map("Preset.TButton", background=[("active", self.colors["primary"])])
        style.configure("Danger.TButton", font=("Segoe UI", 11, "bold"), background=self.colors["danger"], foreground="white", padding=(15, 8))
        style.map("Danger.TButton", background=[("active", self.colors["danger_hover"])])
        style.configure("Secondary.TButton", font=("Segoe UI", 10), background=self.colors["surface"], foreground=self.colors["text"], padding=(10, 6))
        style.map("Secondary.TButton", background=[("active", self.colors["primary"])])
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), background=self.colors["accent"], foreground="#1e1e2e", padding=(10, 6))
        style.map("Accent.TButton", background=[("active", "#d97706")])

    def _build_idle_frame(self) -> None:
        self._idle_frame = tk.Frame(self, bg=self.colors["bg"])

        title = ttk.Label(self._idle_frame, text="Auto Shutdown Timer", style="Title.TLabel")
        title.pack(pady=(20, 5))

        subtitle = ttk.Label(self._idle_frame, text="Set Shutdown Timer", style="Subtitle.TLabel")
        subtitle.pack(pady=(0, 15))

        time_frame = tk.Frame(self._idle_frame, bg=self.colors["bg"])
        time_frame.pack(padx=20, pady=5)

        self._hours_var = tk.StringVar(value="00")
        self._minutes_var = tk.StringVar(value="30")
        self._seconds_var = tk.StringVar(value="00")

        for var, label_text in [(self._hours_var, "Hours"), (self._minutes_var, "Minutes"), (self._seconds_var, "Seconds")]:
            col_frame = tk.Frame(time_frame, bg=self.colors["bg"])
            col_frame.pack(side=tk.LEFT, padx=5)
            entry = tk.Entry(col_frame, textvariable=var, width=3, justify=tk.CENTER,
                             font=("Consolas", 24), bg=self.colors["surface"], fg=self.colors["text"],
                             insertbackground=self.colors["text"], relief=tk.FLAT, bd=0)
            entry.pack()
            entry.bind("<FocusIn>", lambda e, w=entry: w.select_range(0, tk.END))
            lbl = ttk.Label(col_frame, text=label_text, style="Subtitle.TLabel")
            lbl.pack()

            sep = ttk.Label(time_frame, text=":", style="Big.TLabel")
            if label_text != "Seconds":
                sep.pack(side=tk.LEFT, padx=2)

        self._start_btn_var = tk.StringVar(value="Start Timer")
        start_btn = ttk.Button(self._idle_frame, textvariable=self._start_btn_var,
                               style="Primary.TButton", command=self._on_start)
        start_btn.pack(pady=15)

        preset_label = ttk.Label(self._idle_frame, text="Quick Timer", style="Subtitle.TLabel")
        preset_label.pack(pady=(10, 5))

        preset_frame = tk.Frame(self._idle_frame, bg=self.colors["bg"])
        preset_frame.pack(padx=20, pady=5)

        for text, seconds in [("30 Min", 1800), ("1 Hour", 3600), ("2 Hours", 7200), ("3 Hours", 10800)]:
            btn = ttk.Button(preset_frame, text=text, style="Preset.TButton",
                             command=lambda s=seconds: self._on_preset(s))
            btn.pack(side=tk.LEFT, padx=3)

        bottom_frame = tk.Frame(self._idle_frame, bg=self.colors["bg"])
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=10)
        settings_btn = ttk.Button(bottom_frame, text="Settings", style="Secondary.TButton",
                                  command=self._on_settings)
        settings_btn.pack(side=tk.RIGHT)

        self._error_var = tk.StringVar(value="")
        self._error_label = ttk.Label(self._idle_frame, textvariable=self._error_var,
                                      font=("Segoe UI", 9), foreground=self.colors["danger"],
                                      background=self.colors["bg"])
        self._error_label.pack(pady=(0, 5))

        if self._test_mode:
            test_banner = tk.Label(self._idle_frame, text="TEST MODE - Power actions are disabled",
                                   font=("Segoe UI", 9, "italic"), bg="#7c3aed", fg="white",
                                   padx=10, pady=3)
            test_banner.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=(0, 5))

    def _build_running_frame(self) -> None:
        self._running_frame = tk.Frame(self, bg=self.colors["bg"])

        title = ttk.Label(self._running_frame, text="Auto Shutdown Timer", style="Title.TLabel")
        title.pack(pady=(20, 5))

        self._action_label_var = tk.StringVar(value="SHUTDOWN IN")
        ttk.Label(self._running_frame, textvariable=self._action_label_var, style="Subtitle.TLabel").pack(pady=(10, 5))

        self._countdown_var = tk.StringVar(value="00:00:00")
        countdown_label = ttk.Label(self._running_frame, textvariable=self._countdown_var, style="Big.TLabel")
        countdown_label.pack(pady=5)

        self._schedule_var = tk.StringVar(value="")
        schedule_label = ttk.Label(self._running_frame, textvariable=self._schedule_var, style="Info.TLabel")
        schedule_label.pack(pady=(5, 20))

        self._pause_var = tk.StringVar(value="Pause")
        pause_btn = ttk.Button(self._running_frame, textvariable=self._pause_var, style="Secondary.TButton",
                               command=self._on_pause_resume)
        pause_btn.pack(side=tk.LEFT, padx=(40, 5), pady=5)

        add_btn = ttk.Button(self._running_frame, text="+30 Minutes", style="Accent.TButton",
                             command=self._on_add_30)
        add_btn.pack(side=tk.RIGHT, padx=(5, 40), pady=5)

        btn_frame = tk.Frame(self._running_frame, bg=self.colors["bg"])
        btn_frame.pack(fill=tk.X, padx=40, pady=(10, 5))

        change_btn = ttk.Button(btn_frame, text="Change Timer", style="Secondary.TButton",
                                command=self._on_change_timer)
        change_btn.pack(side=tk.LEFT, padx=(0, 5), expand=True, fill=tk.X)

        cancel_btn = ttk.Button(btn_frame, text="Cancel", style="Danger.TButton",
                                command=self._on_cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(5, 0), expand=True, fill=tk.X)

    def _show_idle(self) -> None:
        self._running_frame.pack_forget()
        self._idle_frame.pack(fill=tk.BOTH, expand=True)
        self._error_var.set("")

    def _show_running(self) -> None:
        self._idle_frame.pack_forget()
        self._running_frame.pack(fill=tk.BOTH, expand=True)
        self._pause_var.set("Pause")

    def _update_action_labels(self) -> None:
        label = ACTION_LABELS.get(self._selected_action, "Shut Down")
        self._start_btn_var.set(f"Start {label}")
        verb = "SHUTDOWN"
        if self._selected_action == PowerAction.SLEEP:
            verb = "SLEEP"
        elif self._selected_action == PowerAction.HIBERNATE:
            verb = "HIBERNATE"
        elif self._selected_action == PowerAction.RESTART:
            verb = "RESTART"
        elif self._selected_action == PowerAction.LOCK:
            verb = "LOCK"
        elif self._selected_action == PowerAction.SIGN_OUT:
            verb = "SIGN OUT"
        self._action_label_var.set(f"{verb} IN")

    def _on_start(self) -> None:
        total, errors = self.timer.validate_duration(
            self._hours_var.get(), self._minutes_var.get(), self._seconds_var.get()
        )
        if errors:
            self._error_var.set("; ".join(errors))
            return

        self._error_var.set("")
        self.timer.start(total, on_expire=self._on_timer_expired, tick_callback=self._on_tick)
        self._show_running()
        self._update_countdown(total)
        self._update_schedule(total)
        logger.info("Timer started: %s", format_duration(total))

    def _on_preset(self, seconds: int) -> None:
        self._hours_var.set("00")
        self._minutes_var.set(f"{seconds // 60:02d}" if seconds < 3600 else f"{seconds // 3600:02d}")
        self._seconds_var.set("00")
        if seconds >= 3600:
            h = seconds // 3600
            m = (seconds % 3600) // 60
            self._hours_var.set(f"{h:02d}")
            self._minutes_var.set(f"{m:02d}")
        self._on_start()

    def _on_pause_resume(self) -> None:
        if self.timer.state == TimerState.RUNNING:
            self.timer.pause()
            self._pause_var.set("Resume")
        elif self.timer.state == TimerState.PAUSED:
            self.timer.resume()
            self._pause_var.set("Pause")

    def _on_add_30(self) -> None:
        if self.timer.state == TimerState.RUNNING:
            self.timer.add_time(1800)
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
        self._error_var.set("Shutdown cancelled")
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
        elif self.timer.state == TimerState.WARNING:
            pass

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
            self._error_var.set("Shutdown cancelled")
        elif action == "postpone":
            self.timer.cancel()
            self.timer.start(1800, on_expire=self._on_timer_expired, tick_callback=self._on_tick)
            self._show_running()
            self._update_countdown(1800)
            self._update_schedule(1800)
            self._error_var.set("Shutdown postponed")
        elif action == "new_timer":
            self.timer.cancel()
            self.power_manager.abort()
            self._show_idle()
        elif action == "shutdown":
            self.timer.cancel()
            self._show_idle()

    def _on_settings(self) -> None:
        SettingsDialog(self, self.settings)

    def _on_close(self) -> None:
        if self._warning_window is not None:
            self._warning_window.destroy()
            self._warning_window = None
            self.timer.cancel()
            self.power_manager.abort()
            self._show_idle()

        if self.timer.state in (TimerState.RUNNING, TimerState.PAUSED):
            if messagebox.askyesno("Active Timer",
                                   "A shutdown timer is active. Cancel timer and exit?"):
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
        self.shutdown_manager = power_manager
        self.settings = settings
        self.on_done = on_done
        self._session_id = timer.session_id
        self._warning_duration = settings.get("warning_duration", 20)
        self._remaining = self._warning_duration
        self._closed_safely = False

        action_label = ACTION_LABELS.get(self.parent_app._selected_action, "Shut Down")
        self.title(f"{action_label} Ready")
        self.geometry("380x400")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if settings.get("always_on_top_warning", True):
            self.attributes("-topmost", True)

        self.grab_set()
        self.focus_force()

        bg = "#1e1e2e"
        self.configure(bg=bg)

        action_label = ACTION_LABELS.get(self.parent_app._selected_action, "Shut Down")
        title = tk.Label(self, text=f"{action_label} Ready", font=("Segoe UI", 20, "bold"),
                         bg=bg, fg="#dc2626")
        title.pack(pady=(20, 5))

        verb = ACTION_VERBS.get(self.parent_app._selected_action, "shut down")
        subtitle = tk.Label(self, text=f"Your PC will {verb} in", font=("Segoe UI", 12),
                            bg=bg, fg="#e2e8f0")
        subtitle.pack(pady=(5, 5))

        self._countdown_var = tk.StringVar(value=str(self._warning_duration))
        countdown_label = tk.Label(self, textvariable=self._countdown_var,
                                   font=("Consolas", 56, "bold"), bg=bg, fg="#f59e0b")
        countdown_label.pack(pady=5)

        sec_label = tk.Label(self, text="seconds", font=("Segoe UI", 12),
                             bg=bg, fg="#94a3b8")
        sec_label.pack(pady=(0, 5))

        warn_label = tk.Label(self, text="Save your work now.", font=("Segoe UI", 11, "italic"),
                              bg=bg, fg="#e2e8f0")
        warn_label.pack(pady=(0, 15))

        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill=tk.X, padx=20)

        style_cfg = {"font": ("Segoe UI", 10, "bold"), "relief": "flat", "bd": 0, "padx": 10, "pady": 8}

        cancel_btn = tk.Button(btn_frame, text="Cancel Shutdown", bg="#16a34a", fg="white",
                               activebackground="#15803d", command=self._on_cancel, **style_cfg)
        cancel_btn.pack(fill=tk.X, pady=3)

        postpone_btn = tk.Button(btn_frame, text="+30 Minutes", bg="#7c3aed", fg="white",
                                 activebackground="#6d28d9", command=self._on_postpone, **style_cfg)
        postpone_btn.pack(fill=tk.X, pady=3)

        new_timer_btn = tk.Button(btn_frame, text="Set New Timer", bg="#2563eb", fg="white",
                                  activebackground="#1d4ed8", command=self._on_new_timer, **style_cfg)
        new_timer_btn.pack(fill=tk.X, pady=3)

        shutdown_btn = tk.Button(btn_frame, text="Shut Down Now", bg="#dc2626", fg="white",
                                 activebackground="#b91c1c", command=self._on_shutdown_now, **style_cfg)
        shutdown_btn.pack(fill=tk.X, pady=3)

        play_alert_sound(settings.get("alert_sound_enabled", True))
        self._tick()

    def _tick(self) -> None:
        if self._remaining <= 0:
            self.power_manager.execute(self.parent_app._selected_action, delay_seconds=10)
            self._closed_safely = True
            self.on_done("shutdown", self._session_id)
            self.destroy()
            return

        self._countdown_var.set(str(int(self._remaining)))
        self._remaining -= 1
        self.after(1000, self._tick)

    def _on_cancel(self) -> None:
        self._closed_safely = True
        self.on_done("cancel", self._session_id)
        self.destroy()

    def _on_postpone(self) -> None:
        self._closed_safely = True
        self.on_done("postpone", self._session_id)
        self.destroy()

    def _on_new_timer(self) -> None:
        self._closed_safely = True
        self.on_done("new_timer", self._session_id)
        self.destroy()

    def _on_shutdown_now(self) -> None:
        if self.settings.get("confirm_before_shutdown", True):
            from tkinter import messagebox
            if not messagebox.askyesno("Confirm Shutdown", "Shut down your PC now?"):
                return
        self._closed_safely = True
        self.power_manager.execute_immediate(self.parent_app._selected_action)
        self.on_done("shutdown", self._session_id)
        self.destroy()

    def _on_close(self) -> None:
        self._closed_safely = True
        self.on_done("cancel", self._session_id)
        self.destroy()


class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, settings: SettingsManager):
        super().__init__(parent)
        self.settings = settings
        self.title("Settings")
        self.geometry("350x350")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")
        self.transient(parent)
        self.grab_set()

        bg = "#1e1e2e"

        tk.Label(self, text="Settings", font=("Segoe UI", 16, "bold"),
                 bg=bg, fg="#e2e8f0").pack(pady=(15, 10))

        frame = tk.Frame(self, bg=bg)
        frame.pack(fill=tk.X, padx=20)

        self._warning_var = tk.IntVar(value=settings.get("warning_duration", 20))
        tk.Label(frame, text="Warning countdown (seconds):", bg=bg, fg="#e2e8f0",
                 font=("Segoe UI", 10)).pack(anchor=tk.W, pady=(5, 0))
        tk.Spinbox(frame, from_=5, to=120, textvariable=self._warning_var, width=5,
                   font=("Consolas", 12), bg="#2a2a3e", fg="#e2e8f0",
                   insertbackground="#e2e8f0").pack(anchor=tk.W, pady=2)

        self._sound_var = tk.BooleanVar(value=settings.get("alert_sound_enabled", True))
        tk.Checkbutton(frame, text="Alert sound", variable=self._sound_var, bg=bg,
                       fg="#e2e8f0", selectcolor="#2a2a3e", font=("Segoe UI", 10),
                       activebackground=bg).pack(anchor=tk.W, pady=5)

        self._topmost_var = tk.BooleanVar(value=settings.get("always_on_top_warning", True))
        tk.Checkbutton(frame, text="Always on top (warning)", variable=self._topmost_var, bg=bg,
                       fg="#e2e8f0", selectcolor="#2a2a3e", font=("Segoe UI", 10),
                       activebackground=bg).pack(anchor=tk.W, pady=5)

        self._confirm_var = tk.BooleanVar(value=settings.get("confirm_before_shutdown", True))
        tk.Checkbutton(frame, text="Confirm before immediate shutdown", variable=self._confirm_var, bg=bg,
                       fg="#e2e8f0", selectcolor="#2a2a3e", font=("Segoe UI", 10),
                       activebackground=bg).pack(anchor=tk.W, pady=5)

        btn_frame = tk.Frame(self, bg=bg)
        btn_frame.pack(fill=tk.X, padx=20, pady=15)

        tk.Button(btn_frame, text="Save", bg="#7c3aed", fg="white", font=("Segoe UI", 10, "bold"),
                  activebackground="#6d28d9", relief="flat", command=self._save).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(btn_frame, text="Cancel", bg="#2a2a3e", fg="#e2e8f0", font=("Segoe UI", 10),
                  activebackground="#3a3a4e", relief="flat", command=self.destroy).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Reset Defaults", bg="#dc2626", fg="white", font=("Segoe UI", 9),
                  activebackground="#b91c1c", relief="flat", command=self._reset).pack(side=tk.RIGHT)

    def _save(self) -> None:
        self.settings.set("warning_duration", self._warning_var.get())
        self.settings.set("alert_sound_enabled", self._sound_var.get())
        self.settings.set("always_on_top_warning", self._topmost_var.get())
        self.settings.set("confirm_before_shutdown", self._confirm_var.get())
        self.destroy()

    def _reset(self) -> None:
        self.settings.reset()
        self._warning_var.set(20)
        self._sound_var.set(True)
        self._topmost_var.set(True)
        self._confirm_var.set(True)
