# 🐭 Jerry — Autonomous Qwen3.5 Agent (Alpha)

> **⚠️ Alpha Release** — This is a **minimal proof-of-concept (POC)**. Jerry is mobile-first, aesthetic-focused, and built for fast local inference on Termux/Android. Expect bugs and rapid iteration.

---

## What is Jerry?

**Jerry** is an autonomous AI agent with an emotional ASCII face, designed to run **locally on mobile devices** (Termux/Android) with Qwen3.5 (or compatible) models. Jerry thinks, plans, executes tasks, and displays emotions in real-time — all while staying minimal and keyboard-friendly.

### Core Features

#### UI/UX
- **Emotional ASCII Face** — Real-time emotion display with smooth transitions
- **Two Visibility Modes**:
  - **Compact** — Keyboard-friendly, minimal feed (chat + recent logs)
  - **Full** — Debug-style full log feed with all tool calls, results, thoughts
- **Dark/Light Themes** — Auto-detect based on terminal background or manual toggle
- **Smooth Animations** — Loading bars, typing indicators, transition effects
- **Face Panel Toggle** — Enable/disable with `/face show` or `/face hide`
- **Chat Threshold** — Auto-switch modes based on available rows (default: 15)

#### Agent Capabilities
- **Autonomous Planning** — Creates todo lists with stable IDs, works independently
- **Parallel Message Injection** — Non-blocking operation with background agent thread
- **Basic Tool Calling** — Shell, file ops, navigation, search, todo management
- **Diary System** — Jerry writes reflections with mood tags to `jerry_workspace/diary/`
- **Session Archival** — Automatic summaries, persona documents, and raw logs on shutdown
- **Emotion Tags** — Jerry expresses feelings via `<tags>` in responses
- **No Timeouts** — Connections held indefinitely (no arbitrary cutoffs)

#### Mobile Optimization
- **Lightweight** — Minimal context (60 msg limit), no prompt bloat
- **Fast Local Inference** — Runs on-device with Qwen3.5 via llama.cpp/Ollama
- **Keyboard-Friendly** — Arrow keys for scrolling, shortcuts, compact mode
- **Location-Agnostic** — Relative path system, run from anywhere
- **tmux Streaming** — Watch Jerry run programs live in real-time

---

## Quick Start

### Install on Termux (Android)

```bash
# Install dependencies
pkg update && pkg upgrade
pkg install python git tmux

# Clone Jerry
git clone https://github.com/Dahl404/Jerry.git
cd Jerry

# Run Jerry
./jerry
```

### Model Setup

Jerry expects local AI model API endpoints:
- **Default**: Both Agent and Worker use `http://localhost:8080/v1/chat/completions`
- **Separate Ports**: Agent on `8080`, Worker on `8081` (optional)

**Configuration Options:**

1. **Same Port (Default)**:
   ```bash
   # Both agent and worker use port 8080
   export JERRY_AGENT_PORT=8080
   export JERRY_WORKER_PORT=8080  # Or omit, defaults to agent port
   ```

2. **Separate Ports**:
   ```bash
   export JERRY_AGENT_PORT=8080
   export JERRY_WORKER_PORT=8081
   ```

3. **Custom Ports**:
   ```bash
   export JERRY_AGENT_PORT=11434  # e.g., Ollama default
   export JERRY_WORKER_PORT=11434
   ```

Configure in `jerry_core/config.py` if not using environment variables.

**Recommended Models:**
- Qwen3.5 (via llama.cpp, Ollama, or vLLM)
- Any OpenAI-compatible local model

---

## Usage

### Basic Commands

| Command | Description |
|---------|-------------|
| `Type + Enter` | Talk to Jerry |
| `/help` | Show all commands |
| `/quit` | Exit Jerry |
| `/face hide` | Hide face panel (compact mode) |
| `/face show` | Show face panel (full mode) |
| `/theme dark|light|auto` | Toggle or set theme |
| `/chat_threshold <n>` | Switch to full feed at N+ rows (default: 15) |
| `/stream <session>` | Watch/control tmux session |
| `/type <text>` | Type into streamed session |
| `/inject <msg>` | Inject message into agent stream |
| `/compress` | Compress conversation history |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Scroll focused panel |
| `Ctrl+Q` | Exit stream mode |
| `q` | Exit stream mode (when streaming) |
| `Enter` | Send message / Execute command |

### Emotion System

Jerry displays emotions via ASCII art face. Current emotions:

| Tag | Context |
|-----|---------|
| `<smiling>` / `<happy>` | Helping, succeeding, positive |
| `<thinking>` / `<pondering>` | Analyzing, considering options |
| `<mad>` / `<angry>` | Frustrated, encountering errors |
| `<bummed>` / `<sad>` | Failed, disappointing news |
| `<questioning>` / `<confused>` | Puzzled, uncertain, wondering |
| `<surprise>` / `<surprised>` | Something unexpected |
| `<shocked>` / `<amazed>` | Very surprised or impressed |
| `<neutral>` | Default state, between emotions |

**Live Parsing:** Jerry's face updates in real-time as emotion tags appear in responses. The **last tag** in a message determines the displayed emotion.

Example:
```
Jerry: <thinking> Let me check that file... <smiling> Found it!
→ Face transitions: neutral → thinking → smiling
```

---

## Roadmap (Planned Features)

### Near-Term
- [ ] **Robust Tool Calling** — Expanded tool system with better error handling, retry logic
- [ ] **Worker Improvements** — Single port (8080) or dual port (8080+8081) configuration
- [ ] **Model Switching** — Hot-swap models at runtime via config or command
- [ ] **Integrated Inference** — Bundle inference engine (llama.cpp) with Jerry
- [ ] **Enhanced Screen Streaming** — More reliable tmux capture, better error recovery
- [ ] **More Emotions** — Expanded emotion set, custom face creation
- [ ] **Generative Emotion Panels** — Dynamic ASCII art based on context
- [ ] **Better Animations** — Smooth transitions, visual polish, performance optimization

### Future Vision
- [ ] **C++ Port** — Convert performance-critical parts to C++ for speed
- [ ] **RAG Integration** — Retrieval-augmented generation for long-term memory
- [ ] **TTT-E2E** — Test-Time Training for end-to-end adaptation
- [ ] **DISCOVER** — Autonomous exploration and learning capabilities
- [ ] **Minor QLoRAs** — Continual adaptation via lightweight fine-tuning
- [ ] **Persistent Memory** — Long-term knowledge retention across sessions
- [ ] **Multi-Modal** — Image/code screenshot analysis

### Core Goals
- **Ease of Use** — Zero-config, works out of the box
- **Fluidity** — Smooth UI, responsive interactions, no lag
- **Speed** — Fast inference, minimal latency, efficient rendering
- **Mobile-First** — Optimized for Termux/Android, low resource usage
- **Minimal Bloat** — Lean context, efficient prompts, no token waste

---

## Project Structure

```
Jerry/
├── jerry                    # Bash launcher script (location-agnostic)
├── jerry.py                 # Main entry point (ncurses TUI)
├── jerry_core/              # Core Python package
│   ├── __init__.py          # Package exports
│   ├── agent.py             # Autonomous agent loop with streaming
│   ├── config.py            # Configuration & tool catalog
│   ├── executor.py          # Tool execution engine
│   ├── faces_display.py     # ASCII emotion face rendering
│   ├── models.py            # Data models (State, ChatMsg, Todo, LogEntry)
│   ├── screen_stream.py     # Terminal screen capture & streaming
│   ├── session.py           # Session archival (summaries, persona, logs)
│   ├── terminal.py          # Terminal control via tmux
│   ├── tools_minimal.py     # Minimal tool definitions
│   ├── tui.py               # ncurses TUI renderer
│   └── worker.py            # Worker model manager
├── faces/                   # ASCII face art files (.txt)
├── jerry_workspace/         # Working directory (auto-created)
│   ├── diary/               # Jerry's reflections
│   ├── summaries/           # Session summaries
│   ├── persona/             # Persona documents
│   └── logs/                # Runtime logs
└── logs/                    # Application logs (jerry_stdout.log)
```

---

## Configuration

Edit `jerry_core/config.py` to customize:

```python
# API Endpoints (can also use environment variables)
# Default: Both use port 8080
AGENT_PORT   = 8080
WORKER_PORT  = 8080  # Same as agent by default

# Or use environment variables:
# export JERRY_AGENT_PORT=8080
# export JERRY_WORKER_PORT=8081

AGENT_URL    = f"http://localhost:{AGENT_PORT}/v1/chat/completions"
WORKER_URL   = f"http://localhost:{WORKER_PORT}/v1/chat/completions"

# Model Parameters
MAX_TOKENS  = 15000
TEMPERATURE = 0.7
CYCLE_SLEEP = 5.0  # Seconds between agent cycles

# Limits
LOG_LIMIT   = 600   # Visible log entries in feed
CONV_TRIM   = 60    # Keep last 60 messages in context
RAW_LOG_LIMIT = 10000  # Raw log entries for archival

# Directory Paths (relative, location-agnostic)
JERRY_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JERRY_BASE     = os.path.join(JERRY_BASE_DIR, "jerry_workspace")
```

---

## Tool System

Jerry's tool catalog (call `help()` for full usage):

### Core Tools
- `execute_command` — Run shell/bash commands
- `read_file` — Read file with line numbers (loads into worker context)
- `write_file` — Write content to file
- `list_directory` — List directory contents

### File Editing
- `replace_lines` — Replace line range in file
- `insert_lines` — Insert lines after given line number
- `delete_lines` — Delete line range from file

### Task Management
- `todo_add` — Add task(s) to todo list
- `todo_complete` — Mark todo as done by index
- `todo_remove` — Remove todo by index

### Terminal Streaming
- `run_program` — Run program/command in stream mode
- `send_keys` — Send keystrokes to terminal
- `capture_screen` — Capture current terminal screen
- `send_ctrl` — Send control sequences (Ctrl+C, etc.)

### Worker AI
- `query_worker` — Ask worker about loaded file
- `reset_worker` — Clear worker conversation history

### Utilities
- `enter` — Change current working directory
- `pwd` — Show current working directory
- `write_diary` — Write reflection to diary
- `read_diary` — Read past diary entries
- `set_expression` — Set emotional/physical state
- `help` — Show tool usage details

---

## Known Issues (Alpha)

- **Display flickering** — Fixed with optimized rendering (v0.0.3)
- **Tool errors** — Some tools may fail silently or return unexpected results
- **Emotion lag** — Face may not update instantly on slow devices
- **tmux issues** — Streaming can be unstable, especially on low-RAM devices
- **Memory growth** — Long sessions may consume RAM over time
- **Path validation** — Some edge cases in relative path resolution
- **Same-port worker** — If using same port for agent+worker, ensure model supports both chat and text-processing tasks

**Workaround:** Restart Jerry (`/quit`) if issues occur. Check `logs/jerry_stdout.log` for errors.

---

## Active TODOs & Bugs

### High Priority
- [ ] **Worker context persistence** — Worker resets on every file load, losing previous context
- [ ] **Tool call error handling** — Better error messages and retry logic
- [ ] **Screen capture reliability** — Improve tmux capture for curses-based terminals
- [ ] **Memory leaks** — Long-running sessions accumulate state

### Medium Priority
- [ ] **Emotion transition smoothing** — Add fade effects between face changes
- [ ] **Chat scroll persistence** — Remember scroll position across renders
- [ ] **Input validation** — Better handling of malformed tool calls
- [ ] **Worker compression** — Test and optimize conversation compression

### Low Priority / Future
- [ ] **Custom face creation** — Allow users to design custom emotion faces
- [ ] **Theme customization** — User-defined color schemes
- [ ] **Plugin system** — Extensible tool architecture
- [ ] **Multi-session support** — Run multiple Jerry instances

### Known Bugs (Tracked)
- **BUG-A**: Worker context lost on file reload (design limitation)
- **BUG-B**: Emotion parsing can miss tags in long streaming responses
- **BUG-C**: Duplicate task prompts when task #0 completes (partially fixed)
- **BUG-D**: Screen flicker during rapid updates (improved in v0.0.3)

---

## Philosophy

Jerry is built on three principles:

1. **Minimal Bloat** — Every token counts. Lean prompts, fast inference, no waste.
2. **Mobile-First** — If it doesn't work on Termux, it doesn't work. Period.
3. **Aesthetic & Fluid** — Beautiful UI, smooth animations, satisfying interactions.

This is a **proof-of-concept**, not a polished product. Expect bugs, but also expect rapid iteration and improvement.

---

## Technical Details

### Architecture
- **Modular Design** — Clean separation: Agent, Executor, TUI, Worker, Session
- **Thread-Safe State** — Shared state with proper locking for concurrency
- **Streaming Output** — Real-time token display as model generates
- **Background Agent** — Non-blocking operation with watchdog restart
- **Relative Paths** — Location-agnostic, works from any directory

### Performance
- **10 FPS Rendering** — Smooth but not CPU-intensive
- **Non-Blocking Input** — Nodelay mode for responsive keyboard handling
- **Efficient Context** — 60 message limit prevents token bloat
- **Lazy Loading** — Tools discovered on-demand via `help()`

### Session Management
- **Automatic Archival** — Summaries, persona docs, and raw logs saved on shutdown
- **Dated Files** — All artifacts timestamped for easy retrieval
- **Symlink to Latest** — `jerry_stdout.log` always points to current session

---

## Contributing

This is a personal project, but ideas and feedback are welcome!

**Ways to Help:**
- Report bugs (open an issue with logs)
- Suggest features (see roadmap above)
- Optimize code (especially C++ port candidates)
- Test on different devices/models
- Improve documentation

---

## Contact

**Author:** Dahl404  
**Repo:** https://github.com/Dahl404/Jerry  
**Issues:** https://github.com/Dahl404/Jerry/issues

---

## License

MIT License — Modify, distribute, experiment!

---

## Acknowledgments

- **Qwen3.5** — Primary AI model
- **llama.cpp** — Local inference engine
- **ncurses** — Terminal UI library
- **Qwen-Code CLI** — Tool system inspiration

---

> **Jerry is alpha software.** Use at your own risk. Experiment freely. Have fun!
