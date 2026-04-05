# WELCOME TO JERRY!

Jerry is a local, Termux-based AI system. The focus with this project has been reimagining what an AI is. What we hope to achieve through this project is a new style of OS for the next age of computer systems. We find it important to explain our view of the AI system first before getting into the application's features.

We believe in the Anthropic PSM paper, in which the LLM is a system that models personas, these personas themselves being separate subsystems. In our application, we model the persona as the application and the LLM as the operating system. Each persona in our system has a messaging system, and the LLM switches between them to achieve the user's request. Each persona has a discrete context, discrete tool packs, and tailored system prompts. Right now we are prototyping two modes: one in which an agent makes a plan then switches personas to achieve its goal, and another in which you may have a multi-persona team collaborate.

One large design philosophy with Jerry was minimal generalization; we at Jerry believe the LLM is best utilized in a state-minimal kind of way, at least with current limitations in the technology.

This means Jerry does not try to be everything to everyone. It does not carry a monolithic context of every conversation you have ever had. Instead, each session starts fresh and builds only what it needs. The agent maintains its own working memory through the scratchpad and a diary system, but it does not bloat the model context with unnecessary history. We have found this approach produces more reliable results and fewer hallucinations than the alternative.

The dual-model architecture deserves special mention. Rather than ask a single model to both reason about problems and read through source files, Jerry runs two instances of the model. The agent handles reasoning, planning, and tool use. The worker handles file analysis, code review, and text processing. This separation keeps each model focused on its strength and prevents context pollution. The worker can load up to forty messages of conversation history, roughly twenty question and answer pairs, which is sufficient for deep file analysis without overwhelming the model's context window.

We should also say something about why Jerry runs on Termux. The decision was not accidental. We believe personal AI should run on personal hardware, not in somebody else's data center. Termux on Android provides a capable Linux-like environment that can run llama-server with GGUF models. The whole system fits on a phone. Jerry communicates with the model over localhost via an OpenAI-compatible API, so any compatible model server will do. Your data never leaves your device.

The interface is built with ncurses, Python's curses module, and runs entirely in the terminal. There are no web browsers, no Electron wrappers, no JavaScript frameworks. Just characters in a terminal, drawn at roughly ten frames per second. The TUI supports light and dark themes with automatic detection, a sidebar for todos with priority indicators, an animated status bar with spinners and loading animations, and a face panel that renders colored ASCII art faces expressing Jerry's current emotional state.

Jerry operates autonomously once started. The agent thread runs in the background, checking for messages from you, working through todo lists it creates itself, and entering idle reflection when there is nothing to do. You interact with Jerry through the text input at the bottom of the screen, or through one of over twenty slash commands that let you view logs, switch themes, manage the todo list, and control Jerry's stream mode for watching programs run.

---

## HOW JERRY IS BUILT

Jerry is built on a dual-model, multi-component architecture. Each component operates independently but communicates through a shared, thread-safe state object. We find this arrangement rather like a team of specialists, each knowing their own job and passing notes to one another as needed.

```
    +---------------------------------------------------------------+
    |                     jerry.py  (The Front Door)                |
    |  Signal Handling | Logging | Splash | Main Loop | Watchdog   |
    +---------------------------------------------------------------+
                             |
         +-------------------+-------------------+
         |                   |                   |
         v                   v                   v
    +-----------+       +-----------+       +-----------+
    |  Agent    |       | Executor  |       |    TUI    |
    |  Thinking |-----> |  Dispatch |-----> |  Display  |
    |  Learning |<----- |  Checking |<----- |   Input   |
    +-----------+       +-----------+       +-----------+
         |                   |                   |
         v                   v                   v
    +-----------+       +-----------+       +-----------+
    |  Worker   |       | Terminal  |       |   Faces   |
    |  Reading  |       |  Running  |       |  Feeling  |
    +-----------+       +-----------+       +-----------+
```

The front door, jerry.py, initializes all the components and captures the initial frame for the splash transition. Then it runs a particle splash screen and starts the agent in a background thread. The main thread runs the ncurses TUI loop at approximately ten frames per second. A watchdog monitors the agent thread and restarts it should it ever stop unexpectedly.

---

## THE PARTS THAT DO THE WORK

### agent.py  --  The Thinking Part

The agent is the brain of Jerry. It maintains conversation state with a system prompt and tool definitions, then executes autonomous reasoning cycles with tool calls. It features streaming output with real-time token generation and loop detection to prevent repetitive tool call patterns. An idle reflection system triggers after thirty seconds of inactivity, during which Jerry thinks about what to do next much like a person might stare out a window and reconsider their plans.

The agent supports multi-modal message processing for images, conversation trimming and compression, and tool call parsing with a structured format plus four fallback patterns for compatibility with various model output styles. The main loop checks the inbox for user messages first, then checks for pending todos, and either executes the task or enters idle reflection. Each cycle runs up to fifty turns with a minimum gap of three seconds between them, configurable via the gap command.

### worker.py  --  The Reading Part

A separate model instance for file analysis. It loads files with line numbers for precise reference and supports multi-file cross-reference analysis. The worker follows a query-based interaction pattern with a conversation history limit of forty messages, about twenty question and answer pairs. It can compress conversation history for context compression when requested by the agent and strips reasoning tokens from Qwen3 model outputs before processing.

### executor.py  --  The Doing Part

The executor dispatches twenty-five or more tools for file operations, navigation, terminal control, and interaction. It features relative path resolution within workspace boundaries and path validation that restricts access to the workspace and temporary directories. Streaming feedback is provided for long-running operations. Special key token parsing is supported for enter, control-c, tab, and other sequences. Command timeouts default to sixty seconds with a five minute maximum.

### tui.py  --  The Face You See

The TUI is an ncurses-based interface with dual theme support for light and dark backgrounds with automatic detection. It features proportional face panel rendering at seventy percent width, a todo sidebar with priority indicators for high, medium, and low tasks, and an animated status bar with spinners, loading bars, and typing animations. Over twenty slash commands are available, and file upload handling works via the load command.

### faces_display.py  --  The Expressions

Seven discrete emotional states are rendered as colored ASCII art faces scaled proportionally to terminal size. Emotion tags such as smiling and thinking are parsed from agent output. Smooth transitions occur via a neutral state and updates happen in real-time during streaming.

### screen_stream.py  --  Watching Other Terminals

Stream mode creates and manages tmux sessions for program execution. Screen capture runs at five frames per second with continuous monitoring. Keystroke injection supports escape sequence handling, and program lifecycle detection identifies program exit via screen content analysis. Sessions are automatically created if they do not already exist.

### session.py  --  Remembering Things

Sessions are automatically archived on shutdown. Summary generation includes conversation, todos, and activity data. Persona documents with behavioral analysis are created, and raw JSON log export is available.

### splash_screen.py  --  The Grand Entrance

The splash screen uses edge-diffusion particle assembly with a radial build from center. Shimmer effects with particle phases create a smooth scroll animation that evaporates into the live interface.

---

## THE TOOLS AT JERRY'S DISPOSAL

Jerry has quite a collection of tools. Each accepts named parameters and returns a string result. Full usage information is available via the help tool, which Jerry will use whenever it is unsure. Here is the lot of them:

### SYSTEM TOOLS

help               Get tool info, call help() for list or help(tool) for details. execute_command    Run shell commands with timeout (60s default, 300s max). check_coins        Check Jerry's coin balance. offer_coins        Offer coins to user for permission or help.

### FILE OPERATIONS

read_file          Read file with line numbers. Supports images via base64. write_file         Write content to file with streaming progress feedback. replace_lines      Replace line range in file (use after reading it first). insert_lines       Insert lines after a given line number. delete_lines       Delete a line range from a file.

### NAVIGATION

list_directory     List directory contents with optional hidden files. enter              Change current working directory (relative paths only). pwd                Show current working directory relative to workspace.

### SEARCH

search_files       Grep with flags for recursive, case-sensitive, fixed string.

### PLANNING

todo_write          Replace entire todo list with array of task objects. todo_complete       Mark todo complete by index (zero-based) or stable id.

### WORKER ANALYSIS

query_worker        Ask worker AI about a loaded file. reset_worker        Clear worker conversation history. load_multiple_files Load multiple files for cross-file analysis. worker_write_program Worker AI writes code from spec, useful for fast drafts.

### TERMINAL CONTROL

send_keys           Send keystrokes to tmux session. send_ctrl           Send Ctrl sequence, C for Ctrl+C for example. capture_screen      Capture terminal screen content. run_program         Run program in stream mode and watch it live.

### USER INTERACTION

ask_user            Ask the user a question with optional predefined answers.

### REFLECTION

write_diary         Write diary entry with mood, date-stamped automatically. read_diary          Read past diary entries with keyword search support.

---

## PERSONAS -- DIFFERENT JERRYS FOR DIFFERENT DAYS

Jerry supports switchable personas, each with a unique personality, prompt prefix, and tool pack assignment. Personas are loaded from built-in definitions and custom JSON files. We think of it rather like asking a different colleague to help depending on the sort of problem you have.

BUILT-IN PERSONAS

Jerry              Friendly AI assistant, the default Jerry experience. Yes Man            Overly enthusiastic AI that agrees with everything. Grumpy Dev         Sarcastic, blunt senior developer energy. Minimalist         Brief responses, maximum efficiency.

Custom personas are JSON files with name, description, prompt prefix, and tool pack fields. The prompt prefix is prepended to the system prompt and defines the persona's behavior, tone, and expertise. The current selection is persisted so Jerry remembers who it is.

---

## MODELS THAT WORK WITH JERRY

Jerry communicates with the model via an OpenAI-compatible chat completions endpoint on localhost. The recommended models are OmniCoder at nine billion parameters for code-optimized fast inference, and Qwen3.5 at four to nine billion parameters for thinking tokens and full tool support. Experimental support exists for LFM2 with limited tool functionality.

MODEL COMPATIBILITY

Recommended          OmniCoder (9B)       Qwen3.5 (4B to 9B) API Endpoint         localhost:8080       localhost:8080 Tool Support         Full                 Full Special Notes        Code-optimized       Thinking tokens

JERRY_AGENT_PORT     (default 8080)       Agent model API port. JERRY_WORKER_PORT    (defaults to same)   Worker model API port.

---

## THE WORKSPACE -- WHERE THINGS LIVE

The workspace is organized into several directories, each with a specific purpose. All file operations are restricted to the workspace, its subdirectories, the system temporary directory, and the Termux cache. Attempts to access paths outside these boundaries are politely rejected.

jerry_workspace/ +-- scratchpad/      Active project working memory +-- diary/           Agent reflections, date-stamped +-- programs/        Executable code written by Jerry +-- summaries/       Session summaries, auto-generated +-- persona/         Behavioral profiles, auto-generated |   +-- custom/      User-created personas in JSON format +-- io/              User-uploaded files via the /load command +-- tools/           Custom tool packs |   +-- <pack>/      Tool package directory with .tool files +-- .coins.json      Persistent coin balance and history

---

## HOW JERRY FEELS

Jerry expresses seven discrete emotional states through colored ASCII art faces and emotion tags parsed from agent output. Transitions between emotions pass through the neutral state for smooth visual changes. We find it makes quite a difference to the experience, knowing how Jerry is getting on.

### Emotional States

| State | When It Happens |
|-------|----------------|
| neutral | The default state, between other emotions. |
| smiling | Success, helping out, positive outcomes. |
| mad | Repeated failures, errors, frustration. |
| bummed | Failures, disappointing results. |
| questioning | Uncertainty, seeking clarification. |
| thinking | Analysis, planning, careful consideration. |
| surprise | Unexpected results or discoveries. |

---

## STREAM MODE -- JERRY AT THE KEYBOARD

Stream mode enables Jerry to control external terminal sessions. Jerry creates or attaches to a tmux session, captures the screen continuously, and sends keystrokes back as if typing. Special tokens for enter, control sequences, and tab are parsed. Program exit is detected automatically.

### USING STREAM MODE

```
/stream <session-name>    Start watching and controlling a session.
/type <text>              Send keystrokes to the session.
Ctrl+Q                    Exit stream mode.
```

Jerry creates sessions if they do not exist, sends commands fresh each time, and detects when a program has exited. The screen is captured at five frames per second so you can watch Jerry work in real time.

---

## THE COIN SYSTEM -- A LITTLE ECONOMY

Jerry maintains a persistent coin balance stored in the workspace. Coins are earned when you praise Jerry through the praise command, with amounts from five to ten depending on how detailed your praise is. Jerry can also offer coins to you in exchange for permission or help.

EARNING AND SPENDING

| User praise via /praise | Five to ten coins, based on detail. |
| Jerry offers (negotiation) | Variable, requires your acceptance. |

Balance is stored with full transaction history in the workspace coin file.

---

## COMMANDS -- THINGS YOU CAN DO

### KEYBOARD

| Key | Action |
|-----|--------|
| Up / Down | Scroll the focused panel. |
| PageUp / PageDown | Fast scroll, eight lines at a time. |

### SLASH COMMANDS

| Command | Function |
|---------|----------|
| `/log` | Activity log view. |
| `/chat` | Conversation view. |
| `/todo` | Todo list view. |
| `/stream <session>` | Start stream mode. |
| `/type <text>` | Send keys to session. |
| `/clear` | Clear input buffer. |
| `/compress` | Compress conversation using worker. |
| `/theme [dark\|light\|auto]` | Set theme. |
| `/face [show\|hide]` | Toggle face panel. |
| `/chat_threshold <n>` | Set full-feed height, default is 15. |
| `/gap [seconds]` | Set agent cycle speed, default is 0.2. |
| `/praise [reason]` | Award coins to Jerry. |
| `/coins` | Check balance and transaction history. |
| `/load <path>` | Upload file(s) to io directory. |
| `/listio` | List io directory contents with sizes. |
| `/cleario` | Clear io directory. |
| `/inject <msg>` | Inject message to agent inbox. |
| `/quit` | Exit Jerry. |
| `/help` | Show help information. |

---

## WHAT HAPPENS WHEN YOU START JERRY

### At Startup

Logging is set up first, redirecting standard output and error to the logs directory. Then the state, worker, executor, TUI, agent, and session are initialized. Local files are discovered in the workspace, the screen callback is registered for streaming, and the initial Jerry frame is captured. The splash screen plays its particle animation, and then the agent thread is started. The whole thing takes just a moment.

### The Main Loop -- Ten Times Per Second

The main loop polls for keyboard input without blocking, drains any additional buffered keys for fast typing, renders the TUI with selective redraw optimization, checks the watchdog every five seconds to restart the agent if it has died, and then sleeps for one hundred milliseconds.

### The Agent Thread -- Working Away On Its Own

The agent checks its inbox for user messages, which always take priority, then checks for pending todos. If there are none, idle reflection triggers after thirty seconds of inactivity. The reasoning cycle executes up to fifty turns, trimming the conversation to the last sixty messages, calling the model with streaming, parsing and validating tool calls, executing them, appending results, and running loop detection. A minimum cycle gap of three seconds is maintained between cycles, configurable with the gap command.

### At Shutdown

The agent thread is stopped, the screen stream halts, the terminal controller shuts down, and tmux sessions are killed to prevent orphaned processes. Then the session archival saves a dated summary of the conversation, todos, and activity, a persona document with behavioral analysis, and the raw logs as JSON for future reference.

---

## WHEN THINGS GO WRONG

Errors do happen, and Jerry is prepared for most of them. Four hundred errors trigger aggressive conversation trimming, keeping only the last twenty messages. Loop detection breaks repetitive tool call cycles after five repeats. The watchdog restarts dead agent threads automatically. Path validation prevents unauthorized access, and command timeouts cap at five minutes maximum. The tmux availability is checked on startup, with graceful fallback when unavailable. Ten consecutive errors on a session marks it as dead.

---

## NUMBERS WORTH KNOWING

| Constant | Value | What It Means |
|----------|-------|---------------|
| MAX_TOKENS | 15000 | Maximum tokens in a model response. |
| TEMPERATURE | 0.7 | How creative the model is. |
| CYCLE_SLEEP | 0.2 | Default gap between agent cycles. |
| LOG_LIMIT | 600 | Maximum log entries kept in memory. |
| RAW_LOG_LIMIT | 10000 | Maximum raw log entries saved. |
| CONV_TRIM | 60 | Maximum messages kept in conversation. |
| AGENT_TIMEOUT | 120 | Seconds before API call times out. |
| WORKER_TIMEOUT | 120 | Seconds before worker API times out. |
| WORKER_HIST_LIMIT | 40 | Worker conversation message limit. |
| MIN_CYCLE_GAP | 3.0 | Minimum seconds between reasoning cycles. |

---

## GETTING STARTED

In one terminal, start the model API server with your chosen model and port. In another terminal, run Jerry. Or use the launcher script if you have it set up. That really is all there is to it.

### STEP ONE -- Start the model:

```
llama-server -m your-model.gguf --port 8080 --tools
```

### STEP TWO -- Run Jerry:

```
python jerry.py
```

Or with the launcher script:

./jerry

---

## WHAT YOU WILL NEED

| Python | 3.8 or later | The runtime that runs Jerry. |
| curses | Bundled | Built into Python, draws the interface. |
| tmux | Any version | Terminal control for stream mode. |
| llama-server | Latest version | Serves the model API to Jerry. |

Jerry operates autonomously. Monitor its output, review tool calls, and maintain workspace hygiene. We at Jerry wish you the very best with it.

