#!/usr/bin/env python3
"""Jerry UI — Colour Pairs and Constants"""

import curses
from typing import Dict, Tuple

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

__all__ = [
    "_C",
    "THEME_DARK",
    "THEME_LIGHT",
    "_SPINNERS",
    "_THINK_PHRASES",
    "_THINK_FEED",
    "_STREAM_FEED",
    "_BAR_FULL",
    "_BAR_MED",
    "_BAR_LOW",
    "_BAR_EMPTY",
    "_TYPE_FRAMES",
    "_TYPE_PAUSE",
    "_ERASE_FRAMES",
]
