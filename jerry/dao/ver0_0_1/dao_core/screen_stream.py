#!/usr/bin/env python3
"""Dao — Screen Stream Mode

Connects to an external tmux session and:
- Captures screen continuously (Dao's "eyes")
- Sends Dao's output as keystrokes (Dao's "hands")
- Displays captured screen in main window for user to watch

Auto-creates target session if it doesn't exist.
"""

import subprocess
import time
import threading
from typing import Optional, Callable


def session_exists(session_name: str) -> bool:
    """Check if a tmux session exists."""
    try:
        result = subprocess.run(
            ['tmux', 'has-session', '-t', session_name],
            capture_output=True, timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def create_session(session_name: str, shell: str = "bash", workdir: str = None) -> bool:
    """Create a new tmux session with interactive shell.

    Args:
        session_name: Name for the session
        shell: Shell to run (default: bash)
        workdir: Working directory for the session (default: dao_workspace)

    Returns:
        True if created successfully
    """
    try:
        # Default to dao_workspace if not specified
        if workdir is None:
            workdir = "/data/data/com.termux/files/home/dao/dao_workspace"

        # Start detached session with specified shell in workspace directory
        cmd = ['tmux', 'new', '-d', '-s', session_name, '-c', workdir, shell]
        subprocess.run(cmd, capture_output=True, timeout=5)
        # Verify it was created and give time to start
        time.sleep(0.5)
        return session_exists(session_name)
    except Exception as e:
        return False


class ScreenStreamer:
    """Streams terminal screen to Dao and sends Dao output back as keystrokes."""

    def __init__(self, target_session: str, auto_create: bool = True, workdir: str = None, command: str = None):
        self.target_session = target_session
        self.running = False
        self._capture_thread: Optional[threading.Thread] = None
        self._last_screen = ""
        self._screen_callback: Optional[Callable[[str], None]] = None
        self._input_queue: list = []
        self.workdir = workdir or "/data/data/com.termux/files/home/dao/dao_workspace"
        self.command = command

        # Ensure session exists, then always send the command fresh
        if not session_exists(target_session):
            if create_session(target_session, workdir=self.workdir):
                time.sleep(0.5)  # Give shell time to initialize
            else:
                return  # Can't proceed without session
        else:
            # Session already exists — kill any running process before sending new command
            try:
                subprocess.run(
                    ['tmux', 'send-keys', '-t', target_session, 'C-c'],
                    capture_output=True, timeout=3
                )
                time.sleep(0.5)
            except Exception:
                pass

        # ALWAYS send the command if one was provided
        if self.command:
            if not session_exists(target_session):
                return

            try:
                # Send command directly (not via script wrapper)
                subprocess.run(
                    ['tmux', 'send-keys', '-t', target_session, self.command, 'Enter'],
                    capture_output=True, timeout=5
                )
                time.sleep(2.0)  # Give program time to initialize
            except Exception:
                pass

    def start(self, screen_callback: Callable[[str], None]):
        """Start continuous screen capture.
        
        Args:
            screen_callback: Function called with each screen update
        """
        self._screen_callback = screen_callback
        self.running = True
        self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._capture_thread.start()

    def stop(self):
        """Stop screen capture."""
        self.running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=2)

    def _capture_loop(self):
        """Continuously capture screen and call callback."""
        empty_count = 0
        
        while self.running:
            try:
                screen = self.capture_screen()
                
                # Detect if program exited (screen becomes small or shows shell prompt)
                if screen and len(screen) < 200:
                    empty_count += 1
                    # If screen has been small for 2 seconds (10 captures), program likely exited
                    if empty_count >= 10:
                        # Check for common shell prompt patterns
                        if any(prompt in screen for prompt in ['$ ', '# ', '% ', 'C:\\>', '>>>', '(venv)']):
                            self.running = False
                            break
                else:
                    empty_count = 0
                
                if screen != self._last_screen:
                    self._last_screen = screen
                    if self._screen_callback:
                        self._screen_callback(screen)
                time.sleep(0.2)  # 5 FPS update
            except Exception:
                time.sleep(1)

    def capture_screen(self, lines: int = 24) -> str:
        """Capture current screen from target session using file-based capture for curses support."""
        try:
            import os
            
            # Use workspace temp file for screen capture (not /tmp - permission issues)
            temp_file = '/data/data/com.termux/files/home/dao/dao_workspace/.screen_capture.txt'
            
            # Capture to file using shell redirection (more reliable for curses)
            # Note: no -E flag (defaults to end of visible pane), -S -100 = last 100 lines of scrollback
            subprocess.run(
                f"tmux capture-pane -p -J -t '{self.target_session}' -S -100 > '{temp_file}' 2>/dev/null",
                shell=True, timeout=5
            )
            
            # Read captured content
            if os.path.exists(temp_file):
                with open(temp_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Return content if it has meaningful data (not just spaces)
                if content and len(content) > 50:
                    return content

            # Fallback: direct capture
            result = subprocess.run(
                ['tmux', 'capture-pane', '-p', '-J', '-t', self.target_session, '-S', f'-{lines}'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout if result.stdout else ""

        except Exception as e:
            return f"ERROR capturing screen: {e}"

    def send_keys(self, text: str, enter: bool = True):
        """Send keystrokes to target session."""
        try:
            if enter:
                subprocess.run(
                    ['tmux', 'send-keys', '-t', self.target_session, text, 'Enter'],
                    capture_output=True, timeout=5
                )
            else:
                subprocess.run(
                    ['tmux', 'send-keys', '-t', self.target_session, text],
                    capture_output=True, timeout=5
                )
        except Exception as e:
            pass

    def send_ctrl(self, key: str):
        """Send Ctrl+key to target session."""
        try:
            subprocess.run(
                ['tmux', 'send-keys', '-t', self.target_session, f'C-{key}'],
                capture_output=True, timeout=5
            )
        except Exception as e:
            pass

    def queue_input(self, text: str, enter: bool = True):
        """Queue text to be sent to target session."""
        self._input_queue.append((text, enter))

    def process_input_queue(self):
        """Process all queued input."""
        while self._input_queue:
            text, enter = self._input_queue.pop(0)
            self.send_keys(text, enter)


# Global streamer instance
_streamer: Optional[ScreenStreamer] = None


def start_screen_stream(target_session: str, callback: Callable[[str], None], auto_create: bool = True, workdir: str = None, command: str = None):
    """Start streaming screen from target session.

    Args:
        target_session: tmux session name
        callback: Function to call with screen updates
        auto_create: Auto-create session if it doesn't exist (default: True)
        workdir: Working directory for session (default: dao_workspace)
        command: Optional command to run in session (default: interactive shell)
    """
    global _streamer
    _streamer = ScreenStreamer(target_session, auto_create, workdir, command)
    _streamer.start(callback)


def stop_screen_stream():
    """Stop screen streaming."""
    global _streamer
    if _streamer:
        _streamer.stop()
        _streamer = None


def send_to_screen(text: str, enter: bool = True):
    """Send text to streamed session."""
    if _streamer:
        _streamer.send_keys(text, enter)


def get_screen_streamer() -> Optional[ScreenStreamer]:
    """Get current screen streamer instance."""
    return _streamer

