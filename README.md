# JERRY vALPHA_006 — Autonomous Agent System

## System Overview

Jerry is an autonomous AI agent operating within a sandboxed workspace environment. The system consists of a background reasoning agent, a dual-model architecture for task execution and file analysis, and a real-time ncurses terminal interface.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        jerry.py (Entry)                         │
│  Signal handling │ Logging │ Splash │ Main loop │ Watchdog     │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│   Agent       │   │   Executor      │   │   TUI         │
│   Reasoning   │──▶│   Tool Dispatch │──▶│   Display     │
│   Streaming   │◀──│   Validation    │◀──│   Input       │
└───────────────┘   └─────────────────┘   └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌─────────────────┐   ┌───────────────┐
│   Worker      │   │   Terminal      │   │   Faces       │
│   Analysis    │   │   Control (tmux)│   │   Emotions    │
└───────────────┘   └─────────────────┘   └───────────────┘
```

---

## Core Modules

### agent.py — Autonomous Reasoning Engine
- Maintains conversation state with system prompt and tool definitions
- Executes autonomous reasoning cycles with tool calls
- Streaming output with real-time token generation
- Loop detection (prevents repetitive tool call patterns)
- Idle reflection system (triggers after 30s inactivity)
- Multi-modal message processing (image support)
- Conversation trimming and compression
- Tool call parsing (structured + 4 fallback patterns)

### worker.py — Secondary Analysis Model
- Separate model instance for file analysis (default: same port as agent)
- Loads files with line numbers for precise reference
- Supports multi-file cross-reference analysis
- Conversation history compression
- Query-based interaction pattern
- Worker history limit: 40 messages (~20 Q&A pairs)

### executor.py — Tool Dispatch System
- 25 tools for file operations, navigation, terminal control
- Relative path resolution within workspace boundaries
- Path validation (restricts access to workspace and temp directories)
- Streaming feedback for long-running operations
- Special key token parsing (`<enter>`, `<ctrl-c>`, `<tab>`, etc.)
- Command timeout: 60s default, 300s max

### tui.py — Terminal User Interface
- ncurses-based interface (~2520 lines)
- Dual theme support (light/dark with auto-detection)
- Proportional face panel rendering (70% width, aspect-preserving)
- Todo sidebar with priority indicators (high/medium/low)
- Animated status bar (spinners, loading bars, typing animations)
- Stream mode display for terminal control
- Question panels with multi-select support
- Command system (20+ `/` commands)
- File upload handling (`/load`)

### faces_display.py — Emotional State Rendering
- 7 discrete emotional states
- ASCII art face scaling (proportional to terminal size)
- Emotion tag parsing from agent responses
- Smooth transitions via neutral state
- Real-time updates during streaming

### terminal.py — Terminal Control
- tmux-based screen capture and input injection
- Special key support (arrows, function keys, Ctrl sequences)
- Session management
- Capability detection

### screen_stream.py — Stream Mode
- Creates/manages tmux sessions for program execution
- Continuous screen capture (5 FPS)
- Keystroke injection with escape sequence handling
- Program lifecycle detection (exit detection via screen analysis)
- Auto-creates sessions if not exists

### session.py — Session Management
- Automatic archival on shutdown
- Summary generation (conversation, todos, activity)
- Persona document creation (behavioral analysis)
- Raw JSON log export
- Compression support

### splash_screen.py — Particle Animation System
- Edge-diffusion particle assembly
- Radial build from center
- Shimmer effect with particle phases
- Smooth scroll animation
- Evaporation transition to live interface
- Uses `jerry_core/splash_faces` ASCII art

---

## Tool Catalog

| Tool | Category | Description |
|------|----------|-------------|
| `help` | System | Get tool info (call for details) |
| `execute_command` | System | Run shell commands with timeout |
| `read_file` | File | Read file with line numbers, supports images |
| `write_file` | File | Write content to file |
| `replace_lines` | File | Replace line range |
| `insert_lines` | File | Insert lines after position |
| `delete_lines` | File | Delete line range |
| `list_directory` | Navigation | List directory contents |
| `enter` | Navigation | Change working directory |
| `pwd` | Navigation | Show current directory |
| `search_files` | Search | Grep with flags (recursive, case-sensitive) |
| `todo_write` | Planning | Set todo list (array of {content, priority, completed}) |
| `todo_complete` | Planning | Mark task complete by index or stable ID |
| `query_worker` | Analysis | Ask worker about loaded file |
| `reset_worker` | Analysis | Clear worker context |
| `load_multiple_files` | Analysis | Load multiple files for cross-reference |
| `worker_write_program` | Analysis | Worker AI writes code from spec (fast drafts) |
| `send_keys` | Terminal | Send keystrokes to tmux (supports `<token>` format) |
| `send_ctrl` | Terminal | Send Ctrl sequence |
| `capture_screen` | Terminal | Capture terminal screen |
| `run_program` | Terminal | Run program in stream mode |
| `ask_user` | Interaction | Ask user with scrollable options + custom input |
| `write_diary` | Reflection | Write diary entry with mood |
| `read_diary` | Reflection | Read past entries |
| `check_coins` | System | Check coin balance |
| `offer_coins` | System | Offer coins to user for permission/help |

---

## Model Compatibility

### Recommended Models

| Model | Size | Status | Notes |
|-------|------|--------|-------|
| **OmniCoder** | 9B | ✓ Production | Code-optimized, fast inference |
| **Qwen3.5** | 4B-9B | ✓ Production | Thinking tokens, full tool support |

### Tested Configurations

| Model | Port | Status | Notes |
|-------|------|--------|-------|
| Qwen3.5 | 8080 | ✓ Production | Thinking tokens, full tool support |
| Qwen3 | 8080 | ✓ Production | Standard tool calling |
| OmniCoder | 8080 | ✓ Production | Code-optimized |

### Experimental Support

| Model | Status | Notes |
|-------|--------|-------|
| LFM2 | ⚠ Experimental | Limited tool support |
| Python-style tool calling models | ⚠ Experimental | Fallback parser supports bracket syntax |

### API Specification

```
POST /v1/chat/completions
Host: localhost:8080

{
  "messages": [{"role": "system", "content": "..."}],
  "tools": [...],
  "tool_choice": "auto",
  "max_tokens": 15000,
  "temperature": 0.7,
  "stream": true
}
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JERRY_AGENT_PORT` | 8080 | Agent model API port |
| `JERRY_WORKER_PORT` | (same) | Worker model API port |

---

## Workspace Structure

```
jerry_workspace/
├── scratchpad/     # Active project working memory
├── diary/          # Agent reflections (date-stamped)
├── programs/       # Executable code
├── summaries/      # Session summaries (auto-generated)
├── persona/        # Behavioral profiles (auto-generated)
├── io/             # User-uploaded files (via /load)
└── .coins.json     # Persistent coin balance
```

### Path Restrictions

All file operations are restricted to:
- `jerry_workspace/` and subdirectories
- `/tmp`
- `/data/data/com.termux/cache` (Termux)

Attempts to access paths outside these boundaries are rejected.

---

## Emotional States

| State | Trigger Conditions |
|-------|-------------------|
| `neutral` | Default, between emotions |
| `smiling` | Success, helping, positive outcomes |
| `mad` | Repeated failures, errors, frustration |
| `bummed` | Failures, disappointing results |
| `questioning` | Uncertainty, seeking clarification |
| `thinking` | Analysis, planning, consideration |
| `surprise` | Unexpected results, discoveries |

Emotion tags are parsed from agent output: `<smiling>`, `<thinking>`, etc.

---

## Stream Mode

Stream mode enables Jerry to control external terminal sessions:

```
/stream <session-name>   # Start watching/controlling session
/type <text>             # Send keystrokes to session
Ctrl+Q                   # Exit stream mode
```

### How It Works

1. Jerry creates or attaches to a tmux session
2. Screen is captured via `tmux capture-pane` (5 FPS)
3. Keystrokes are sent via `tmux send-keys`
4. Special tokens (`<enter>`, `<ctrl-c>`, `<tab>`) are parsed
5. Program exit is detected via screen content analysis

---

## Coin System

Jerry maintains a persistent coin balance:

| Action | Coins |
|--------|-------|
| User praise (`/praise`) | +5 to +10 (based on detail) |
| Jerry offers (negotiation) | Variable (requires user acceptance) |

Balance is stored in `jerry_workspace/.coins.json` with full transaction history.

---

## Commands

### Navigation
- `↑` / `↓` — Scroll focused panel
- `PageUp` / `PageDown` — Fast scroll (8 lines)

### Slash Commands

| Command | Function |
|---------|----------|
| `/log` | Activity log view |
| `/chat` | Conversation view |
| `/todo` | Todo list view |
| `/stream <session>` | Start stream mode |
| `/type <text>` | Send keys to session |
| `/clear` | Clear input buffer |
| `/compress` | Compress conversation using worker |
| `/theme [dark|light|auto]` | Set theme |
| `/face [show|hide]` | Toggle face panel |
| `/chat_threshold <n>` | Set full-feed height (default: 15) |
| `/gap [seconds]` | Set agent cycle speed (default: 0.2) |
| `/praise [reason]` | Award coins |
| `/coins` | Check balance + transaction history |
| `/load <path>` | Upload file(s) to io/ |
| `/listio` | List io/ contents with sizes |
| `/cleario` | Clear io/ directory |
| `/inject <msg>` | Inject to agent inbox |
| `/quit` | Exit |
| `/help` | Show help |

---

## Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Startup                                                   │
│    - Setup logging (redirect stdout/stderr to logs/)        │
│    - Initialize state, worker, executor, TUI, agent, session │
│    - Discover local files in workspace                       │
│    - Register screen callback for streaming                  │
│    - Capture initial Jerry frame                             │
│    - Display splash screen (particle animation)              │
│    - Start agent thread                                      │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 2. Main Loop (10 FPS)                                        │
│    - Poll for keyboard input (non-blocking)                  │
│    - Drain additional buffered keys (fast typing)            │
│    - Render TUI (selective redraw optimization)              │
│    - Watchdog: restart agent if dead (check every 5s)        │
│    - Sleep 100ms                                             │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 3. Agent Thread (Autonomous)                                 │
│    - Check inbox for user messages (priority)                │
│    - Check for pending todos                                 │
│    - Idle reflection (30s timeout)                           │
│    - Execute reasoning cycle (max 30-50 turns)               │
│      ├─ Trim conversation (keep last 60 messages)            │
│      ├─ Call model (streaming with retry)                    │
│      ├─ Parse tool calls (structured + fallback)             │
│      ├─ Validate tool calls (filter incomplete)              │
│      ├─ Execute tools                                        │
│      ├─ Append results                                       │
│      └─ Loop detection (same tool+args x5)                   │
│    - Update token count                                      │
│    - Minimum cycle gap: 3.0s                                 │
└──────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────────────┐
│ 4. Shutdown                                                  │
│    - Stop agent thread                                       │
│    - Stop screen stream                                      │
│    - Stop terminal controller                                │
│    - Kill tmux sessions (prevent orphans)                    │
│    - Session archival:                                       │
│      ├─ Save dated summary (conversation, todos, activity)   │
│      ├─ Save persona document (behavioral analysis)          │
│      └─ Archive raw logs as JSON                             │
└──────────────────────────────────────────────────────────────┘
```

---

## Error Handling

### Conversation Recovery
- 400 errors trigger aggressive conversation trimming (keep last 20)
- Loop detection breaks repetitive tool call cycles (5 repeats)
- Watchdog restarts dead agent threads
- Retry logic for streaming failures (max 2 retries)

### Tool Execution
- Path validation prevents unauthorized access
- Command timeouts (60s default, 300s max)
- Streaming feedback for long operations
- Help text included in error messages

### Terminal Control
- tmux availability check on startup
- Graceful fallback when tmux unavailable
- Session existence verification
- Consecutive error detection (10 errors = session dead)

---

## Requirements

| Component | Version | Purpose |
|-----------|---------|---------|
| Python | 3.8+ | Runtime |
| curses | bundled | TUI rendering |
| tmux | any | Terminal control |
| llama-server | latest | Model API |

---

## Quick Start

```bash
# Terminal 1: Start model API
llama-server -m your-model.gguf --port 8080 --tools

# Terminal 2: Run Jerry
python jerry.py
```

---

## System Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `MAX_TOKENS` | 15000 | Max response tokens |
| `TEMPERATURE` | 0.7 | Model temperature |
| `CYCLE_SLEEP` | 0.2 | Default cycle gap (user-configurable via `/gap`) |
| `LOG_LIMIT` | 600 | Max log entries in memory |
| `RAW_LOG_LIMIT` | 10000 | Max raw log entries |
| `CONV_TRIM` | 60 | Max conversation messages |
| `AGENT_TIMEOUT` | 120 | API timeout seconds |
| `WORKER_TIMEOUT` | 120 | Worker API timeout |
| `WORKER_HIST_LIMIT` | 40 | Worker conversation limit |
| `MIN_CYCLE_GAP` | 3.0 | Minimum seconds between cycles |

---

*Jerry operates autonomously. Monitor output. Review tool calls. Maintain workspace hygiene.*
