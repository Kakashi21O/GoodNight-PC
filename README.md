# GoodNight PC - Auto Shutdown Timer

A polished, reliable Windows Auto Shutdown Timer desktop application built with Python and tkinter.

Designed for situations like watching YouTube, movies, streams, listening to music, downloading files, or leaving the computer running temporarily. Configure a shutdown countdown and continue using your PC normally. When the timer expires, a prominent warning popup appears with options to cancel, postpone, change the timer, or power action immediately.

## Features

### Timer & Scheduling
- **Duration Mode** - Set hours, minutes, and seconds for auto-shutdown
- **Schedule Mode** - Pick a specific time (HH:MM AM/PM) for auto-shutdown
- **Quick Presets** - One-click timers: 15 min, 30 min, 1 hour, 2 hours
- **Custom Presets** - Save up to 8 user-defined presets (right-click to delete)
- **Start Confirmation** - Timer summary dialog before starting

### Power Actions
- **6 Power Actions** - Shut Down, Restart, Sleep, Hibernate, Lock, Sign Out
- **Action Selector** - Choose your preferred action before starting
- **Action-Specific Labels** - UI dynamically reflects the selected action
- **Hibernate Detection** - Automatically detects available power states

### Active Timer
- **Large Countdown Display** - Big clock-style countdown with target time
- **Progress Bar** - Visual progress indicator
- **Pause/Resume** - Freeze and continue the countdown (Space key)
- **Add 30 Minutes** - Postpone shutdown with one click
- **Configurable Postpone** - Choose from 1-60 minute postpone durations
- **Change Timer** - Return to editor with remaining time
- **Cancel** - Completely abort the shutdown process

### Warning & Recovery
- **20-Second Warning** - Prominent popup with configurable countdown
- **4 Warning Actions** - Cancel, Postpone (configurable), New Timer, or Action Now
- **Configurable Postpone Durations** - Set your own postpone options (5, 10, 15, 30, 60 min)
- **Alert Sound** - Windows notification sound on warning (configurable)
- **Timer Recovery** - Persists active timer state; resume after crash or restart
- **Clock Drift Detection** - Detects system sleep/resume and updates timer state

### UI & UX
- **Theme System** - Dark and light themes with centralized color management
- **Dashboard Layout** - Greeting, time input, action selector, presets
- **Status Bar** - Shows current state (Ready/Timer active/Paused) + TEST MODE badge
- **Settings Dialog** - Scrollable settings with Warning, Appearance, and About sections
- **Keyboard Shortcuts** - Space (pause), Escape (close), Ctrl+S (settings)

### Safety & Reliability
- **Single Instance** - Prevents conflicting duplicate timers
- **Atomic Settings** - Crash-safe settings writes via tempfile + replace
- **Settings Migration** - Automatic schema versioning and migration
- **Session IDs** - Prevent stale callbacks from triggering shutdown
- **Test Mode** - Run safely without real shutdown commands
- **Global Exception Handler** - Catches and logs unhandled exceptions

## Screenshots

*Coming soon*

## Requirements

- **Operating System**: Windows 10/11
- **Python**: 3.8 or later
- **Dependencies**: None (uses only Python standard library)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Kakashi21O/GoodNight-PC.git
cd GoodNight-PC
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

No third-party packages are required. The project uses only Python standard library modules.

## Running the Application

```bash
python main.py
```

### Test Mode

Run without real shutdown commands:

```bash
python main.py --test
```

In test mode, shutdown operations are logged instead of executed.

## Usage

### Setting a Timer

1. Choose a mode: **Countdown** (duration) or **At time** (specific time)
2. Enter the time values
3. Select a power action from the dropdown (Shut Down, Sleep, Restart, etc.)
4. Click **Start** (or a quick preset) and confirm in the summary dialog

### Custom Presets

1. Set a duration in countdown mode
2. Click the **+** button to save it as a preset
3. Right-click a custom preset to delete it
4. Up to 8 custom presets can be saved

### During Countdown

- **Pause** (Space) - Freeze the countdown
- **Resume** (Space) - Continue from where you paused
- **+30 Minutes** - Add 30 minutes to the countdown
- **Change Timer** - Return to the timer editor with the remaining time
- **Cancel** - Abort completely

### Warning Popup

When the timer expires, a popup appears with a configurable countdown:

- **Cancel** - Stop everything, return to idle
- **Postpone** - Choose a duration from the dropdown (configurable in Settings)
- **New Timer** - Return to the timer editor
- **Action Now** - Execute the power action immediately (requires confirmation)

Closing the warning popup with the X button cancels the action.

### Settings

Click **Settings** (or Ctrl+S) to configure:

- Warning countdown duration (5-300 seconds, default: 20)
- Alert sound on/off
- Always-on-top for warning popup
- Confirm before immediate action
- Postpone durations (comma-separated minutes)
- Theme (dark/light)

Settings are saved to `~/.goodnight_pc_settings.json`.

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Pause / Resume timer |
| Escape | Close window / Cancel |
| Ctrl+S | Open Settings |

## Test/Safe Mode

When run with `--test`, all shutdown commands are logged instead of executed:

```
[TEST MODE] Shut Down requested (delay=60s)
[TEST MODE] Power action aborted
[TEST MODE] Immediate Shut Down requested
```

This allows full workflow testing without risk of shutting down your PC.

## Architecture

```
GoodNight PC/
├── main.py                  # Entry point, single-instance lock, logging
├── requirements.txt         # Dependencies (none required)
├── README.md                # This file
├── .gitignore               # Git ignore rules
│
├── app/
│   ├── __init__.py          # Package init
│   ├── version.py           # App name and version constants
│   ├── theme.py             # ThemeManager with dark/light palettes
│   ├── ui.py                # Main window, warning popup, settings dialog
│   ├── timer_manager.py     # Timer engine with state machine
│   ├── power_manager.py     # PowerAction enum, command routing, execution guard
│   ├── shutdown_manager.py  # Original Windows shutdown commands
│   ├── settings_manager.py  # Atomic JSON settings with schema migration
│   ├── recovery.py          # Timer state persistence and recovery
│   └── utils.py             # Formatting, sound, platform detection
│
├── tests/
│   ├── test_timer_manager.py    # Timer state machine tests (26 tests)
│   ├── test_settings_manager.py # Settings persistence tests (14 tests)
│   ├── test_power_manager.py    # Power manager tests (17 tests)
│   └── test_recovery.py         # Recovery state tests (7 tests)
│
└── context/                 # Architecture docs (gitignored)
```

## Development Notes

- **State Machine**: IDLE -> RUNNING -> PAUSED -> WARNING -> SHUTTING_DOWN
- **Timer Engine**: Uses absolute timestamps (`target_time = time.time() + duration`) to prevent drift
- **Session IDs**: Increment on cancel/start to prevent stale callbacks from triggering shutdown
- **Power Centralization**: All power calls go through `PowerManager` - never scattered in UI code
- **Non-Blocking UI**: Uses tkinter's `after()` method instead of `time.sleep()`
- **Mock Mode**: `--test` flag enables safe testing without real OS commands
- **Atomic Writes**: Settings and recovery state use tempfile + `os.replace()` to prevent corruption
- **Schema Migration**: Settings automatically migrate between schema versions

## Safety Behavior

- **No shutdown over unexpected shutdown**: When state is ambiguous, the app defaults to not shutting down
- **Confirmation required**: Immediate power action always asks for confirmation
- **X button on warning**: Cancels the action, does NOT trigger it
- **Stale callback protection**: Session IDs ensure old timer callbacks cannot trigger shutdown after cancellation
- **Cancel always works**: `shutdown /a` is called to abort any pending OS shutdown
- **Test mode**: Cannot accidentally shut down the computer
- **Timer recovery**: Active timers survive app crashes; offer to resume on next launch
- **Clock drift detection**: Detects system sleep/resume and updates persisted state

## License

MIT
