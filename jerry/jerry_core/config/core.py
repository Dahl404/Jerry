#!/usr/bin/env python3
"""Jerry — Core Configuration Constants

Paths are relative to the jerry.py script location for portability.
"""

import os
from typing import List, Dict

# ─── Base Directory (relative to script location) ─────────────────────────────
# Get the directory where jerry_core is located
JERRY_CORE_DIR = os.path.dirname(os.path.abspath(__file__))
# Parent of jerry_core = jerry root
JERRY_BASE = os.path.dirname(os.path.dirname(JERRY_CORE_DIR))

# ─── API Endpoints ─────────────────────────────────────────────────────────────
AGENT_URL    = "http://localhost:8080/v1/chat/completions"
WORKER_URL   = "http://localhost:8081/v1/chat/completions"

# ─── Model Parameters ──────────────────────────────────────────────────────────
MAX_TOKENS   = 15000
TEMPERATURE  = 0.7
CYCLE_SLEEP  = 5.0

# ─── Limits ────────────────────────────────────────────────────────────────────
LOG_LIMIT    = 600
CONV_TRIM    = 60  # Keep last 60 messages (prevents 4k+ token issues with tool calls)
RAW_LOG_LIMIT = 10000

# ─── Directory Paths (all relative to JERRY_BASE) ─────────────────────────────
WORKSPACE_DIR = os.path.join(JERRY_BASE, "jerry_workspace")
DIARY_DIR     = os.path.join(WORKSPACE_DIR, "diary")
LOGS_DIR      = os.path.join(JERRY_BASE, "logs")
SUMMARY_DIR   = os.path.join(WORKSPACE_DIR, "summaries")
PERSONA_DIR   = os.path.join(WORKSPACE_DIR, "persona")
