#!/usr/bin/env python3
"""Jerry UI — Main Render Loop

Coordinates all rendering operations.
"""

import curses


class RenderCoordinator:
    """Mixin for coordinating the main render loop."""

    def render(self):
        """Main render method - coordinates all drawing operations."""
        try:
            self.stdscr.erase()
            H, W = self.stdscr.getmaxyx()

            # Minimum size check
            if not self._check_minimum_size(H, W):
                return

            # Check state for stream mode
            if self.state.is_stream_mode():
                # Stream mode: show captured terminal screen
                self._draw_stream_screen(H, W)
            else:
                # Normal mode: show face panel + conversation feed
                self._draw_normal_mode(H, W)

            self.stdscr.refresh()
            self.frame += 1

            # Parse emotion tags from recent chat every 10 frames
            if self.frame % 10 == 0 and self.face_enabled:
                self._parse_recent_emotions()
        except curses.error:
            # Gracefully handle curses errors from resize
            try:
                self.stdscr.refresh()
            except:
                pass
        except Exception as e:
            # Catch any other errors to prevent crash
            try:
                self.stdscr.refresh()
            except:
                pass

    def _parse_recent_emotions(self):
        """Parse emotion tags from recent chat messages."""
        chat = self.state.chat[:]
        # Check last 3 messages for emotion tags
        for msg in reversed(chat[-3:]):
            if msg.role == "jerry" and msg.text:
                # This will set emotion if tags are found
                from jerry_core.faces_display import parse_and_set_emotion
                parse_and_set_emotion(msg.text)
                break
