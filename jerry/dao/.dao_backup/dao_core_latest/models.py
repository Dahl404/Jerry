#!/usr/bin/env python3
"""Dao — Data Models"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from collections import deque
import threading

from .config import LOG_LIMIT, RAW_LOG_LIMIT


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


@dataclass
class LogEntry:
    kind: str   # tool | result | think | error | worker | system | info | stream
    text: str
    ts: str = field(default_factory=ts)


@dataclass
class ChatMsg:
    role: str   # user | dao
    text: str
    ts: str = field(default_factory=ts)
    expression: str = ""  # e.g., "<smiling>", "<laughing>"


@dataclass
class Todo:
    text:     str
    priority: str  = "medium"   # high | medium | low
    done:     bool = False
    ts:       str  = field(default_factory=lambda: datetime.now().strftime("%H:%M"))


@dataclass
class DiaryEntry:
    entry: str
    mood: str
    ts: str = field(default_factory=lambda: datetime.now().isoformat())


class State:
    """Thread-safe shared state for the Dao agent."""

    def __init__(self):
        self._lock   = threading.Lock()
        self.log:    List[LogEntry] = []
        self.chat:   List[ChatMsg]  = []
        self.todos:  List[Todo]     = []
        self.status: str            = "starting"
        self.inbox:  deque          = deque()
        self.quit:   bool           = False
        self.wfile:  Optional[str]  = None   # file currently loaded in worker
        self.expression: str = ""   # current expression state
        self.local_files: List[str] = field(default_factory=list)  # known local files
        self.session_start: str = field(default_factory=lambda: datetime.now().isoformat())
        self.raw_logs: List[Dict] = []  # complete raw logs for archival

    # ── Log ────────────────────────────────────────────────────────────────────
    def push_log(self, kind: str, text: str):
        with self._lock:
            self.log.append(LogEntry(kind, text))
            self.raw_logs.append({"kind": kind, "text": text, "ts": ts()})
            if len(self.log) > LOG_LIMIT:
                self.log = self.log[-LOG_LIMIT:]
            if len(self.raw_logs) > RAW_LOG_LIMIT:
                self.raw_logs = self.raw_logs[-RAW_LOG_LIMIT:]

    # ── Streaming log (for real-time output) ───────────────────────────────────
    def push_stream(self, text: str):
        with self._lock:
            self.log.append(LogEntry("stream", text))
            self.raw_logs.append({"kind": "stream", "text": text, "ts": ts()})

    # ── Chat ───────────────────────────────────────────────────────────────────
    def push_chat(self, role: str, text: str, expression: str = ""):
        with self._lock:
            self.chat.append(ChatMsg(role, text, expression=expression))

    # ── Inbox ──────────────────────────────────────────────────────────────────
    def add_inbox(self, msg: str):
        with self._lock:
            self.inbox.append(msg)

    def drain_inbox(self) -> List[str]:
        with self._lock:
            out = list(self.inbox)
            self.inbox.clear()
            return out

    # ── Status ─────────────────────────────────────────────────────────────────
    def set_status(self, s: str):
        with self._lock:
            self.status = s

    # ── Expression ─────────────────────────────────────────────────────────────
    def set_expression(self, expr: str):
        with self._lock:
            self.expression = expr

    # ── Local Files ────────────────────────────────────────────────────────────
    def set_local_files(self, files: List[str]):
        with self._lock:
            self.local_files = files

    # ── Snapshot for rendering ─────────────────────────────────────────────────
    def snapshot(self):
        with self._lock:
            return (
                self.log[:],
                self.chat[:],
                self.todos[:],
                self.status,
                self.wfile,
                self.expression,
            )
