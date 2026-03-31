#!/usr/bin/env python3
"""
Stream Mode Debug Test Program

This test program simulates what happens when the agent opens a stream session.
It shows:
1. What the TUI displays (your view)
2. What the agent receives (AI's view)
3. Real-time screen capture from the actual ScreenStreamer

Press:
  - 'a' : Show what would be sent to the agent
  - 's' : Show current screen capture
  - 'q' : Quit

This uses the ACTUAL codebase components, not a simulation.
"""

import curses
import time
import sys
import os

# Add dao to path
sys.path.insert(0, '/data/data/com.termux/files/home/dao')

from dao_core.screen_stream import ScreenStreamer, stop_screen_stream, get_screen_streamer
from dao_core.tui import set_current_screen, _current_screen


def get_command(stdscr):
    """Get command from user."""
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, " Stream Debug Test - Command Input ", curses.A_REVERSE)
    stdscr.addstr(2, 0, "Enter a command to run in the test session:", curses.A_BOLD)
    stdscr.addstr(4, 0, "Examples:", curses.A_DIM)
    stdscr.addstr(5, 0, "  - htop")
    stdscr.addstr(6, 0, "  - top")
    stdscr.addstr(7, 0, "  - vim /etc/hosts")
    stdscr.addstr(8, 0, "  - python3 myscript.py")
    stdscr.addstr(9, 0, "  - ls -la")
    stdscr.addstr(10, 0, "  - nano")
    stdscr.addstr(12, 0, "Command: ", curses.A_BOLD)
    stdscr.refresh()
    
    # Enable echo and input
    curses.echo()
    stdscr.nodelay(False)
    
    try:
        # Get input
        command = stdscr.getstr(12, 10, 200).decode('utf-8').strip()
    except:
        command = ""
    finally:
        curses.noecho()
        curses.curs_set(0)
    
    return command


def draw_box(stdscr, y, x, h, w, title=""):
    """Draw a bordered box."""
    try:
        # Corners
        stdscr.addch(y, x, curses.ACS_ULCORNER)
        stdscr.addch(y, x + w - 1, curses.ACS_URCORNER)
        stdscr.addch(y + h - 1, x, curses.ACS_LLCORNER)
        stdscr.addch(y + h - 1, x + w - 1, curses.ACS_LRCORNER)
        # Lines
        for i in range(1, w - 1):
            stdscr.addch(y, x + i, curses.ACS_HLINE)
            stdscr.addch(y + h - 1, x + i, curses.ACS_HLINE)
        for i in range(1, h - 1):
            stdscr.addch(y + i, x, curses.ACS_VLINE)
            stdscr.addch(y + i, x + w - 1, curses.ACS_VLINE)
        # Title
        if title:
            stdscr.addstr(y, x + 2, f" {title} ", curses.A_BOLD)
    except:
        pass


def main(stdscr):
    # Get command from user first
    command = get_command(stdscr)
    
    if not command:
        stdscr.clear()
        stdscr.addstr(0, 0, " No command entered. Exiting. ", curses.A_REVERSE)
        stdscr.addstr(2, 0, "Press any key to exit...")
        stdscr.refresh()
        stdscr.nodelay(False)
        stdscr.getch()
        return
    
    # Setup curses
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_CYAN, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)
    curses.init_pair(4, curses.COLOR_RED, -1)
    
    H, W = stdscr.getmaxyx()
    
    # Start a test tmux session
    test_session = "dao-test-stream"
    
    # Initialize ScreenStreamer (same as executor does)
    stdscr.clear()
    stdscr.addstr(0, 0, f"Starting test stream session: {test_session}...", curses.A_BOLD)
    stdscr.addstr(2, 0, f"Command: {command}", curses.A_DIM)
    stdscr.refresh()
    
    streamer = ScreenStreamer(test_session, auto_create=True, command=command)
    streamer.start(set_current_screen)
    
    time.sleep(2)  # Give program time to start
    
    last_update = 0
    show_agent_view = False
    show_agent_view_time = 0
    
    while True:
        H, W = stdscr.getmaxyx()
        
        # Get current screen from streamer
        current_screen = streamer.capture_screen()
        
        # Update TUI's global (same as real stream mode)
        if current_screen and len(current_screen) > 50:
            set_current_screen(current_screen)
        
        stdscr.clear()
        
        # Draw header
        header = f" Stream Debug Test | Session: {test_session} | Command: {command} "
        stdscr.addstr(0, 0, header[:W].ljust(W), curses.A_REVERSE)
        
        # Draw TUI view (left side)
        box_w = W // 2
        draw_box(stdscr, 2, 0, H - 4, box_w, "TUI View (What YOU See)")
        
        if current_screen and len(current_screen) > 50 and not current_screen.startswith("ERROR"):
            # Strip ANSI for display
            import re
            clean = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', current_screen)
            lines = clean.split('\n')
            for i, line in enumerate(lines[:(H-7)]):
                try:
                    stdscr.addstr(4 + i, 2, line[:box_w-4], curses.color_pair(1))
                except:
                    pass
        else:
            stdscr.addstr(4, 2, "No screen content yet...", curses.color_pair(4))
            stdscr.addstr(5, 2, f"Current screen length: {len(current_screen) if current_screen else 0}", 
                          curses.color_pair(4))
        
        # Draw Agent view or debug info (right side)
        if show_agent_view and (time.time() - show_agent_view_time < 5):
            # Show what agent would receive
            draw_box(stdscr, 2, box_w, H - 4, W - box_w, "Agent View (What AI Sees) - LAST CAPTURE")
            
            if current_screen and len(current_screen) > 50 and not current_screen.startswith("ERROR"):
                agent_text = (
                    f"\n\n[CURRENT TERMINAL SCREEN - View only, don't save to memory:]\n"
                    f"{current_screen[:3000]}\n"  # Truncated like agent gets it
                    f"[END SCREEN]\n"
                )
                lines = agent_text.split('\n')
                for i, line in enumerate(lines[:(H-7)]):
                    try:
                        stdscr.addstr(4 + i, box_w + 2, line[:W-box_w-4], curses.color_pair(2))
                    except:
                        pass
            else:
                stdscr.addstr(4, box_w + 2, "Agent would NOT see screen (content too short or error)", 
                              curses.color_pair(4))
                stdscr.addstr(5, box_w + 2, f"Length: {len(current_screen) if current_screen else 0} (need >50)", 
                              curses.color_pair(4))
        else:
            # Show debug stats
            draw_box(stdscr, 2, box_w, H - 4, W - box_w, "Debug Stats")
            
            stats = [
                f"Screen length: {len(current_screen) if current_screen else 0}",
                f"Has content: {len(current_screen) > 50 if current_screen else False}",
                f"Starts with ERROR: {current_screen.startswith('ERROR') if current_screen else False}",
                f"Streamer running: {streamer.running}",
                f"Target session: {streamer.target_session}",
                f"",
                f"Controls:",
                f"  'a' - Show agent view (5 sec)",
                f"  's' - Show raw screen capture",
                f"  'q' - Quit",
                f"",
                f"Last capture preview:",
            ]
            
            for i, stat in enumerate(stats):
                try:
                    stdscr.addstr(4 + i, box_w + 2, stat[:W-box_w-4], curses.color_pair(3))
                except:
                    pass
            
            # Show raw capture preview
            if current_screen:
                preview = current_screen[:200].replace('\n', '\\n')
                try:
                    stdscr.addstr(16, box_w + 2, preview[:W-box_w-4], curses.color_pair(2))
                except:
                    pass
        
        # Status bar
        status = f" Press 'a' for agent view | 's' for raw capture | 'q' quit "
        try:
            stdscr.addstr(H - 2, 0, status.center(W)[:W], curses.A_REVERSE)
        except:
            pass
        
        stdscr.refresh()
        
        # Handle input
        try:
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('a') or key == ord('A'):
                show_agent_view = True
                show_agent_view_time = time.time()
            elif key == ord('s') or key == ord('S'):
                # Show raw capture in a popup
                stdscr.clear()
                stdscr.addstr(0, 0, " Raw Screen Capture (press any key to continue) ", curses.A_REVERSE)
                if current_screen:
                    lines = current_screen.split('\n')
                    for i, line in enumerate(lines[:(H-2)]):
                        try:
                            stdscr.addstr(2 + i, 0, line[:W], curses.color_pair(2))
                        except:
                            pass
                else:
                    stdscr.addstr(2, 0, "No capture available", curses.color_pair(4))
                stdscr.refresh()
                stdscr.nodelay(False)
                stdscr.getch()
                stdscr.nodelay(True)
        except:
            pass
        
        time.sleep(0.1)
    
    # Cleanup
    streamer.stop()
    stop_screen_stream()
    
    # Kill test session
    try:
        import subprocess
        subprocess.run(['tmux', 'kill-session', '-t', test_session], capture_output=True, timeout=2)
    except:
        pass


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("\nTest program stopped.")
    print(f"\nCommand that was running: {command}")
    print("\nTo manually check the test session (if still running):")
    print(f"  tmux attach -t {test_session}")
    print(f"  tmux kill-session -t {test_session}")
