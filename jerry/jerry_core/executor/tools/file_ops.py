#!/usr/bin/env python3
"""Jerry Executor — File Operations"""

import os
from typing import Optional


class FileOperations:
    """Mixin for file operation tools."""

    def _write(self, path: str, content: str) -> str:
        """Write content to a file."""
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

    def _read(self, path: str, start: int, maxl: int) -> str:
        """Read file with line numbers, loads into worker context."""
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

    def _replace(self, path: str, s: int, e: int, new: str) -> str:
        """Replace line range in file."""
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

    def _insert(self, path: str, after: int, content: str) -> str:
        """Insert lines after given line number."""
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

    def _delete(self, path: str, s: int, e: int) -> str:
        """Delete line range from file."""
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
