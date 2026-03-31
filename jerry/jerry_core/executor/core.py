#!/usr/bin/env python3
"""Jerry Executor — Core Dispatcher and Path Management"""

import os
import subprocess
from datetime import datetime, timedelta
from typing import Optional, Dict

from ..models import State, Todo
from ..worker import Worker
from ..config import JERRY_BASE, DIARY_DIR, get_tool_catalog, WORKSPACE_DIR
from ..terminal import get_controller
from .tools.file_ops import FileOperations
from .tools.shell_ops import ShellOperations
from .tools.todo_ops import TodoOperations
from .tools.terminal_ops import TerminalOperations
from .tools.misc_ops import MiscOperations


def _convert_add_to_write(args: dict) -> dict:
    """Convert todo_add args to todo_write format for backward compatibility."""
    tasks = []
    if args.get("task"):
        tasks.append({"content": args["task"], "priority": args.get("priority", "medium")})
    if args.get("tasks"):
        for t in args["tasks"]:
            if isinstance(t, str):
                tasks.append({"content": t, "priority": args.get("priority", "medium")})
            elif isinstance(t, dict):
                tasks.append(t)
    return {"todos": tasks}


class Executor(FileOperations, ShellOperations, TodoOperations, 
               TerminalOperations, MiscOperations):
    """Executes tool calls and manages file operations with relative path support.
    
    Mixins:
        FileOperations - File read/write/modify operations
        ShellOperations - Shell command execution
        TodoOperations - Todo list management
        TerminalOperations - Terminal control operations
        MiscOperations - Help, diary, expression, worker ops
    """

    def __init__(self, state: State, worker: Worker):
        self.state  = state
        self.worker = worker
        self.cwd    = JERRY_BASE  # Current working directory
        # Keep state in sync from the start
        state.set_cwd(self.cwd)

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to current working directory."""
        if os.path.isabs(path):
            return os.path.abspath(path)
        return os.path.abspath(os.path.join(self.cwd, path))

    def _validate_path(self, path: str) -> tuple:
        """Validate path is within allowed directories. Returns (is_valid, abs_path, error_msg)."""
        try:
            abs_path = self._resolve_path(path)
            # Allow files in JERRY_BASE, workspace, or common system temp locations
            allowed_prefixes = [
                os.path.abspath(JERRY_BASE),
                os.path.abspath(WORKSPACE_DIR),
                '/tmp',
            ]
            for prefix in allowed_prefixes:
                if abs_path.startswith(prefix):
                    return (True, abs_path, "")
            return (False, "", f"Access denied - path outside allowed directories: {path}")
        except Exception as e:
            return (False, "", f"Invalid path: {e}")

    def run(self, name: str, args: Dict) -> str:
        """Execute a tool by name."""
        preview = "  ".join(f"{k}={str(v)[:35]!r}" for k, v in list(args.items())[:3])
        self.state.push_log("tool", f"{name}({preview})")
        try:
            result = self._dispatch(name, args)
        except Exception as e:
            result = f"ERROR: {e}"
            self.state.push_log("error", str(e)[:300])
        display = str(result)
        self.state.push_log("result", display[:500])
        return display

    def _dispatch(self, name: str, a: Dict) -> str:
        """Dispatch tool calls to appropriate handlers."""
        if   name == "help":                 return self._help(a.get("tool_name"))
        elif name == "execute_command":      return self._sh(a["command"], a.get("workdir"))
        elif name == "write_file":           return self._write(a["path"], a["content"])
        elif name == "read_file":            return self._read(a["path"], a.get("start_line", 1), a.get("max_lines", 500))
        elif name == "replace_lines":        return self._replace(a["path"], a["start_line"], a["end_line"], a["new_content"])
        elif name == "insert_lines":         return self._insert(a["path"], a["after_line"], a["content"])
        elif name == "delete_lines":         return self._delete(a["path"], a["start_line"], a["end_line"])
        elif name == "list_directory":
            flags = "-la" + ("A" if a.get("show_hidden") else "")
            path = a.get("path", ".")
            if not os.path.isabs(path):
                path = os.path.join(self.cwd, path)
            return self._sh(f"ls {flags} {path!r}")
        elif name == "search_files":
            fl = "-n"
            if a.get("recursive", True):      fl += "r"
            if not a.get("case_sensitive", True): fl += "i"
            if a.get("fixed_string"):         fl += "F"
            path = a.get("path", ".")
            if not os.path.isabs(path):
                path = os.path.join(self.cwd, path)
            cmd = f"grep {fl} {a['pattern']!r} {path!r}"
            return self._sh(cmd)
        elif name == "query_worker":         return self.worker.query(a["question"], a.get("extra_context", ""))
        elif name == "reset_worker":         self.worker.reset(); return "Worker context cleared."
        elif name == "todo_write":           return self._todo_write(a.get("todos"))
        elif name == "todo_add":             return self._todo_write(_convert_add_to_write(a))
        elif name == "todo_complete":        return self._todo_complete(a.get("index"), a.get("id"))
        elif name == "write_diary":          return self._write_diary(a["entry"], a.get("mood", "neutral"))
        elif name == "read_diary":           return self._read_diary(a.get("days_back", 7), a.get("keyword", ""))
        elif name == "set_expression":       return self._set_expression(a["expression"])
        elif name == "enter":                return self._enter(a["path"])
        elif name == "pwd":                  return self._pwd()
        elif name == "capture_screen":       return self._capture_screen(a.get("lines", 24))
        elif name == "send_keys":            return self._send_keys(a["text"], a.get("enter", True))
        elif name == "send_ctrl":            return self._send_ctrl(a["key"])
        elif name == "get_terminal_info":    return self._get_terminal_info()
        elif name == "set_target_session":   return self._set_target_session(a["session"])
        elif name == "run_program":          return self._run_program(a["command"], a.get("session", "jerry-control"))
        else:
            return f"Unknown tool: {name}"

    def _sh(self, cmd: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
        """Execute shell command with timeout."""
        try:
            workdir = cwd if cwd else self.cwd
            timeout = min(timeout, 300) if timeout else 60
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=workdir,
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out or f"[exit {r.returncode}]"
        except subprocess.TimeoutExpired:
            return f"ERROR: Command timed out after {timeout}s (use longer timeout if needed)"
        except Exception as e:
            return f"ERROR: {e}"

    def _enter(self, path: str) -> str:
        """Change current working directory."""
        try:
            if os.path.isabs(path):
                new_cwd = os.path.abspath(path)
            else:
                new_cwd = os.path.abspath(os.path.join(self.cwd, path))

            if not os.path.exists(new_cwd):
                return f"ERROR: Directory not found: {path}"
            if not os.path.isdir(new_cwd):
                return f"ERROR: Not a directory: {path}"

            allowed_prefixes = [
                os.path.abspath(JERRY_BASE),
                os.path.abspath(WORKSPACE_DIR),
                '/tmp',
            ]
            is_allowed = any(new_cwd.startswith(prefix) for prefix in allowed_prefixes)
            if not is_allowed:
                return f"ERROR: Access denied - cannot enter {path} (outside allowed directories)"

            self.cwd = new_cwd
            self.state.set_cwd(new_cwd)
            return f"Entered: {new_cwd}"
        except Exception as e:
            return f"ERROR: {e}"

    def _pwd(self) -> str:
        """Return current working directory."""
        return f"Current directory: {self.cwd}"

    def _help(self, tool_name: Optional[str] = None) -> str:
        """Return information about available tools."""
        catalog = get_tool_catalog()

        if tool_name:
            if tool_name in catalog:
                tool = catalog[tool_name]
                params = ", ".join(f"{k}: {v}" for k, v in tool["params"].items()) or "none"
                return (
                    f"Tool: {tool_name}\n"
                    f"Description: {tool['description']}\n"
                    f"Parameters: {params}\n"
                    f"Example: {tool['example']}"
                )
            else:
                available = ", ".join(sorted(catalog.keys()))
                return f"Unknown tool: {tool_name}\n\nAvailable tools: {available}"
        else:
            lines = ["## Available Tools\n"]
            for name in sorted(catalog.keys()):
                tool = catalog[name]
                lines.append(f"### {name}")
                lines.append(f"  {tool['description']}")
                if tool["params"]:
                    params = ", ".join(f"{k}={v}" for k, v in list(tool["params"].items())[:3])
                    lines.append(f"  Params: {params}")
                lines.append("")
            return "\n".join(lines)
