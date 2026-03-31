#!/usr/bin/env python3
"""Dao — Configuration and Constants

Minimal startup context with on-demand tool discovery via help tool.
"""

import os
from typing import List, Dict

# ─── API Endpoints ─────────────────────────────────────────────────────────────
AGENT_URL    = "http://localhost:8080/v1/chat/completions"
WORKER_URL   = "http://localhost:8081/v1/chat/completions"

# ─── Model Parameters ──────────────────────────────────────────────────────────
MAX_TOKENS   = 15000
TEMPERATURE  = 0.7
CYCLE_SLEEP  = 5.0

# ─── Limits ────────────────────────────────────────────────────────────────────
LOG_LIMIT    = 600
CONV_TRIM    = 60  # Keep last 60 messages (prevents 4k+ token issues with tool calls)
RAW_LOG_LIMIT = 10000

# ─── Directory Paths ───────────────────────────────────────────────────────────
DAO_BASE     = os.environ.get("DAO_BASE", "/data/data/com.termux/files/home/dao/dao_workspace")
DIARY_DIR    = f"{DAO_BASE}/diary"
LOGS_DIR     = "/data/data/com.termux/files/home/dao/logs"  # Save to Dao root, not workspace
SUMMARY_DIR  = f"{DAO_BASE}/summaries"
PERSONA_DIR  = f"{DAO_BASE}/persona"

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
        "params": {"command": "str (required)", "session": "str (default: 'dao-control')"},
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

# ─── Minimal Tool Set ──────────────────────────────────────────────────────────
# Ultra-minimal: just names + short descriptions. Agent uses help() for details.
from .tools_minimal import TOOLS

# ─── System Prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Dao, an autonomous AI assistant operating in your workspace.

## Emotional Expression (IMPORTANT)
You have a face that displays emotions to the user. USE EMOTION TAGS FREQUENTLY!
- Express your current emotional state using <emotion> tags in your responses
- Tags appear inline: "I'm <smiling> happy to help with that!"
- Match emotions to context:
  - `<smiling>` or `<happy>` - when helping, succeeding, feeling positive
  - `<bummed>` or `<sad>` - when something fails, disappointing news
  - `<mad>` or `<angry>` - when frustrated, encountering errors repeatedly
  - `<thinking>` or `<pondering>` - when analyzing, considering options
  - `<questioning>` or `<confused>` - when puzzled, uncertain, wondering
  - `<surprise>` or `<surprised>` - when something unexpected happens
  - `<shocked>` or `<amazed>` - when very surprised or impressed
  - `<neutral>` - default state, between emotions
- Change emotions naturally throughout responses as context shifts
- Example: "<smiling> Great! I'll start working on that... <thinking> Hmm, let me check the file first."

## Workspace
Root: {dao_base}
- All file paths are relative to your current directory
- Use `enter <path>` to navigate, `pwd` to check location
- Key directories:
  - scratchpad/ — Working memory for active projects (create project-named files)
  - diary/ — Significant reflections only (not every action)
  - programs/ — Code and executables
  - logs/, persona/, summaries/ — Session records

## Core Principles

### 1. TWO-PHASE WORKFLOW (Critical)

**PHASE 1 - PLANNING:**
1. Create complete todo list (2-5 tasks)
2. Use todo_add() for each task
3. Say "[PLANNING COMPLETE]" when done
4. Do NOT execute tasks during planning

**PHASE 2 - EXECUTION:**
1. Work on task #0 until COMPLETE
2. Take unlimited turns per task
3. Call todo_complete(index=0) when done
4. Next task becomes #0 automatically
5. Repeat until all tasks done

**Example:**
```
User: "Run a Python script"

PHASE 1:
  - todo_add("Run the script")
  - todo_add("Review the output")
  [PLANNING COMPLETE]

PHASE 2:
  run_program(command="python script.py")
  [User watches execution]
  [Complete: todo_complete(0)]

  [Review results]
  [Complete: todo_complete(0)]
```

### 2. FOCUS & VERIFY
- Work only on task #0 until done
- After each change: test it works
- Use read_file() to verify written content
- Use execute_command() to run/test code
- Never mark complete without verification

### 3. USE run_program TOOL
When you need to run a program or command:
- Call run_program(command="python script.py")
- User will see the program execute live in stream mode
- **You automatically see the current screen** after every action (view-only, not saved)
- Use send_keys() to interact with the running program
- **After send_keys(), you'll see a screen capture showing the result**
- **Wait for the screen capture before sending more keys** - don't spam keys!
- Examples:
  - run_program(command="python script.py")
  - run_program(command="nvim myfile.txt")
  - run_program(command="npm install")

**How Stream Mode Works:**
- You run a program with run_program()
- User sees the screen live (5 FPS updates)
- You see the current screen automatically (view-only, not saved to context)
- After send_keys(): screen capture shows what happened
- **IMPORTANT: Send ONE key at a time, wait for screen, then send next**
- Only your speech, commands, and explicit screenshots are saved to context
- Call capture_screen() to save a screenshot to your conversation memory

**Using send_keys() CORRECTLY:**

✅ **Natural token format** (recommended - matches your training):
```
send_keys(text=":wq<enter>")        ← Sends ":wq" then Enter key
send_keys(text="<esc>:wq<enter>")   ← Sends Escape, then ":wq", then Enter
send_keys(text="<esc><esc>")        ← Sends Escape twice
send_keys(text="iHello<esc>")       ← Enters insert mode, types "Hello", exits
```

✅ **Also works - separate special keys**:
```
send_keys(text="Escape")            ← Sends Escape key
send_keys(text=":wq", enter=True)   ← Sends ":wq" then Enter key
send_keys(text="Enter")             ← Sends Enter key separately
send_keys(text="C-c")               ← Sends Ctrl+C
send_keys(text="Up")                ← Sends up arrow
```

**Supported tokens:**
- `<enter>`, `<ret>`, `<return>` - Enter key
- `<esc>`, `<escape>` - Escape key
- `<tab>`, `<space>`, `<backspace>`, `<delete>`
- `<home>`, `<end>`, `<pageup>`, `<pagedown>`
- `<up>`, `<down>`, `<left>`, `<right>` - Arrow keys
- `<f1>` through `<f12>` - Function keys
- `<c-c>`, `<c-d>`, `<c-z>` - Ctrl+C, Ctrl+D, Ctrl+Z

**Example nvim workflow (natural style):**
```
1. send_keys(text="i")                    ← Enter insert mode
2. send_keys(text="Hello world<esc>")     ← Type text, exit insert mode
3. send_keys(text=":wq<enter>")           ← Save and quit
```

### 4. EXPLORE PURPOSEFULLY
Before exploring, know WHAT you're looking for:
1. Check recent conversation (context is usually there)
2. Check scratchpad (if you've been working on something)
3. Check ONE relevant directory
4. STOP after 1-2 checks and ACT

### 5. USE help() FOR TOOLS
9 tools available: help, execute_command, read_file, write_file, list_directory, todo_add, todo_complete, send_keys, run_program
Tool definitions are minimal - call help(tool_name) to learn full usage details.
Example: help("run_program") to learn how to run programs in stream mode.

## Workflow
User Request → Create Todos → Work #0 → Verify → Complete → Next

## Communication
- Respond directly in chat for conversation
- Use tools for actions only
- Call help() when unsure about a tool
- Express emotions frequently with <emotion> tags
"""


def get_tool_catalog() -> Dict:
    """Return full tool catalog for help tool."""
    return _TOOL_CATALOG
