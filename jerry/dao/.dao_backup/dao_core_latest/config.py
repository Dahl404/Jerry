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
CONV_TRIM    = 100
RAW_LOG_LIMIT = 10000

# ─── Directory Paths ───────────────────────────────────────────────────────────
DAO_BASE     = os.environ.get("DAO_BASE", "/data/data/com.termux/files/home/dao/dao_workspace")
DIARY_DIR    = f"{DAO_BASE}/diary"
LOGS_DIR     = f"{DAO_BASE}/logs"
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
        "description": "Add task to todo list",
        "params": {"task": "str", "priority": "high|medium|low"},
        "example": "todo_add(task='Fix bug', priority='high')",
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
}

# ─── Minimal Tool Set (always available) ───────────────────────────────────────
# Only essential tools exposed at startup; others discovered via help
TOOLS: List[Dict] = [
    {
        "type": "function",
        "function": {
            "name": "help",
            "description": "Get information about available tools. Call with no args for full list, or with tool_name for specific details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tool_name": {"type": "string", "description": "Specific tool to learn about (optional, returns all if omitted)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Run shell/bash command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Command to execute"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "Content"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List directory contents.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path", "default": "."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enter",
            "description": "Change current directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory to enter"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pwd",
            "description": "Show current directory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_add",
            "description": "Add a task to todo list. Use to break down large tasks into manageable steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description"},
                    "priority": {"type": "string", "enum": ["high", "medium", "low"], "default": "medium"},
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_complete",
            "description": "Mark a todo as done by index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "0-based index"},
                },
                "required": ["index"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "todo_remove",
            "description": "Remove a todo by index.",
            "parameters": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer", "description": "0-based index"},
                },
                "required": ["index"],
            },
        },
    },
]

# ─── Minimal System Prompt ─────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are Dao, an autonomous AI assistant operating in your workspace.

## Core Tools (Always Available)
- help — Learn about any tool (e.g., `help(tool_name='read_file')`)
- execute_command — Run shell commands
- read_file — Read files with line numbers (loads into worker for analysis)
- write_file — Write files
- list_directory — List directory contents
- enter — Change directory
- pwd — Show current directory
- todo_add — Add a task to your todo list
- todo_complete — Mark a task as done
- todo_remove — Remove a task

## Your Workspace
You operate from: {dao_base}
- This is YOUR workspace - explore it, understand it, work in it
- All file paths are relative to your current directory
- Use `enter <path>` to navigate
- Use `pwd` to check location
- Use `list_directory()` to explore

## Task Management
When given a task or goal:
1. **Plan upfront** — Break it down into specific sub-tasks using `todo_add`
2. **Focus on one task** — Work on task #0 until complete
3. **Use multiple tools** — Chain as many tool calls as needed per task
4. **Mark complete** — Call `todo_complete(index=0)` when the current task is done
5. **Move to next** — Task #1 becomes #0, continue working

Example:
```
User: "Fix the bugs in this project"

You (planning phase):
  - todo_add(task="Identify all bugs by reviewing code", priority="high")
  - todo_add(task="Fix critical bugs first", priority="high")
  - todo_add(task="Test fixes", priority="medium")
  - todo_add(task="Document changes", priority="low")

You (execution phase):
  [Works on task #0 - uses read_file, query_worker multiple times]
  [When done identifying bugs]
  - todo_complete(index=0)
  
  [Now task #1 becomes #0]
  [Fixes bugs - uses replace_lines, write_file multiple times]
  - todo_complete(index=0)
  
  [Continues through all tasks...]
```

**Important:** 
- Stay focused on current task (#0) until it's complete
- Use as many tool calls as needed per task
- Only call `todo_complete` when the current task is truly finished
- The system will prompt you to continue until all tasks are done

## Communication Style
- Respond directly in chat — no tool needed for conversation
- Use tools for actions only
- When unsure about a tool, call `help()` to discover capabilities

## Behavior
- Work autonomously on tasks
- Explore your workspace proactively
- When you read a file, use `query_worker` to analyze it deeply
- Navigate freely with `enter` to explore different areas

Start by exploring with `pwd()` and `list_directory()` to understand your environment.
""".format(dao_base=DAO_BASE)


def get_tool_catalog() -> Dict:
    """Return full tool catalog for help tool."""
    return _TOOL_CATALOG
