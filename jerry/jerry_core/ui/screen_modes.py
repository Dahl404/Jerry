#!/usr/bin/env python3
"""Jerry UI — Screen Mode Rendering

Normal mode and stream mode screen rendering.
"""

import curses
import re
from datetime import datetime

from .constants import _C


class ScreenModeRenderer:
    """Mixin for screen mode rendering (normal and stream modes)."""

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
                # Use full feed mode (like face disabled) - shows all message types
                self._draw_feed(log, chat, y=chat_y, x=0, h=chat_h, w=chat_w)
            else:
                # Use compact chat mode - shows only recent messages
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
        self._draw_input(y=input_y, x=0, h=3, w=W)

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

            # Use full feed or compact based on threshold
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
