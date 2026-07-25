from typing import Dict


THEMES = {
    "dark": {
        "bg": "#1a1b2e",
        "surface": "#242640",
        "surface_hover": "#2e3050",
        "primary": "#7c3aed",
        "primary_hover": "#6d28d9",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "success": "#16a34a",
        "success_hover": "#15803d",
        "warning": "#f59e0b",
        "text": "#e2e8f0",
        "text_dim": "#94a3b8",
        "text_muted": "#64748b",
        "border": "#334155",
        "input_bg": "#2a2c42",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
    },
    "light": {
        "bg": "#f8fafc",
        "surface": "#ffffff",
        "surface_hover": "#f1f5f9",
        "primary": "#7c3aed",
        "primary_hover": "#6d28d9",
        "danger": "#dc2626",
        "danger_hover": "#b91c1c",
        "success": "#16a34a",
        "success_hover": "#15803d",
        "warning": "#f59e0b",
        "text": "#1e293b",
        "text_dim": "#475569",
        "text_muted": "#94a3b8",
        "border": "#e2e8f0",
        "input_bg": "#f1f5f9",
        "accent": "#f59e0b",
        "accent_hover": "#d97706",
    },
}


class ThemeManager:
    def __init__(self, theme_name: str = "dark"):
        self._current = theme_name if theme_name in THEMES else "dark"

    @property
    def name(self) -> str:
        return self._current

    @property
    def colors(self) -> Dict[str, str]:
        return THEMES[self._current]

    def set_theme(self, name: str) -> None:
        if name in THEMES:
            self._current = name

    def get(self, key: str, default: str = "#000000") -> str:
        return self.colors.get(key, default)
