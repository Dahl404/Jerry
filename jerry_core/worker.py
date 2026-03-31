#!/usr/bin/env python3
"""Jerry — Worker Model Manager"""

import requests
from typing import Dict, List
from .config import WORKER_URL, WORKER_TIMEOUT
from .models import State

# Maximum number of messages kept in the worker's rolling history.
# Each load() resets to 1 message; queries add 2 (user + assistant) each time.
# 40 messages ≈ 20 query/answer pairs — enough for deep file analysis without
# blowing the worker's context window over long sessions.
WORKER_HIST_LIMIT = 40


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
            self.state.wfiles = []  # Track multiple files
        self.state.push_log("worker", "Worker context cleared.")

    def load(self, path: str, content: str) -> str:
        """Load a file (line-numbered) into worker context.
        
        This REPLACES any previously loaded files. For multiple files, use load_multiple().
        """
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
            self.state.wfiles = [path]
        resp = self._call()
        self.hist.append({"role": "assistant", "content": resp})
        self.state.push_log("worker", f"Loaded: {path}  ({line_count} lines)")
        return resp

    def load_multiple(self, files: List[tuple]) -> str:
        """Load multiple files into worker context without resetting.
        
        Args:
            files: List of (path, content) tuples
        
        Returns:
            Confirmation message
        """
        if not files:
            return "No files to load"
        
        # Build multi-file prompt
        file_contents = []
        file_list = []
        for path, content in files:
            line_count = content.count("\n") + 1
            file_list.append(f"- {path} ({line_count} lines)")
            file_contents.append(f"### File: {path}\n\n```\n{content}\n```\n")
        
        combined_content = "\n\n".join(file_contents)
        file_list_str = "\n".join(file_list)
        
        self.hist = [{
            "role": "user",
            "content": (
                f"You are a text-processing and code analysis assistant.\n"
                f"Multiple files have been loaded for cross-file analysis.\n\n"
                f"**Loaded Files:**\n{file_list_str}\n\n"
                f"{combined_content}\n\n"
                f"Please acknowledge receipt and describe the relationship between these files. "
                f"Then wait for questions."
            ),
        }]
        
        with self.state._lock:
            self.state.wfile = files[0][0]  # Set first as primary
            self.state.wfiles = [f[0] for f in files]  # Track all loaded files
        
        resp = self._call()
        self.hist.append({"role": "assistant", "content": resp})
        self.state.push_log("worker", f"Loaded {len(files)} files: {', '.join(f[0] for f in files)}")
        return f"Loaded {len(files)} files into worker context"

    def query(self, question: str, extra: str = "") -> str:
        """Ask the worker a question about the loaded file."""
        if extra:
            self.hist.append({"role": "user", "content": extra})
        self.hist.append({"role": "user", "content": question})
        resp = self._call()
        self.hist.append({"role": "assistant", "content": resp})
        self.state.push_log("worker", f"Q: {question[:80]}")
        # Trim history: always keep the first message (file load) + recent exchanges.
        # Preserving message[0] ensures the worker never loses the file it loaded.
        if len(self.hist) > WORKER_HIST_LIMIT:
            self.hist = [self.hist[0]] + self.hist[-(WORKER_HIST_LIMIT - 1):]
        return resp

    def compress_history(self, messages: List[Dict]) -> str:
        """Compress conversation history using worker model.
        
        Args:
            messages: List of conversation messages to compress
            
        Returns:
            Compressed summary of the conversation
        """
        if not messages:
            return ""
        
        # Build compression prompt
        conv_text = "\n".join([f"{m['role']}: {m.get('content', '')[:500]}" for m in messages[-50:]])  # Last 50 messages
        
        prompt = f"""You are summarizing a conversation for context compression.

CONVERSATION TO SUMMARIZE:
{conv_text}

TASK:
Create a concise summary (3-5 bullet points) that captures:
1. Key topics discussed
2. Important decisions made
3. Tasks completed or in progress
4. Any critical information to preserve

Format:
## Summary
- Point 1
- Point 2
- Point 3

## Current State
Brief description of current activity/state

Keep it under 200 words. Preserve essential context but remove redundancy."""

        try:
            r = requests.post(
                WORKER_URL,
                json={"messages": [{"role": "user", "content": prompt}], "max_tokens": 500, "temperature": 0.3},
                timeout=WORKER_TIMEOUT,
            )
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            raw = choices[0].get("message", {}).get("content") or ""
            return strip_think(raw)
        except requests.RequestException as e:
            self.state.push_log("error", f"Worker compression error: {e}")
            return f"[Compression failed: {e}]"
        except (KeyError, IndexError, ValueError) as e:
            self.state.push_log("error", f"Worker compression parse error: {e}")
            return f"[Compression failed: {e}]"

    def _call(self) -> str:
        try:
            r = requests.post(
                WORKER_URL,
                json={"messages": self.hist, "max_tokens": 2048, "temperature": 0.2},
                timeout=WORKER_TIMEOUT,
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
