#!/usr/bin/env python3
"""Jerry UI — Input Handling

Keyboard input and command processing.
"""

import curses
from typing import Optional

from .constants import _C


class InputHandler:
    """Mixin for keyboard input and command handling."""

    def handle_key(self, key: int) -> bool:
        """Return False to signal quit."""
        if key == curses.KEY_RESIZE:
            # Handle resize gracefully - just return True and let render() handle it
            try:
                curses.endwin()
                self.stdscr.refresh()
                curses.doupdate()
            except curses.error:
                pass
            return True

        # Ctrl+Q or 'q' exits stream mode (when in stream mode)
        if key == 17:  # Ctrl+Q (ASCII 0x11)
            if self.state.is_stream_mode():
                self.disable_stream_mode()
                from .screen_stream import stop_screen_stream
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
            from .screen_stream import stop_screen_stream
            stop_screen_stream()
            self.state.push_log("info", "Exited stream mode")
            try:
                self.stdscr.erase()
                self.stdscr.refresh()
            except:
                pass
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

    def _handle_command(self, raw: str) -> bool:
        """Handle slash commands."""
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
            self.state.push_log("info", "/face [show|hide] toggle face panel (default: show)")
            self.state.push_log("info", "/chat_threshold <n> full feed at N+ rows (default: 15)")
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
                # Set face visibility: /face show, /face hide, /face toggle
                face_arg = parts[1].lower()
                if face_arg in ("show", "on", "enable", "true"):
                    self.face_enabled = True
                    self.state.push_log("info", "✓ Face panel enabled")
                elif face_arg in ("hide", "off", "disable", "false"):
                    self.face_enabled = False
                    self.state.push_log("info", "✓ Face panel disabled")
                elif face_arg == "toggle":
                    self.face_enabled = not self.face_enabled
                    state_str = "enabled" if self.face_enabled else "disabled"
                    self.state.push_log("info", f"✓ Face panel {state_str}")
                else:
                    self.state.push_log("info", f"Unknown face option: {face_arg} (use: show, hide, or toggle)")
            else:
                # Toggle face: /face
                self.face_enabled = not self.face_enabled
                state_str = "enabled" if self.face_enabled else "disabled"
                self.state.push_log("info", f"✓ Face panel {state_str}")

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

    def _draw_input(self, y: int, x: int, h: int, w: int):
        """Draw input bar."""
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
