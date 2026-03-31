#!/usr/bin/env python3
"""Dao — qwen-code style single-feed TUI  ·  light terminal"""

import curses
import os
import textwrap
from typing import List, Tuple, Optional
from datetime import datetime
from .models import State, LogEntry, ChatMsg, Todo
from .config import LOG_LIMIT

# ─────────────────────────────────────────────────────────────────────────────
#  Colour pairs  (0 = reserved by curses)
# ─────────────────────────────────────────────────────────────────────────────
_C = {
    "border":    1,
    "user_lbl":  2,
    "user_txt":  3,
    "dao_lbl":   4,
    "dao_txt":   5,
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
    "synthesizing",
    "reasoning through this",
    "considering the possibilities",
    "working it out",
    "tracing the logic",
    "processing context",
    "connecting the dots",
    "exploring solution space",
    "weighing the options",
    "distilling an answer",
    "examining the edges",
    "following the thread",
    "mapping the problem",
    "untangling this",
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
        self.frame      = 0          # master frame counter; ticks each render()

        # Compat shims
        self.log_scroll  = 0
        self.chat_scroll = 0

        # Performance / context metrics (updated externally via update_tokens)
        self.ctx_tokens: int   = 0
        self.tps:        float = 0.0

        # Thinking-phrase animation state
        self._tp_phrase_idx:  int = 0   # which phrase we're on
        self._tp_char_count:  int = 0   # chars revealed so far
        self._tp_phase:       int = 0   # 0=typing  1=pause  2=erasing
        self._tp_pause_cnt:   int = 0   # frames spent in pause phase

    # ── Public helpers ────────────────────────────────────────────────────────

    def update_tokens(self, ctx: int, tps: float = 0.0) -> None:
        """Call this from your agent loop whenever token counts change."""
        self.ctx_tokens = ctx
        self.tps        = tps

    # ── Curses init ───────────────────────────────────────────────────────────

    def setup(self, stdscr):
        self.stdscr = stdscr
        curses.curs_set(1)
        curses.start_color()
        curses.use_default_colors()
        bg = -1

        pairs = [
            (_C["border"],   curses.COLOR_BLUE,    bg),
            (_C["user_lbl"], curses.COLOR_BLUE,    bg),
            (_C["user_txt"], curses.COLOR_BLUE,    bg),
            (_C["dao_lbl"],  curses.COLOR_GREEN,   bg),
            (_C["dao_txt"],  curses.COLOR_BLACK,   bg),
            (_C["tool_hdr"], curses.COLOR_MAGENTA, bg),
            (_C["tool_bdr"], curses.COLOR_MAGENTA, bg),
            (_C["tool_txt"], curses.COLOR_BLACK,   bg),
            (_C["think"],    curses.COLOR_BLUE,    bg),
            (_C["error"],    curses.COLOR_RED,     bg),
            (_C["worker"],   curses.COLOR_MAGENTA, bg),
            (_C["info"],     curses.COLOR_CYAN,    bg),
            (_C["stream"],   curses.COLOR_GREEN,   bg),
            (_C["th"],       curses.COLOR_RED,     bg),
            (_C["tm"],       curses.COLOR_MAGENTA, bg),
            (_C["tl"],       curses.COLOR_GREEN,   bg),
            (_C["td"],       curses.COLOR_BLACK,   bg),
            (_C["inp_pre"],  curses.COLOR_GREEN,   bg),
            (_C["inp_txt"],  curses.COLOR_BLACK,   bg),
            (_C["muted"],    curses.COLOR_BLACK,   bg),
            (_C["ts"],       curses.COLOR_BLACK,   bg),
            (_C["scroll"],   curses.COLOR_BLUE,    bg),
            (_C["sep"],      curses.COLOR_BLUE,    bg),
            (_C["stat_lo"],  curses.COLOR_BLACK,   bg),
            (_C["stat_hi"],  curses.COLOR_GREEN,   bg),
            (_C["bar_fill"], curses.COLOR_BLUE,    bg),
            (_C["bar_dim"],  curses.COLOR_BLACK,   bg),
            (_C["ctx_col"],  curses.COLOR_CYAN,    bg),
            (_C["tps_col"],  curses.COLOR_GREEN,   bg),
        ]
        for pid, fg, bk in pairs:
            curses.init_pair(pid, fg, bk)

        stdscr.nodelay(True)
        stdscr.keypad(True)

    # ── Layout ────────────────────────────────────────────────────────────────

    def _layout(self):
        """
        Row allocation (H rows total):
          rows  0 … H-5   feed box      (height = H-4)
          row   H-4       status bar    (1 row)
          rows  H-3 … H-1 input box     (height = 3)
        """
        H, W = self.stdscr.getmaxyx()
        _, _, todos, _, _, _ = self.state.snapshot()
        todo_w = max(24, min(30, W // 5)) if todos else 0
        feed_w = W - todo_w
        feed_h = max(4, H - 4)          # includes top+bottom border
        return H, W, 0, 0, feed_h, feed_w, feed_w, todo_w

    # ── Full redraw ───────────────────────────────────────────────────────────

    def render(self):
        try:
            self.stdscr.erase()
            H, W, fy, fx, fh, fw, tx, tw = self._layout()
            log, chat, todos, status, wfile, expression = self.state.snapshot()

            self._advance_think_anim(status)

            self._draw_feed(log, chat, y=fy, x=fx, h=fh, w=fw)
            if todos:
                self._draw_todo(todos, y=fy, x=tx, h=fh, w=tw)
            self._draw_status_bar(H - 4, W, status, wfile, expression)
            self._draw_input(y=H - 3, x=0, h=3, w=W)
            self.stdscr.refresh()
            self.frame += 1
        except curses.error:
            pass

    # ── Status bar ────────────────────────────────────────────────────────────

    def _draw_status_bar(self, y: int, W: int, status: str,
                          wfile: Optional[str], expression: str):
        """The info row sandwiched between feed and input."""
        slug = status.lower().strip()

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

        # ── right section: expr · file · ⟨ctx⟩ · tps · time ──
        segs: List[str] = []
        if expression:
            segs.append(f"✦ {expression}")
        segs.append(f"◈ {os.path.basename(wfile)}" if wfile else "◈ dao")
        if self.ctx_tokens:
            segs.append(f"⟨{self._fmt_tokens(self.ctx_tokens)}⟩")
        if self.tps > 0.5:
            segs.append(f"{self.tps:.0f} t/s")
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
            # Re-paint ctx token count
            if self.ctx_tokens:
                tok_str = f"⟨{self._fmt_tokens(self.ctx_tokens)}⟩"
                tok_x   = row.find(tok_str)
                if 0 <= tok_x < W:
                    self.stdscr.addstr(y, tok_x, tok_str[:W - tok_x], ctx_a)
            # Re-paint tps
            if self.tps > 0.5:
                tps_str = f"{self.tps:.0f} t/s"
                tps_x   = row.find(tps_str)
                if 0 <= tps_x < W:
                    self.stdscr.addstr(y, tps_x, tps_str[:W - tps_x], tps_a)
        except curses.error:
            pass

    # ── Loading bar ───────────────────────────────────────────────────────────

    def _loading_bar(self, width: int, status: str) -> str:
        """Animated marching-highlight bar when active; dotted when idle."""
        if status in ("idle", "error", ""):
            return "·" * width

        # A 3-cell bright window slides across the bar
        pos = self.frame % (width + 6)
        bar: List[str] = []
        for i in range(width):
            d = i - (pos - 3)
            if   d == 0:         bar.append(_BAR_FULL)
            elif abs(d) == 1:    bar.append(_BAR_MED)
            elif abs(d) == 2:    bar.append(_BAR_LOW)
            else:                bar.append(_BAR_EMPTY)
        return "".join(bar)

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
        stream_g = _STREAM_FEED[self.frame % len(_STREAM_FEED)]

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
                    lines.append((_C["dao_lbl"],
                                  f"dao{expr}  ·  {ts}", curses.A_BOLD))
                    for chunk in self._wrap(ev.text, max(1, w - 2)):
                        lines.append((_C["dao_txt"], "  " + chunk, 0))
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
                        lines.append((_C["stream"],
                                      f"  {stream_g} " + chunk, 0))

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
        hint = ("/log  /chat  /todo  /clear  /inject  /quit  /help"
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

    # ── Keyboard handler ──────────────────────────────────────────────────────

    def handle_key(self, key: int) -> bool:
        """Return False to signal quit."""
        if key == curses.KEY_RESIZE:
            curses.resizeterm(*self.stdscr.getmaxyx())
            return True

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

        elif cmd == "help":
            self.state.push_log("info", "─── commands ─────────────────────────────────")
            self.state.push_log("info", "/log            activity log   (↑↓ scroll)")
            self.state.push_log("info", "/chat           conversation view")
            self.state.push_log("info", "/todo           plan / todo panel")
            self.state.push_log("info", "/clear          clear input buffer")
            self.state.push_log("info", "/quit           exit dao")
            self.state.push_log("info", "/inject <msg>   inject into agent stream")
            self.state.push_log("info", "──────────────────────────────────────────────")

        else:
            self.state.push_log("error", f"unknown command: /{cmd}  —  try /help")

        return True