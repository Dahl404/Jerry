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


class Executor:
    """Executes tool calls and manages file operations with relative path support."""

    def __init__(self, state: State, worker: Worker):
        self.state  = state
        self.worker = worker
        self.cwd    = DAO_BASE  # Current working directory

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
        if   name == "help":               return self._help(a.get("tool_name"))
        elif name == "execute_command":  return self._sh(a["command"], a.get("workdir"))
        elif name == "write_file":       return self._write(a["path"], a["content"])
        elif name == "read_file":        return self._read(a["path"], a.get("start_line", 1), a.get("max_lines", 500))
        elif name == "replace_lines":    return self._replace(a["path"], a["start_line"], a["end_line"], a["new_content"])
        elif name == "insert_lines":     return self._insert(a["path"], a["after_line"], a["content"])
        elif name == "delete_lines":     return self._delete(a["path"], a["start_line"], a["end_line"])
        elif name == "list_directory":
            flags = "-la" + ("A" if a.get("show_hidden") else "")
            path = a.get("path", ".")
            # Resolve relative paths
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
        elif name == "query_worker":     return self.worker.query(a["question"], a.get("extra_context", ""))
        elif name == "reset_worker":     self.worker.reset(); return "Worker context cleared."
        elif name == "todo_add":         return self._tadd(a["task"], a.get("priority", "medium"))
        elif name == "todo_complete":    return self._tdone(a["index"])
        elif name == "todo_remove":      return self._trem(a["index"])
        elif name == "reply":
            expr = self.state.expression
            self.state.push_chat("dao", a["message"], expression=expr)
            return "[message sent to user]"
        elif name == "write_diary":      return self._write_diary(a["entry"], a.get("mood", "neutral"))
        elif name == "read_diary":       return self._read_diary(a.get("days_back", 7), a.get("keyword", ""))
        elif name == "set_expression":   return self._set_expression(a["expression"])
        elif name == "enter":            return self._enter(a["path"])
        elif name == "pwd":              return self._pwd()
        else:
            return f"Unknown tool: {name}"

    # ── Shell ──────────────────────────────────────────────────────────────────
    def _sh(self, cmd: str, cwd: Optional[str] = None) -> str:
        """Execute shell command with no timeout (waits indefinitely)."""
        try:
            # Use cwd from args, or fall back to self.cwd
            workdir = cwd if cwd else self.cwd
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=workdir,
            )
            out = (r.stdout + r.stderr).strip()
            return out or f"[exit {r.returncode}]"
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
    def _tadd(self, task: str, priority: str) -> str:
        with self.state._lock:
            self.state.todos.append(Todo(task, priority))
        return f"Added: {task}"

    def _tdone(self, idx: int) -> str:
        with self.state._lock:
            if 0 <= idx < len(self.state.todos):
                self.state.todos[idx].done = True
                return f"Completed #{idx}: {self.state.todos[idx].text}"
            return f"No todo at index {idx}"

    def _trem(self, idx: int) -> str:
        with self.state._lock:
            if 0 <= idx < len(self.state.todos):
                t = self.state.todos.pop(idx)
                return f"Removed: {t.text}"
            return f"No todo at index {idx}"

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
