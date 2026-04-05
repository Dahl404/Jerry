#!/usr/bin/env python3
"""Jerry — Tool Executor with Relative Path Support"""

import os
import subprocess
import json
from datetime import datetime, timedelta
from typing import Optional, Dict
from .models import State, Todo
from .worker import Worker
from .config import JERRY_BASE, DIARY_DIR, get_tool_catalog
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
        self.cwd    = JERRY_BASE  # Current working directory
        self._dynamic_tools = {}  # Loaded dynamic tool implementations
        self._load_dynamic_tools()
        # Keep state in sync from the start
        state.set_cwd(self.cwd)

    def _load_dynamic_tools(self):
        """Load dynamic tool implementations from .py files."""
        from .config import JERRY_BASE
        self._dynamic_tools = {}
        tools_root = os.path.join(JERRY_BASE, "tools")
        if not os.path.isdir(tools_root):
            return

        for pack in os.listdir(tools_root):
            pack_dir = os.path.join(tools_root, pack)
            if not os.path.isdir(pack_dir):
                continue
            for fname in os.listdir(pack_dir):
                if fname.endswith('.py'):
                    tool_name = fname[:-3]
                    fpath = os.path.join(pack_dir, fname)
                    try:
                        # Load the module
                        import importlib.util
                        spec = importlib.util.spec_from_file_location(f"dynamic_{pack}_{tool_name}", fpath)
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        if hasattr(module, 'execute'):
                            self._dynamic_tools[tool_name] = module.execute
                    except Exception as e:
                        self.state.push_log("error", f"Failed to load dynamic tool {tool_name}: {e}")

    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to current working directory."""
        if os.path.isabs(path):
            return os.path.abspath(path)
        return os.path.abspath(os.path.join(self.cwd, path))

    def _validate_path(self, path: str) -> tuple:
        """Validate path is within allowed directories. Returns (is_valid, abs_path, error_msg)."""
        try:
            abs_path = self._resolve_path(path)
            # Allow files in JERRY_BASE or common system temp locations
            allowed_prefixes = [os.path.abspath(JERRY_BASE), '/tmp', '/data/data/com.termux/cache']
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
            # Include help output for the tool that failed
            error_msg = f"ERROR: {e}"
            help_text = self._get_tool_help(name)
            result = f"{error_msg}\n\n📖 Usage:\n{help_text}"
            self.state.push_log("error", str(e)[:300])
        display = str(result)
        self.state.push_log("result", display[:500])
        return display

    # ── Dispatcher ─────────────────────────────────────────────────────────────
    def _dispatch(self, name: str, a: Dict) -> str:
        # Check dynamic tools first
        if name in self._dynamic_tools:
            try:
                result = self._dynamic_tools[name](**a)
                return str(result) if result is not None else ""
            except Exception as e:
                return f"ERROR executing {name}: {e}"

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
        elif name == "query_worker":         return self._query_worker(a.get("file"), a["question"], a.get("extra_context", ""))
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
        elif name == "run_program":           return self._run_program(a["command"], a.get("session", "jerry-control"))
        # Question tool
        elif name == "ask_user":             return self._ask_user(a["question"], a.get("options"))
        # Coin/reward system tools (Jerry CAN use these)
        elif name == "check_coins":          return self._check_coins()
        elif name == "offer_coins":          return self._offer_coins(a.get("amount", 0), a.get("reason", ""))
        # Multi-file worker support
        elif name == "load_multiple_files":  return self._load_multiple_files(a.get("files", []))
        # Worker program creation
        elif name == "worker_write_program": return self._worker_write_program(a.get("path"), a.get("spec"), a.get("language", "python"))
        # Role/persona management tools
        elif name == "switch_role":          return self._switch_role(a["role_name"])
        elif name == "create_role":          return self._create_role(a["name"], a["description"], a["prompt_prefix"], a.get("tool_packs", ["agent"]))
        elif name == "list_roles":           return self._list_roles()
        # Tool management tools
        elif name == "create_tool":          return self._create_tool(a["tool_name"], a["pack_name"], a["tool_description"], a["implementation"], a.get("parameters"), a.get("required"))
        elif name == "edit_tool":            return self._edit_tool(a["tool_name"], a["pack_name"], a.get("description"), a.get("parameters"), a.get("required"), a.get("implementation"))
        elif name == "delete_tool":          return self._delete_tool(a["tool_name"], a["pack_name"])
        elif name == "read_tool":            return self._read_tool(a["tool_name"], a["pack_name"])
        elif name == "list_tools":           return self._list_tools(a.get("pack_name"))
        # NOTE: 'praise' is USER-ONLY via /praise command, not a tool Jerry can call
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
        """Change current working directory. Paths must be RELATIVE."""
        try:
            # Reject absolute paths — all navigation must be relative
            if os.path.isabs(path):
                rel = os.path.relpath(path, self.cwd)
                if rel.startswith('..'):
                    return f"ERROR: Use relative paths only. Current: {self._pwd_rel()}"
                path = rel

            new_cwd = os.path.abspath(os.path.join(self.cwd, path))

            # Validate it exists and is a directory
            if not os.path.exists(new_cwd):
                return f"ERROR: Directory not found: {path}"
            if not os.path.isdir(new_cwd):
                return f"ERROR: Not a directory: {path}"

            # Validate it's within allowed directories
            allowed_prefixes = [os.path.abspath(JERRY_BASE), '/tmp', '/data/data/com.termux/cache']
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
        """Return current working directory (relative to workspace root)."""
        rel = self._pwd_rel()
        return f"Current directory: {rel}"

    def _pwd_rel(self) -> str:
        """Return relative path from workspace root."""
        try:
            return os.path.relpath(self.cwd, JERRY_BASE)
        except ValueError:
            return "."

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

    def _get_tool_help(self, tool_name: str) -> str:
        """Get concise help for a specific tool (for error messages)."""
        catalog = get_tool_catalog()
        if tool_name not in catalog:
            return f"Unknown tool: {tool_name}"
        
        tool = catalog[tool_name]
        params = ", ".join(f"{k}: {v}" for k, v in tool["params"].items()) or "none"
        return (
            f"Tool: {tool_name}\n"
            f"Description: {tool['description']}\n"
            f"Parameters: {params}\n"
            f"Example: {tool['example']}"
        )

    # ── File write ─────────────────────────────────────────────────────────────
    def _write(self, path: str, content: str) -> str:
        """Write file with streaming progress feedback."""
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        
        # Stream start message to chat
        char_count = len(content)
        line_count = content.count('\n') + 1
        self.state.push_chat("dao", f"✏️ Writing `{path}`... ({char_count:,} chars, {line_count} lines)", expression="thinking")
        
        try:
            d = os.path.dirname(abs_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # Stream completion message
            self.state.push_chat("dao", f"✓ Wrote `{path}` ({char_count:,} chars)", expression="smiling")
            return f"Wrote {char_count:,} chars → {path}"
        except Exception as e:
            # Stream error message
            self.state.push_chat("dao", f"✗ Failed to write `{path}`: {e}", expression="bummed")
            return f"ERROR: {e}"

    # ── File read (returns content only, worker loaded on query) ──────────────
    def _read(self, path: str, start: int, maxl: int) -> str:
        """Read file with line numbers. Supports text files and images.
        
        For images: Returns base64-encoded data for multi-modal model analysis.
        For text: Returns line-numbered content as usual.
        """
        is_valid, abs_path, error = self._validate_path(path)
        if not is_valid:
            return error
        if not os.path.exists(abs_path):
            return f"ERROR: File not found: {path}"
        
        # Check if it's an image file
        image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
        file_ext = os.path.splitext(path)[1].lower()
        
        if file_ext in image_extensions:
            # Read image as base64 for multi-modal model
            try:
                import base64
                with open(abs_path, "rb") as f:
                    image_data = base64.b64encode(f.read()).decode('utf-8')
                
                # Get file size for display
                file_size = os.path.getsize(abs_path)
                
                # Return special format for images
                return f"[IMAGE: {path}]\nFormat: {file_ext[1:].upper()}\nSize: {file_size:,} bytes\nBase64 data: {image_data[:500]}...[truncated]\n\n[Full base64 data available in agent context for multi-modal analysis]"
            except Exception as e:
                return f"ERROR reading image: {e}"
        
        # Text file - original behavior
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

    # ── Worker Query (auto-loads file if specified) ───────────────────────────
    def _query_worker(self, file: Optional[str], question: str, extra: str = "") -> str:
        """Query worker about a file. Auto-loads file if path provided."""
        try:
            # If file path provided, load it into worker first
            if file:
                is_valid, abs_path, error = self._validate_path(file)
                if not is_valid:
                    return error
                if not os.path.exists(abs_path):
                    return f"ERROR: File not found: {file}"
                
                # Read and load file
                with open(abs_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self.worker.load(abs_path, content)
            
            # Query the worker
            return self.worker.query(question, extra)
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
            lines.append("tmux new -s jerry")
            lines.append("```")
        return "\n".join(lines)

    def _set_target_session(self, session: str) -> str:
        """Set the target tmux session for terminal control."""
        controller = get_controller()
        controller.tmux_session = session
        return f"Target session set to: {session}"

    def _run_program(self, command: str, session: str = "jerry-control") -> str:
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

    def _ask_user(self, question: str, options: list = None) -> str:
        """Ask the user a question with optional predefined answers."""
        try:
            # Debug: Log raw parameters
            self.state.push_log("info", f"❓ ask_user called")
            self.state.push_log("info", f"  question={question}")
            self.state.push_log("info", f"  options={options} (type={type(options).__name__})")
            
            # Ensure options is a list
            if options is None:
                options = []
                self.state.push_log("info", f"  → options was None, set to []")
            elif not isinstance(options, list):
                options = [str(options)]
                self.state.push_log("info", f"  → options was not list, converted to {options}")
            
            self.state.push_log("info", f"  → Final options: {options}")

            # Store question in state for UI to render
            self.state.pending_question = {
                "question": str(question),
                "options": options,
                "selected": 0,
                "selected_indices": set(),  # For multi-select with Space
                "active": True,
                "answer": None
            }
            
            self.state.push_log("info", f"  → Stored in pending_question: {self.state.pending_question}")

            # Set status to waiting
            self.state.set_status("waiting for answer...")

            return f"Waiting for user to answer: {question}"
        except Exception as e:
            self.state.push_log("error", f"ask_user error: {e}")
            return f"Error asking question: {e}"

    def _check_coins(self) -> str:
        """Check Jerry's current coin balance."""
        coins = self.state.get_coins()
        return f"🪙 Jerry has {coins} coins"

    def _offer_coins(self, amount: int, reason: str) -> str:
        """Offer coins to user in exchange for permission or help.
        
        This creates a negotiation request. User can accept or decline.
        Coins are only deducted if user accepts.
        """
        current_coins = self.state.get_coins()
        
        if amount <= 0:
            return "❌ Must offer at least 1 coin"
        
        if amount > current_coins:
            return f"❌ Not enough coins! Jerry has {current_coins}, trying to offer {amount}"
        
        # Log the offer (coins not deducted yet - waiting for user acceptance)
        self.state.push_log("info", f"💰 Jerry offers {amount} coins: {reason}")
        self.state.push_chat("dao", f"💰 I'll offer you {amount} coins if you let me: {reason}", expression="smiling")
        
        return f"💰 Offered {amount} coins to user: {reason} (waiting for acceptance...)"

    def _praise(self, reason: str) -> str:
        """Praise/reward Jerry for a job well done.
        
        This is a USER-ONLY tool - Jerry can't call this on himself.
        Awards coins as a reward.
        """
        # Award 5-10 coins based on praise length/enthusiasm
        base_coins = 5
        bonus = min(5, len(reason) // 20)  # Up to 5 bonus coins for detailed praise
        total_coins = base_coins + bonus
        
        self.state.add_coins(total_coins, reason)
        
        # Show happy face
        self.state.push_chat("dao", f"🪙 *blushes happily* Thank you! {reason}", expression="smiling")
        
        return f"🪙 Jerry earned {total_coins} coins! (Total: {self.state.get_coins()})"

    def _load_multiple_files(self, files: list) -> str:
        """Load multiple files into worker context for cross-file analysis.

        Args:
            files: List of {path, content} dicts

        Returns:
            Confirmation message
        """
        if not files:
            return "❌ No files specified"

        try:
            # Convert to list of (path, content) tuples
            file_list = [(f["path"], f["content"]) for f in files]

            # Load into worker
            result = self.worker.load_multiple(file_list)

            return f"✓ {result}"
        except Exception as e:
            return f"ERROR loading files: {e}"

    def _worker_write_program(self, path: str, spec: str, language: str = "python") -> str:
        """Have worker AI write a program based on specifications.
        
        This is faster than main AI for initial drafts since worker has less context.
        Main AI can then review, test, and debug as needed.
        
        Args:
            path: File path to write
            spec: Detailed specification of what to create
            language: Programming language (default: python)
        
        Returns:
            Result message with file stats
        """
        try:
            # Validate path
            is_valid, abs_path, error = self._validate_path(path)
            if not is_valid:
                return error
            
            # Stream start message
            self.state.push_chat("dao", f"🤖 Worker AI writing `{path}`...", expression="thinking")
            
            # Build prompt for worker
            worker_prompt = f"""You are a code generation assistant. Write a complete, working {language} program based on this specification:

**Specification:**
{spec}

**Requirements:**
- Write complete, runnable code
- Include necessary imports
- Add clear comments explaining key sections
- Follow best practices for {language}
- Handle errors appropriately
- Include example usage if applicable

Write the complete file content. DO NOT explain or describe - just write the code."""

            # Call worker to generate code
            generated_code = self.worker.query(worker_prompt)
            
            # Extract code from response (remove any markdown fences or explanations)
            code = generated_code.strip()
            
            # Remove markdown code fences if present
            if code.startswith("```"):
                # Remove first line (```language) and last line (```)
                lines = code.split('\n')
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                code = '\n'.join(lines)
            
            # Write the file
            d = os.path.dirname(abs_path)
            if d:
                os.makedirs(d, exist_ok=True)
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(code)
            
            char_count = len(code)
            line_count = code.count('\n') + 1
            
            # Stream completion
            self.state.push_chat("dao", f"✓ Worker wrote `{path}` ({char_count:,} chars, {line_count} lines)\n\n💡 Main AI should now review and test the code.", expression="smiling")
            
            return f"✓ Worker wrote {path} ({char_count:,} chars, {line_count} lines)\n\nGenerated code preview:\n{code[:500]}{'...' if len(code) > 500 else ''}"
            
        except Exception as e:
            self.state.push_chat("dao", f"✗ Worker failed to write `{path}`: {e}", expression="bummed")
            return f"ERROR: {e}"

    # ── Role/persona management tools ──────────────────────────────────────────
    def _switch_role(self, role_name: str) -> str:
        """Switch to a different persona/role."""
        from .personas import get_persona_manager
        persona_mgr = get_persona_manager()
        success = persona_mgr.set_persona(role_name)
        if success:
            persona = persona_mgr.get_current()
            # Update agent via state
            agent = getattr(self.state, '_agent_ref', None)
            if agent:
                agent.set_persona_prefix(persona.prompt_prefix)
                agent.set_tool_packs(persona.tool_packs)
            return f"✓ Switched to role: {role_name}"
        return f"ERROR: Role '{role_name}' not found. Use list_roles() to see available roles."

    def _create_role(self, name: str, description: str, prompt_prefix: str, tool_packs: list = None) -> str:
        """Create a new persona/role."""
        from .personas import get_persona_manager
        persona_mgr = get_persona_manager()
        if tool_packs is None:
            tool_packs = ["agent"]
        success = persona_mgr.create_custom_persona(name, description, prompt_prefix, tool_packs)
        if success:
            return f"✓ Created role: {name} (packs: {', '.join(tool_packs)})"
        return f"ERROR: Role '{name}' already exists."

    def _create_tool_pack(self, pack_name: str, tools: list) -> str:
        """Create a new tool package."""
        from .config import JERRY_BASE
        pack_dir = os.path.join(JERRY_BASE, "tools", pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        created = []
        for tool_def in tools:
            tool_name = tool_def.get("name", "")
            if not tool_name:
                continue
            filepath = os.path.join(pack_dir, f"{tool_name}.tool")
            with open(filepath, 'w') as f:
                json.dump(tool_def, f, indent=2)
            created.append(tool_name)

        if created:
            return f"✓ Created tool pack '{pack_name}' with {len(created)} tools: {', '.join(created)}"
        return "ERROR: No valid tools provided."

    def _list_roles(self) -> str:
        """List all available personas/roles."""
        from .personas import get_persona_manager
        persona_mgr = get_persona_manager()
        personas = persona_mgr.list_personas()
        current = persona_mgr.get_current()

        lines = ["Available roles:"]
        for p in personas:
            marker = "✓" if p.name == current.name else " "
            tag = " (custom)" if p.custom else ""
            packs = ", ".join(p.tool_packs) if p.tool_packs else "(none)"
            lines.append(f"  {marker} {p.name}{tag} — {p.description}")
            lines.append(f"     Packs: {packs}")
        return "\n".join(lines)

    # ── Tool management tools ──────────────────────────────────────────────────
    def _create_tool(self, tool_name: str, pack_name: str, description: str, implementation: str, parameters: dict = None, required: list = None) -> str:
        """Create or update a tool with implementation."""
        from .config import JERRY_BASE
        pack_dir = os.path.join(JERRY_BASE, "tools", pack_name)
        os.makedirs(pack_dir, exist_ok=True)

        # Save tool definition
        tool_def = {
            "name": tool_name,
            "description": description,
            "parameters": parameters or {},
            "required": required or []
        }
        with open(os.path.join(pack_dir, f"{tool_name}.tool"), 'w') as f:
            json.dump(tool_def, f, indent=2)

        # Save implementation
        with open(os.path.join(pack_dir, f"{tool_name}.py"), 'w') as f:
            f.write(implementation)

        # Reload dynamic tools
        self._load_dynamic_tools()

        # Reload agent tools
        agent = getattr(self.state, '_agent_ref', None)
        if agent:
            agent._load_tools_and_prompt()

        return f"✓ Created tool '{tool_name}' in pack '{pack_name}'"

    def _edit_tool(self, tool_name: str, pack_name: str, description: str = None, parameters: dict = None, required: list = None, implementation: str = None) -> str:
        """Edit an existing tool's definition or implementation."""
        from .config import JERRY_BASE
        pack_dir = os.path.join(JERRY_BASE, "tools", pack_name)
        tool_path = os.path.join(pack_dir, f"{tool_name}.tool")
        impl_path = os.path.join(pack_dir, f"{tool_name}.py")

        if not os.path.exists(tool_path):
            return f"ERROR: Tool '{tool_name}' not found in pack '{pack_name}'"

        # Update definition
        with open(tool_path, 'r') as f:
            tool_def = json.load(f)
        if description is not None:
            tool_def["description"] = description
        if parameters is not None:
            tool_def["parameters"] = parameters
        if required is not None:
            tool_def["required"] = required
        with open(tool_path, 'w') as f:
            json.dump(tool_def, f, indent=2)

        # Update implementation if provided
        if implementation is not None:
            with open(impl_path, 'w') as f:
                f.write(implementation)

        # Reload
        self._load_dynamic_tools()
        agent = getattr(self.state, '_agent_ref', None)
        if agent:
            agent._load_tools_and_prompt()

        return f"✓ Updated tool '{tool_name}' in pack '{pack_name}'"

    def _delete_tool(self, tool_name: str, pack_name: str) -> str:
        """Delete a tool from a tool pack."""
        from .config import JERRY_BASE
        pack_dir = os.path.join(JERRY_BASE, "tools", pack_name)
        tool_path = os.path.join(pack_dir, f"{tool_name}.tool")
        impl_path = os.path.join(pack_dir, f"{tool_name}.py")

        if not os.path.exists(tool_path):
            return f"ERROR: Tool '{tool_name}' not found in pack '{pack_name}'"

        if os.path.exists(tool_path):
            os.remove(tool_path)
        if os.path.exists(impl_path):
            os.remove(impl_path)

        # Reload
        self._load_dynamic_tools()
        agent = getattr(self.state, '_agent_ref', None)
        if agent:
            agent._load_tools_and_prompt()

        return f"✓ Deleted tool '{tool_name}' from pack '{pack_name}'"

    def _read_tool(self, tool_name: str, pack_name: str) -> str:
        """Read a tool's definition and implementation."""
        from .config import JERRY_BASE
        pack_dir = os.path.join(JERRY_BASE, "tools", pack_name)
        tool_path = os.path.join(pack_dir, f"{tool_name}.tool")
        impl_path = os.path.join(pack_dir, f"{tool_name}.py")

        if not os.path.exists(tool_path):
            return f"ERROR: Tool '{tool_name}' not found in pack '{pack_name}'"

        lines = [f"Tool: {tool_name} (pack: {pack_name})"]

        with open(tool_path, 'r') as f:
            tool_def = json.load(f)
        lines.append(f"Description: {tool_def.get('description', 'N/A')}")
        lines.append(f"Parameters: {json.dumps(tool_def.get('parameters', {}), indent=2)}")
        lines.append(f"Required: {tool_def.get('required', [])}")

        if os.path.exists(impl_path):
            with open(impl_path, 'r') as f:
                impl = f.read()
            lines.append(f"\nImplementation:\n{impl}")
        else:
            lines.append("\nNo implementation file found")

        return "\n".join(lines)

    def _list_tools(self, pack_name: str = None) -> str:
        """List all tools in a pack, or all packs."""
        from .config import JERRY_BASE
        tools_root = os.path.join(JERRY_BASE, "tools")

        if not os.path.isdir(tools_root):
            return "No tool packs found."

        if pack_name:
            # List specific pack
            pack_dir = os.path.join(tools_root, pack_name)
            if not os.path.isdir(pack_dir):
                return f"ERROR: Pack '{pack_name}' not found."

            lines = [f"Tools in pack '{pack_name}':"]
            for fname in sorted(os.listdir(pack_dir)):
                if fname.endswith('.tool'):
                    fpath = os.path.join(pack_dir, fname)
                    try:
                        with open(fpath, 'r') as f:
                            tool = json.load(f)
                        desc = tool.get('description', 'No description')
                        params = tool.get('parameters', {})
                        req = tool.get('required', [])
                        param_str = ", ".join(f"{k}{'*' if k in req else ''}" for k in params)
                        has_impl = "✓" if os.path.exists(fpath.replace('.tool', '.py')) else "✗"
                        lines.append(f"  {has_impl} {tool['name']}({param_str}) — {desc}")
                    except Exception:
                        lines.append(f"  • {fname} (error reading)")
            return "\n".join(lines)
        else:
            # List all packs
            lines = ["Available tool packs:"]
            for pack in sorted(os.listdir(tools_root)):
                pack_dir = os.path.join(tools_root, pack)
                if os.path.isdir(pack_dir):
                    tools = [f.replace('.tool', '') for f in os.listdir(pack_dir) if f.endswith('.tool')]
                    lines.append(f"  📦 {pack} ({len(tools)} tools): {', '.join(tools)}")
            return "\n".join(lines)
