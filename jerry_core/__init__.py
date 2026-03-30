#!/usr/bin/env python3
"""Jerry Core Package — Autonomous AI Agent"""

from .config import (
    AGENT_URL,
    WORKER_URL,
    MAX_TOKENS,
    TEMPERATURE,
    CYCLE_SLEEP,
    LOG_LIMIT,
    CONV_TRIM,
    JERRY_BASE,
    DIARY_DIR,
    LOGS_DIR,
    SUMMARY_DIR,
    PERSONA_DIR,
    TOOLS,
    SYSTEM_PROMPT,
)

from .models import (
    ts,
    LogEntry,
    ChatMsg,
    Todo,
    DiaryEntry,
    State,
)

from .worker import (
    strip_think,
    Worker,
)

from .executor import (
    Executor,
)

from .agent import (
    Agent,
)

from .tui import (
    TUI,
)

from .session import (
    SessionManager,
)

__all__ = [
    # Config
    "AGENT_URL",
    "WORKER_URL",
    "MAX_TOKENS",
    "TEMPERATURE",
    "CYCLE_SLEEP",
    "LOG_LIMIT",
    "CONV_TRIM",
    "JERRY_BASE",
    "DIARY_DIR",
    "LOGS_DIR",
    "SUMMARY_DIR",
    "PERSONA_DIR",
    "TOOLS",
    "SYSTEM_PROMPT",
    # Models
    "ts",
    "LogEntry",
    "ChatMsg",
    "Todo",
    "DiaryEntry",
    "State",
    # Worker
    "strip_think",
    "Worker",
    # Executor
    "Executor",
    # Agent
    "Agent",
    # TUI
    "TUI",
    # Session
    "SessionManager",
]
