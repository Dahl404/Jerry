#!/usr/bin/env python3
"""Dao — Terminal Screen Capture & Control for Termux

Captures live terminal text and sends input using tmux or termux-api.
"""

import subprocess
import os
from typing import Optional, List, Dict


class TerminalController:
    """Controls terminal screen capture and input for real-time interaction."""

    def __init__(self):
        self.tmux_session = "dao-control"  # Default tmux session
        self.use_tmux = self._check_tmux()
        self.use_termux_api = self._check_termux_api()

    def _check_tmux(self) -> bool:
        """Check if tmux is available and we're in a tmux session."""
        try:
            result = subprocess.run(
                ["tmux", "info"],
                capture_output=True, text=True, timeout=2
            )
            return result.returncode == 0
        except Exception:
            return False

    def _check_termux_api(self) -> bool:
        """Check if termux-api is available."""
        try:
            result = subprocess.run(
                ["termux-setup-storage"],
                capture_output=True, timeout=2
            )
            return True
        except Exception:
            return False

    def capture_screen(self, lines: int = 24) -> str:
        """Capture current terminal screen content.
        
        Args:
            lines: Number of lines to capture (default 24 = full screen)
            
        Returns:
            Terminal screen content as string
        """
        if self.use_tmux:
            return self._capture_tmux(lines)
        else:
            return self._capture_scrollback(lines)

    def _capture_tmux(self, lines: int) -> str:
        """Capture screen using tmux capture-pane."""
        try:
            result = subprocess.run(
                ["tmux", "capture-pane", "-p", "-t", self.tmux_session, "-S", f"-{lines}"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout
        except Exception as e:
            return f"ERROR capturing screen: {e}"

    def _capture_scrollback(self, lines: int) -> str:
        """Fallback: Try to capture from scrollback or current buffer."""
        # Without tmux, we can't easily capture the terminal
        # This is a limitation - tmux is strongly recommended
        return (
            "⚠️ Terminal capture requires tmux.\n"
            "Install: pkg install tmux\n"
            "Then run Dao inside a tmux session: tmux new -s dao\n"
        )

    def send_keys(self, text: str, enter: bool = True) -> str:
        """Send keystrokes to terminal.
        
        Args:
            text: Text to type (supports special keys: Escape, Up, Down, etc.)
            enter: Whether to press Enter after typing
            
        Returns:
            Status message
        """
        if self.use_tmux:
            return self._send_tmux(text, enter)
        else:
            return "⚠️ Cannot send keys without tmux. Install tmux for full control."

    def _send_tmux(self, text: str, enter: bool) -> str:
        """Send keys using tmux send-keys with special key support."""
        try:
            # Map special key names to tmux escape sequences
            special_keys = {
                "Escape": "Escape",
                "Esc": "Escape",
                "Up": "Up",
                "Down": "Down",
                "Left": "Left",
                "Right": "Right",
                "Tab": "Tab",
                "Backspace": "BSPACE",
                "Delete": "DC",
                "Home": "Home",
                "End": "End",
                "PageUp": "PGUP",
                "PageDown": "PGDN",
                "Insert": "IC",
                "F1": "F1", "F2": "F2", "F3": "F3", "F4": "F4",
                "F5": "F5", "F6": "F6", "F7": "F7", "F8": "F8",
                "F9": "F9", "F10": "F10", "F11": "F11", "F12": "F12",
                "C-c": "C-c", "C-d": "C-d", "C-z": "C-z",  # Ctrl keys
                "C-C": "C-C", "C-D": "C-D", "C-Z": "C-Z",
            }
            
            # Check if text is a special key
            if text in special_keys:
                tmux_key = special_keys[text]
                cmd = ["tmux", "send-keys", "-t", self.tmux_session, tmux_key]
            else:
                # Regular text - escape special characters
                escaped = text.replace("\\", "\\\\").replace("'", "'\\''")
                if enter:
                    cmd = ["tmux", "send-keys", "-t", self.tmux_session, escaped, "Enter"]
                else:
                    cmd = ["tmux", "send-keys", "-t", self.tmux_session, escaped]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                action = "sent"
                return f"✓ Keys: '{text[:50]}...' ({action})"
            else:
                return f"ERROR: {result.stderr}"
                
        except Exception as e:
            return f"ERROR sending keys: {e}"

    def send_ctrl(self, key: str) -> str:
        """Send control sequence (Ctrl+C, Ctrl+Z, etc.).
        
        Args:
            key: Single character (e.g., 'C' for Ctrl+C)
            
        Returns:
            Status message
        """
        if not self.use_tmux:
            return "⚠️ Cannot send control sequences without tmux."
        
        try:
            # tmux format for Ctrl+key
            ctrl_seq = f"C-{key}"
            cmd = ["tmux", "send-keys", "-t", self.tmux_session, ctrl_seq]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                return f"✓ Sent Ctrl+{key}"
            else:
                return f"ERROR: {result.stderr}"
                
        except Exception as e:
            return f"ERROR sending Ctrl+{key}: {e}"

    def get_session_info(self) -> Dict:
        """Get information about terminal control capabilities."""
        return {
            "tmux_available": self.use_tmux,
            "tmux_session": self.tmux_session if self.use_tmux else None,
            "termux_api": self.use_termux_api,
            "capabilities": {
                "screen_capture": self.use_tmux,
                "send_input": self.use_tmux,
                "control_sequences": self.use_tmux,
            }
        }


# Singleton instance
_controller: Optional[TerminalController] = None


def get_controller() -> TerminalController:
    """Get or create the terminal controller singleton."""
    global _controller
    if _controller is None:
        _controller = TerminalController()
    return _controller


def stop_controller():
    """Stop and cleanup the terminal controller."""
    global _controller
    if _controller is not None:
        # Clear the singleton - any tmux sessions are left running
        # as they may be used by other processes
        _controller = None


def capture_terminal(lines: int = 24) -> str:
    """Convenience function to capture terminal screen."""
    return get_controller().capture_screen(lines)


def send_to_terminal(text: str, enter: bool = True) -> str:
    """Convenience function to send text to terminal."""
    return get_controller().send_keys(text, enter)
