#!/usr/bin/env python3
"""Jerry UI — Feed Rendering

Unified feed display with log and chat message merging.
"""

import curses
from typing import List, Tuple

from .constants import _C, _THINK_FEED
from jerry_core.models import LogEntry, ChatMsg, Todo


class FeedRenderer:
    """Mixin for feed rendering functionality."""

    def _draw_feed(self, log: List[LogEntry], chat: List[ChatMsg],
                   y: int, x: int, h: int, w: int):
        """Draw unified feed with log and chat messages."""
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

    def _build_feed_lines(self, log: List[LogEntry], chat: List[ChatMsg],
                          w: int) -> List[Tuple[int, str, int]]:
        """Build list of feed lines from log and chat messages."""
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
                    for chunk in self._wrap(ev.text, max(1, w - 2)):
                        lines.append((_C["user_txt"], "  " + chunk, 0))
                    lines.append((_C["sep"],
                                  "  " + "╌" * min(w - 4, 40), curses.A_DIM))
                else:
                    expr = f"  {ev.expression}" if ev.expression else ""
                    lines.append((_C["jerry_lbl"],
                                  f"jerry{expr}  ·  {ts}", curses.A_BOLD))
                    for chunk in self._wrap(ev.text, max(1, w - 2)):
                        lines.append((_C["jerry_txt"], "  " + chunk, 0))
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
                        lines.append((_C["jerry_txt"],
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

    def _draw_todo(self, todos: List[Todo], y: int, x: int, h: int, w: int):
        """Draw todo sidebar."""
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
