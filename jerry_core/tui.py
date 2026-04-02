#!/usr/bin/env python3
"""Jerry — qwen-code style single-feed TUI  ·  light terminal

Supports screen stream mode for watching Jerry control other terminals.
Enhanced with automatic light/dark theme detection and manual theme toggle.
"""

import curses
import os
import re
import textwrap
import math
import time
import random
import unicodedata
from typing import List, Tuple, Optional, Dict
from datetime import datetime
from .models import State, LogEntry, ChatMsg, Todo
from .config import LOG_LIMIT
from .faces_display import get_face_display, parse_and_set_emotion, get_available_emotions

# Stream mode display buffer — pure UI state, not shared with agent
_current_screen = ""

def set_current_screen(text: str):
    """Set the current screen content (called by screen_stream callback)."""
    global _current_screen
    _current_screen = text

def render_face_panel(stdscr, y: int, x: int, width: int, height: int):
    """Render the face panel at the specified position."""
    try:
        from .faces_display import get_current_face_lines
        face_lines = get_current_face_lines()
        
        # Draw each line of the face
        for i, line in enumerate(face_lines[:height]):
            if y + i < curses.LINES:
                # Truncate line to fit width
                display_line = line[:width] if len(line) > width else line
                stdscr.addstr(y + i, x, display_line, curses.A_DIM)
    except Exception:
        pass  # Ignore face rendering errors

# ─────────────────────────────────────────────────────────────────────────────
#  Colour pairs  (0 = reserved by curses)
# ─────────────────────────────────────────────────────────────────────────────
_C = {
    "border":    1,
    "user_lbl":  2,
    "user_txt":  3,
    "jerry_lbl": 4,
    "jerry_txt": 5,
    "tool_hdr":  6,
    "tool_bdr":  7,
    "tool_txt":  8,
    "think":     9,
    "error":     10,
    "worker":    11,
    "info":      12,
    "stream":    13,
    "th":        14,
    "tm":        15,
    "tl":        16,
    "td":        17,
    "inp_pre":   18,
    "inp_txt":   19,
    "muted":     20,
    "ts":        21,
    "scroll":    22,
    "sep":       23,
    "stat_lo":   24,
    "stat_hi":   25,
    "bar_fill":  26,
    "bar_dim":   27,
    "ctx_col":   28,
    "tps_col":   29,
}

# ─────────────────────────────────────────────────────────────────────────────
#  Theme Definitions
# ─────────────────────────────────────────────────────────────────────────────

# Dark theme (default) - optimized for dark backgrounds
# Uses bright foreground colors that pop on dark backgrounds
THEME_DARK: Dict[str, Tuple[int, int]] = {
    "border":    (curses.COLOR_BLUE,    -1),
    "user_lbl":  (curses.COLOR_BLUE,    -1),
    "user_txt":  (curses.COLOR_WHITE,   -1),
    "jerry_lbl": (curses.COLOR_GREEN,   -1),
    "jerry_txt": (curses.COLOR_WHITE,   -1),
    "tool_hdr":  (curses.COLOR_MAGENTA, -1),
    "tool_bdr":  (curses.COLOR_MAGENTA, -1),
    "tool_txt":  (curses.COLOR_WHITE,   -1),
    "think":     (curses.COLOR_CYAN,    -1),
    "error":     (curses.COLOR_RED,     -1),
    "worker":    (curses.COLOR_MAGENTA, -1),
    "info":      (curses.COLOR_CYAN,    -1),
    "stream":    (curses.COLOR_GREEN,   -1),
    "th":        (curses.COLOR_RED,     -1),
    "tm":        (curses.COLOR_MAGENTA, -1),
    "tl":        (curses.COLOR_GREEN,   -1),
    "td":        (curses.COLOR_BLACK,   -1),
    "inp_pre":   (curses.COLOR_GREEN,   -1),
    "inp_txt":   (curses.COLOR_WHITE,   -1),
    "muted":     (curses.COLOR_BLACK,   -1),
    "ts":        (curses.COLOR_WHITE,   -1),
    "scroll":    (curses.COLOR_BLUE,    -1),
    "sep":       (curses.COLOR_BLUE,    -1),
    "stat_lo":   (curses.COLOR_WHITE,   -1),
    "stat_hi":   (curses.COLOR_GREEN,   -1),
    "bar_fill":  (curses.COLOR_BLUE,    -1),
    "bar_dim":   (curses.COLOR_WHITE,   -1),
    "ctx_col":   (curses.COLOR_CYAN,    -1),
    "tps_col":   (curses.COLOR_GREEN,   -1),
}

# Light theme - optimized for light backgrounds
# Uses dark foreground colors that are readable on light backgrounds
THEME_LIGHT: Dict[str, Tuple[int, int]] = {
    "border":    (curses.COLOR_BLUE,    -1),
    "user_lbl":  (curses.COLOR_BLUE,    -1),
    "user_txt":  (curses.COLOR_BLACK,   -1),
    "jerry_lbl": (curses.COLOR_GREEN,   -1),
    "jerry_txt": (curses.COLOR_BLACK,   -1),
    "tool_hdr":  (curses.COLOR_MAGENTA, -1),
    "tool_bdr":  (curses.COLOR_MAGENTA, -1),
    "tool_txt":  (curses.COLOR_BLACK,   -1),
    "think":     (curses.COLOR_BLUE,    -1),
    "error":     (curses.COLOR_RED,     -1),
    "worker":    (curses.COLOR_MAGENTA, -1),
    "info":      (curses.COLOR_CYAN,    -1),
    "stream":    (curses.COLOR_GREEN,   -1),
    "th":        (curses.COLOR_RED,     -1),
    "tm":        (curses.COLOR_MAGENTA, -1),
    "tl":        (curses.COLOR_GREEN,   -1),
    "td":        (curses.COLOR_BLACK,   -1),
    "inp_pre":   (curses.COLOR_GREEN,   -1),
    "inp_txt":   (curses.COLOR_BLACK,   -1),
    "muted":     (curses.COLOR_BLACK,   -1),
    "ts":        (curses.COLOR_BLACK,   -1),
    "scroll":    (curses.COLOR_BLUE,    -1),
    "sep":       (curses.COLOR_BLUE,    -1),
    "stat_lo":   (curses.COLOR_BLACK,   -1),
    "stat_hi":   (curses.COLOR_GREEN,   -1),
    "bar_fill":  (curses.COLOR_BLUE,    -1),
    "bar_dim":   (curses.COLOR_BLACK,   -1),
    "ctx_col":   (curses.COLOR_CYAN,    -1),
    "tps_col":   (curses.COLOR_GREEN,   -1),
}

# ─────────────────────────────────────────────────────────────────────────────
#  Animation constants
# ─────────────────────────────────────────────────────────────────────────────

# Spinner sequences per status (loop by frame)
_SPINNERS = {
    "idle":      "○",
    "thinking":  "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏",
    "running":   "⣀⣄⣆⣇⣧⣷⣿⣶⣴⣠",
    "streaming": "▏▎▍▌▋▊▉█▊▋▌▍▎▏",
    "working":   "◜◝◞◟",
    "error":     "✕",
}

# Cycling phrases typed out character-by-character when thinking
_THINK_PHRASES = [
    "trying to figure this out",
    "working through it",
    "doing my best here",
    "thinking really hard",
    "hope this works",
    "putting the pieces together",
    "doing the thing",
    "almost got it",
    "bear with me",
    "working on it",
    "giving it a shot",
    "doing my job",
    "trying my best",
    "hang in there",
]

# Animated glyphs for think entries in the feed (cycle per frame)
_THINK_FEED  = "◌◍◎●◉◎◍◌"
# Animated glyphs for stream entries in the feed
_STREAM_FEED = "∿〜∿〜"

# Loading bar characters: active fill / inactive fill
_BAR_FULL  = "█"
_BAR_MED   = "▓"
_BAR_LOW   = "▒"
_BAR_EMPTY = "░"

# Typing speed: advance one character every N frames (50 ms each → ~100 ms/char)
_TYPE_FRAMES = 2
# Pause at end of phrase before erasing (frames)
_TYPE_PAUSE  = 30
# Erase speed: remove one character every N frames
_ERASE_FRAMES = 1

class TUI:
    """Single-feed ncurses TUI  —  qwen-code aesthetic, light terminal."""

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
        self.face_enabled: bool = True  # Face panel visibility toggle
        self.chat_threshold: int = 15  # Switch to full feed at this height (default: 15)
        self._last_parsed_msg_idx: int = -1  # Track last message parsed for emotions

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

    # ── Theme Management ───────────────────────────────────────────────────────

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

    # ── Public helpers ────────────────────────────────────────────────────────

    def update_tokens(self, ctx: int, tps: float = 0.0) -> None:
        """Call this from your agent loop whenever token counts change."""
        self.ctx_tokens = ctx
        self.tps        = tps

    # ── Curses init ───────────────────────────────────────────────────────────

    def _init_colors(self):
        """Initialize color pairs based on current theme."""
        # Select theme data
        theme_data = THEME_LIGHT if self.theme == "light" else THEME_DARK
        
        # Initialize all color pairs
        for name, pair_id in _C.items():
            fg, bg = theme_data.get(name, (curses.COLOR_WHITE, -1))
            curses.init_pair(pair_id, fg, bg)

    def setup(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(1)  # Show cursor
        curses.start_color()
        curses.use_default_colors()
        
        # Basic curses setup
        curses.noecho()
        stdscr.keypad(True)

        # Auto-detect theme on first run
        if self._theme_auto:
            self.theme = self._detect_background_brightness()

        # Initialize colors with detected/current theme
        self._init_colors()

        stdscr.nodelay(True)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _layout(self):
        """
        Row allocation (H rows total):
          If face enabled:
            rows  0-face_h    face panel (proportional: ~50% of H) + todo sidebar
            rows  face_h-(H-5) chat feed (fills remaining space)
            row   H-4         status bar (1 row)
            rows  H-3 … H-1   input box (height = 3)
          If face disabled:
            rows  0-(H-5)     full chat feed (like original)
            row   H-4         status bar (1 row)
            rows  H-3 … H-1   input box (height = 3)
        """
        H, W = self.stdscr.getmaxyx()
        _, _, todos, _, _, _ = self.state.snapshot()
        
        # Status bar and input (always same position)
        status_y = H - 4
        input_y = H - 3
        
        if self.face_enabled:
            # Face panel: scale by width only, maintain aspect ratio
            # Face is 70% of terminal width, height scales proportionally
            # ASCII chars are ~2:1 (width:height), so 100x50 chars = ~1:1 visual
            face_w = max(20, int(W * 0.7))  # 70% of terminal width
            face_h = max(10, int(face_w * 0.5))  # 2:1 char aspect = 1:1 visual

            # Chat feed fills space between face and status bar
            # Available rows: from row face_h to row (H-5), inclusive
            chat_y = face_h  # Start right after face
            chat_h = H - 4 - face_h  # From face bottom to status bar top

            # Todo sidebar fills space between face and right edge
            # Only show if todos exist AND terminal is wider than face
            todo_w = 0
            if todos and W > face_w:
                todo_w = W - face_w  # Fill remaining space

            # Chat width is full terminal width
            chat_w = W

            return H, W, face_h, face_w, todo_w, chat_h, chat_w, status_y, input_y
        else:
            # Face disabled - use original full-height feed layout
            feed_h = H - 4  # Full height minus status/input
            feed_w = W
            todo_w = max(24, min(30, W // 5)) if todos else 0
            
            return H, W, 0, 0, todo_w, feed_h, feed_w, status_y, input_y

    # ── Full redraw ───────────────────────────────────────────────────────────

    def render(self, skip_erase: bool = False):
        """Render the screen.
        
        Args:
            skip_erase: If True, don't clear screen before rendering (for overlays)
        """
        try:
            H, W = self.stdscr.getmaxyx()
        except curses.error:
            return  # Terminal not ready

        # Minimum size check (relaxed for proportional face sizing)
        if self.face_enabled:
            if H < 20 or W < 30:
                self._draw_min_size_warning(H, W, "30x20")
                return
        else:
            if H < 20 or W < 40:
                self._draw_min_size_warning(H, W, "40x20")
                return

        # Clear screen and draw (unless skipping for overlay transitions)
        if not skip_erase:
            self.stdscr.erase()

        if self.state.is_stream_mode():
            self._draw_stream_screen(H, W)
        else:
            self._draw_normal_mode(H, W)

        # Refresh screen
        self.stdscr.refresh()

        self.frame += 1

        # Update face transition (diffusion animation)
        if self.face_enabled and hasattr(self.face_display, 'update_transition'):
            self.face_display.update_transition(0.03)  # 3% per frame

        # Parse emotion tags from complete messages
        # Live streaming emotion parsing happens in agent.py during token generation
        if self.face_enabled:
            self._parse_recent_emotions()
    
    def _draw_min_size_warning(self, H: int, W: int, required: str):
        """Draw minimum terminal size warning."""
        try:
            self.stdscr.erase()
            self.stdscr.addstr(4, 0, f"Terminal too small! Need {required}, have {W}x{H}".center(W)[:W])
            self.stdscr.addstr(6, 0, "Please resize your terminal window.".center(W)[:W])
            self.stdscr.addstr(8, 0, f"Or use: /face hide".center(W)[:W])
            self.stdscr.refresh()
        except curses.error:
            pass
    
    def _check_state_changed(self, snapshot) -> bool:
        """Check if state has changed since last render."""
        if self._last_state_snapshot is None:
            return True
        
        log, chat, todos, status, wfile, expression = snapshot
        prev_log, prev_chat, prev_todos, prev_status, prev_wfile, prev_expr = self._last_state_snapshot
        
        # Check for changes
        if len(chat) != len(prev_chat):
            return True
        if len(log) != len(prev_log):
            return True
        if status != prev_status:
            return True
        if len(todos) != len(prev_todos):
            return True
        if wfile != prev_wfile:
            return True
        
        # Check last few chat messages for streaming changes
        if chat and prev_chat:
            last_msg = chat[-1].text if chat else ""
            prev_last_msg = prev_chat[-1].text if prev_chat else ""
            if last_msg != prev_last_msg:
                return True
        
        return False
    
    def _check_face_changed(self, snapshot) -> bool:
        """Check if face panel needs redrawing."""
        if not self.face_enabled:
            return False
        
        current_emotion = self.face_display.current_emotion
        if current_emotion != self._face_last_emotion:
            self._face_last_emotion = current_emotion
            self._face_dirty = True
            return True
        
        return self._face_dirty
    
    def _check_feed_changed(self, snapshot) -> bool:
        """Check if feed panel needs redrawing."""
        log, chat, todos, status, wfile, expression = snapshot
        
        if self._last_state_snapshot is None:
            self._feed_dirty = True
            return True
        
        prev_log, prev_chat, prev_todos, prev_status, prev_wfile, prev_expr = self._last_state_snapshot
        
        # Check for new messages or log entries
        if len(chat) != len(prev_chat):
            self._feed_dirty = True
            return True
        if len(log) != len(prev_log):
            self._feed_dirty = True
            return True
        if len(todos) != len(prev_todos):
            self._feed_dirty = True
            return True
        
        # Check for streaming message updates
        if chat and prev_chat:
            last_msg = chat[-1].text if chat else ""
            prev_last_msg = prev_chat[-1].text if prev_chat else ""
            if last_msg != prev_last_msg:
                self._feed_dirty = True
                return True
        
        return self._feed_dirty
    
    def _check_status_changed(self, snapshot) -> bool:
        """Check if status bar needs redrawing."""
        log, chat, todos, status, wfile, expression = snapshot
        
        if self._last_state_snapshot is None:
            self._status_dirty = True
            return True
        
        prev_log, prev_chat, prev_todos, prev_status, prev_wfile, prev_expr = self._last_state_snapshot
        
        # Status changes frequently (spinner animation), so always mark as dirty
        # But we'll optimize the drawing to only update changed parts
        self._status_dirty = True
        return True
    
    def _snapshot_for_comparison(self, snapshot):
        """Create a snapshot for state comparison."""
        log, chat, todos, status, wfile, expression = snapshot
        # Return copies to avoid reference issues
        return (log[:], chat[:], todos[:], status, wfile, expression)
    
    def _draw_normal_mode_to_window(self, win, H: int, W: int, snapshot, face_changed: bool, feed_changed: bool, status_changed: bool):
        """Draw normal mode to specified window with selective redrawing.
        
        Args:
            win: Window to draw to (can be off-screen buffer)
            H, W: Screen dimensions
            snapshot: State snapshot (log, chat, todos, status, wfile, expression)
            face_changed: Whether face panel needs redrawing
            feed_changed: Whether feed panel needs redrawing
            status_changed: Whether status bar needs redrawing
        """
        log, chat, todos, status, wfile, expression = snapshot
        _, _, face_h, face_w, todo_w, chat_h, chat_w, status_y, input_y = self._layout()
        
        self._advance_think_anim(status)
        
        if self.face_enabled:
            # Draw face panel only if changed (optimization)
            if face_changed:
                self._draw_face_panel_to_window(win, y=0, x=0, h=face_h, w=face_w)
                self._face_dirty = False  # Reset dirty flag after drawing
            
            # Draw todo sidebar beside face
            if todos and todo_w > 0:
                todo_x = face_w
                self._draw_todo_vertical_to_window(win, todos, y=0, x=todo_x, h=face_h, w=todo_w)
            
            # Draw chat feed below face
            chat_y = face_h
            chat_visible_rows = chat_h - 2
            
            if chat_visible_rows >= self.chat_threshold:
                self._draw_feed_to_window(win, log, chat, y=chat_y, x=0, h=chat_h, w=chat_w)
            else:
                self._draw_chat_feed_to_window(win, log, chat, y=chat_y, x=0, h=chat_h, w=chat_w)
        else:
            # Face disabled - draw full feed
            feed_y = 0
            feed_h = H - 4
            feed_w = W
            
            if todos and todo_w > 0:
                feed_w = W - todo_w
                todo_x = W - todo_w
                self._draw_todo_to_window(win, todos, y=feed_y, x=todo_x, h=feed_h, w=todo_w)
            
            self._draw_feed_to_window(win, log, chat, y=feed_y, x=0, h=feed_h, w=feed_w)
        
        # Draw status bar and input (always redraw for animations)
        self._draw_status_bar_to_window(win, status_y, W, status, wfile, expression)
        self._draw_input_to_window(win, y=input_y, x=0, h=3, w=W)
    
    def _draw_stream_screen_to_window(self, win, H: int, W: int, snapshot):
        """Draw stream mode to specified window.
        
        Args:
            win: Window to draw to (can be off-screen buffer)
            H, W: Screen dimensions
            snapshot: State snapshot
        """
        log, chat, todos, status, wfile, expression = snapshot
        target_session = self.state.get_stream_session() or "unknown"
        
        header_row = 0
        status_row = H - 4
        input_start = H - 3
        min_chat_h = 5
        screen_end = H - input_start - min_chat_h
        
        # Draw header
        header = f" 📺 Streaming: {target_session}  |  Press 'q' to exit  |  {datetime.now().strftime('%H:%M:%S')} "
        try:
            win.addstr(header_row, 0, header.center(W)[:W], curses.color_pair(1) | curses.A_BOLD)
        except curses.error:
            pass
        
        # Draw captured screen
        if _current_screen and len(_current_screen) > 50 and not _current_screen.startswith("ERROR"):
            clean_screen = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', _current_screen)
            lines = clean_screen.split('\n')
            for i, line in enumerate(lines[:screen_end]):
                try:
                    win.addstr(i + 1, 0, line[:W].ljust(W), curses.color_pair(5))
                except curses.error:
                    pass
        else:
            try:
                mid_row = screen_end // 2
                win.addstr(mid_row, 0, "⏳ Waiting for terminal screen...".center(W)[:W], curses.color_pair(6))
                win.addstr(mid_row + 2, 0, f"Target session: {target_session}".center(W)[:W], curses.color_pair(6))
                win.addstr(mid_row + 4, 0, "Make sure tmux session exists and has content".center(W)[:W], curses.color_pair(6))
            except curses.error:
                pass
        
        # Draw chat feed
        chat_y = screen_end + 1
        chat_h = input_start - chat_y
        if chat_h >= 5:
            chat_visible_rows = chat_h - 2
            if chat_visible_rows >= self.chat_threshold:
                self._draw_feed_to_window(win, log, chat, y=chat_y, x=0, h=chat_h, w=W)
            else:
                self._draw_chat_feed_to_window(win, log, chat, y=chat_y, x=0, h=chat_h, w=W)
        
        # Draw status bar and input
        self._draw_status_bar_to_window(win, status_row, W, status, wfile, expression)
        self._draw_input_to_window(win, y=input_start, x=0, h=3, w=W)

    def _parse_recent_emotions(self):
        """Parse emotion tags from NEW chat messages and update face display.

        Only processes messages that haven't been parsed yet, finding the most
        recent emotion tag to keep the face display stable and persistent.
        """
        import re

        chat = self.state.chat[:]

        # Find the last Jerry message we haven't parsed yet
        last_jerry_idx = -1
        last_emotion_found = None

        # Scan through messages starting after our last parsed position
        start_idx = max(0, self._last_parsed_msg_idx + 1)
        for i in range(start_idx, len(chat)):
            msg = chat[i]
            if msg.role == "jerry" and msg.text:
                # Track this as the latest Jerry message
                last_jerry_idx = i

                # Find all emotion tags in this message
                tags = re.findall(r'<(\w+)>', msg.text.lower())
                if tags:
                    # Use the LAST emotion tag in this message
                    # (in case of multiple tags, the last one is most current)
                    last_emotion_found = tags[-1]

        # If we found a new emotion, update the face display
        if last_emotion_found:
            # Validate it's a known emotion (check both old and new face systems)
            from .faces_display import EMOTION_MAP
            if last_emotion_found in EMOTION_MAP or last_emotion_found in self.face_display.colored_faces or last_emotion_found in self.face_display.faces:
                self.face_display.set_emotion(last_emotion_found)

        # Update our tracking to the last Jerry message we processed
        # (even if no emotion was found, we've checked this message)
        if last_jerry_idx >= 0:
            self._last_parsed_msg_idx = last_jerry_idx

    def _draw_stream_screen(self, H: int, W: int):
        """Draw captured terminal screen in stream mode with dynamic chat area."""
        global _current_screen

        # Read session name from state (sole source of truth)
        target_session = self.state.get_stream_session() or "unknown"

        # Layout:
        # Row 0: Header
        # Row 1 to (H-7): Captured screen (dynamic height)
        # Row (H-6) to (H-2): Chat feed (fills remaining space, min 5 rows)
        # Row H-1: Status bar
        # Row H: Input bar
        
        # Calculate dynamic areas
        header_row = 0
        status_row = H - 4
        input_start = H - 3
        
        # Screen area: from row 1 to where chat starts
        # Chat needs at least 5 rows (3 visible + 2 borders)
        min_chat_h = 5
        screen_end = H - input_start - min_chat_h  # Leave room for chat + status + input
        
        # Draw header
        header = f" 📺 Streaming: {target_session}  |  Press 'q' to exit  |  {datetime.now().strftime('%H:%M:%S')} "
        try:
            self.stdscr.addstr(header_row, 0, header.center(W)[:W], curses.color_pair(1) | curses.A_BOLD)
        except:
            pass

        # Draw captured screen (or placeholder if empty)
        if _current_screen and len(_current_screen) > 50 and not _current_screen.startswith("ERROR"):
            # Strip ANSI escape codes from captured screen
            clean_screen = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', _current_screen)

            lines = clean_screen.split('\n')
            # Draw as many lines as fit in screen area
            for i, line in enumerate(lines[:screen_end]):
                try:
                    self.stdscr.addstr(i + 1, 0, line[:W].ljust(W), curses.color_pair(5))
                except:
                    pass
        else:
            # Show placeholder when no screen content yet
            try:
                mid_row = screen_end // 2
                self.stdscr.addstr(mid_row, 0, "⏳ Waiting for terminal screen...".center(W)[:W], curses.color_pair(6))
                self.stdscr.addstr(mid_row + 2, 0, f"Target session: {target_session}".center(W)[:W], curses.color_pair(6))
                self.stdscr.addstr(mid_row + 4, 0, "Make sure tmux session exists and has content".center(W)[:W], curses.color_pair(6))
            except:
                pass

        # Draw chat feed in remaining space (dynamic height)
        chat_y = screen_end + 1
        chat_h = input_start - chat_y

        if chat_h >= 5:  # Only draw if we have enough space
            log, chat, todos, status, wfile, expression = self.state.snapshot()

            # Use full feed or compact based on height
            chat_visible_rows = chat_h - 2  # Minus borders
            if chat_visible_rows >= self.chat_threshold:
                self._draw_feed(log, chat, y=chat_y, x=0, h=chat_h, w=W)
            else:
                self._draw_chat_feed(log, chat, y=chat_y, x=0, h=chat_h, w=W)

        # Draw status bar
        log, chat, todos, status, wfile, expression = self.state.snapshot()
        self._draw_status_bar(status_row, W, status, wfile, expression)

        # Draw input bar
        self._draw_input(y=input_start, x=0, h=3, w=W)

    def _draw_ai_speech(self, y: int, W: int):
        """Draw AI's last speech output (non-command responses)."""
        # Get last chat message from jerry
        chat = self.state.chat[:]
        last_jerry_msg = ""
        for msg in reversed(chat):
            if msg.role == "jerry" and msg.text.strip():
                last_jerry_msg = msg.text
                break

        if last_jerry_msg:
            # Truncate to fit one line
            truncated = last_jerry_msg[:W-4].replace('\n', ' ')
            try:
                self.stdscr.addstr(y, 0, f" ◦ {truncated}".ljust(W)[:W],
                                   curses.color_pair(4) | curses.A_DIM)
            except:
                pass

    def _draw_normal_mode(self, H: int, W: int):
        """Draw normal mode with optional face panel and chat feed."""
        _, _, face_h, face_w, todo_w, chat_h, chat_w, status_y, input_y = self._layout()
        log, chat, todos, status, wfile, expression = self.state.snapshot()

        self._advance_think_anim(status)

        if self.face_enabled:
            # Draw face panel at top-left (rows 0-49, 100 chars wide)
            self._draw_face_panel(y=0, x=0, h=face_h, w=face_w)

            # Draw todo sidebar beside face (fills remaining space to the right)
            if todos and todo_w > 0:
                todo_x = face_w  # Right next to face panel
                self._draw_todo_vertical(todos, y=0, x=todo_x, h=face_h, w=todo_w)

            # Draw chat feed below face - choose style based on height
            chat_y = face_h
            chat_visible_rows = chat_h - 2  # Minus borders (consistent with draw methods)

            if chat_visible_rows >= self.chat_threshold:
                # Full screen mode - show full debug feed with all logs, tools, etc.
                self._draw_feed(log, chat, y=chat_y, x=0, h=chat_h, w=chat_w)
            else:
                # Minimized mode (keyboard onscreen) - show compact view with chat + recent logs
                self._draw_chat_feed(log, chat, y=chat_y, x=0, h=chat_h, w=chat_w)
        else:
            # Face disabled - draw full feed like original
            feed_y = 0
            feed_h = H - 4  # Full height minus status/input
            feed_w = W

            # Draw todo sidebar if enabled
            if todos and todo_w > 0:
                feed_w = W - todo_w
                todo_x = W - todo_w
                self._draw_todo(todos, y=feed_y, x=todo_x, h=feed_h, w=todo_w)

            # Draw full feed
            self._draw_feed(log, chat, y=feed_y, x=0, h=feed_h, w=feed_w)

        # Draw status bar and input (always same position)
        self._draw_status_bar(status_y, W, status, wfile, expression)
        
        # Draw question panel if there's a pending question (overlay on top)
        question = self.state.get_pending_question()
        if question and question.get("active"):
            self._draw_question_panel(input_y, W, question)
        
        self._draw_input(y=input_y, x=0, h=3, w=W)

    def _draw_face_panel(self, y: int, x: int, h: int, w: int):
        """Draw face panel - diffuses in from edges"""
        try:
            face_lines, color_grid = self.face_display.get_colored_face(w - 2, h - 2)
            
            if not face_lines:
                return
            
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            emotion = self.face_display.current_face.capitalize()

            # Top border
            try:
                top_border = "╭" + "─" * (w - 2) + "╮"
                self.stdscr.addstr(y, x, top_border[:w], battr)
                label = f"◦ {emotion} "
                self.stdscr.addstr(y, x + 2, label, battr | curses.A_BOLD)
            except curses.error:
                pass

            # Initialize revealed set for edge diffusion
            if not hasattr(self, '_face_revealed'):
                self._face_revealed = set()
                self._face_last_update = time.time()
            
            face_h = len(face_lines)
            face_w = len(face_lines[0]) if face_lines else 0
            total = face_h * face_w
            
            # Update revealed positions (diffuse from edges)
            current_time = time.time()
            if current_time - self._face_last_update > 0.02:  # 20ms = 50 FPS
                self._face_last_update = current_time
                target_revealed = min(len(self._face_revealed) + max(5, int(total * 0.03)), total)
                
                while len(self._face_revealed) < target_revealed:
                    # 70% bias towards edges
                    if random.random() < 0.7 and len(self._face_revealed) < total * 0.5:
                        if random.random() < 0.5:
                            row = random.randint(0, face_h - 1)
                            col = random.choice([0, face_w - 1])
                        else:
                            row = random.choice([0, face_h - 1])
                            col = random.randint(0, face_w - 1)
                    else:
                        row = random.randint(0, face_h - 1)
                        col = random.randint(0, face_w - 1)
                    self._face_revealed.add((row, col))
            
            # Reset revealed set when face changes
            if not hasattr(self, '_face_last_face') or self._face_last_face != self.face_display.current_face:
                self._face_revealed = set()
                self._face_last_face = self.face_display.current_face
            
            # Initialize color pairs
            if not hasattr(self, '_face_color_map'):
                self._face_color_map = {}
                self._face_next_pair = 100
            
            # Draw particles
            for i, line in enumerate(face_lines):
                row = y + i + 1
                if row >= y + h - 1:
                    break
                try:
                    self.stdscr.addstr(row, x, "│", battr)
                    self.stdscr.addstr(row, x + w - 1, "│", battr)
                    
                    colors = color_grid[i] if i < len(color_grid) else []
                    for col, char in enumerate(line[:w-2]):
                        if char != ' ' and (i, col) in self._face_revealed:
                            color_hex = colors[col] if col < len(colors) else 'FFFFFF'
                            
                            if color_hex not in self._face_color_map and self._face_next_pair < 255:
                                try:
                                    r = int(color_hex[0:2], 16)
                                    g = int(color_hex[2:4], 16)
                                    b = int(color_hex[4:6], 16)
                                    curses.init_color(self._face_next_pair, r*1000//255, g*1000//255, b*1000//255)
                                    curses.init_pair(self._face_next_pair, self._face_next_pair, -1)
                                    self._face_color_map[color_hex] = self._face_next_pair
                                    self._face_next_pair += 1
                                except:
                                    self._face_color_map[color_hex] = _C["jerry_txt"]
                            
                            attr = curses.color_pair(self._face_color_map[color_hex])
                            self.stdscr.addch(row, x + 1 + col, char, attr)
                except curses.error:
                    pass

            # Bottom border
            try:
                bottom_border = "╰" + "─" * (w - 2) + "╯"
                self.stdscr.addstr(y + h - 1, x, bottom_border[:w], battr)
            except curses.error:
                pass
        except Exception:
            pass

    def _draw_question_panel(self, y: int, W: int, question: Dict):
        """Draw question panel with scrollable options and custom answer input."""
        try:
            q_text = str(question.get("question", "?"))
            options = question.get("options", [])
            selected = question.get("selected", 0)
            selected_indices = question.get("selected_indices") or set()
            
            # Ensure options is a list
            if not isinstance(options, list):
                options = []
            
            # Fixed panel size - always same dimensions
            panel_h = 11  # Fixed height (includes input row)
            panel_w = min(70, W - 4)
            panel_x = (W - panel_w) // 2
            panel_y = y - panel_h  # Position directly above input bar
            
            if panel_y < 1:
                panel_y = 1
            
            battr = curses.color_pair(_C["border"]) | curses.A_BOLD
            selattr = curses.color_pair(_C["tool_hdr"]) | curses.A_BOLD  # Currently highlighted
            normattr = curses.color_pair(_C["jerry_txt"])
            mutedattr = curses.color_pair(_C["muted"])
            checkattr = curses.color_pair(_C["tool_txt"]) | curses.A_BOLD  # Selected (checked)
            bgattr = curses.color_pair(_C["border"])  # Background fill
            
            # Draw border
            self.stdscr.addstr(panel_y, panel_x, "╭" + "─" * (panel_w - 2) + "╮", battr)
            for i in range(1, panel_h - 1):
                self.stdscr.addstr(panel_y + i, panel_x, "│", battr)
                self.stdscr.addstr(panel_y + i, panel_x + panel_w - 1, "│", battr)
            self.stdscr.addstr(panel_y + panel_h - 1, panel_x, "╰" + "─" * (panel_w - 2) + "╯", battr)
            
            # Fill panel background to prevent bleed-through
            for i in range(1, panel_h - 1):
                self.stdscr.addstr(panel_y + i, panel_x + 1, " " * (panel_w - 2), bgattr)
            
            # Draw question title (scroll if too long)
            title = f" ❓ {q_text}"
            if len(title) > panel_w - 4:
                title = title[:panel_w - 7] + "..."
            self.stdscr.addstr(panel_y + 1, panel_x + 2, title[:panel_w-4], selattr | curses.A_BOLD)
            
            # Options area: rows 3 to panel_h-3 (leaving room for custom option + input)
            # Row 2 = instruction, Rows 3-6 = options (4 visible), Row 7 = custom, Row 8 = input
            options_start_row = panel_y + 3
            options_end_row = panel_y + panel_h - 4  # Row before custom
            visible_rows = options_end_row - options_start_row  # 4 rows
            
            # Calculate scroll offset to keep selected item visible
            scroll_offset = 0
            if selected >= visible_rows:
                scroll_offset = selected - visible_rows + 1
            
            # Draw instruction
            self.stdscr.addstr(panel_y + 2, panel_x + 2, "↑↓ scroll, Space select, Enter confirm:", normattr)
            
            # Draw options with scrolling
            for visible_idx in range(visible_rows):
                actual_idx = scroll_offset + visible_idx
                if actual_idx >= len(options):
                    break
                
                row = options_start_row + visible_idx
                
                # Determine marker and color based on state
                is_selected = actual_idx in selected_indices  # Checked with Space
                is_highlighted = actual_idx == selected  # Current cursor position
                
                if is_selected and is_highlighted:
                    marker = "◉"  # Both selected and highlighted
                    attr = checkattr  # Selected color takes priority
                elif is_selected:
                    marker = "✓"  # Selected only
                    attr = checkattr
                elif is_highlighted:
                    marker = "●"  # Highlighted only
                    attr = selattr
                else:
                    marker = "○"  # Neither
                    attr = normattr
                
                opt_text = f"  {marker} {str(options[actual_idx])[:panel_w-12]}"
                self.stdscr.addstr(row, panel_x + 2, opt_text[:panel_w-4], attr)
            
            # Draw custom answer option (always visible at bottom)
            custom_row = panel_y + panel_h - 3
            is_custom_selected = selected >= len(options)
            custom_marker = "●" if is_custom_selected else "○"
            custom_text = f"  {custom_marker} ── Type custom answer below ──"
            custom_attr = selattr if is_custom_selected else mutedattr
            self.stdscr.addstr(custom_row, panel_x + 2, custom_text[:panel_w-4], custom_attr)
            
            # Draw input buffer INSIDE panel (for custom answer)
            input_row = panel_y + panel_h - 2
            prompt = "Answer: "
            avail = panel_w - len(prompt) - 4
            disp = (self.input_buf[-avail:]
                    if len(self.input_buf) > avail else self.input_buf)
            self.stdscr.addstr(input_row, panel_x + 2, prompt,
                              curses.color_pair(_C["inp_pre"]) | curses.A_BOLD)
            self.stdscr.addstr(input_row, panel_x + 2 + len(prompt), disp,
                              curses.color_pair(_C["inp_txt"]))
            
        except Exception as e:
            # Silently fail - don't crash UI
            pass

    def _draw_todo_vertical(self, todos: List[Todo], y: int, x: int, h: int, w: int):
        """Draw todo panel vertically beside face panel.
        
        Args:
            y: Starting row
            x: Starting column
            h: Height (50 rows to match face)
            w: Width (fills remaining space to right edge)
        """
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            title = "plan"
            pad = max(0, w - len(title) - 5)
            
            # Top border
            try:
                self.stdscr.addstr(y, x, f"╭─ {title} {'─'*pad}╮"[:w], battr)
            except curses.error:
                pass
            
            # Side borders
            for r in range(y + 1, y + h - 1):
                try:
                    self.stdscr.addstr(r, x, "│", battr)
                    self.stdscr.addstr(r, x + w - 1, "│", battr)
                except curses.error:
                    pass
            
            # Bottom border
            try:
                self.stdscr.addstr(y + h - 1, x, ("╰" + "─"*(w-2) + "╯")[:w], battr)
            except curses.error:
                pass

            # Priority colors
            _PRI = {
                "high":   (_C["th"], "●", curses.A_BOLD),
                "medium": (_C["tm"], "◐", 0),
                "low":    (_C["tl"], "○", curses.A_DIM),
            }
            
            iw = max(1, w - 3)
            row = y + 1
            
            for t in todos:
                if row >= y + h - 1:
                    break
                if t.done:
                    cp, glyph, xa = _C["td"], "✓", curses.A_DIM
                else:
                    cp, glyph, xa = _PRI.get(t.priority, (_C["tm"], "◐", 0))
                
                text = f" {glyph} {t.text}"
                if len(text) > iw:
                    text = text[:iw-1] + "…"
                
                try:
                    self.stdscr.addstr(row, x + 1,
                                       text.ljust(iw)[:iw],
                                       curses.color_pair(cp) | xa)
                except curses.error:
                    pass
                row += 1
        except Exception:
            pass

    def _draw_chat_feed(self, log: List[LogEntry], chat: List[ChatMsg],
                        y: int, x: int, h: int, w: int):
        """Draw chat feed with dynamic height and scrolling - compact view (chat only)."""
        battr = curses.color_pair(_C["border"]) | curses.A_DIM
        try:
            # Top border
            self.stdscr.addstr(y, x, ("╭" + "─" * (w - 2) + "╮")[:w], battr)
            # Bottom border
            self.stdscr.addstr(y + h - 1, x, ("╰" + "─" * (w - 2) + "╯")[:w], battr)
            # Side borders
            for r in range(y + 1, y + h - 1):
                self.stdscr.addstr(r, x, "│", battr)
                self.stdscr.addstr(r, x + w - 1, "│", battr)
        except curses.error:
            pass

        iw = max(4, w - 4)
        ih = h - 2  # Visible lines (minus borders)

        # Build list of all chat lines
        all_lines = []
        for msg in chat:
            role_label = "you: " if msg.role == "user" else "jerry: "
            wrapped = textwrap.wrap(msg.text, width=iw - len(role_label)) or [""]

            # Only add role label to first line of each message
            for i, chunk in enumerate(wrapped):
                if i == 0:
                    all_lines.append((msg.role, role_label + chunk, True))
                else:
                    all_lines.append((msg.role, "     " + chunk, False))

        # Handle scrolling
        total = len(all_lines)
        self.chat_scroll = min(self.chat_scroll, max(0, total - ih))
        start = max(0, total - ih - self.chat_scroll)

        # Draw visible chat lines
        for i in range(ih):
            line_idx = start + i
            if line_idx >= total:
                break

            role, text, is_first_line = all_lines[line_idx]

            cp = _C["user_txt"] if role == "user" else _C["jerry_txt"]
            lbl = _C["user_lbl"] if role == "user" else _C["jerry_lbl"]

            try:
                if is_first_line:
                    # First line - show role label in bold
                    if role == "user":
                        self.stdscr.addstr(y + 1 + i, x + 2, "you: ",
                                           curses.color_pair(lbl) | curses.A_BOLD)
                        self.stdscr.addstr(y + 1 + i, x + 7, text[5:][:iw-7],
                                           curses.color_pair(cp))
                    else:
                        self.stdscr.addstr(y + 1 + i, x + 2, "jerry: ",
                                           curses.color_pair(lbl) | curses.A_BOLD)
                        self.stdscr.addstr(y + 1 + i, x + 9, text[7:][:iw-9],
                                           curses.color_pair(cp))
                else:
                    # Continuation line - just draw text
                    self.stdscr.addstr(y + 1 + i, x + 2, text[:iw-2],
                                       curses.color_pair(cp))
            except curses.error:
                pass

    # ── Status bar ────────────────────────────────────────────────────────────

    def _draw_status_bar(self, y: int, W: int, status: str,
                          wfile: Optional[str], expression: str):
        """The info row sandwiched between feed and input."""
        # Normalize status - strip trailing ellipsis and special chars for matching
        slug = status.lower().strip().rstrip('…').rstrip('.')

        # ── spinner ──
        seq       = _SPINNERS.get(slug, "·")
        spin_char = seq[self.frame % len(seq)]

        # ── left section: spinner + label or animated phrase ──
        if slug == "thinking":
            phrase = self._think_phrase_display()
            left   = f"  {spin_char}  {phrase}"
        else:
            left   = f"  {spin_char}  {slug}"

        # ── loading bar (12 chars) ──
        bar = self._loading_bar(12, slug)

        # ── right section: expr · file · ⟨ctx⟩ · tps · time · theme ──
        segs: List[str] = []
        if expression:
            segs.append(f"✦ {expression}")
        segs.append(f"◈ {os.path.basename(wfile)}" if wfile else "◈ jerry")
        if self.ctx_tokens:
            segs.append(f"⟨{self._fmt_tokens(self.ctx_tokens)}⟩")
        if self.tps > 0.5:
            segs.append(f"{self.tps:.0f} t/s")
        # Theme indicator
        segs.append(f"🎨 {self.theme}")
        segs.append(datetime.now().strftime("%H:%M"))
        right = "  ·  ".join(segs) + "  "

        bar_block = f"  {bar}  "

        # ── assemble, pad between left and bar ──
        gap  = max(1, W - len(left) - len(bar_block) - len(right))
        row  = (left + " " * gap + bar_block + right)[:W]

        dim_a  = curses.color_pair(_C["stat_lo"]) | curses.A_DIM
        hi_a   = curses.color_pair(_C["stat_hi"]) | curses.A_BOLD
        bar_a  = curses.color_pair(_C["bar_fill"]) | curses.A_DIM
        ctx_a  = curses.color_pair(_C["ctx_col"])  | curses.A_DIM
        tps_a  = curses.color_pair(_C["tps_col"])  | curses.A_DIM

        try:
            self.stdscr.addstr(y, 0, row.ljust(W)[:W], dim_a)
            # Re-paint spinner bright
            if 2 < W:
                self.stdscr.addstr(y, 2, spin_char, hi_a)
            # Re-paint loading bar
            bar_x = len(left) + gap + 2
            if 0 <= bar_x < W:
                self.stdscr.addstr(y, bar_x, bar[:W - bar_x], bar_a)
            # Re-paint ctx token count using proper column calculation
            if self.ctx_tokens:
                tok_str = f"⟨{self._fmt_tokens(self.ctx_tokens)}⟩"
                tok_x = self._col_of_substr(row, tok_str)
                if 0 <= tok_x < W:
                    self.stdscr.addstr(y, tok_x, self._clip_to_cols(tok_str, W - tok_x), ctx_a)
            # Re-paint tps using proper column calculation
            if self.tps > 0.5:
                tps_str = f"{self.tps:.0f} t/s"
                tps_x = self._col_of_substr(row, tps_str)
                if 0 <= tps_x < W:
                    self.stdscr.addstr(y, tps_x, self._clip_to_cols(tps_str, W - tps_x), tps_a)
        except curses.error:
            pass

    # ── Loading bar ───────────────────────────────────────────────────────────

    def _loading_bar(self, width: int, status: str) -> str:
        """Animated loading bar with three states:
        - idle/ready: solid bar (no animation)
        - thinking: whole bar pulses (brightness change)
        - streaming: fade bounces back and forth
        - tool execution (→): fade bounces back and forth
        """
        # Normalize status
        status_lower = status.lower().strip()

        # IDLE: solid bar when ready, idle, or no status
        if status_lower in ("idle", "ready", ""):
            return _BAR_FULL * width

        # THINKING: whole bar pulses when processing prompt
        elif status_lower in ("thinking…", "thinking"):
            # Smooth pulse using sine wave
            pulse = (math.sin(self.frame * 0.3) + 1) / 2  # 0 to 1
            if pulse > 0.6:
                return _BAR_FULL * width
            elif pulse > 0.3:
                return _BAR_MED * width
            else:
                return _BAR_LOW * width

        # STREAMING: fade bounces back and forth during output
        elif status_lower == "streaming":
            # Bounce position (0 to width-1 and back)
            cycle = (self.frame * 2) % (width * 2 - 2)
            pos = cycle if cycle < width else (width * 2 - 2 - cycle)
            
            bar = []
            for i in range(width):
                dist = abs(i - pos)
                if dist == 0:
                    bar.append(_BAR_FULL)
                elif dist == 1:
                    bar.append(_BAR_MED)
                elif dist == 2:
                    bar.append(_BAR_LOW)
                elif dist == 3:
                    bar.append(_BAR_EMPTY)
                else:
                    bar.append(" ")
            return "".join(bar)

        # TOOL EXECUTION: fade bounces back and forth (→ execute_command)
        elif status_lower.startswith("→") or status_lower.startswith("->") or \
             status_lower in ("running", "working", "executing"):
            # Bounce position (0 to width-1 and back)
            cycle = (self.frame * 2) % (width * 2 - 2)
            pos = cycle if cycle < width else (width * 2 - 2 - cycle)
            
            bar = []
            for i in range(width):
                dist = abs(i - pos)
                if dist == 0:
                    bar.append(_BAR_FULL)
                elif dist == 1:
                    bar.append(_BAR_MED)
                elif dist == 2:
                    bar.append(_BAR_LOW)
                elif dist == 3:
                    bar.append(_BAR_EMPTY)
                else:
                    bar.append(" ")
            return "".join(bar)

        # ERROR: flash on/off
        elif "error" in status_lower:
            if (self.frame // 10) % 2 == 0:
                return _BAR_FULL * width
            else:
                return " " * width

        # Default: solid
        return _BAR_FULL * width

    # ── Thinking phrase animation ──────────────────────────────────────────────

    def _advance_think_anim(self, status: str) -> None:
        """Advance the character-by-character thinking phrase each frame."""
        if status.lower() != "thinking":
            # Soft-reset when we leave thinking state
            self._tp_char_count = 0
            self._tp_phase      = 0
            self._tp_pause_cnt  = 0
            return

        phrase = _THINK_PHRASES[self._tp_phrase_idx % len(_THINK_PHRASES)]

        if self._tp_phase == 0:                         # ── typing in ──
            if self.frame % _TYPE_FRAMES == 0:
                self._tp_char_count += 1
                if self._tp_char_count >= len(phrase):
                    self._tp_phase     = 1
                    self._tp_pause_cnt = 0

        elif self._tp_phase == 1:                       # ── pause ──
            self._tp_pause_cnt += 1
            if self._tp_pause_cnt >= _TYPE_PAUSE:
                self._tp_phase = 2

        elif self._tp_phase == 2:                       # ── erasing ──
            if self.frame % _ERASE_FRAMES == 0:
                self._tp_char_count -= 1
                if self._tp_char_count <= 0:
                    self._tp_char_count  = 0
                    self._tp_phrase_idx += 1
                    self._tp_phase       = 0

    def _think_phrase_display(self) -> str:
        """Return the currently-visible slice of the phrase + blinking cursor."""
        phrase  = _THINK_PHRASES[self._tp_phrase_idx % len(_THINK_PHRASES)]
        visible = phrase[: min(self._tp_char_count, len(phrase))]
        cursor  = "▌" if (self.frame // 6) % 2 == 0 else " "
        return visible + cursor

    # ── Unified feed ──────────────────────────────────────────────────────────

    def _draw_feed(self, log: List[LogEntry], chat: List[ChatMsg],
                   y: int, x: int, h: int, w: int):
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            try:
                self.stdscr.addstr(y,       x, ("╭" + "─" * (w - 2) + "╮")[:w], battr)
                self.stdscr.addstr(y+h-1,   x, ("╰" + "─" * (w - 2) + "╯")[:w], battr)
                for r in range(y + 1, y + h - 1):
                    self.stdscr.addstr(r, x,       "│", battr)
                    self.stdscr.addstr(r, x+w-1,   "│", battr)
            except curses.error:
                pass

            iw = max(4, w - 4)
            ih = h - 2
            lines = self._build_feed_lines(log, chat, iw)
            total = len(lines)

            self.scroll = min(self.scroll, max(0, total - ih))
            start = max(0, total - ih - self.scroll)

            # ── scrollbar ──
            if total > ih:
                sbx   = x + w - 2
                ratio = self.scroll / max(1, total - ih)
                thumb = ih - 1 - int(ratio * (ih - 1))
                sb_a  = curses.color_pair(_C["scroll"]) | curses.A_DIM
                for r in range(ih):
                    try:
                        self.stdscr.addstr(y+1+r, sbx,
                                           "▐" if r == thumb else "╎", sb_a)
                    except curses.error:
                        pass

            for i, (cp, text, xattr) in enumerate(lines[start: start + ih]):
                if i >= ih:
                    break
                try:
                    self.stdscr.addstr(y+1+i, x+2,
                                       text[:iw].ljust(iw)[:iw],
                                       curses.color_pair(cp) | xattr)
                except curses.error:
                    pass
                    
            # If no lines, show placeholder
            if not lines and h > 2:
                try:
                    self.stdscr.addstr(y+1, x+2,
                                       "  start typing below  ·  /help for commands"[:iw].ljust(iw)[:iw],
                                       curses.color_pair(_C["muted"]) | curses.A_DIM)
                except:
                    pass
        except Exception as e:
            # Draw error in feed area
            try:
                self.stdscr.addstr(y+1, x+2, f"Feed error: {e}"[:w].ljust(w)[:w],
                                   curses.color_pair(_C["error"]))
            except:
                pass

    # ── Feed line builder ─────────────────────────────────────────────────────

    def _build_feed_lines(self, log: List[LogEntry], chat: List[ChatMsg],
                          w: int) -> List[Tuple[int, str, int]]:
        lines: List[Tuple[int, str, int]] = []

        # Merge log + chat by timestamp
        events: List[Tuple[str, object]] = []
        for e in log:
            events.append((e.ts, e))
        for m in chat:
            events.append((m.ts, m))
        events.sort(key=lambda t: t[0])

        in_tool   = False
        tool_buf: List[str] = []

        # Animated glyph characters, keyed to current frame
        think_g  = _THINK_FEED[self.frame % len(_THINK_FEED)]

        def flush_tool():
            nonlocal in_tool, tool_buf
            if not tool_buf:
                return
            inner = max(2, w - 4)
            lines.append((_C["tool_bdr"],
                          "  ╭" + "─" * inner + "╮",
                          curses.A_DIM))
            for tl in tool_buf:
                for chunk in (self._wrap(tl, max(1, inner - 2)) if tl.strip() else [""]):
                    cell = chunk.ljust(inner - 2)[:inner - 2]
                    lines.append((_C["tool_txt"],
                                  "  │ " + cell + " │",
                                  curses.A_DIM))
            lines.append((_C["tool_bdr"],
                          "  ╰" + "─" * inner + "╯",
                          curses.A_DIM))
            in_tool = False
            tool_buf.clear()

        for _, ev in events:

            if isinstance(ev, ChatMsg):
                flush_tool()
                ts = ev.ts[-5:] if len(ev.ts) >= 5 else ev.ts

                if ev.role == "user":
                    lines.append((_C["sep"], "", 0))
                    lines.append((_C["user_lbl"],
                                  f"you  ·  {ts}", curses.A_BOLD))
                    # Wrap text and add to lines
                    wrapped = self._wrap(ev.text, max(1, w - 4))
                    for i, chunk in enumerate(wrapped):
                        if i == 0:
                            lines.append((_C["user_txt"], "  " + chunk, 0))
                        else:
                            lines.append((_C["user_txt"], "     " + chunk, 0))
                    lines.append((_C["sep"],
                                  "  " + "╌" * min(w - 4, 40), curses.A_DIM))
                else:
                    expr = f"  {ev.expression}" if ev.expression else ""
                    lines.append((_C["jerry_lbl"],
                                  f"jerry{expr}  ·  {ts}", curses.A_BOLD))
                    # Wrap text and add to lines - handle empty text
                    text_to_wrap = ev.text if ev.text else "(thinking...)"
                    wrapped = self._wrap(text_to_wrap, max(1, w - 4))
                    for i, chunk in enumerate(wrapped):
                        if i == 0:
                            lines.append((_C["jerry_txt"], "  " + chunk, 0))
                        else:
                            lines.append((_C["jerry_txt"], "     " + chunk, 0))
                    lines.append((_C["sep"], "", 0))

            elif isinstance(ev, LogEntry):
                kind = ev.kind

                if kind == "tool":
                    ts = ev.ts[-5:] if len(ev.ts) >= 5 else ev.ts
                    if not in_tool:
                        flush_tool()
                        in_tool = True
                    tool_buf.append(f"⬡ {ev.text}  ·  {ts}")

                elif kind == "result":
                    if in_tool:
                        tool_buf.append("")
                        for chunk in self._wrap(ev.text, max(1, w - 8)):
                            tool_buf.append("  " + chunk)
                    else:
                        for chunk in self._wrap(ev.text, max(1, w - 2)):
                            lines.append((_C["tool_txt"],
                                          "  " + chunk, curses.A_DIM))

                elif kind == "think":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 6)):
                        lines.append((_C["think"],
                                      f"  {think_g} " + chunk, curses.A_DIM))

                elif kind == "stream":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 6)):
                        lines.append((_C["dao_txt"],
                                      "  " + chunk, 0))

                elif kind == "error":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 4)):
                        lines.append((_C["error"],
                                      "  ✕ " + chunk, curses.A_BOLD))

                elif kind == "worker":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 4)):
                        lines.append((_C["worker"], "  ◈ " + chunk, 0))

                elif kind == "system":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 4)):
                        lines.append((_C["muted"], "  ◆ " + chunk, curses.A_DIM))

                elif kind == "info":
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 4)):
                        lines.append((_C["info"], "  ◦ " + chunk, curses.A_DIM))

                else:
                    flush_tool()
                    for chunk in self._wrap(ev.text, max(1, w - 4)):
                        lines.append((_C["muted"], "    " + chunk, curses.A_DIM))

        flush_tool()

        if not lines:
            lines.append((_C["muted"],
                          "  start typing below  ·  /help for commands",
                          curses.A_DIM))
        return lines

    # ── Todo sidebar ──────────────────────────────────────────────────────────

    def _draw_todo(self, todos: List[Todo], y: int, x: int, h: int, w: int):
        battr = curses.color_pair(_C["border"]) | curses.A_DIM
        title = "plan"
        pad   = max(0, w - len(title) - 5)
        try:
            self.stdscr.addstr(y,     x, f"╭─ {title} {'─'*pad}╮"[:w], battr)
            self.stdscr.addstr(y+h-1, x, ("╰" + "─"*(w-2) + "╯")[:w], battr)
            for r in range(y+1, y+h-1):
                self.stdscr.addstr(r, x,     "│", battr)
                self.stdscr.addstr(r, x+w-1, "│", battr)
        except curses.error:
            pass

        _PRI = {
            "high":   (_C["th"], "●", curses.A_BOLD),
            "medium": (_C["tm"], "◐", 0),
            "low":    (_C["tl"], "○", curses.A_DIM),
        }
        iw  = max(1, w - 3)
        row = y + 1
        for t in todos:
            if row >= y + h - 1:
                break
            if t.done:
                cp, glyph, xa = _C["td"], "✓", curses.A_DIM
            else:
                cp, glyph, xa = _PRI.get(t.priority, (_C["tm"], "◐", 0))
            text = f" {glyph} {t.text}"
            if len(text) > iw:
                text = text[:iw-1] + "…"
            try:
                self.stdscr.addstr(row, x+1,
                                   text.ljust(iw)[:iw],
                                   curses.color_pair(cp) | xa)
            except curses.error:
                pass
            row += 1

    # ── Input bar ─────────────────────────────────────────────────────────────

    def _draw_input(self, y: int, x: int, h: int, w: int):
        # Check if question is active
        question = self.state.get_pending_question()
        if question and question.get("active"):
            # Show minimal hint during question - NO INPUT TEXT (it's in panel)
            hint = "Type answer in panel ↑"
            
            battr = curses.color_pair(_C["border"]) | curses.A_BOLD
            hpad  = max(0, w - len(hint) - 5)
            try:
                self.stdscr.addstr(y,     x,
                                   f"╭─ {hint[:max(0,w-5)]} {'─'*hpad}╮"[:w], battr)
                self.stdscr.addstr(y+h-1, x,
                                   ("╰" + "─"*(w-2) + "╯")[:w], battr)
                for r in range(y+1, y+h-1):
                    self.stdscr.addstr(r, x,     "│", battr)
                    self.stdscr.addstr(r, x+w-1, "│", battr)
                # Don't draw input text - it's in the panel
            except curses.error:
                pass
        else:
            # Normal input bar
            hint = ("/log  /chat  /todo  /clear  /inject  /load  /listio  /cleario  /quit  /help"
                    if self.input_buf.startswith("/")
                    else "↑↓ scroll   /help for commands")

            battr = curses.color_pair(_C["border"]) | curses.A_BOLD
            hpad  = max(0, w - len(hint) - 5)
            try:
                self.stdscr.addstr(y,     x,
                                   f"╭─ {hint[:max(0,w-5)]} {'─'*hpad}╮"[:w], battr)
                self.stdscr.addstr(y+h-1, x,
                                   ("╰" + "─"*(w-2) + "╯")[:w], battr)
                for r in range(y+1, y+h-1):
                    self.stdscr.addstr(r, x,     "│", battr)
                    self.stdscr.addstr(r, x+w-1, "│", battr)
            except curses.error:
                pass

            prompt = " ›  "
            avail  = max(1, w - len(prompt) - 3)
            disp   = (self.input_buf[-avail:]
                      if len(self.input_buf) > avail else self.input_buf)
            try:
                self.stdscr.addstr(y+1, x+1, prompt,
                                   curses.color_pair(_C["inp_pre"]) | curses.A_BOLD)
                self.stdscr.addstr(y+1, x+1+len(prompt), disp,
                                   curses.color_pair(_C["inp_txt"]))
                self.stdscr.move(y+1, x+1+len(prompt)+len(disp))
            except curses.error:
                pass

    # ── Window-based drawing methods (for double-buffering) ─────────────────

    def _draw_face_panel_to_window(self, win, y: int, x: int, h: int, w: int):
        """Draw face panel to window - scaled like splash_screen.py"""
        try:
            # Scale face to panel size (minus borders)
            face_lines = self.face_display.get_current_face(w - 2, h - 2)
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            emotion = self.face_display.current_emotion.capitalize()

            # Top border
            top_border = "╭" + "─" * (w - 2) + "╮"
            win.addstr(y, x, top_border[:w], battr)
            label = f"◦ {emotion} "
            win.addstr(y, x + 2, label, battr | curses.A_BOLD)

            # Draw face lines
            for i, line in enumerate(face_lines):
                row = y + i + 1
                if row >= y + h - 1:
                    break
                win.addstr(row, x, "│", battr)
                win.addstr(row, x + w - 1, "│", battr)
                win.addstr(row, x + 1, line[:w-2], curses.color_pair(_C["jerry_txt"]))

            # Bottom border
            bottom_border = "╰" + "─" * (w - 2) + "╯"
            win.addstr(y + h - 1, x, bottom_border[:w], battr)
        except curses.error:
            pass

    def _draw_todo_vertical_to_window(self, win, todos: List[Todo], y: int, x: int, h: int, w: int):
        """Draw todo panel to specified window.
        
        Args:
            win: Window to draw to
            todos: List of todo items
            y, x: Position
            h, w: Dimensions
        """
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            title = "plan"
            pad = max(0, w - len(title) - 5)

            win.addstr(y, x, f"╭─ {title} {'─'*pad}╮"[:w], battr)

            for r in range(y + 1, y + h - 1):
                win.addstr(r, x, "│", battr)
                win.addstr(r, x + w - 1, "│", battr)

            win.addstr(y + h - 1, x, ("╰" + "─"*(w-2) + "╯")[:w], battr)

            _PRI = {
                "high":   (_C["th"], "●", curses.A_BOLD),
                "medium": (_C["tm"], "◐", 0),
                "low":    (_C["tl"], "○", curses.A_DIM),
            }

            iw = max(1, w - 3)
            row = y + 1

            for t in todos:
                if row >= y + h - 1:
                    break
                if t.done:
                    cp, glyph, xa = _C["td"], "✓", curses.A_DIM
                else:
                    cp, glyph, xa = _PRI.get(t.priority, (_C["tm"], "◐", 0))

                text = f" {glyph} {t.text}"
                if len(text) > iw:
                    text = text[:iw-1] + "…"

                win.addstr(row, x + 1, text.ljust(iw)[:iw], curses.color_pair(cp) | xa)
                row += 1
        except curses.error:
            pass

    def _draw_feed_to_window(self, win, log: List[LogEntry], chat: List[ChatMsg],
                              y: int, x: int, h: int, w: int):
        """Draw full feed to specified window.
        
        Args:
            win: Window to draw to
            log, chat: Log and chat entries
            y, x: Position
            h, w: Dimensions
        """
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM

            # Top border
            win.addstr(y, x, "╭" + "─" * (w - 2) + "╮", battr)
            for r in range(y + 1, y + h - 1):
                win.addstr(r, x, "│", battr)
                win.addstr(r, x + w - 1, "│", battr)
            win.addstr(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", battr)

            # Build feed lines
            lines = self._build_feed_lines(log, chat, w - 3)

            # Draw visible lines
            ih = h - 2
            total = len(lines)
            self.log_scroll = min(self.log_scroll, max(0, total - ih))
            start = max(0, total - ih - self.log_scroll)

            for i in range(ih):
                line_idx = start + i
                if line_idx >= total:
                    break
                cp, text, xattr = lines[line_idx]
                win.addstr(y + 1 + i, x + 1, text[:w-2].ljust(w-2)[:w-2],
                          curses.color_pair(cp) | xattr)
        except curses.error:
            pass

    def _draw_chat_feed_to_window(self, win, log: List[LogEntry], chat: List[ChatMsg],
                                   y: int, x: int, h: int, w: int):
        """Draw compact chat feed to specified window.
        
        Args:
            win: Window to draw to
            log, chat: Log and chat entries
            y, x: Position
            h, w: Dimensions
        """
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM

            # Top border
            win.addstr(y, x, "╭" + "─" * (w - 2) + "╮", battr)
            for r in range(y + 1, y + h - 1):
                win.addstr(r, x, "│", battr)
                win.addstr(r, x + w - 1, "│", battr)
            win.addstr(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", battr)

            # Build chat lines
            all_lines = []
            iw = max(1, w - 4)
            ih = h - 2

            for msg in chat:
                if not msg.text:
                    continue
                text = msg.text.replace('\n', ' ')
                role_label = "you: " if msg.role == "user" else "jerry: "
                wrapped = textwrap.wrap(text, width=iw - len(role_label)) or [""]

                for i, chunk in enumerate(wrapped):
                    if i == 0:
                        all_lines.append((msg.role, role_label + chunk, True))
                    else:
                        all_lines.append((msg.role, "     " + chunk, False))

            # Draw visible lines
            total = len(all_lines)
            self.chat_scroll = min(self.chat_scroll, max(0, total - ih))
            start = max(0, total - ih - self.chat_scroll)

            for i in range(ih):
                line_idx = start + i
                if line_idx >= total:
                    break

                role, text, is_first_line = all_lines[line_idx]
                cp = _C["user_txt"] if role == "user" else _C["jerry_txt"]
                lbl = _C["user_lbl"] if role == "user" else _C["jerry_lbl"]

                if is_first_line:
                    if role == "user":
                        win.addstr(y + 1 + i, x + 2, "you: ",
                                   curses.color_pair(lbl) | curses.A_BOLD)
                        win.addstr(y + 1 + i, x + 7, text[5:][:iw-7],
                                   curses.color_pair(cp))
                    else:
                        win.addstr(y + 1 + i, x + 2, "jerry: ",
                                   curses.color_pair(lbl) | curses.A_BOLD)
                        win.addstr(y + 1 + i, x + 9, text[7:][:iw-9],
                                   curses.color_pair(cp))
                else:
                    win.addstr(y + 1 + i, x + 2, text[:iw-2],
                               curses.color_pair(cp))
        except curses.error:
            pass

    def _draw_todo_to_window(self, win, todos: List[Todo], y: int, x: int, h: int, w: int):
        """Draw todo panel to specified window.
        
        Args:
            win: Window to draw to
            todos: List of todo items
            y, x: Position
            h, w: Dimensions
        """
        try:
            battr = curses.color_pair(_C["border"]) | curses.A_DIM

            # Borders
            win.addstr(y, x, "╭" + "─" * (w - 2) + "╮", battr)
            for r in range(y + 1, y + h - 1):
                win.addstr(r, x, "│", battr)
                win.addstr(r, x + w - 1, "│", battr)
            win.addstr(y + h - 1, x, "╰" + "─" * (w - 2) + "╯", battr)

            # Title
            title = " plan "
            win.addstr(y, x + (w // 2 - len(title) // 2), title, battr | curses.A_BOLD)

            # Todo items
            _PRI = {
                "high":   (_C["th"], "●", curses.A_BOLD),
                "medium": (_C["tm"], "◐", 0),
                "low":    (_C["tl"], "○", curses.A_DIM),
            }

            iw = max(1, w - 3)
            row = y + 1

            for t in todos:
                if row >= y + h - 1:
                    break
                if t.done:
                    cp, glyph, xa = _C["td"], "✓", curses.A_DIM
                else:
                    cp, glyph, xa = _PRI.get(t.priority, (_C["tm"], "◐", 0))

                text = f" {glyph} {t.text}"
                if len(text) > iw:
                    text = text[:iw-1] + "…"

                win.addstr(row, x + 1, text.ljust(iw)[:iw], curses.color_pair(cp) | xa)
                row += 1
        except curses.error:
            pass

    def _draw_status_bar_to_window(self, win, y: int, W: int, status: str,
                                    wfile: Optional[str], expression: str):
        """Draw status bar to specified window.
        
        Args:
            win: Window to draw to
            y: Row position
            W: Screen width
            status, wfile, expression: Status info
        """
        try:
            # Status line
            spin = _SPINNERS.get(status, "○")
            if isinstance(spin, str) and len(spin) > 1:
                # Animated spinner
                spin = spin[self.frame % len(spin)]

            slug = status.split()[0].lower() if status else "idle"
            bar = self._loading_bar(12, slug)

            left = f" {spin} {status} " if status else " ○ idle "
            right = f"│ {wfile or 'no file'} │ {expression or 'neutral'} "

            avail = W - len(left) - len(right) - 6
            bar_str = bar[:avail] if avail > 0 else ""

            status_line = f"{left}{bar_str}  {right}"
            win.addstr(y, 0, status_line[:W].ljust(W)[:W],
                      curses.color_pair(_C["stat_lo"]))
        except curses.error:
            pass

    def _draw_input_to_window(self, win, y: int, x: int, h: int, w: int):
        """Draw input bar to specified window."""
        try:
            # Check if question is active
            question = self.state.get_pending_question()
            if question and question.get("active"):
                # Show minimal hint during question - NO INPUT TEXT (it's in panel)
                hint = "Type answer in panel ↑"
                
                battr = curses.color_pair(_C["border"]) | curses.A_BOLD
                hpad = max(0, w - len(hint) - 5)
                win.addstr(y, x, f"╭─ {hint[:max(0,w-5)]} {'─'*hpad}╮"[:w], battr)
                win.addstr(y + h - 1, x, ("╰" + "─"*(w-2) + "╯")[:w], battr)
                for r in range(y + 1, y + h - 1):
                    win.addstr(r, x, "│", battr)
                    win.addstr(r, x + w - 1, "│", battr)
                # Don't draw input text - it's in the panel
            else:
                hint = ("/log  /chat  /todo  /clear  /inject  /load  /listio  /cleario  /quit  /help"
                        if self.input_buf.startswith("/")
                        else "↑↓ scroll   /help for commands")

                battr = curses.color_pair(_C["border"]) | curses.A_BOLD
                hpad = max(0, w - len(hint) - 5)
                win.addstr(y, x, f"╭─ {hint[:max(0,w-5)]} {'─'*hpad}╮"[:w], battr)
                win.addstr(y + h - 1, x, ("╰" + "─"*(w-2) + "╯")[:w], battr)
                for r in range(y + 1, y + h - 1):
                    win.addstr(r, x, "│", battr)
                    win.addstr(r, x + w - 1, "│", battr)

                prompt = " ›  "
                avail = max(1, w - len(prompt) - 3)
                disp = (self.input_buf[-avail:]
                        if len(self.input_buf) > avail else self.input_buf)
                win.addstr(y + 1, x + 1, prompt,
                          curses.color_pair(_C["inp_pre"]) | curses.A_BOLD)
                win.addstr(y + 1, x + 1 + len(prompt), disp,
                          curses.color_pair(_C["inp_txt"]))
                win.move(y + 1, x + 1 + len(prompt) + len(disp))
        except curses.error:
            pass

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _wrap(text: str, width: int) -> List[str]:
        if width < 1:
            return [text[:1] or ""]
        return textwrap.wrap(text, width=width) or [""]

    @staticmethod
    def _fmt_tokens(n: int) -> str:
        """Human-readable token count: 1234 → 1.2k, 1234567 → 1.2M"""
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.1f}k"
        return str(n)

    @staticmethod
    def _col_of_substr(s: str, substr: str) -> int:
        """Get display column where substr starts in s (accounts for wide unicode)."""
        idx = s.find(substr)
        if idx == -1:
            return 0
        # Count display columns (not codepoints) before substr
        cols = 0
        for ch in s[:idx]:
            width = unicodedata.east_asian_width(ch)
            cols += 2 if width in ('F', 'W') else 1
        return cols

    @staticmethod
    def _clip_to_cols(s: str, max_cols: int) -> str:
        """Clip string to max display columns (not codepoints)."""
        cols = 0
        result = []
        for ch in s:
            width = unicodedata.east_asian_width(ch)
            col_inc = 2 if width in ('F', 'W') else 1
            if cols + col_inc > max_cols:
                break
            cols += col_inc
            result.append(ch)
        return ''.join(result)

    # ── Keyboard handler ──────────────────────────────────────────────────────

    def handle_key(self, key: int) -> bool:
        """Return False to signal quit."""
        if key == curses.KEY_RESIZE:
            # Handle resize gracefully - curses handles this automatically
            # Just clear and refresh the screen to redraw with new dimensions
            try:
                self.stdscr.clear()
                self.stdscr.refresh()
            except curses.error:
                pass
            return True

        # Ctrl+Q or 'q' exits stream mode (when in stream mode)
        if key == 17:  # Ctrl+Q (ASCII 0x11)
            if self.state.is_stream_mode():
                self.disable_stream_mode()
                from jerry_core.screen_stream import stop_screen_stream
                stop_screen_stream()
                self.state.push_log("info", "Exited stream mode")
                # Force refresh to show normal mode immediately
                try:
                    self.stdscr.erase()
                    self.stdscr.refresh()
                except:
                    pass
            return True

        # Also allow 'q' to exit when in stream mode (convenience)
        if key == ord('q') and self.state.is_stream_mode():
            self.disable_stream_mode()
            from jerry_core.screen_stream import stop_screen_stream
            stop_screen_stream()
            self.state.push_log("info", "Exited stream mode")
            try:
                self.stdscr.erase()
                self.stdscr.refresh()
            except:
                pass
            return True

        # Check if there's a pending question - handle specially
        question = self.state.get_pending_question()
        if question and question.get("active"):
            # Allow quit/exit even during question
            if key in (17, ord('q')):  # Ctrl+Q or q
                return False  # Signal quit
            elif key in (10, 13, curses.KEY_ENTER) and self.input_buf.strip() == "/quit":
                return False  # Allow /quit during question
            elif key in (10, 13, curses.KEY_ENTER) and self.input_buf.strip() == "/exit":
                return False  # Allow /exit during question
            
            options = question.get("options", [])
            if not isinstance(options, list):
                options = []
            selected = question.get("selected", 0)
            selected_indices = question.get("selected_indices", set())  # Multi-select
            
            # Handle question navigation
            if key == curses.KEY_UP:
                if options:
                    with self.state._lock:
                        # Scroll up through options, wrap to custom at top
                        new_selected = selected - 1
                        if new_selected < 0:
                            new_selected = len(options)  # Custom option
                        question["selected"] = new_selected
                return True
            elif key == curses.KEY_DOWN:
                if options:
                    with self.state._lock:
                        # Scroll down through options, wrap to first at bottom
                        new_selected = selected + 1
                        if new_selected > len(options):
                            new_selected = 0  # Wrap to first option
                        question["selected"] = new_selected
                return True
            elif key == ord(' '):
                # Toggle selection for multi-select (only if on an option, not custom)
                if options and selected < len(options):
                    with self.state._lock:
                        if selected not in selected_indices:
                            selected_indices.add(selected)
                        else:
                            selected_indices.discard(selected)
                        question["selected_indices"] = selected_indices
                    return True
                # If on custom option, fall through to text input (to type space)
            elif key in (10, 13, curses.KEY_ENTER):
                # Submit answer
                raw = self.input_buf.strip()
                self.input_buf = ""
                
                if raw:
                    # Custom answer typed
                    self.state.answer_question(raw)
                elif selected_indices:
                    # Submit all selected options
                    answers = [options[i] for i in sorted(selected_indices)]
                    self.state.answer_question(answers)
                elif selected < len(options):
                    # Submit highlighted option (default fallback)
                    self.state.answer_question(options[selected])
                else:
                    # Custom option selected but no text - submit empty or wait
                    # For now, just submit empty string to avoid lock
                    self.state.answer_question("")
                
                # Clear pending question immediately
                self.state.clear_pending_question()
                
                # Clear input and force refresh
                self.input_buf = ""
                try:
                    self.stdscr.refresh()
                except:
                    pass
                
                return True
            
            # Text input for custom answer (always works, including space)
            if 32 <= key < 127:
                self.input_buf += chr(key)
                # Auto-select custom option when typing
                with self.state._lock:
                    question["selected"] = len(options) if options else 0
                return True
            
            # Backspace
            if key in (curses.KEY_BACKSPACE, 127, 8):
                self.input_buf = self.input_buf[:-1]
                return True
            
            # Block other keys
            return True

        # Normal mode - no pending question
        if key == curses.KEY_UP:
            self.scroll      += 1
            self.log_scroll  += 1
            self.chat_scroll += 1
            return True
        if key == curses.KEY_DOWN:
            self.scroll      = max(0, self.scroll      - 1)
            self.log_scroll  = max(0, self.log_scroll  - 1)
            self.chat_scroll = max(0, self.chat_scroll - 1)
            return True
        if key == curses.KEY_PPAGE:
            self.scroll      += 8
            self.log_scroll  += 8
            self.chat_scroll += 8
            return True
        if key == curses.KEY_NPAGE:
            self.scroll      = max(0, self.scroll      - 8)
            self.log_scroll  = max(0, self.log_scroll  - 8)
            self.chat_scroll = max(0, self.chat_scroll - 8)
            return True

        if key in (curses.KEY_BACKSPACE, 127, 8):
            self.input_buf = self.input_buf[:-1]
            return True

        if key in (10, 13, curses.KEY_ENTER):
            raw = self.input_buf.strip()
            self.input_buf = ""
            if not raw:
                return True
            if raw.startswith("/"):
                return self._handle_command(raw)
            self.state.push_chat("user", raw)
            self.state.add_inbox(raw)
            self.scroll      = 0
            self.chat_scroll = 0
            return True

        if 32 <= key < 127:
            self.input_buf += chr(key)

        return True

    # ── Command handler ───────────────────────────────────────────────────────

    def _handle_command(self, raw: str) -> bool:
        parts = raw[1:].lower().split()
        cmd   = parts[0] if parts else ""

        if cmd in ("q", "quit", "exit"):
            return False

        elif cmd in ("log", "chat", "todo"):
            self.focus = cmd
            self.state.push_log("info", f"focus → {cmd}")

        elif cmd == "clear":
            self.input_buf = ""

        elif cmd == "inject":
            if len(parts) > 1:
                msg = " ".join(parts[1:])
                self.state.add_inbox(f"[injected] {msg}")
                self.state.push_log("info", f"injected: {msg[:50]}")
            else:
                self.state.push_log("info", "usage: /inject <message>")

        elif cmd == "load":
            # Upload file(s) from device to jerry_workspace/io/
            self._handle_load_command(parts)

        elif cmd == "cleario":
            # Clear all files from io/ directory
            self._handle_cleario_command()

        elif cmd == "listio":
            # List files in io/ directory
            self._handle_listio_command()

        elif cmd == "compress":
            # Compress conversation history using worker
            self.state.push_log("info", "Compressing conversation history...")
            try:
                # Get conversation history (excluding system message)
                with self.state._lock:
                    # Get agent instance to access worker
                    # We'll compress chat + recent log entries
                    chat_summary = "\n".join([f"{m.role}: {m.text[:200]}" for m in self.state.chat[-30:]])
                
                # Use worker to compress
                from .worker import Worker
                worker = Worker(self.state)
                summary = worker.compress_history([{"role": "user", "content": chat_summary}])
                
                # Clear chat and add summary
                with self.state._lock:
                    # Keep last 5 messages, replace rest with summary
                    if len(self.state.chat) > 5:
                        old_count = len(self.state.chat)
                        self.state.chat = self.state.chat[-5:]
                        self.state.chat.insert(0, type(self.state.chat[0])(
                            role="system",
                            text=f"[COMPRESSED] Previous {old_count-5} messages summarized:\n{summary}"
                        ))
                
                self.state.push_log("info", f"✓ Compressed from {old_count} to {len(self.state.chat)} messages")
            except Exception as e:
                self.state.push_log("error", f"Compression failed: {e}")

        elif cmd == "help":
            self.state.push_log("info", "─── commands ─────────────────────────────────")
            self.state.push_log("info", "/log              activity log   (↑↓ scroll)")
            self.state.push_log("info", "/chat             conversation view")
            self.state.push_log("info", "/todo             plan / todo panel")
            self.state.push_log("info", "/stream <session> watch/control tmux session")
            self.state.push_log("info", "/type <text>      type into streamed session")
            self.state.push_log("info", "/clear            clear input buffer")
            self.state.push_log("info", "/compress         compress conversation history")
            self.state.push_log("info", "/theme [dark|light|auto]  toggle or set theme")
            self.state.push_log("info", "/face [show|hide|toggle]  toggle face panel")
            self.state.push_log("info", "/face <name>  set face (plain, unique, result, grumpy, happy, neutral)")
            self.state.push_log("info", "/face list  show available faces")
            self.state.push_log("info", "/chat_threshold <n> full feed at N+ rows (default: 15)")
            self.state.push_log("info", "/gap [seconds]    set agent cycle speed (default: 0.2)")
            self.state.push_log("info", "/praise [reason]  reward Jerry with coins (default: 'Great job!')")
            self.state.push_log("info", "/coins            check Jerry's coin balance")
            self.state.push_log("info", "/load             upload file(s) to io/ folder")
            self.state.push_log("info", "/listio           list files in io/ folder")
            self.state.push_log("info", "/cleario          delete all files from io/")
            self.state.push_log("info", "/quit             exit jerry")
            self.state.push_log("info", "/inject <msg>     inject into agent stream")
            self.state.push_log("info", "──────────────────────────────────────────────")
            self.state.push_log("info", "Stream mode: Ctrl+Q to exit")

        elif cmd == "theme":
            if len(parts) > 1:
                # Set specific theme: /theme dark, /theme light, /theme auto
                theme_arg = parts[1].lower()
                if theme_arg in ("dark", "light", "auto"):
                    self.set_theme(theme_arg)
                else:
                    self.state.push_log("info", f"Unknown theme: {theme_arg} (use: dark, light, or auto)")
            else:
                # Toggle theme: /theme
                self.toggle_theme()

        elif cmd == "face":
            if len(parts) > 1:
                face_arg = parts[1].lower()
                # Check if it's a face name
                face_names = ['plain', 'unique', 'result', 'grumpy', 'happy', 'neutral']
                if face_arg in face_names:
                    # Set specific face
                    self.face_display.set_face(face_arg)
                    # Reset face diffusion animation
                    if hasattr(self, '_face_revealed'):
                        self._face_revealed.clear()
                    self.state.push_log("info", f"✓ Face set to '{face_arg}'")
                elif face_arg in ("show", "on", "enable", "true"):
                    self.face_enabled = True
                    self.state.push_log("info", "✓ Face panel enabled")
                elif face_arg in ("hide", "off", "disable", "false"):
                    self.face_enabled = False
                    self.state.push_log("info", "✓ Face panel disabled")
                elif face_arg == "toggle":
                    self.face_enabled = not self.face_enabled
                    state_str = "enabled" if self.face_enabled else "disabled"
                    self.state.push_log("info", f"✓ Face panel {state_str}")
                elif face_arg == "list":
                    self.state.push_log("info", "Available faces: " + ", ".join(face_names))
                else:
                    self.state.push_log("info", f"Unknown face option: {face_arg}")
                    self.state.push_log("info", "Use: /face <name> or /face show|hide|toggle|list")
            else:
                # Toggle face: /face
                self.face_enabled = not self.face_enabled
                state_str = "enabled" if self.face_enabled else "disabled"
                self.state.push_log("info", f"✓ Face panel {state_str}")

        elif cmd == "praise":
            # User praising Jerry: /praise [reason]
            try:
                reason = " ".join(parts[1:]) if len(parts) > 1 else "Great job!"
                # Award 5-10 coins based on praise length
                base_coins = 5
                bonus = min(5, len(reason) // 20)
                total_coins = base_coins + bonus
                self.state.add_coins(total_coins, reason)
                self.state.push_chat("dao", f"🪙 *blushes happily* Thank you! {reason}", expression="smiling")
            except Exception as e:
                self.state.push_log("error", f"Praise error: {e}")

        elif cmd == "coins":
            # Check Jerry's coin balance: /coins
            try:
                coins = self.state.get_coins()
                self.state.push_log("info", f"🪙 Jerry has {coins} coins")
                # Show recent coin history
                if self.state.coin_history:
                    self.state.push_log("info", "Recent transactions:")
                    for tx in self.state.coin_history[-5:]:
                        sign = "+" if tx["type"] == "earn" else "-"
                        self.state.push_log("info", f"  {sign}{abs(tx['amount'])} - {tx['reason'][:40]} (balance: {tx['balance']})")
                else:
                    self.state.push_log("info", "No transactions yet. Use /praise to reward Jerry!")
            except Exception as e:
                self.state.push_log("error", f"Coins error: {e}")

        elif cmd == "chat_threshold":
            if len(parts) > 1:
                try:
                    threshold = int(parts[1])
                    if threshold >= 3:
                        self.chat_threshold = threshold
                        self.state.push_log("info", f"✓ Chat threshold set to {threshold} rows")
                    else:
                        self.state.push_log("info", "Minimum threshold is 3 rows")
                except ValueError:
                    self.state.push_log("info", "usage: /chat_threshold <number>")
            else:
                self.state.push_log("info", f"Current chat threshold: {self.chat_threshold} rows")

        elif cmd == "gap":
            if len(parts) > 1:
                try:
                    gap = float(parts[1])
                    if gap >= 0:
                        self.state.set_cycle_gap(gap)
                        self.state.push_log("info", f"✓ Cycle gap set to {gap}s")
                    else:
                        self.state.push_log("info", "Gap must be >= 0")
                except ValueError:
                    self.state.push_log("info", "usage: /gap <seconds>")
            else:
                current = self.state.get_cycle_gap()
                self.state.push_log("info", f"Current cycle gap: {current}s (default: 0.2s)")

        elif cmd == "stream":
            if len(parts) > 1:
                session = parts[1]
                self.enable_stream_mode(session)
                self.state.push_log("info", f"Stream mode: watching {session}")
                # Start screen capture in jerry_workspace
                try:
                    from .screen_stream import start_screen_stream
                    from .config import JERRY_BASE
                    start_screen_stream(session, self.update_screen, auto_create=True, workdir=JERRY_BASE)
                    # Also set this as the default target for terminal control
                    from .terminal import get_controller
                    controller = get_controller()
                    controller.tmux_session = session
                except Exception as e:
                    self.state.push_log("error", f"Stream error: {e}")
            else:
                self.state.push_log("info", "usage: /stream <tmux-session-name>")

        elif cmd == "type":
            # Send keys to streamed session
            if self.state.is_stream_mode() and len(parts) > 0:
                text = " ".join(parts)
                try:
                    from .screen_stream import send_to_screen
                    send_to_screen(text, enter=True)
                    session = self.state.get_stream_session() or "?"
                    self.state.push_log("info", f"Typed to {session}: {text[:40]}")
                except Exception as e:
                    self.state.push_log("error", f"Type error: {e}")
            elif not self.state.is_stream_mode():
                self.state.push_log("info", "usage: /type <text> (only works in stream mode)")
            else:
                self.state.push_log("info", "usage: /type <text>")

        else:
            self.state.push_log("error", f"unknown command: /{cmd}  —  try /help")

        return True

    # ── File Upload Commands ───────────────────────────────────────────────────

    def _handle_load_command(self, parts):
        """Handle /load command - copy file(s) to jerry_workspace/io/
        
        Usage:
          /load <path> [path2] ...  - Copy specified file(s) to io/
          /load                      - Shows help message
        """
        import os
        import shutil
        from .config import JERRY_BASE

        # Ensure io/ directory exists
        io_dir = os.path.join(JERRY_BASE, "io")
        os.makedirs(io_dir, exist_ok=True)

        # Check if paths provided
        if not parts:
            self.state.push_log("info", "Usage: /load <file_path> [file2] ...")
            self.state.push_log("info", "Example: /load /sdcard/Download/screenshot.png")
            self.state.push_log("info", "Files will be copied to jerry_workspace/io/")
            return

        uploaded_files = []
        
        for src_path in parts:
            # Expand ~ to home directory
            src_path = os.path.expanduser(src_path)
            
            if not os.path.exists(src_path):
                self.state.push_log("error", f"File not found: {src_path}")
                continue
            
            if not os.path.isfile(src_path):
                self.state.push_log("error", f"Not a file: {src_path}")
                continue
            
            filename = os.path.basename(src_path)
            dest_path = os.path.join(io_dir, filename)
            
            # Handle naming conflicts
            if os.path.exists(dest_path):
                self.state.push_log("info", f"File exists: {filename}")
                # Auto-rename with number
                name_parts = filename.rsplit('.', 1)
                counter = 2
                while os.path.exists(dest_path):
                    if len(name_parts) == 2:
                        new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
                    else:
                        new_filename = f"{filename}_{counter}"
                    dest_path = os.path.join(io_dir, new_filename)
                    counter += 1
                self.state.push_log("info", f"Renamed to: {os.path.basename(dest_path)}")
            
            # Copy file
            try:
                shutil.copy2(src_path, dest_path)
                file_size = os.path.getsize(dest_path)
                
                # Detect file type
                ext = os.path.splitext(filename)[1].lower().lstrip('.')
                mime_type = "unknown"
                if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp']:
                    mime_type = "image"
                elif ext in ['txt', 'md', 'py', 'js', 'json', 'yaml', 'yml']:
                    mime_type = "text"
                elif ext in ['pdf', 'doc', 'docx']:
                    mime_type = "document"
                
                uploaded_files.append({
                    "filename": os.path.basename(dest_path),
                    "size": file_size,
                    "type": mime_type,
                    "ext": ext
                })
                
                self.state.push_log("info", f"✓ Copied: {os.path.basename(dest_path)} ({file_size:,} bytes)")
            except Exception as e:
                self.state.push_log("error", f"Failed to copy {filename}: {e}")
        
        # Build auto-message for Jerry
        if uploaded_files:
            file_list = "\n".join([
                f"- **{f['filename']}** ({f['size']:,} bytes, {f['type']})"
                for f in uploaded_files
            ])
            
            # Customize message based on file types
            has_images = any(f['type'] == 'image' for f in uploaded_files)
            has_code = any(f['ext'] in ['py', 'js', 'ts', 'java', 'c', 'cpp', 'h'] for f in uploaded_files)
            
            if has_images:
                hint = "💡 **Tip:** These are image files. I can analyze them with my vision capabilities using `read_file()`!"
            elif has_code:
                hint = "💡 **Tip:** These are code files. I can read and analyze them with `read_file()`!"
            else:
                hint = "💡 **Tip:** You can read these files with `read_file(path=\"io/filename\")`"
            
            auto_message = f"""📎 **File Upload Complete**

**Files uploaded to `io/` directory:**
{file_list}

{hint}"""
            
            # Inject to Jerry's inbox
            self.state.add_inbox(auto_message)
            self.state.push_log("info", f"📎 {len(uploaded_files)} file(s) uploaded to io/")
        else:
            self.state.push_log("info", "No files uploaded")

    def _handle_cleario_command(self):
        """Handle /cleario command - delete all files in io/ directory"""
        import os
        import shutil
        from .config import JERRY_BASE

        io_dir = os.path.join(JERRY_BASE, "io")
        
        if not os.path.exists(io_dir):
            self.state.push_log("info", "io/ directory doesn't exist yet")
            return

        try:
            # Count files first
            files = os.listdir(io_dir)
            file_count = len([f for f in files if os.path.isfile(os.path.join(io_dir, f))])
            
            if file_count == 0:
                self.state.push_log("info", "io/ directory is already empty")
                return

            # Delete all files
            for filename in os.listdir(io_dir):
                filepath = os.path.join(io_dir, filename)
                if os.path.isfile(filepath):
                    os.remove(filepath)
            
            self.state.push_log("info", f"✓ Cleared {file_count} file(s) from io/")
        except Exception as e:
            self.state.push_log("error", f"Error clearing io/: {e}")

    def _handle_listio_command(self):
        """Handle /listio command - list files in io/ directory"""
        import os
        from .config import JERRY_BASE

        io_dir = os.path.join(JERRY_BASE, "io")
        
        if not os.path.exists(io_dir):
            self.state.push_log("info", "io/ directory doesn't exist yet")
            return

        try:
            files = os.listdir(io_dir)
            if not files:
                self.state.push_log("info", "io/ directory is empty")
                return

            self.state.push_log("info", f"📁 Files in io/ ({len(files)} total):")
            for filename in sorted(files):
                filepath = os.path.join(io_dir, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    self.state.push_log("info", f"  • {filename} ({size:,} bytes)")
        except Exception as e:
            self.state.push_log("error", f"Error listing io/: {e}")