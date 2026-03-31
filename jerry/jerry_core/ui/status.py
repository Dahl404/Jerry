#!/usr/bin/env python3
"""Jerry UI — Status Bar Rendering

Status bar and loading bar with animations.
"""

import curses
import math
import os
from typing import List, Optional

from .constants import _C, _SPINNERS, _BAR_FULL, _BAR_MED, _BAR_LOW, _BAR_EMPTY


class StatusBarRenderer:
    """Mixin for status bar rendering."""

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
        from datetime import datetime
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
        import unicodedata
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
        import unicodedata
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
