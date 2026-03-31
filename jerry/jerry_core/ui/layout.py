#!/usr/bin/env python3
"""Jerry UI — Layout Management

Screen layout calculation and panel positioning.
"""

from typing import Tuple, List

from jerry_core.models import Todo


class LayoutManager:
    """Mixin for layout management functionality."""

    def _layout(self) -> Tuple[int, int, int, int, int, int, int, int, int]:
        """Calculate screen layout.
        
        Row allocation (H rows total):
          If face enabled:
            rows  0-49        face panel (50 rows) + todo sidebar
            rows  50-(H-5)    chat feed (fills remaining space)
            row   H-4         status bar (1 row)
            rows  H-3 … H-1   input box (height = 3)
          If face disabled:
            rows  0-(H-5)     full chat feed (like original)
            row   H-4         status bar (1 row)
            rows  H-3 … H-1   input box (height = 3)
            
        Returns:
            Tuple of (H, W, face_h, face_w, todo_w, chat_h, chat_w, status_y, input_y)
        """
        H, W = self.stdscr.getmaxyx()
        _, _, todos, _, _, _ = self.state.snapshot()

        # Status bar and input (always same position)
        status_y = H - 4
        input_y = H - 3

        if self.face_enabled:
            # Face panel is always 50 lines tall, 100 chars wide (fixed)
            face_h = 50
            face_w = 100  # Fixed width for face

            # Chat feed fills space between face and status bar
            # Available rows: from row 50 to row (H-5), inclusive
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

    def _check_minimum_size(self, H: int, W: int) -> bool:
        """Check if terminal meets minimum size requirements.

        Returns:
            True if size is adequate, False if too small
        """
        if self.face_enabled:
            # Face needs 100x60 - auto-disable if too small
            if H < 60 or W < 100:
                # Auto-disable face panel for small terminals
                self.face_enabled = False
                self.state.push_log("info", f"Face panel auto-disabled (terminal {W}x{H} < 100x60)")
                return True  # Continue rendering without face
        else:
            # Without face, minimum is 80x24
            if H < 24 or W < 80:
                try:
                    self.stdscr.addstr(0, 0, f"Terminal too small! Need 80x24, have {W}x{H}".center(W)[:W])
                    self.stdscr.addstr(2, 0, "Please resize your terminal window.".center(W)[:W])
                    self.stdscr.refresh()
                except curses.error:
                    pass
                return False
        return True
