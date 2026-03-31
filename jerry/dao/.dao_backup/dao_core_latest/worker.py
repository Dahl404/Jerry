#!/usr/bin/env python3
"""Dao — Worker Model Manager"""

import requests
from typing import Dict, List
from .config import WORKER_URL
from .models import State


def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks (Qwen3 reasoning tokens)."""
    import re
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


class Worker:
    """Manages conversation with the text-processing worker model on port 8081."""

    def __init__(self, state: State):
        self.state = state
        self.hist:  List[Dict] = []

    def reset(self):
        self.hist = []
        with self.state._lock:
            self.state.wfile = None
        self.state.push_log("worker", "Worker context cleared.")

    def load(self, path: str, content: str) -> str:
        """Load a file (line-numbered) into worker context."""
        line_count = content.count("\n") + 1
        self.hist = [{
            "role": "user",
            "content": (
                f"You are a text-processing and code analysis assistant.\n"
                f"A file has been loaded for you to study carefully.\n\n"
                f"File path: {path}\n"
                f"Line count: {line_count}\n\n"
                f"```\n{content}\n```\n\n"
                f"Please acknowledge receipt, state the line count, and briefly describe "
                f"the file structure. Then wait for questions."
            ),
        }]
        with self.state._lock:
            self.state.wfile = path
        resp = self._call()
        self.hist.append({"role": "assistant", "content": resp})
        self.state.push_log("worker", f"Loaded: {path}  ({line_count} lines)")
        return resp

    def query(self, question: str, extra: str = "") -> str:
        """Ask the worker a question about the loaded file."""
        if extra:
            self.hist.append({"role": "user", "content": extra})
        self.hist.append({"role": "user", "content": question})
        resp = self._call()
        self.hist.append({"role": "assistant", "content": resp})
        self.state.push_log("worker", f"Q: {question[:80]}")
        return resp

    def _call(self) -> str:
        try:
            r = requests.post(
                WORKER_URL,
                json={"messages": self.hist, "max_tokens": 2048, "temperature": 0.2},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            raw = choices[0].get("message", {}).get("content") or ""
            return strip_think(raw)
        except requests.RequestException as e:
            self.state.push_log("error", f"Worker API error: {e}")
            raise
        except (KeyError, IndexError, ValueError) as e:
            self.state.push_log("error", f"Worker response parsing error: {e}")
            raise
