# Jerry — Autonomous Qwen3.5 Agent (Alpha 0.0.4)

> **⚠️ Alpha Release** — This is a **minimal proof-of-concept (POC)**. Mobile-first, aesthetic-focused TUI agent built for fast local inference on Termux/Android.

---

## Latest Updates (Alpha 0.0.4)

### 🪙 Coin/Reward System (NEW!)
- **User Praise** — Use `/praise [reason]` to reward Jerry with 5-10 coins
- **Coin Balance** — Check with `/coins` to see balance and transaction history
- **Jerry Can Offer Coins** — New `offer_coins()` tool for negotiations
- **Jerry Can Check Coins** — New `check_coins()` tool to see balance
- **Coin Persistence** — Coins saved to `.coins.json`, persists across sessions!
- **Barter System** — Jerry can offer coins for permissions or special requests

### 📁 Multi-File Worker (NEW!)
- **`load_multiple_files()`** — Load multiple files at once for cross-file analysis
- **Worker Keeps Context** — Option to preserve context when loading multiple files
- **Cross-File Analysis** — Worker can now compare and analyze multiple files together

### 🔄 Continue Token Loop (Qwen-Code CLI Pattern)
- **Always Uses `[continue]`** — Jerry gets continue prompt while tasks pending
- **Loop Continues Until**:
  1. Task complete (calls `todo_complete`)
  2. User interrupts with new message
  3. Jerry asks question (`ask_user` tool)
- **No More Assistant-Replying-to-Assistant** — Fixed 400 errors from conversation format

### ❓ Ask User Tool
- **`ask_user(question)`** — Jerry can ask for clarification/decisions
- **Blocks Until Answer** — Jerry waits for user response
- **Shows Questioning Face** — Emotion matches the interaction

### 🐛 Critical Fixes
- **Tool Call Validation** — Generate IDs instead of filtering, prevents losing tool calls
- **Break After Text Response** — Prevents 400 errors from assistant replying to assistant
- **User Interrupt During Streaming** — Check inbox every iteration, not just at turn start
- **Command Error Handling** — `/praise` and `/coins` now have try/catch

### 📝 Documentation
- **debug.md** — Documents 400 error root cause and fix
- **clean.sh Updated** — Now properly cleans all workspace subdirectories

### Recommended Setup
For the best experience, we recommend:
- **llama.cpp** — Build locally from source for optimal performance on your device
- **Omni-Coder 9B** — **DEFAULT MODEL** — Best balance of speed and capability for Jerry's tool-calling tasks
- **Disable enable_thinking** — Launch llama-server without `--enable-thinking` flag

### Default Model Configuration
```bash
# Recommended: Omni-Coder 9B for tool-calling
./llama-server --model models/omni-coder-9b.gguf --port 8080 --ctx-size 32768

# Alternative: Qwen3.5 7B for faster inference
./llama-server --model models/qwen3.5-7b.gguf --port 8080 --ctx-size 32768
```

---

## What is Jerry?

**Jerry** is an autonomous AI agent with an emotional ASCII face, designed to run **locally on mobile devices** (Termux/Android) with Qwen3.5 or Omni-Coder 9B (or compatible) models. Jerry thinks, plans, executes tasks, and displays emotions in real-time — all while staying minimal and keyboard-friendly.

### Core Features

#### UI/UX
- **Emotional ASCII Face** — Real-time emotion display with smooth transitions through neutral
- **Live Emotion Parsing** — Face changes dynamically as emotion tags appear in streaming responses
- **Two Visibility Modes**:
  - **Compact** — Keyboard-friendly, minimal feed (chat + recent logs)
  - **Full** — Debug-style full log feed with all tool calls, results, thoughts
- **Dark/Light Themes** — Auto-detect based on terminal background or manual toggle
- **Smooth Animations** — Loading bars, typing indicators, transition effects
- **Face Panel Toggle** — Enable/disable with `/face show` or `/face hide`
- **Chat Threshold** — Auto-switch modes based on available rows (default: 15)
- **Coin/Reward Display** — Track Jerry's earnings and spending with `/coins`

#### Agent Capabilities
- **Autonomous Planning** — Creates todo lists with stable IDs, works independently
- **Continue Token Loop** — Uses `[continue]` pattern (Qwen-Code CLI style)
- **Parallel Message Injection** — Non-blocking operation with background agent thread
- **Tool Calling** — Shell, file ops, navigation, search, todo management
- **Ask User Questions** — `ask_user()` tool for clarification/decisions
- **Diary System** — Jerry writes reflections with mood tags to `jerry_workspace/diary/`
- **Session Archival** — Automatic summaries, persona documents, and raw logs on shutdown
- **Emotion Tags** — Jerry expresses feelings via `<tags>` in responses (e.g., `<smiling>`, `<thinking>`)
- **No Timeouts** — Connections held indefinitely for edge device inference (no arbitrary cutoffs)
- **Workspace Security** — File access restricted to workspace directory only

#### Worker AI (On-Demand Analysis)
- **Lazy Loading** — Worker only loads files when explicitly queried
- **Auto-Load on Query** — `query_worker(file="...", question="...")` loads and analyzes in one call
- **Multi-File Loading** — `load_multiple_files()` loads multiple files at once
- **Cross-File Analysis** — Worker can compare and analyze multiple files together
- **Manual Clear** — `reset_worker()` clears worker context when finished
- **Efficient Context** — Worker context stays clean, only used for actual analysis

#### Coin/Reward System
- **User Praise** — `/praise [reason]` awards 5-10 coins to Jerry
- **Check Balance** — `/coins` shows current balance and transaction history
- **Jerry Can Check** — `check_coins()` tool to see current balance
- **Jerry Can Offer** — `offer_coins(amount, reason)` for negotiations
- **Persistent Across Sessions** — Coins saved to `.coins.json` in workspace

#### Mobile Optimization
- **Lightweight** — Minimal context (60 msg limit), no prompt bloat
- **Fast Local Inference** — Runs on-device with Omni-Coder 9B / Qwen3.5 via llama.cpp/Ollama
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
- `read_file` — Read file with line numbers (returns content only, doesn't load worker)
- `write_file` — Write content to file
- `list_directory` — List directory contents (defaults to current directory)

### File Editing
- `replace_lines` — Replace line range in file
- `insert_lines` — Insert lines after given line number
- `delete_lines` — Delete line range from file

### Task Management
- `todo_write` — Replace entire todo list (Qwen-Code CLI style)
- `todo_complete` — Mark todo as done by index or stable ID
- `todo_add` — Add tasks (backward compatible)
- `todo_remove` — Remove todo by index

### Terminal Streaming
- `run_program` — Run program/command in stream mode
- `send_keys` — Send keystrokes to terminal (supports `<enter>`, `<esc>`, etc.)
- `capture_screen` — Capture current terminal screen
- `send_ctrl` — Send control sequences (Ctrl+C, etc.)

### Worker AI (On-Demand Analysis)
- `query_worker(file="...", question="...")` — Load file and ask question in one call
- `reset_worker` — Clear worker conversation history (unload file)

### Utilities
- `enter` — Change current working directory
- `pwd` — Show current working directory
- `write_diary` — Write reflection to diary
- `read_diary` — Read past diary entries
- `set_expression` — Set emotional/physical state
- `help` — Show tool usage details

### Error Help
When a tool call fails, Jerry automatically includes usage help in the error message:

```
ERROR: Missing required argument: 'path'

📖 Usage:
Tool: read_file
Description: Read file with line numbers
Parameters: path: str, start_line: int (default: 1), max_lines: int (default: 500)
Example: read_file(path='main.py', max_lines=100)
```

This helps the model learn correct tool usage from mistakes automatically.

---

## Known Issues (Alpha 0.0.4)

### Server-Side Issues
- **None currently known** — Jerry is stable with llama.cpp/llama-server

### Client-Side Issues
- **tmux streaming instability** — Can be unstable on low-RAM devices or with curses-based terminals
  - **Workaround:** File-based screen capture fallback is automatic
- **Path validation edge cases** — Some relative path resolution edge cases
  - **Workaround:** Use absolute paths when uncertain
- **Same-port worker** — If using same port for agent+worker, ensure model supports both chat and text-processing tasks

**Debugging:** Check `logs/jerry_stdout.log` for errors.

---

## Active TODOs

### High Priority
- [ ] **Screen capture reliability** — Improve tmux capture for curses-based terminals

### Medium Priority
- [ ] **Coin Spending System** — User acceptance/decline UI for coin offers
- [ ] **Chat scroll persistence** — Remember scroll position across renders
- [ ] **Input validation** — Better handling of malformed tool calls

### Low Priority / Future
- [ ] **Coin Shop/Rewards** — What can Jerry buy with coins?
  - Permission for risky commands
  - New tools/features
  - "Break time" (idle reflection)
  - Extra API calls for complex tasks
- [ ] **Achievements/Badges** — Milestone rewards for Jerry
- [ ] **Custom face creation** — Allow users to design custom emotion faces
- [ ] **Theme customization** — User-defined color schemes
- [ ] **Plugin system** — Extensible tool architecture
- [ ] **Multi-session support** — Run multiple Jerry instances

### ✅ Recently Completed
- ✓ **Coin Persistence** — Coins now saved to `.coins.json` across sessions
- ✓ **Multi-File Worker** — `load_multiple_files()` for cross-file analysis
- ✓ **Tool Call Validation** — Generate IDs instead of filtering
- ✓ **400 Error Fix** — content="", break after text response
- ✓ **User Interrupt** — Check inbox every streaming iteration
- ✓ **Ask User Tool** — Jerry can ask questions
- ✓ **Continue Token Loop** — Qwen-Code CLI pattern

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
