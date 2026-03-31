#!/usr/bin/env python3
"""Jerry Configuration Package"""

# Re-export from core.py
from .core import (
    JERRY_CORE_DIR,
    JERRY_BASE,
    AGENT_URL,
    WORKER_URL,
    MAX_TOKENS,
    TEMPERATURE,
    CYCLE_SLEEP,
    LOG_LIMIT,
    CONV_TRIM,
    RAW_LOG_LIMIT,
    WORKSPACE_DIR,
    DIARY_DIR,
    LOGS_DIR,
    SUMMARY_DIR,
    PERSONA_DIR,
)

# Re-export from tools.py
from .tools import (
    TOOL_CATALOG,
    get_tool_catalog,
)

# Re-export from prompt.py
from .prompt import (
    SYSTEM_PROMPT,
)

# Backward compatibility - re-export TOOLS from tools_minimal
from ..tools_minimal import TOOLS

__all__ = [
    "JERRY_CORE_DIR",
    "JERRY_BASE",
    "AGENT_URL",
    "WORKER_URL",
    "MAX_TOKENS",
    "TEMPERATURE",
    "CYCLE_SLEEP",
    "LOG_LIMIT",
    "CONV_TRIM",
    "RAW_LOG_LIMIT",
    "WORKSPACE_DIR",
    "DIARY_DIR",
    "LOGS_DIR",
    "SUMMARY_DIR",
    "PERSONA_DIR",
    "TOOL_CATALOG",
    "get_tool_catalog",
    "TOOLS",
    "SYSTEM_PROMPT",
]
