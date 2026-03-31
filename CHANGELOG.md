# Jerry Changelog

## Alpha 0.0.4 (Current)

### 🐛 Bug Fixes

#### Debug Code Removal (FIXED)
- **Issue**: Debug print statements left in `jerry.py:147-149`
- **Fix**: Removed debug code from production
- **Files**: `jerry.py`

#### Emotion Transition Reset (FIXED)
- **Issue**: Face would reset to neutral during long streaming responses
- **Fix**: Improved transition logic to prevent reset during streaming
- **Files**: `jerry_core/faces_display.py`, `jerry_core/agent.py`

#### Duplicate Task Prompts (FIXED)
- **Issue**: Agent would prompt for same task #0 repeatedly
- **Fix**: Added `last_task_text` tracking in agent loop
- **Files**: `jerry_core/agent.py`

### ✨ Improvements

#### Configuration Centralization
- **Change**: All timeouts and magic numbers moved to `config.py` with documentation
- **Added**: `AGENT_TIMEOUT`, `WORKER_TIMEOUT` constants
- **Documented**: `CONV_TRIM`, `CYCLE_SLEEP`, `LOG_LIMIT`, `RAW_LOG_LIMIT` reasoning
- **Files**: `jerry_core/config.py`

#### Tool Error Auto-Help
- **Change**: Failed tool calls now include usage help automatically
- **Benefit**: Model learns correct tool usage from mistakes
- **Files**: `jerry_core/executor.py`

#### Code Quality Cleanup
- Removed outdated debug documentation files (`debug.md`, `Update_failure.txt`)
- Updated `CODE_REVIEW.md` with resolved issues marked
- Cleaned up resolved bug tracking in README

### 📝 Documentation

#### Updated README.md
- Version bumped to Alpha 0.0.4
- Added llama-server `enable_thinking` incompatibility note
- Updated Known Issues section (removed fixed bugs)
- Updated Active TODOs with current priorities
- Added Resolved Bugs section with strikethrough

#### Updated CODE_REVIEW.md
- Marked resolved issues as FIXED
- Updated code quality section with current status
- Removed outdated bug reports

### 🔧 Technical Changes

#### agent.py
- Added `last_task_text` tracking for duplicate prompt prevention
- Improved emotion transition handling during streaming
- Fixed fallback parser to handle all Qwen output formats

#### faces_display.py
- Improved transition logic to prevent reset during streaming
- Better handling of rapid emotion changes

#### executor.py
- Added automatic help output on tool execution errors
- Improved error message formatting

#### config.py
- Added `AGENT_TIMEOUT` and `WORKER_TIMEOUT` constants
- Added documentation comments for magic numbers

### 📊 Statistics

- **Files Changed**: 8
- **Lines Added**: ~150
- **Lines Removed**: ~80
- **Bugs Fixed**: 3 major
- **Improvements**: 4
- **Documentation**: 3 files updated

---

## Alpha 0.0.3 (March 30, 2026)

### Critical Fixes
- **Streaming Tool Call Fix** — Fixed llama-server compatibility where `arguments` are sent as parsed JSON objects
- **Fallback Parser Bug** — Fixed tool call parsing to handle all Qwen output formats
- **Same-Port Default** — Agent and Worker now use same port (8080) by default

### Features
- Tool error auto-help system
- Improved status indicators ("processing" vs "streaming")
- Silent failure detection
- User interruption during streaming

[See `jerry_release/CHANGELOG.md` for earlier versions]

---

## Reporting Issues

- **GitHub**: https://github.com/Dahl404/Jerry/issues
- **Logs**: Check `logs/jerry_stdout.log`
- **Debug Mode**: Run with verbose logging enabled

---

**Release Date**: Current
**Version**: Alpha 0.0.4
**Author**: Dahl404
