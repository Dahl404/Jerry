#!/usr/bin/env python3
"""Jerry — Data Models"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from collections import deque
import itertools
import threading
import json

from .config import LOG_LIMIT, RAW_LOG_LIMIT, JERRY_BASE


def ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


# Monotonic counter for stable Todo IDs — survives index shifts caused by
# concurrent todo_add + todo_complete calls in the same multi-tool response.
_todo_id_counter = itertools.count(1)


@dataclass
class LogEntry:
    kind: str   # tool | result | think | error | worker | system | info | stream
    text: str
    ts: str = field(default_factory=ts)


@dataclass
class ChatMsg:
    role: str   # user | jerry
    text: str
    ts: str = field(default_factory=ts)
    expression: str = ""  # e.g., "<smiling>", "<laughing>"


@dataclass
class Todo:
    text:     str
    priority: str  = "medium"   # high | medium | low
    done:     bool = False
    ts:       str  = field(default_factory=lambda: datetime.now().strftime("%H:%M"))
    id:       int  = field(default_factory=lambda: next(_todo_id_counter))


@dataclass
class DiaryEntry:
    entry: str
    mood: str
    ts: str = field(default_factory=lambda: datetime.now().isoformat())


class State:
    """Thread-safe shared state for the Jerry agent."""

    def __init__(self):
        self._lock   = threading.Lock()
        self.log:    List[LogEntry] = []
        self.chat:   List[ChatMsg]  = []
        self.todos:  List[Todo]     = []
        self.status: str            = "starting"
        self.inbox:  deque          = deque()
        self.quit:   bool           = False
        self.wfile:  Optional[str]  = None   # file currently loaded in worker
        self.wfiles: List[str]     = []     # all files currently loaded in worker (multi-file support)
        self.expression: str = ""   # current expression state
        self.local_files: List[str] = []  # known local files
        self.session_start: str = datetime.now().isoformat()
        self.raw_logs: List[Dict] = []  # complete raw logs for archival
        self.stream_session: Optional[str] = None  # tmux session for stream mode
        self._screen_callback = None  # Callback for screen updates (set by TUI)
        # Agent phase: "idle" | "planning" | "executing"
        self.phase: str = "idle"
        # Current working directory — kept in sync with Executor.cwd so the
        # agent can always inject it into API messages without reading executor directly.
        self.cwd: str = JERRY_BASE
        # Coin/reward system
        self.coins: int = 0  # Jerry's coin balance
        self.coin_history: List[Dict] = []  # Track coin transactions
        self._load_coins()  # Load coins from file on startup
        # Pending question from ask_user tool
        self.pending_question: Optional[Dict] = None  # {question, options, selected, active, answer}
        # Agent cycle timing
        self.min_cycle_gap: float = 0.2  # Minimum seconds between agent cycles

    def _get_coins_file(self) -> str:
        """Get path to coins persistence file."""
        return os.path.join(JERRY_BASE, ".coins.json")

    def _load_coins(self):
        """Load coins from file on startup."""
        try:
            coins_file = self._get_coins_file()
            if os.path.exists(coins_file):
                with open(coins_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.coins = data.get("coins", 0)
                    self.coin_history = data.get("history", [])
        except Exception as e:
            self.coins = 0
            self.coin_history = []

    def _save_coins(self):
        """Save coins to file."""
        try:
            coins_file = self._get_coins_file()
            with open(coins_file, "w", encoding="utf-8") as f:
                json.dump({
                    "coins": self.coins,
                    "history": self.coin_history,
                }, f, indent=2)
        except Exception as e:
            self.push_log("error", f"Failed to save coins: {e}")

    # ── Screen callback registration ───────────────────────────────────────────
    def set_screen_callback(self, callback):
        """Set the callback for screen updates (called by TUI)."""
        with self._lock:
            self._screen_callback = callback

    # ── Stream mode ────────────────────────────────────────────────────────────

    # ── Stream mode ────────────────────────────────────────────────────────────
    def enable_stream_mode(self, session: str):
        """Enable stream mode for a tmux session."""
        with self._lock:
            self.stream_session = session

    def disable_stream_mode(self):
        """Disable stream mode."""
        with self._lock:
            self.stream_session = None

    def is_stream_mode(self) -> bool:
        """Check if stream mode is enabled."""
        with self._lock:
            return self.stream_session is not None

    def get_stream_session(self) -> Optional[str]:
        """Get the current stream session name."""
        with self._lock:
            return self.stream_session

    # ── Screen update callback (for stream mode) ───────────────────────────────
    def update_screen(self, screen_text: str):
        """Callback for screen capture in stream mode. Forwards to TUI for display only.
        
        IMPORTANT: This does NOT add screen content to conversation context.
        Screen updates are for USER display only (5 FPS streaming).
        
        To save screen to agent context, agent must explicitly call capture_screen() tool.
        """
        with self._lock:
            if self._screen_callback:
                # Call TUI's update_screen method - display only, not saved to context
                self._screen_callback(screen_text)

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
        """Append streaming text to the last stream entry (not a new line)."""
        with self._lock:
            # Find last stream entry and append to it
            for entry in reversed(self.log):
                if entry.kind == "stream":
                    entry.text += text
                    break
            else:
                # No existing stream entry, create new one
                self.log.append(LogEntry("stream", text))
            
            self.raw_logs.append({"kind": "stream", "text": text, "ts": ts()})

    # ── Chat ───────────────────────────────────────────────────────────────────
    def push_chat(self, role: str, text: str, expression: str = "", replace_last: bool = False):
        with self._lock:
            if replace_last and self.chat and self.chat[-1].role == role:
                # Don't replace if expression changed (thinking vs normal)
                if self.chat[-1].expression != expression:
                    # Different expression - create new message
                    self.chat.append(ChatMsg(role, text, expression=expression))
                else:
                    # Same expression - replace last message (for streaming)
                    self.chat[-1].text = text
                    self.chat[-1].expression = expression
            else:
                # Add new message
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

    # ── Phase ──────────────────────────────────────────────────────────────────
    def set_phase(self, phase: str):
        """Set agent phase: 'idle' | 'planning' | 'executing'."""
        with self._lock:
            self.phase = phase

    def get_phase(self) -> str:
        with self._lock:
            return self.phase

    # ── Working directory ──────────────────────────────────────────────────────
    def set_cwd(self, cwd: str):
        """Keep executor cwd in sync so agent can inject it into API messages."""
        with self._lock:
            self.cwd = cwd

    def get_cwd(self) -> str:
        with self._lock:
            return self.cwd

    # ── Token count ────────────────────────────────────────────────────────────
    def count_tokens(self) -> int:
        """Estimate total tokens in conversation (system + messages)."""
        with self._lock:
            # Rough estimate: 4 chars per token for English
            total_chars = 0
            
            # Count conversation tokens
            for msg in self.chat:
                total_chars += len(msg.text)
            
            # Count log tokens (recent only)
            for entry in self.log[-50:]:
                total_chars += len(entry.text)
            
            return total_chars // 4

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

    # ── Coin/Reward System ─────────────────────────────────────────────────────
    def add_coins(self, amount: int, reason: str = ""):
        """Add coins to Jerry's balance (user praise/reward)."""
        with self._lock:
            self.coins += amount
            self.coin_history.append({
                "type": "earn",
                "amount": amount,
                "balance": self.coins,
                "reason": reason,
                "ts": ts(),
            })
            # Don't call _save_coins() inside lock - it calls push_log which needs the lock
        # Save outside lock to avoid deadlock
        self._save_coins()
        self.push_log("info", f"🪙 Jerry earned {amount} coins! Total: {self.coins}")

    def spend_coins(self, amount: int, reason: str = "") -> bool:
        """Try to spend coins. Returns True if successful."""
        with self._lock:
            if self.coins >= amount:
                self.coins -= amount
                self.coin_history.append({
                    "type": "spend",
                    "amount": -amount,
                    "balance": self.coins,
                    "reason": reason,
                    "ts": ts(),
                })
                # Don't call _save_coins() inside lock
            else:
                self.push_log("error", f"❌ Not enough coins! Has {self.coins}, needs {amount}")
                return False
        
        # Save outside lock to avoid deadlock
        if self.coins >= 0:  # Only if spend was successful
            self._save_coins()
            self.push_log("info", f"💰 Jerry spent {amount} coins. Remaining: {self.coins}")
            return True
        return False

    def get_coins(self) -> int:
        """Get current coin balance."""
        with self._lock:
            return self.coins

    def answer_question(self, answer):
        """Submit answer to pending question. Answer can be string or list."""
        submitted = False
        with self._lock:
            if self.pending_question and self.pending_question.get("active"):
                # Handle both single answer (string) and multiple answers (list)
                if isinstance(answer, list):
                    self.pending_question["answer"] = answer
                    self.pending_question["active"] = False
                    answer_str = ", ".join(str(a) for a in answer)
                    self.inbox.append(f"[answer] {answer_str}")
                    submitted = True
                else:
                    self.pending_question["answer"] = str(answer)
                    self.pending_question["active"] = False
                    self.inbox.append(f"[answer] {answer}")
                    submitted = True
        
        # Log outside lock to prevent deadlock
        if submitted:
            self.push_log("info", f"✓ Answer submitted")

    def get_pending_question(self) -> Optional[Dict]:
        """Get current pending question."""
        with self._lock:
            return self.pending_question

    def clear_pending_question(self):
        """Clear pending question after answer is processed."""
        with self._lock:
            self.pending_question = None

    def cancel_question(self):
        """Cancel pending question."""
        with self._lock:
            if self.pending_question:
                self.pending_question["active"] = False
                self.pending_question = None

    # ── Cycle timing ─────────────────────────────────────────────────────────────
    def set_cycle_gap(self, gap: float):
        """Set minimum gap between agent cycles (seconds)."""
        with self._lock:
            self.min_cycle_gap = max(0.0, gap)  # Prevent negative values

    def get_cycle_gap(self) -> float:
        """Get current minimum cycle gap."""
        with self._lock:
            return self.min_cycle_gap

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
