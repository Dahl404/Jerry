#!/usr/bin/env python3
"""Dao — Tool Executor with Relative Path Support"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from .models import State, Todo
from .worker import Worker
from .config import DAO_BASE, DIARY_DIR, get_tool_catalog
from .terminal import get_controller


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


class Executor:
    """Executes tool calls and manages file operations with relative path support."""

    def __init__(self, state: State, worker: Worker):
        self.state  = state
        self.worker = worker
        self.cwd    = DAO_BASE  # Current working directory
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
            # Allow files in DAO_BASE or common system temp locations
            allowed_prefixes = [os.path.abspath(DAO_BASE), '/tmp', '/data/data/com.termux/cache']
            for prefix in allowed_prefixes:
                if abs_path.startswith(prefix):
                    return (True, abs_path, "")
            return (False, "", f"Access denied - path outside allowed directories: {path}")
        except Exception as e:
            return (False, "", f"Invalid path: {e}")

    def run(self, name: str, args: Dict) -> str:
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

    # ── Dispatcher ─────────────────────────────────────────────────────────────
    def _dispatch(self, name: str, a: Dict) -> str:
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
        elif name == "todo_add":             return self._todo_write(_convert_add_to_write(a))  # Backward compat
        elif name == "todo_complete":        return self._todo_complete(a.get("index"), a.get("id"))
        elif name == "write_diary":          return self._write_diary(a["entry"], a.get("mood", "neutral"))
        elif name == "read_diary":           return self._read_diary(a.get("days_back", 7), a.get("keyword", ""))
        elif name == "set_expression":       return self._set_expression(a["expression"])
        elif name == "enter":                return self._enter(a["path"])
        elif name == "pwd":                  return self._pwd()
        # Terminal control tools
        elif name == "capture_screen":       return self._capture_screen(a.get("lines", 24))
        elif name == "send_keys":            return self._send_keys(a["text"], a.get("enter", True))
        elif name == "send_ctrl":            return self._send_ctrl(a["key"])
        elif name == "get_terminal_info":    return self._get_terminal_info()
        elif name == "set_target_session":   return self._set_target_session(a["session"])
        elif name == "run_program":           return self._run_program(a["command"], a.get("session", "dao-control"))
        else:
            return f"Unknown tool: {name}"

    # ── Shell ──────────────────────────────────────────────────────────────────
    def _sh(self, cmd: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
        """Execute shell command with timeout to prevent freezing.
        
        Args:
            cmd: Shell command to execute
            cwd: Working directory (default: self.cwd)
            timeout: Timeout in seconds (default: 60, max: 300)
        """
        try:
            # Use cwd from args, or fall back to self.cwd
            workdir = cwd if cwd else self.cwd
            # Cap timeout at 5 minutes to prevent permanent hangs
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

    # ── Enter directory ────────────────────────────────────────────────────────
    def _enter(self, path: str) -> str:
        """Change current working directory."""
        try:
            # Resolve the path
            if os.path.isabs(path):
                new_cwd = os.path.abspath(path)
            else:
                new_cwd = os.path.abspath(os.path.join(self.cwd, path))
            
            # Validate it exists and is a directory
            if not os.path.exists(new_cwd):
                return f"ERROR: Directory not found: {path}"
            if not os.path.isdir(new_cwd):
                return f"ERROR: Not a directory: {path}"
            
            # Validate it's within allowed directories
            allowed_prefixes = [os.path.abspath(DAO_BASE), '/tmp', '/data/data/com.termux/cache']
            is_allowed = any(new_cwd.startswith(prefix) for prefix in allowed_prefixes)
            if not is_allowed:
                return f"ERROR: Access denied - cannot enter {path} (outside allowed directories)"
            
            self.cwd = new_cwd
            self.state.set_cwd(new_cwd)   # Keep State in sync
            return f"Entered: {new_cwd}"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Print working directory ────────────────────────────────────────────────
    def _pwd(self) -> str:
        """Return current working directory."""
        return f"Current directory: {self.cwd}"

    # ── Help tool ──────────────────────────────────────────────────────────────
    def _help(self, tool_name: Optional[str] = None) -> str:
        """Return information about available tools."""
        catalog = get_tool_catalog()
        
        if tool_name:
            # Return specific tool info
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
            # Return full catalog summary
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

    # ── File write ─────────────────────────────────────────────────────────────
    def _write(self, path: str, content: str) -> str:
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        try:
            d = os.path.dirname(abs_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Wrote {len(content):,} chars → {path}"
        except Exception as e:
            return f"ERROR: {e}"

    # ── File read (loads into worker) ──────────────────────────────────────────
    def _read(self, path: str, start: int, maxl: int) -> str:
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
            total = len(all_lines)
            end   = min(start - 1 + maxl, total)
            chunk = all_lines[start - 1 : end]
            w     = len(str(end))
            numbered = "".join(
                f"{str(start + i).rjust(w)} │ {ln}" for i, ln in enumerate(chunk)
            )
            # Load into worker
            self.worker.load(abs_path, numbered)
            note = f"\n[Lines {start}–{end} of {total} total]"
            return numbered + note
        except Exception as e:
            return f"ERROR: {e}"

    # ── Line replace ───────────────────────────────────────────────────────────
    def _replace(self, path: str, s: int, e: int, new: str) -> str:
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        if s < 1 or e < s:
            return f"ERROR: Invalid line range: {s}-{e} (must be 1-indexed, start <= end)"
        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Split new content into lines, preserving newlines
            new_lines = new.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines[:s - 1] + new_lines + lines[e:])
            return f"Replaced lines {s}–{e} ({e-s+1} lines → {len(new_lines)} lines) in {path}"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Line insert ────────────────────────────────────────────────────────────
    def _insert(self, path: str, after: int, content: str) -> str:
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        if after < 0:
            return f"ERROR: Invalid line number: {after} (must be >= 0)"
        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = content.splitlines(keepends=True)
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines[-1] += "\n"
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines[:after] + new_lines + lines[after:])
            return f"Inserted {len(new_lines)} lines after line {after} in {path}"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Line delete ────────────────────────────────────────────────────────────
    def _delete(self, path: str, s: int, e: int) -> str:
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        if s < 1 or e < s:
            return f"ERROR: Invalid line range: {s}-{e} (must be 1-indexed, start <= end)"
        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            del lines[s - 1 : e]
            with open(abs_path, "w", encoding="utf-8") as f:
                f.writelines(lines)
            return f"Deleted lines {s}–{e} from {path}"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Todo ops ───────────────────────────────────────────────────────────────
    def _tadd(self, task: str = None, tasks: list = None, priority: str = "medium") -> str:
        """Add todo(s). Accepts single task or array of tasks."""
        with self.state._lock:
            if tasks and isinstance(tasks, list):
                # Batch add multiple tasks
                for t in tasks:
                    if t.strip():
                        self.state.todos.append(Todo(t.strip(), priority))
                return f"Added {len(tasks)} tasks"
            elif task:
                # Single task
                self.state.todos.append(Todo(task, priority))
                return f"Added: {task}"
            else:
                return "ERROR: No task(s) provided"

    def _tdone(self, idx: int = None, todo_id: int = None) -> str:
        """Mark a todo complete by stable id (preferred) or positional index."""
        with self.state._lock:
            # Prefer stable ID lookup — immune to index shifts from concurrent adds
            if todo_id is not None:
                for t in self.state.todos:
                    if t.id == todo_id:
                        t.done = True
                        return f"Completed (id={todo_id}): {t.text}"
                return f"No todo with id={todo_id}"
            # Fallback: positional index (model default: index=0)
            if idx is not None and 0 <= idx < len(self.state.todos):
                self.state.todos[idx].done = True
                return f"Completed #{idx}: {self.state.todos[idx].text}"
            return f"No todo at index {idx}"

    def _trem(self, idx: int) -> str:
        with self.state._lock:
            if 0 <= idx < len(self.state.todos):
                t = self.state.todos.pop(idx)
                return f"Removed: {t.text}"
            return f"No todo at index {idx}"

    # ── Todo Write (Qwen-Code CLI style) ───────────────────────────────────────
    def _todo_write(self, todos: list) -> str:
        """Add new tasks to the todo list (doesn't replace existing)."""
        try:
            if not todos or not isinstance(todos, list):
                return "ERROR: todo_write requires a list of todos"

            with self.state._lock:
                # Add new tasks (existing tasks keep their IDs)
                for i, todo in enumerate(todos):
                    if isinstance(todo, str):
                        self.state.todos.append(Todo(todo, "medium"))
                    elif isinstance(todo, dict):
                        content = todo.get("content", "Untitled task")
                        priority = todo.get("priority", "medium")
                        completed = todo.get("completed", False)
                        self.state.todos.append(Todo(content, priority))
                        if completed:
                            self.state.todos[-1].done = True

            # Show tasks with their stable IDs
            task_list = []
            for i, t in enumerate(self.state.todos):
                status = "✓" if t.done else "○"
                task_list.append(f"  {status} #{t.id}: {t.text}")
            
            return f"✓ Todo list:\n" + "\n".join(task_list)
        except Exception as e:
            return f"ERROR: {e}"

    # ── Todo Complete (Qwen-Code CLI style) ────────────────────────────────────
    def _todo_complete(self, index: int = None, id: int = None) -> str:
        """Mark a todo as complete by ID (preferred) or index."""
        try:
            with self.state._lock:
                if not self.state.todos:
                    return "ERROR: No todos to complete"

                # If id is specified, use it (preferred method)
                if id is not None:
                    for todo in self.state.todos:
                        if todo.id == id:
                            todo.done = True
                            return f"✓ Completed task #{id}: {todo.text}"
                    return f"ERROR: No task with id={id}"

                # If index specified, find the task at that position
                if index is not None:
                    if index < 0 or index >= len(self.state.todos):
                        return f"ERROR: Invalid index {index}"
                    self.state.todos[index].done = True
                    return f"✓ Completed task #{self.state.todos[index].id}: {self.state.todos[index].text}"

                # No index or id - find first pending task
                for todo in self.state.todos:
                    if not todo.done:
                        todo.done = True
                        return f"✓ Completed task #{todo.id}: {todo.text}"
                
                return "✓ All tasks already complete!"
        except Exception as e:
            return f"ERROR: {e}"

    # ── Diary ops ──────────────────────────────────────────────────────────────
    def _write_diary(self, entry: str, mood: str) -> str:
        os.makedirs(DIARY_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = f"{DIARY_DIR}/{date_str}.md"

        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n## [{timestamp}] ({mood})\n\n{entry}\n")
        return f"Diary entry written → {filepath}"

    def _read_diary(self, days_back: int, keyword: str) -> str:
        if not os.path.exists(DIARY_DIR):
            return "No diary entries found."

        entries = []
        cutoff = datetime.now() - timedelta(days=days_back)

        for fname in sorted(os.listdir(DIARY_DIR), reverse=True):
            if not fname.endswith(".md"):
                continue
            fpath = f"{DIARY_DIR}/{fname}"
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            if keyword and keyword.lower() not in content.lower():
                continue

            entries.append(f"=== {fname} ===\n{content}")

        if not entries:
            return f"No diary entries found for the last {days_back} days."

        return "\n\n".join(entries[:10])  # Limit to 10 entries

    # ── Expression ops ─────────────────────────────────────────────────────────
    def _set_expression(self, expr: str) -> str:
        self.state.set_expression(expr)
        return f"Expression set: {expr}"

    # ── Terminal control ops ───────────────────────────────────────────────────
    def _capture_screen(self, lines: int) -> str:
        """Capture terminal screen content."""
        controller = get_controller()
        return controller.capture_screen(lines)

    def _send_keys(self, text: str, enter: bool) -> str:
        """Send keystrokes to terminal with support for special key tokens.
        
        Supports natural token formats like <enter>, <esc>, <tab>, etc.
        which are parsed and sent as actual special keys.
        """
        controller = get_controller()
        
        # Parse and send special key tokens
        results = []
        import re
        
        # Pattern to match <key> tokens
        token_pattern = r'<(\w+)>'
        
        # Split text by tokens
        parts = re.split(token_pattern, text)
        
        for i, part in enumerate(parts):
            if not part:
                continue
                
            # Check if this is a token (odd indices in split result are the captured groups)
            if i % 2 == 1:
                # This is a token name like "enter", "esc", etc.
                token = part.lower()
                
                # Map common token names to special key names
                token_map = {
                    'enter': 'Enter',
                    'ret': 'Enter',
                    'return': 'Enter',
                    'esc': 'Escape',
                    'escape': 'Escape',
                    'tab': 'Tab',
                    'space': ' ',
                    'spacebar': ' ',
                    'backspace': 'Backspace',
                    'bs': 'Backspace',
                    'delete': 'Delete',
                    'del': 'Delete',
                    'home': 'Home',
                    'end': 'End',
                    'pageup': 'PageUp',
                    'pgup': 'PageUp',
                    'pagedown': 'PageDown',
                    'pgdn': 'PageDown',
                    'up': 'Up',
                    'down': 'Down',
                    'left': 'Left',
                    'right': 'Right',
                    'f1': 'F1', 'f2': 'F2', 'f3': 'F3', 'f4': 'F4',
                    'f5': 'F5', 'f6': 'F6', 'f7': 'F7', 'f8': 'F8',
                    'f9': 'F9', 'f10': 'F10', 'f11': 'F11', 'f12': 'F12',
                }
                
                if token in ('c-c', 'cc', 'ctrlc', 'controlc'):
                    # Send Ctrl+C
                    result = controller.send_ctrl('C')
                    results.append(f"Sent Ctrl+C")
                elif token in ('c-d', 'cd', 'ctrld', 'controld'):
                    # Send Ctrl+D
                    result = controller.send_ctrl('D')
                    results.append(f"Sent Ctrl+D")
                elif token in ('c-z', 'cz', 'ctrlz', 'controlz'):
                    # Send Ctrl+Z
                    result = controller.send_ctrl('Z')
                    results.append(f"Sent Ctrl+Z")
                elif token in token_map:
                    # Send special key
                    result = controller.send_keys(token_map[token], enter=False)
                    results.append(f"Sent {token_map[token]}")
                else:
                    # Unknown token, type it literally
                    result = controller.send_keys(f"<{token}>", enter=False)
                    results.append(f"Typed <{token}>")
            else:
                # This is regular text
                if part:
                    result = controller.send_keys(part, enter=False)
                    results.append(f"Typed text")
        
        # Handle the enter parameter
        if enter:
            controller.send_keys("", enter=True)
            results.append("Sent Enter")
        
        # In stream mode, capture screen after sending keys so agent can see result
        if self.state.is_stream_mode():
            import time
            time.sleep(0.3)  # Give terminal time to process the key
            try:
                from .screen_stream import get_screen_streamer
                streamer = get_screen_streamer()
                if streamer:
                    screen = streamer.capture_screen()
                    # Return screen if it has content (including errors!)
                    if screen and len(screen) > 20:
                        # Return full screen (truncated if very long)
                        screen_display = screen[:2000] if len(screen) > 2000 else screen
                        return f"✓ Keys processed\n\n[Terminal screen:]\n{screen_display}"
            except Exception:
                pass

        return "✓ " + ", ".join(results)

    def _send_ctrl(self, key: str) -> str:
        """Send control sequence (Ctrl+C, etc.)."""
        controller = get_controller()
        result = controller.send_ctrl(key)

        # In stream mode, capture screen after sending ctrl so agent can see result
        if self.state.is_stream_mode():
            import time
            time.sleep(0.5)  # Give terminal more time for ctrl sequences
            try:
                from .screen_stream import get_screen_streamer
                streamer = get_screen_streamer()
                if streamer:
                    screen = streamer.capture_screen()
                    # Return screen if it has content (including errors!)
                    if screen and len(screen) > 20:
                        screen_display = screen[:2000] if len(screen) > 2000 else screen
                        result += f"\n\n[Terminal screen:]\n{screen_display}"
            except Exception:
                pass

        return result

    def _get_terminal_info(self) -> str:
        """Get terminal control capabilities."""
        controller = get_controller()
        info = controller.get_session_info()
        lines = ["## Terminal Control Status"]
        lines.append(f"- tmux available: {info['tmux_available']}")
        if info['tmux_session']:
            lines.append(f"- tmux session: {info['tmux_session']}")
        lines.append(f"- termux-api: {info['termux_api']}")
        lines.append("")
        lines.append("### Capabilities")
        for cap, available in info['capabilities'].items():
            status = "✓" if available else "✗"
            lines.append(f"- {status} {cap}")
        if not info['tmux_available']:
            lines.append("")
            lines.append("⚠️ **Install tmux for full terminal control:**")
            lines.append("```")
            lines.append("pkg install tmux")
            lines.append("tmux new -s dao")
            lines.append("```")
        return "\n".join(lines)

    def _set_target_session(self, session: str) -> str:
        """Set the target tmux session for terminal control."""
        controller = get_controller()
        controller.tmux_session = session
        return f"Target session set to: {session}"

    def _run_program(self, command: str, session: str = "dao-control") -> str:
        """Run a program/command and show it to user in stream mode."""
        try:
            self.state.enable_stream_mode(session)
            controller = get_controller()
            controller.tmux_session = session

            from .tui import set_current_screen
            from .screen_stream import start_screen_stream
            start_screen_stream(session, set_current_screen, auto_create=True, workdir=self.cwd, command=command)

            # Wait for program to start and capture initial screen
            import time
            time.sleep(1.0)
            
            try:
                from .screen_stream import get_screen_streamer
                streamer = get_screen_streamer()
                if streamer:
                    screen = streamer.capture_screen()
                    if screen and len(screen) > 20:
                        screen_display = screen[:2000] if len(screen) > 2000 else screen
                        self.state.push_log("info", f"📺 Running: {command}")
                        return f"✓ Running: {command}\n\n[Initial terminal output:]\n{screen_display}"
            except Exception:
                pass

            self.state.push_log("info", f"📺 Running: {command}")
            return f"✓ Running: {command}\nUser can now watch execution in stream mode."
        except Exception as e:
            self.state.disable_stream_mode()
            return f"ERROR running program: {e}"
