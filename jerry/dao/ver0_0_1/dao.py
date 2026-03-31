#!/usr/bin/env python3
"""
Dao — Autonomous Qwen3.5 Agent  ·  ncurses TUI

Enhanced Features:
  · Modular architecture with separate components
  · Streaming output for real-time model responses
  · Professional aesthetic interface with improved visuals
  · Diary system for agent reflections
  · Expression tags for physical/emotional state (<smiling>, <laughing>, etc.)
  · Parallel message injection system for autonomous operation
  · Session archival with dated summaries, persona documents, and raw logs
  · Relative path system with enter/pwd tools
  · No timeouts - holds connections indefinitely
  · Enhanced agentic abilities with autonomous thinking

Worker model (port 8081) for file analysis with line numbers
Full Qwen-Code style tools: shell, file ops, search, line editing
Todo / plan system
User inbox → Dao checks and replies at will
"""

import curses
import threading
import os
import sys
import signal
import time
from datetime import datetime

from dao_core import (
    State,
    Worker,
    Executor,
    Agent,
    TUI,
    SessionManager,
    DAO_BASE,
    DIARY_DIR,
    LOGS_DIR,
    SUMMARY_DIR,
    PERSONA_DIR,
    AGENT_URL,
    WORKER_URL,
)

# ─── Redirect stdout/stderr to log file ────────────────────────────────────────
# This prevents debug prints from corrupting the curses display
def setup_logging():
    """Redirect stdout and stderr to log file before curses starts."""
    log_dir = os.path.join(DAO_BASE, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(log_dir, f"dao_stdout_{timestamp}.log")
    
    # Also create a symlink to latest log for easy access
    latest_link = os.path.join(log_dir, "dao_stdout.log")
    if os.path.exists(latest_link) or os.path.islink(latest_link):
        os.remove(latest_link)
    os.symlink(log_path, latest_link)
    
    # Redirect stdout and stderr
    sys.stdout = open(log_path, 'a', buffering=1)  # Line-buffered
    sys.stderr = sys.stdout
    
    print(f"=== Dao Session Started at {datetime.now().isoformat()} ===")
    print(f"Log file: {log_path}")
    return log_path

# ─── Helper Functions ──────────────────────────────────────────────────────────

def discover_local_files() -> list:
    """Discover local files in the dao_workspace directory for the model to be aware of."""
    files = []
    try:
        for root, dirs, filenames in os.walk(DAO_BASE):
            # Skip hidden directories and common non-essential dirs
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ('__pycache__', 'logs', 'summaries')]
            for fname in filenames:
                if fname.endswith(('.py', '.md', '.txt', '.json', '.yaml', '.yml')):
                    fpath = os.path.join(root, fname)
                    files.append(fpath)
    except Exception as e:
        pass
    return files


def ensure_directories():
    """Ensure all required directories exist."""
    for d in [DAO_BASE, DIARY_DIR, LOGS_DIR, SUMMARY_DIR, PERSONA_DIR]:
        os.makedirs(d, exist_ok=True)


# ─── Signal Handler for Clean Shutdown ─────────────────────────────────────────

def signal_handler(sig, frame):
    """Handle SIGINT (Ctrl+C) and SIGTERM for clean shutdown."""
    print("\n\n⚠️  Received shutdown signal, cleaning up...")
    try:
        from dao_core.screen_stream import stop_screen_stream
        stop_screen_stream()
    except Exception:
        pass
    try:
        from dao_core.terminal import stop_controller
        stop_controller()
    except Exception:
        pass
    # Kill tmux sessions to prevent orphans
    try:
        import subprocess
        subprocess.run(['tmux', 'kill-session', '-t', 'dao-control'], capture_output=True, timeout=2)
    except Exception:
        pass
    sys.exit(0)


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def main(stdscr):
    # Setup logging BEFORE curses starts (prevents display corruption)
    log_path = setup_logging()
    
    # Setup
    ensure_directories()

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    state    = State()
    worker   = Worker(state)
    executor = Executor(state, worker)
    tui      = TUI(state)
    agent    = Agent(state, executor, tui)  # Pass tui for token count updates
    session  = SessionManager(state)

    # Register TUI's update_screen as callback for stream mode
    state.set_screen_callback(tui.update_screen)

    # Discover and set local files
    local_files = discover_local_files()
    state.set_local_files(local_files)

    tui.setup(stdscr)

    state.push_log("system", "━━━ Dao Agent ━━━")
    state.push_log("system", f"Workspace: {DAO_BASE}")
    state.push_log("system", f"Agent model:  {AGENT_URL}")
    state.push_log("system", f"Worker model: {WORKER_URL}")
    state.push_log("system", "Type a message and press Enter to talk to Dao.")
    state.push_log("system", "↑↓ arrows scroll focused panel.  /help for commands.")
    state.push_log("system", "Tools: enter, pwd, execute_command, read_file, write_file, ...")
    state.push_log("system", "No timeouts - connections held indefinitely.")

    # Start agent in background thread
    t = threading.Thread(target=agent.run, daemon=True, name="dao-agent")
    t.start()

    try:
        # Use nodelay mode for non-blocking input
        stdscr.nodelay(True)
        _watchdog_check = time.time()

        while not state.quit:
            try:
                # Non-blocking getch - returns ERR immediately if no key
                key = stdscr.getch()
                if key != curses.ERR:
                    if not tui.handle_key(key):
                        break
                    # Drain any additional buffered keys (fast typing)
                    while True:
                        k2 = stdscr.getch()
                        if k2 == curses.ERR:
                            break
                        if not tui.handle_key(k2):
                            state.quit = True
                            break
            except curses.error:
                pass

            tui.render()

            # Watchdog: if the agent thread dies restart it so the UI stays live.
            # Check every 5 seconds to avoid overhead.
            now = time.time()
            if now - _watchdog_check >= 5.0:
                _watchdog_check = now
                if not t.is_alive():
                    state.push_log("error", "Agent thread died — restarting")
                    state.set_status("restarting…")
                    agent._stop = False  # Allow re-entry into the run loop
                    t = threading.Thread(target=agent.run, daemon=True, name="dao-agent")
                    t.start()

            # Small sleep to prevent CPU spinning and slow animations
            # 100ms = 10 FPS for smooth but not frantic animations
            time.sleep(0.1)
    finally:
        # Restore blocking mode before cleanup
        stdscr.nodelay(False)
        
        # Stop agent thread
        agent.stop()
        
        # Stop screen capture thread (if running)
        try:
            from dao_core.screen_stream import stop_screen_stream
            stop_screen_stream()
        except Exception:
            pass
        
        # Stop terminal controller (if running)
        try:
            from dao_core.terminal import stop_controller
            stop_controller()
        except Exception:
            pass
        
        # Kill tmux sessions created by Dao (prevent orphans)
        try:
            import subprocess
            subprocess.run(['tmux', 'kill-session', '-t', 'dao-control'], capture_output=True, timeout=2)
        except Exception:
            pass
        
        # Session shutdown - save summaries, persona, and logs
        session.on_shutdown()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Dao stopped.")
