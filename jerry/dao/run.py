#!/usr/bin/env python3
"""
Dao Launcher — Auto-starts tmux and runs Dao inside it

This wrapper automatically:
1. Checks if running inside tmux
2. If not, starts a new tmux session and runs Dao inside it
3. If yes, runs Dao directly
"""

import os
import sys
import subprocess

def is_inside_tmux():
    """Check if we're running inside a tmux session."""
    return 'TMUX' in os.environ

def check_tmux_installed():
    """Check if tmux is installed."""
    try:
        result = subprocess.run(['tmux', '-V'], capture_output=True, timeout=2)
        return result.returncode == 0
    except Exception:
        return False

def run_in_tmux():
    """Start a new tmux session and run Dao inside it."""
    session_name = "dao"
    
    # Get the path to this script
    script_path = os.path.abspath(__file__)
    dao_dir = os.path.dirname(script_path)
    
    print("🔧 Starting Dao in tmux session...")
    print(f"   Session name: {session_name}")
    print(f"   Working directory: {dao_dir}")
    print()
    print("💡 To reconnect later: tmux attach -t {session_name}")
    print("💡 To detach: Ctrl+B, then D")
    print()
    
    # Start tmux with Dao inside
    try:
        # Change to dao directory and run the main dao.py
        os.chdir(dao_dir)
        subprocess.run(['tmux', 'new', '-s', session_name, 'python3', 'dao.py'])
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

def run_directly():
    """Run Dao directly (already inside tmux or user chose not to use tmux)."""
    # Import and run the main Dao application
    from dao import main
    import curses
    
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("Dao stopped.")

def main():
    """Main launcher logic."""
    # Check if already in tmux
    if is_inside_tmux():
        print("✓ Running inside tmux - terminal control enabled!")
        run_directly()
        return
    
    # Check if tmux is installed
    if not check_tmux_installed():
        print("⚠️  tmux is not installed!")
        print()
        print("For full terminal control (nvim, htop, etc.), install tmux:")
        print("  pkg install tmux")
        print()
        print("Running without tmux - terminal control features will be limited.")
        print()
        choice = input("Continue without tmux? [y/N]: ").strip().lower()
        if choice == 'y':
            run_directly()
        else:
            print("Install tmux and try again!")
            sys.exit(0)
        return
    
    # Not in tmux, but tmux is available - offer to use it
    print("📦 Dao works best inside tmux for terminal control.")
    print()
    print("Options:")
    print("  1. Start in tmux (recommended) - full terminal control")
    print("  2. Run without tmux - limited functionality")
    print()
    
    choice = input("Choice [1/2]: ").strip()
    
    if choice == "1" or choice == "":
        run_in_tmux()
    else:
        print("Running without tmux...")
        run_directly()

if __name__ == "__main__":
    main()
