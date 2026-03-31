#!/usr/bin/env python3
"""Jerry — Tool Catalog for Help Tool

Full tool descriptions used by the help() tool.
"""

# ─── Tool Catalog (full descriptions for help tool) ────────────────────────────
TOOL_CATALOG = {
    "execute_command": {
        "description": "Run shell/bash commands",
        "params": {"command": "str", "timeout": "int (default: 60)", "workdir": "str (optional)"},
        "example": "execute_command(command='ls -la')",
    },
    "write_file": {
        "description": "Write content to a file",
        "params": {"path": "str", "content": "str"},
        "example": "write_file(path='test.txt', content='hello')",
    },
    "read_file": {
        "description": "Read file with line numbers, loads into worker context",
        "params": {"path": "str", "start_line": "int (default: 1)", "max_lines": "int (default: 500)"},
        "example": "read_file(path='main.py', max_lines=100)",
    },
    "replace_lines": {
        "description": "Replace line range in file (use after read_file)",
        "params": {"path": "str", "start_line": "int", "end_line": "int", "new_content": "str"},
        "example": "replace_lines(path='main.py', start_line=10, end_line=20, new_content='...')",
    },
    "insert_lines": {
        "description": "Insert lines after given line number",
        "params": {"path": "str", "after_line": "int", "content": "str"},
        "example": "insert_lines(path='main.py', after_line=5, content='new code')",
    },
    "delete_lines": {
        "description": "Delete line range from file",
        "params": {"path": "str", "start_line": "int", "end_line": "int"},
        "example": "delete_lines(path='main.py', start_line=10, end_line=15)",
    },
    "list_directory": {
        "description": "List directory contents",
        "params": {"path": "str (default: '.')", "show_hidden": "bool", "long_format": "bool"},
        "example": "list_directory(path='.', show_hidden=False)",
    },
    "search_files": {
        "description": "Search files with grep",
        "params": {"pattern": "str", "path": "str (default: '.')", "recursive": "bool", "case_sensitive": "bool"},
        "example": "search_files(pattern='TODO', recursive=True)",
    },
    "query_worker": {
        "description": "Ask worker AI about loaded file",
        "params": {"question": "str", "extra_context": "str (optional)"},
        "example": "query_worker(question='What does this function do?')",
    },
    "reset_worker": {
        "description": "Clear worker conversation history",
        "params": {},
        "example": "reset_worker()",
    },
    "todo_add": {
        "description": "Add task(s) to todo list",
        "params": {"task": "str (single task)", "tasks": "array of str (multiple tasks)", "priority": "high|medium|low"},
        "example": "todo_add(tasks=['Task 1', 'Task 2', 'Task 3'], priority='high')",
    },
    "todo_complete": {
        "description": "Mark todo as done by index",
        "params": {"index": "int (0-based)"},
        "example": "todo_complete(index=0)",
    },
    "todo_remove": {
        "description": "Remove todo by index",
        "params": {"index": "int (0-based)"},
        "example": "todo_remove(index=0)",
    },
    "write_diary": {
        "description": "Write reflection to diary",
        "params": {"entry": "str", "mood": "str (default: neutral)"},
        "example": "write_diary(entry='Learned something new', mood='curious')",
    },
    "read_diary": {
        "description": "Read past diary entries",
        "params": {"days_back": "int (default: 7)", "keyword": "str (optional)"},
        "example": "read_diary(days_back=3)",
    },
    "set_expression": {
        "description": "Set emotional/physical state",
        "params": {"expression": "str (e.g., '<smiling>', '<thinking>')"},
        "example": "set_expression(expression='<focused>')",
    },
    "enter": {
        "description": "Change current working directory",
        "params": {"path": "str"},
        "example": "enter(path='src/components')",
    },
    "pwd": {
        "description": "Show current working directory",
        "params": {},
        "example": "pwd()",
    },
    "run_program": {
        "description": "Run a program/command and show it to user in stream mode",
        "params": {"command": "str (required)", "session": "str (default: 'jerry-control')"},
        "example": "run_program(command='python programs/games/arcade_game/game.py')",
    },
    "send_keys": {
        "description": "Send keystrokes to terminal (type text, commands, or interact with programs)",
        "params": {"text": "str (required)", "enter": "bool (default: True)"},
        "example": "send_keys(text='ls -la', enter=True) or send_keys(text=' ', enter=False) for spacebar",
    },
    "capture_screen": {
        "description": "Capture current terminal screen content",
        "params": {"lines": "int (default: 24)"},
        "example": "capture_screen(lines=24)",
    },
    "send_ctrl": {
        "description": "Send control sequence like Ctrl+C, Ctrl+Z",
        "params": {"key": "str (e.g., 'C' for Ctrl+C)"},
        "example": "send_ctrl(key='C') for Ctrl+C",
    },
    "get_terminal_info": {
        "description": "Check terminal control capabilities",
        "params": {},
        "example": "get_terminal_info()",
    },
    "set_target_session": {
        "description": "Set target tmux session for terminal control",
        "params": {"session": "str"},
        "example": "set_target_session(session='coding')",
    },
}


def get_tool_catalog():
    """Return full tool catalog for help tool."""
    return TOOL_CATALOG
