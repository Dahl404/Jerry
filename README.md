# Jerry — Autonomous Qwen3.5 Agent (Alpha 0.0.5)

> **⚠️ Alpha Release** — This is a **minimal proof-of-concept (POC)**. Mobile-first, aesthetic-focused TUI agent built for fast local inference on Termux/Android.

---

## Latest Updates (Alpha 0.0.5)

### 🎯 Core Features

#### Interactive Question Tool (`ask_user`)
- **Multiple Choice Questions** — Jerry can ask questions with selectable options
- **Multi-Select Support** — Press Space to select multiple options, Enter submits all
- **Beautiful UI Panel** — Centered popup with solid background (no bleed-through)
- **Keyboard Navigation**:
  - `↑↓` — Navigate options
  - `Space` — Toggle selection (✓) on options, types space in custom answer
  - `Enter` — Submit selected (or highlighted option if none selected)
- **Custom Answers** — Type any response in "Answer:" field
- **Non-Blocking** — Jerry waits for answer without freezing
- **Quit Anytime** — Ctrl+Q, q, or /quit even during questions

**Example:**
```
Jerry: ask_user(question="What should I do?", options=["Task A", "Task B", "Task C"])

╭────────────────────────────────────╮
│ ❓ What should I do?               │
│ ↑↓ scroll, Space select, Enter     │
│ ✓ Task A                           │
│ ◉ Task B                           │
│ ○ Task C                           │
│ ○ ── Type custom answer below ──   │
│ Answer: my custom answer           │
╰────────────────────────────────────╯

Press Enter → Submits: ["Task A", "Task B"]
```

**Visual Markers:**
- `○` = Unselected
- `●` = Currently highlighted (cursor position)
- `✓` = Selected (permanently checked with Space)
- `◉` = Both selected AND highlighted

**Usage Patterns:**
```python
# Single answer - navigate and press Enter
ask_user(question="Continue?", options=["Yes", "No"])

# Multiple answers - Space to select multiple, Enter to submit all
ask_user(question="Which features?", options=["A", "B", "C", "D"])
# → Space on A, Space on C, Enter → Submits: ["A", "C"]

# Custom answer - navigate to bottom option, type response
ask_user(question="What task?", options=["Task 1", "Task 2"])
# → ↓↓ to "Type custom answer", type "Task 3 with details", Enter
```

#### Bracket-Style Tool Calls (Python/LFM Style)
- **New Syntax** — `[tool_name(arg="value", options=["A", "B"])]`
- **Array Support** — Options and other array parameters parse correctly
- **Type Support**:
  - Strings: `arg="value"` or `arg='value'`
  - Numbers: `arg=123`
  - Arrays: `arg=["A", "B", "C"]`
- **Backward Compatible** — All existing tool call formats still work

**Examples:**
```python
# Simple call
[ask_user(question="Continue?", options=["Yes", "No"])]

# Multiple arguments
[worker_write_program(path='test.py', spec='A test script', language='python')]

# Array arguments
[load_multiple_files(files=[{'path': 'a.py', 'content': '...'}, {'path': 'b.py'}])]

# Numeric arguments
[capture_screen(lines=50)]
```

### 🐛 Critical Fixes

#### Fixed: Options Not Showing in Question Panel
- **Bug:** `ask_user()` options parameter was ignored in dispatcher (line 116)
- **Fix:** Changed `self._ask_user(a["question"])` → `self._ask_user(a["question"], a.get("options"))`
- **Result:** Options now display correctly in UI

#### Fixed: UI Deadlock on Question Answer
- **Bug:** `answer_question()` caused deadlock (lock → push_log → lock)
- **Fix:** Moved `push_log()` outside lock, removed unnecessary locking
- **Result:** No more freezes when pressing Enter

#### Fixed: Question Panel UI Issues
- **Background Bleed-Through** — Panel now fills background with solid color
- **Panel Positioning** — Positioned above input bar, no overlap
- **Input Display** — Shows in panel, not main input bar
- **Space Bar** — Works for multi-select on options, types space in custom answer
- **Enter Key** — Always submits (highlighted option if nothing selected)

#### Fixed: Duplicate Tool Calls
- **Bug:** Model outputs same tool call twice, both executed
- **Fix:** Track seen tool names, skip duplicates
- **Result:** Each tool only executes once

### 🪙 Coin System Updates
- **Persistence** — Coins saved to `.coins.json`, persist across sessions
- **Fixed Deadlock** — Coin operations no longer cause UI freezes

### 📁 Worker Enhancements
- **`worker_write_program()`** — Delegate code writing to faster worker model
- **`load_multiple_files()`** — Load multiple files for cross-file analysis
- **Workflow:** Main AI plans → Worker drafts → Main AI reviews/tests

### ✏️ File Write Improvements
- **Streaming Feedback** — Shows "✏️ Writing file.py... (2,345 chars)" before completion
- **Success/Error Messages** — Clear feedback with emotions (😊/😞)
- **User Visibility** — Know Jerry is working, not stuck

### 🔧 Technical Improvements
- **Bracket Parser** — Handles arrays, strings, numbers correctly
- **Tool Validation** — Generates IDs, validates required fields
- **400 Error Recovery** — Retry logic with conversation cleanup
- **User Interrupt** — Messages interrupt streaming immediately
- **Question Blocking** — Jerry stops and waits (no more talking over questions)

---

## Known Issues (Alpha 0.0.5)

### Server-Side Issues
- **None currently known** — Jerry is stable with llama.cpp/llama-server

### Client-Side Issues
- **tmux streaming instability** — Can be unstable on low-RAM devices
  - **Workaround:** File-based screen capture fallback is automatic
- **Path validation edge cases** — Some relative path resolution issues
  - **Workaround:** Use absolute paths when uncertain
- **Same-port worker** — Ensure model supports both chat and text-processing

**Debugging:** Check `logs/jerry_stdout.log` for errors.

---

## Active TODOs

### High Priority
- [ ] **Screen capture reliability** — Improve tmux capture for curses terminals
- [ ] **Internet Search Tool** — Web search, fetch URLs (USER REQUESTED!)

### Medium Priority
- [ ] **Chat scroll persistence** — Remember scroll position across renders
- [ ] **Input validation** — Better handling of malformed tool calls

### Low Priority / Future
- [ ] **Coin Spending UI** — User acceptance/decline for coin offers
- [ ] **Coin Shop/Rewards** — What can Jerry buy with coins?
- [ ] **Achievements/Badges** — Milestone rewards
- [ ] **Custom face creation** — User-designed emotion faces
- [ ] **Theme customization** — User-defined color schemes
- [ ] **Plugin system** — Extensible tool architecture

### ✅ Recently Completed (Alpha 0.0.5)
- ✓ **Interactive Question Tool** — Multi-select, Space/Enter, custom answers
- ✓ **Bracket Tool Syntax** — Python/LFM style `[tool(arg="val", options=["A","B"])]`
- ✓ **Question UI Fixes** — No bleed-through, proper positioning, input in panel
- ✓ **Coin Persistence** — Saved to `.coins.json`
- ✓ **Worker Code Gen** — `worker_write_program()` for fast drafts
- ✓ **Multi-File Worker** — `load_multiple_files()` for cross-file analysis
- ✓ **Streaming File Write** — Shows progress when writing large files
- ✓ **400 Error Fixes** — Proper conversation format, tool validation
- ✓ **User Interrupt** — Messages interrupt streaming (no UI freeze)
- ✓ **Todo Context** — Model sees full todo list, not just "[continue]"
- ✓ **Duplicate Tool Calls** — Deduplication prevents double execution

---

## What is Jerry?

**Jerry** is an autonomous AI agent with an emotional ASCII face, designed to run **locally on mobile devices** (Termux/Android) with Qwen3.5, Omni-Coder 9B, or Qwen2.5-VL (or compatible) models. Jerry thinks, plans, executes tasks, displays emotions, and can now analyze images — all while staying minimal and keyboard-friendly.

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

#### Multi-Modal Vision (NEW!)
- **Image Analysis** — `read_file()` works with images (PNG, JPG, GIF, WebP, BMP)
- **Automatic Conversion** — Images converted to base64 for model
- **Vision Models** — Works with Qwen2.5-VL, LLaVA, or compatible
- **Use Cases** — Screenshots, diagrams, charts, photos, UI mockups, code screenshots

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
pkg install python git tmux termux-api

# Clone Jerry
git clone https://github.com/Dahl404/Jerry.git
cd Jerry

# Run Jerry
./jerry
```

### Termux API Setup

For full functionality (file uploads, notifications, clipboard), install termux-api:

```bash
pkg install termux-api
```

This enables:
- `/load` — Upload files from your device
- `/listio` — List uploaded files
- `/cleario` — Clear uploaded files

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
| `/load` | Upload file(s) from device to io/ folder |
| `/listio` | List files in io/ folder |
| `/cleario` | Delete all files from io/ folder |
| `/praise [reason]` | Reward Jerry with coins |
| `/coins` | Check Jerry's coin balance |

### Keyboard Controls

| Key | Action |
|-----|--------|
| `↑` / `↓` | Scroll focused panel |
| `Ctrl+Q` | Exit stream mode |
| `q` | Exit stream mode (when streaming) |
| `Enter` | Send message / Execute command |

### File Upload (Termux API Required)

Jerry supports uploading files from your device using Termux's file picker:

**Commands:**
- `/load` — Open file picker, select file(s) to upload
- `/listio` — List files in `io/` folder
- `/cleario` — Delete all files from `io/`

**How it works:**
1. Type `/load` and press Enter
2. Termux file picker opens — navigate and select file(s)
3. Optional: Add a message to include with the upload
4. Files are copied to `jerry_workspace/io/`
5. Jerry receives an auto-message with file details
6. Jerry can now read files with `read_file(path="io/filename")`

**File Naming Conflicts:**
If a file already exists, you can:
- **Overwrite** — Replace existing file
- **Rename** — Specify a number (e.g., `2` → `file_2.png`)
- **Skip** — Don't upload this file

**Example:**
```
User: /load
[Selects screenshot.png]
[Adds message: "Can you analyze this error?"]

→ Jerry receives:
📎 **File Upload Complete**
**Files uploaded to `io/` directory:**
- **screenshot.png** (234,567 bytes, image)

**User Message:** Can you analyze this error?

💡 **Tip:** These are image files. I can analyze them with my vision capabilities using `read_file()`!

Jerry: <thinking> Let me read that screenshot... read_file(path="io/screenshot.png")
```

**Supported File Types:**
- **Images** — PNG, JPG, JPEG, GIF, WebP, BMP (vision model can analyze)
- **Code** — PY, JS, TS, Java, C, CPP, H (Jerry can read and analyze)
- **Text** — TXT, MD, JSON, YAML, YML
- **Documents** — PDF, DOC, DOCX (text extraction)

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
- `read_file` — Read file with line numbers (**supports images!** PNG, JPG, GIF, WebP, BMP)
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
- `load_multiple_files` — Load multiple files at once for cross-file analysis

### User Interaction
- `ask_user` — Ask user a question when clarification needed
- `check_coins` — Check Jerry's current coin balance
- `offer_coins` — Offer coins to user for permission/help

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

### Multi-Modal Image Support

When Jerry reads an image file with `read_file()`:
1. Image is automatically detected by file extension
2. Converted to base64 encoding
3. Sent to model in multi-modal format
4. Vision-capable models can analyze the image

**Example:**
```
User: What's in this screenshot?
Jerry: read_file(path="error_screenshot.png")
[Image sent to model]
Jerry: <thinking> I can see a Python traceback showing...
```

**Supported formats:** PNG, JPG, JPEG, GIF, WebP, BMP

---

## Known Issues (Alpha 0.0.5)

### Server-Side Issues
- **None currently known** — Jerry is stable with llama.cpp/llama-server

### Client-Side Issues
- **tmux streaming instability** — Can be unstable on low-RAM devices or with curses-based terminals
  - **Workaround:** File-based screen capture fallback is automatic
- **Path validation edge cases** — Some relative path resolution edge cases
  - **Workaround:** Use absolute paths when uncertain
- **Same-port worker** — If using same port for agent+worker, ensure model supports both chat and text-processing tasks
- **Multi-modal requires vision model** — Standard models can't analyze images (use Qwen2.5-VL or LLaVA)

**Debugging:** Check `logs/jerry_stdout.log` for errors.

---

## Roadmap

### ✅ Recently Completed (Alpha 0.0.5)
- ✓ **Multi-Modal Vision** — Image analysis with `read_file()`
- ✓ **Coin Persistence** — Coins saved to `.coins.json` across sessions
- ✓ **Multi-File Worker** — `load_multiple_files()` for cross-file analysis
- ✓ **Continue Token Loop** — Qwen-Code CLI pattern for autonomous work
- ✓ **Ask User Tool** — Jerry can ask questions and wait for answers
- ✓ **User Interrupt** — Messages immediately interrupt streaming (no UI freeze!)
- ✓ **400 Error Fixes** — Proper conversation format, tool call validation
- ✓ **Auto-Help on Errors** — Failed tools include usage examples

### 📍 Current Focus
Jerry is **feature-complete for Alpha 0.0.5**. Current development priorities:

1. **Internet Search Tool** — Web search, fetch URLs, search capabilities (HIGH PRIORITY!)
2. **Persistence** — Save/restore full session state (todos, conversation, context)
3. **Long-Term Memory** — RAG-style retrieval for cross-session knowledge
4. **Robust Terminal Streaming** — Better tmux capture, error recovery, non-tmux fallbacks
5. **Dual-Model Support** — Optional smaller model for low-resource devices

### ✅ New in Alpha 0.0.5
- ✓ **Multi-Modal Vision** — Jerry can now read and analyze images!
  - `read_file()` automatically detects images (PNG, JPG, GIF, WebP, BMP)
  - Images converted to base64 and sent to multi-modal models
  - Works with Qwen2.5-VL, LLaVA, or any vision-capable model

### 🔮 Future Ideas
These are potential features for future versions:

**Coin System Extensions:**
- Coin spending UI (user accepts/declines offers)
- "Coin shop" — What can Jerry buy?
  - Permission for risky commands
  - New tools/features
  - Extra API calls for complex tasks
- Achievements/badges for milestones

**UI Enhancements:**
- Custom ASCII face creation
- Theme customization
- Emotion transition animations
- Chat scroll persistence

**Architecture:**
- Plugin system for extensible tools
- Multi-session support
- C++ port for performance-critical code

---

## Known Limitations

These are **by design** or **external constraints**:

- **Worker is stateless** — Each `load()` replaces previous files (use `load_multiple_files()` for multi-file)
- **tmux required for streaming** — No tmux = no screen capture/send_keys
- **60 message context limit** — Prevents token overflow with tool calls
- **Same-port default** — Agent and worker share port 8080 (configurable)

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
