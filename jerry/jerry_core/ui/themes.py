#!/usr/bin/env python3
"""Jerry UI — Theme Management

Light/dark theme detection, switching, and color initialization.
"""

import curses
import os
from typing import Dict, Tuple

from .constants import _C, THEME_DARK, THEME_LIGHT


class ThemeManager:
    """Mixin for theme management functionality."""

    def _detect_background_brightness(self) -> str:
        """Detect if terminal has light or dark background.

        Uses COLOR_PAIRS and color content to estimate background brightness.
        Falls back to environment variables if detection fails.

        Returns:
            "dark" or "light"
        """
        # Try environment variables first (most reliable)
        bg = os.environ.get("COLORFGBG", "")
        if bg:
            try:
                # COLORFGBG format: "fg;bg" where values are color indices
                # Common values: 0=black, 7=white, 15=white (bright)
                parts = bg.split(";")
                if len(parts) >= 2:
                    bg_val = int(parts[1])
                    # Background is light if it's white (7, 15) or bright colors (8-15)
                    if bg_val in (7, 15) or bg_val >= 8:
                        return "light"
                    elif bg_val == 0:
                        return "dark"
            except (ValueError, IndexError):
                pass

        # Try TERM variable hints
        term = os.environ.get("TERM", "").lower()
        if "light" in term:
            return "light"
        elif "dark" in term or "black" in term:
            return "dark"

        # Default to dark theme (most common for terminals)
        return "dark"

    def set_theme(self, theme: str):
        """Set theme manually ("dark", "light", or "auto").

        Args:
            theme: Theme name or "auto" for automatic detection
        """
        if theme == "auto":
            self._theme_auto = True
            self.theme = self._detect_background_brightness()
        elif theme in ("dark", "light"):
            self._theme_auto = False
            self.theme = theme

        # Re-initialize colors with new theme
        if self.stdscr:
            self._init_colors()
            self.state.push_log("info", f"Theme set to: {self.theme}")

    def toggle_theme(self):
        """Toggle between dark and light themes."""
        if self._theme_auto:
            # First toggle: switch from auto to manual
            self._theme_auto = False
            self.theme = "light" if self.theme == "dark" else "dark"
        else:
            # Toggle between dark and light
            self.theme = "light" if self.theme == "dark" else "dark"

        # Re-initialize colors with new theme
        if self.stdscr:
            self._init_colors()
            self.state.push_log("info", f"Theme toggled to: {self.theme}")

    def _init_colors(self):
        """Initialize color pairs based on current theme."""
        # Select theme data
        theme_data = THEME_LIGHT if self.theme == "light" else THEME_DARK

        # Initialize all color pairs
        for name, pair_id in _C.items():
            fg, bg = theme_data.get(name, (curses.COLOR_WHITE, -1))
            curses.init_pair(pair_id, fg, bg)

    def setup(self, stdscr):
        """Initialize TUI with curses screen.
        
        Note: curses.start_color() and curses.use_default_colors() 
        should already be called by main.py before this.
        """
        self.stdscr = stdscr
        curses.curs_set(1)

        # Auto-detect theme on first run
        if self._theme_auto:
            self.theme = self._detect_background_brightness()

        # Initialize colors with detected/current theme
        self._init_colors()

        stdscr.nodelay(True)
        stdscr.keypad(True)
