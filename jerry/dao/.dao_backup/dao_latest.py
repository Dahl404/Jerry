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
import time

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


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def main(stdscr):
    # Setup
    ensure_directories()

    state    = State()
    worker   = Worker(state)
    executor = Executor(state, worker)
    agent    = Agent(state, executor)
    tui      = TUI(state)
    session  = SessionManager(state)

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

            # Small sleep to prevent CPU spinning and slow animations
            # 100ms = 10 FPS for smooth but not frantic animations
            time.sleep(0.1)
    finally:
        # Restore blocking mode before cleanup
        stdscr.nodelay(False)
        agent.stop()
        # Session shutdown - save summaries, persona, and logs
        session.on_shutdown()

    # Also save a final summary on normal exit
    session.on_shutdown()


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Dao stopped.")
