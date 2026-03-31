#!/usr/bin/env python3
"""Jerry Executor — Miscellaneous Operations"""

import os
from datetime import datetime, timedelta

from ...config import DIARY_DIR


class MiscOperations:
    """Mixin for miscellaneous operations (help, diary, expression, worker)."""

    def _write_diary(self, entry: str, mood: str) -> str:
        """Write reflection to diary."""
        os.makedirs(DIARY_DIR, exist_ok=True)
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = f"{DIARY_DIR}/{date_str}.md"

        timestamp = datetime.now().strftime("%H:%M:%S")
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(f"\n\n## [{timestamp}] ({mood})\n\n{entry}\n")
        return f"Diary entry written → {filepath}"

    def _read_diary(self, days_back: int, keyword: str) -> str:
        """Read past diary entries."""
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

    def _set_expression(self, expr: str) -> str:
        """Set emotional/physical state."""
        self.state.set_expression(expr)
        return f"Expression set: {expr}"
