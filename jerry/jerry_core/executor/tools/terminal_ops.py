#!/usr/bin/env python3
"""Jerry Executor — Terminal Operations"""

import time
import re

from ...terminal import get_controller
from ...screen_stream import get_screen_streamer, start_screen_stream, send_to_screen
from ...config import JERRY_BASE


class TerminalOperations:
    """Mixin for terminal control operations."""

    def _capture_screen(self, lines: int) -> str:
        """Capture terminal screen content."""
        controller = get_controller()
        return controller.capture_screen(lines)

    def _send_keys(self, text: str, enter: bool) -> str:
        """Send keystrokes to terminal with support for special key tokens."""
        controller = get_controller()

        # Parse and send special key tokens
        results = []

        # Pattern to match <key> tokens
        token_pattern = r'<(\w+)>'

        # Split text by tokens
        parts = re.split(token_pattern, text)

        for i, part in enumerate(parts):
            if not part:
                continue

            # Check if this is a token (odd indices in split result are the captured groups)
            if i % 2 == 1:
                # This is a token name like "enter", "esc", etc.
                token = part.lower()

                # Map common token names to special key names
                token_map = {
                    'enter': 'Enter',
                    'ret': 'Enter',
                    'return': 'Enter',
                    'esc': 'Escape',
                    'escape': 'Escape',
                    'tab': 'Tab',
                    'space': ' ',
                    'spacebar': ' ',
                    'backspace': 'Backspace',
                    'bs': 'Backspace',
                    'delete': 'Delete',
                    'del': 'Delete',
                    'home': 'Home',
                    'end': 'End',
                    'pageup': 'PageUp',
                    'pgup': 'PageUp',
                    'pagedown': 'PageDown',
                    'pgdn': 'PageDown',
                    'up': 'Up',
                    'down': 'Down',
                    'left': 'Left',
                    'right': 'Right',
                    'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
                    'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
                    'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
                }

                if token in ('c-c', 'cc', 'ctrlc', 'controlc'):
                    # Send Ctrl+C
                    result = controller.send_ctrl('C')
                    results.append(f"Sent Ctrl+C")
                elif token in ('c-d', 'cd', 'ctrld', 'controld'):
                    # Send Ctrl+D
                    result = controller.send_ctrl('D')
                    results.append(f"Sent Ctrl+D")
                elif token in ('c-z', 'cz', 'ctrlz', 'controlz'):
                    # Send Ctrl+Z
                    result = controller.send_ctrl('Z')
                    results.append(f"Sent Ctrl+Z")
                elif token in token_map:
                    # Send special key
                    result = controller.send_keys(token_map[token], enter=False)
                    results.append(f"Sent {token_map[token]}")
                else:
                    # Unknown token, type it literally
                    result = controller.send_keys(f"<{token}>", enter=False)
                    results.append(f"Typed <{token}>")
            else:
                # This is regular text
                if part:
                    result = controller.send_keys(part, enter=False)
                    results.append(f"Typed text")

        # Handle the enter parameter
        if enter:
            controller.send_keys("", enter=True)
            results.append("Sent Enter")

        # In stream mode, capture screen after sending keys so agent can see result
        if self.state.is_stream_mode():
            time.sleep(0.3)  # Give terminal time to process the key
            try:
                streamer = get_screen_streamer()
                if streamer:
                    screen = streamer.capture_screen()
                    # Return screen if it has content (including errors!)
                    if screen and len(screen) > 20:
                        return screen
            except Exception:
                pass

        return "Keys sent: " + ", ".join(results)

    def _send_ctrl(self, key: str) -> str:
        """Send control sequence like Ctrl+C, Ctrl+Z."""
        controller = get_controller()
        return controller.send_ctrl(key)

    def _get_terminal_info(self) -> str:
        """Check terminal control capabilities."""
        controller = get_controller()
        info = controller.get_session_info()
        lines = ["## Terminal Control Status"]
        lines.append(f"- tmux available: {info['tmux_available']}")
        if info['tmux_session']:
            lines.append(f"- tmux session: {info['tmux_session']}")
        lines.append(f"- termux-api: {info['termux_api']}")
        lines.append("")
        lines.append("### Capabilities")
        for cap, available in info['capabilities'].items():
            status = "✓" if available else "✗"
            lines.append(f"- {status} {cap}")
        if not info['tmux_available']:
            lines.append("")
            lines.append("⚠️ **Install tmux for full terminal control:**")
            lines.append("```")
            lines.append("pkg install tmux  # On Termux")
            lines.append("brew install tmux  # On macOS")
            lines.append("apt install tmux   # On Debian/Ubuntu")
            lines.append("tmux new -s jerry")
            lines.append("```")
        return "\n".join(lines)

    def _set_target_session(self, session: str) -> str:
        """Set the target tmux session for terminal control."""
        controller = get_controller()
        controller.tmux_session = session
        return f"Target session set to: {session}"

    def _run_program(self, command: str, session: str = "jerry-control") -> str:
        """Run a program/command and show it to user in stream mode."""
        try:
            self.state.enable_stream_mode(session)
            controller = get_controller()
            controller.tmux_session = session

            # Start screen streaming
            start_screen_stream(session, self.state.update_screen, 
                              auto_create=True, workdir=JERRY_BASE, command=command)

            # Give program time to initialize
            time.sleep(2.0)

            # Capture initial screen
            screen = controller.capture_screen(24)
            return f"✓ Running in stream mode: {command}\n\n[Initial screen captured]"
        except Exception as e:
            self.state.disable_stream_mode()
            return f"ERROR: {e}"
