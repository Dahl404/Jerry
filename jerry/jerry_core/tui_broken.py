#!/usr/bin/env python3
"""Jerry — qwen-code style single-feed TUI  ·  light terminal

Supports screen stream mode for watching Jerry control other terminals.
Enhanced with automatic light/dark theme detection and manual theme toggle.

Modular design using mixins for separation of concerns.
"""

import curses
from typing import List
from .models import State, LogEntry, ChatMsg, Todo
from .config import LOG_LIMIT
from jerry_core.faces_display import get_face_display
from .ui.constants import (
    _C, THEME_DARK, THEME_LIGHT, _SPINNERS, _THINK_PHRASES,
    _THINK_FEED, _STREAM_FEED, _BAR_FULL, _BAR_MED, _BAR_LOW, _BAR_EMPTY,
    _TYPE_FRAMES, _TYPE_PAUSE, _ERASE_FRAMES,
)
from .ui.feed import FeedRenderer
from .ui.input import InputHandler
from .ui.themes import ThemeManager
from .ui.layout import LayoutManager
from .ui.render_loop import RenderCoordinator
from .ui.panels import PanelRenderer
from .ui.status import StatusBarRenderer
from .ui.screen_modes import ScreenModeRenderer

# Stream mode display buffer — pure UI state, not shared with agent
_current_screen = ""

def set_current_screen(text: str):
    """Set the current screen content (called by screen_stream callback)."""
    global _current_screen
    _current_screen = text


class TUI(FeedRenderer, InputHandler, ThemeManager, LayoutManager, 
          RenderCoordinator, PanelRenderer, StatusBarRenderer, ScreenModeRenderer):
    """Single-feed ncurses TUI  —  qwen-code aesthetic, light terminal.
    
    Mixins:
        FeedRenderer - Feed and todo rendering methods
        InputHandler - Keyboard input and command handling
        ThemeManager - Theme detection and switching
        LayoutManager - Screen layout calculation
        RenderCoordinator - Main render loop coordination
        PanelRenderer - Face panel and todo sidebar
        StatusBarRenderer - Status bar rendering
        ScreenModeRenderer - Normal and stream mode rendering
    """

    def __init__(self, state: State):
        self.state      = state
        self.scroll     = 0
        self.focus      = "feed"
        self.input_buf  = ""
        self.stdscr     = None
        self.log_scroll  = 0
        self.chat_scroll = 0
        self.frame      = 0
        self.ctx_tokens: int   = 0
        self.tps:        float = 0.0
        self._tp_phrase_idx:  int = 0
        self._tp_char_count:  int = 0
        self._tp_phase:       int = 0
        self._tp_pause_cnt:   int = 0
        self.theme:      str   = "dark"  # Current theme: "dark" or "light"
        self._theme_auto: bool  = True   # Auto-detect theme flag
        self.face_display = get_face_display()  # Face display manager
        self.face_lines_cache: List[str] = []  # Cached face lines
        self.last_emotion_check: int = 0  # Frame counter for emotion parsing
        self.face_enabled: bool = False  # Face panel visibility toggle (default off for small terminals)
        self.chat_threshold: int = 5  # Switch to full feed at this height (default: 5 rows)

    def setup(self, stdscr):
        """Initialize TUI with curses screen."""
        # Call ThemeManager's setup which handles colors and theme
        ThemeManager.setup(self, stdscr)

    def enable_stream_mode(self, target_session: str):
        """Enable screen stream mode - shows target terminal screen."""
        # State is the single source of truth for stream mode.
        self.state.enable_stream_mode(target_session)

    def disable_stream_mode(self):
        """Disable screen stream mode."""
        self.state.disable_stream_mode()

    def update_screen(self, screen_text: str):
        """Update the displayed screen (called from stream capture)."""
        global _current_screen
        _current_screen = screen_text

    # ── Public helpers ────────────────────────────────────────────────────────

    def update_tokens(self, ctx: int, tps: float = 0.0) -> None:
        """Call this from your agent loop whenever token counts change."""
        self.ctx_tokens = ctx
        self.tps        = tps

    def _think_phrase_display(self) -> str:
        """Get current thinking phrase with animation."""
        from .ui.constants import _THINK_PHRASES
        if not _THINK_PHRASES:
            return "thinking"
        # Cycle through phrases based on frame
        phrase_idx = (self.frame // 30) % len(_THINK_PHRASES)
        return _THINK_PHRASES[phrase_idx]

    def _advance_think_anim(self, status: str):
        """Advance thinking animation counters based on status."""
        from .ui.constants import _THINK_PHRASES, _TYPE_FRAMES, _TYPE_PAUSE
        if status.lower().strip().rstrip('…') == "thinking":
            # Advance phrase character counter
            self._tp_char_count += 1
            if self._tp_char_count >= _TYPE_FRAMES:
                self._tp_char_count = 0
                self._tp_phase += 1
                # Check if we should pause at end of phrase
                if self._tp_phase >= len(_THINK_PHRASES[0]) if _THINK_PHRASES else 0:
                    self._tp_pause_cnt += 1
                    if self._tp_pause_cnt >= _TYPE_PAUSE:
                        self._tp_phase = 0
                        self._tp_pause_cnt = 0
                        self._tp_phrase_idx = (self._tp_phrase_idx + 1) % len(_THINK_PHRASES) if _THINK_PHRASES else 0
        else:
            # Reset animation when not thinking
            self._tp_pause_cnt = 0

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _wrap(text: str, width: int) -> List[str]:
        """Wrap text to specified width."""
        import textwrap
        if width < 1:
            return [text[:1] or ""]
        return textwrap.wrap(text, width=width) or [""]
