#!/usr/bin/env python3
"""Jerry — Configuration and Constants

Minimal startup context with on-demand tool discovery via help tool.
"""

import os
from typing import List, Dict

# ─── Directory Paths (Relative to this file's location) ────────────────────────
# This allows Jerry to run from any location
JERRY_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JERRY_BASE     = os.path.join(JERRY_BASE_DIR, "jerry_workspace")
DIARY_DIR      = os.path.join(JERRY_BASE, "diary")
LOGS_DIR       = os.path.join(JERRY_BASE_DIR, "logs")
SUMMARY_DIR    = os.path.join(JERRY_BASE, "summaries")
PERSONA_DIR    = os.path.join(JERRY_BASE, "persona")

# ─── API Endpoints ─────────────────────────────────────────────────────────────
# Default: Both agent and worker use the same port (8080)
# To use separate ports, change WORKER_PORT to 8081
AGENT_PORT   = int(os.environ.get("JERRY_AGENT_PORT", "8080"))
WORKER_PORT  = int(os.environ.get("JERRY_WORKER_PORT", str(AGENT_PORT)))  # Same as agent by default

AGENT_URL    = f"http://localhost:{AGENT_PORT}/v1/chat/completions"
WORKER_URL   = f"http://localhost:{WORKER_PORT}/v1/chat/completions"

# ─── Model Parameters ──────────────────────────────────────────────────────────
MAX_TOKENS   = 15000
TEMPERATURE  = 0.7
CYCLE_SLEEP  = 0.2  # Default minimum gap between agent cycles (seconds)

# ─── API Timeouts ─────────────────────────────────────────────────────────────
AGENT_TIMEOUT   = 120  # Seconds for agent API calls
WORKER_TIMEOUT  = 120  # Seconds for worker API calls

# ─── Limits ────────────────────────────────────────────────────────────────────
LOG_LIMIT    = 600
CONV_TRIM    = 60  # Keep last 60 messages (prevents 4k+ token issues with tool calls)
RAW_LOG_LIMIT = 10000

# ─── Tool Catalog (full descriptions for help tool) ────────────────────────────
_TOOL_CATALOG = {
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
        "description": "Read file with line numbers",
        "params": {"path": "str", "start_line": "int (default: 1)", "max_lines": "int (default: 500)", "load_worker": "bool (default: False) - set True to also load into worker for analysis"},
        "example": "read_file(path='main.py', max_lines=100) or read_file(path='config.py', load_worker=True) to enable worker queries",
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
        "description": "Ask worker AI about a file (auto-loads file if path provided)",
        "params": {"file": "str (optional) - path to file to load and analyze", "question": "str (required)", "extra_context": "str (optional)"},
        "example": "query_worker(file='config.py', question='What does the Config class do?') or query_worker(question='Continue analysis') if file already loaded",
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
    "ask_user": {
        "description": "Ask the user a question when you need clarification or decisions",
        "params": {"question": "str"},
        "example": "ask_user(question='What should I name the new file?')",
    },
    "load_multiple_files": {
        "description": "Load multiple files into worker for cross-file analysis",
        "params": {"files": "array of {path, content} objects"},
        "example": "load_multiple_files(files=[{'path': 'a.py', 'content': '...'}, {'path': 'b.py', 'content': '...'}])",
    },
    "worker_write_program": {
        "description": "Have worker AI write a program/file based on specifications (faster for initial drafts)",
        "params": {"path": "str", "spec": "str (detailed specification)", "language": "str (optional, default: python)"},
        "example": "worker_write_program(path='calculator.py', spec='A CLI calculator with add, subtract, multiply, divide functions', language='python')",
    },
}

# ─── Minimal Tool Set ──────────────────────────────────────────────────────────
# Ultra-minimal: just names + short descriptions. Agent uses help() for details.
from .tools_minimal import TOOLS

# ─── System Prompt ─────────────────────────────────────────────────────────────
# GENERIC — no personality, no agent instructions. Jerry's character lives
# in the persona prompt_prefix. Tool packs bundle their own behavioral prompts.
SYSTEM_PROMPT = """\
## Tool Calling

**Available tools:**

{tool_list}

**Call tools directly — no markdown, no XML tags.**
The system detects and executes tool calls automatically.
"""


def get_tool_catalog() -> Dict:
    """Return full tool catalog for help tool."""
    return _TOOL_CATALOG
