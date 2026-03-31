#!/usr/bin/env python3
"""Jerry UI — Panel Rendering

Face panel, todo sidebar, and chat feed rendering.
"""

import curses
import textwrap
from typing import List, Tuple, Optional

from .constants import _C
from jerry_core.models import LogEntry, ChatMsg, Todo


class PanelRenderer:
    """Mixin for panel rendering (face, todo, chat feed)."""

    def _draw_face_panel(self, y: int, x: int, h: int, w: int):
        """Draw the ASCII face panel showing current emotion.

        Args:
            y: Starting row
            x: Starting column
            h: Height (50 rows)
            w: Width (100 chars)
        """
        try:
            # Get current face lines
            face_lines = self.face_display.get_current_face()

            # Draw face lines with border
            battr = curses.color_pair(_C["border"]) | curses.A_DIM
            emotion = self.face_display.current_emotion.capitalize()

            # Top border with emotion label
            try:
                top_border = "╭" + "─" * (w - 2) + "╮"
                self.stdscr.addstr(y, x, top_border[:w], battr)
                # Add emotion label
                label = f"◦ {emotion} "
                self.stdscr.addstr(y, x + 2, label, battr | curses.A_BOLD)
            except curses.error:
                pass

            # Face lines (50 lines total, but we have borders)
            for i, line in enumerate(face_lines[:h-2]):
                try:
                    # Left and right borders
                    self.stdscr.addstr(y + i + 1, x, "│", battr)
                    self.stdscr.addstr(y + i + 1, x + w - 1, "│", battr)
                    # Face content
                    self.stdscr.addstr(y + i + 1, x + 1, line[:w-2], curses.color_pair(_C["jerry_txt"]))
                except curses.error:
                    pass

            # Bottom border
            try:
                bottom_border = "╰" + "─" * (w - 2) + "╯"
                self.stdscr.addstr(y + h - 1, x, bottom_border[:w], battr)
            except curses.error:
                pass
        except Exception:
            # Catch any errors to prevent crash
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
        """Draw chat feed with dynamic height and scrolling.

        Args:
            y: Starting row
            x: Starting column
            h: Height (dynamic, fills space between face and status bar)
            w: Width
        """
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

        # Get chat messages to display
        iw = max(4, w - 4)
        ih = h - 2  # Visible lines (minus borders)

        # Build list of all chat lines
        all_lines = []
        for msg in chat:
            role_label = "you: " if msg.role == "user" else "jerry: "
            # Check if message is thinking content
            is_thinking = msg.expression == "thinking"
            wrapped = textwrap.wrap(msg.text, width=iw - len(role_label)) or [""]
            for chunk in wrapped:
                all_lines.append((msg.role, role_label + chunk, is_thinking))

        # Handle scrolling
        total = len(all_lines)
        self.chat_scroll = min(self.chat_scroll, max(0, total - ih))
        start = max(0, total - ih - self.chat_scroll)

        # Draw visible chat lines
        for i in range(ih):
            line_idx = start + i
            if line_idx >= total:
                break

            role, text, is_thinking = all_lines[line_idx]

            # Use thinking color if expression is "thinking"
            if is_thinking:
                cp = _C["think"]  # Blue/cyan for thinking
                lbl = _C["think"]
            else:
                cp = _C["user_txt"] if role == "user" else _C["jerry_txt"]
                lbl = _C["user_lbl"] if role == "user" else _C["jerry_lbl"]

            try:
                # Draw role label in bold
                if role == "user":
                    self.stdscr.addstr(y + 1 + i, x + 2, "you: ",
                                       curses.color_pair(lbl) | curses.A_BOLD)
                    self.stdscr.addstr(y + 1 + i, x + 7, text[5:][:iw-7],
                                       curses.color_pair(cp))
                else:
                    self.stdscr.addstr(y + 1 + i, x + 2, "jerry: ",
                                       curses.color_pair(lbl) | curses.A_BOLD)
                    self.stdscr.addstr(y + 1 + i, x + 7, text[5:][:iw-7],
                                       curses.color_pair(cp))
            except curses.error:
                pass

        # Draw scrollbar if needed
        if total > ih:
            sbx = x + w - 2
            ratio = self.chat_scroll / max(1, total - ih)
            thumb = ih - 1 - int(ratio * (ih - 1))
            sb_a = curses.color_pair(_C["scroll"]) | curses.A_DIM
            for r in range(ih):
                try:
                    self.stdscr.addstr(y + 1 + r, sbx,
                                       "▐" if r == thumb else "╎", sb_a)
                except curses.error:
                    pass

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
