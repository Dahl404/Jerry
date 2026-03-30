# Jerry Changelog

## Alpha 0.0.2 (March 30, 2026)

### 🐛 Bug Fixes

#### Screen Flickering (FIXED)
- **Issue**: Display flickered badly on startup, especially on Termux/Android
- **Cause**: Debug/test code in render loop, conflicting curses settings
- **Fix**: Simplified rendering flow, removed debug code, optimized curses configuration
- **Files**: `jerry_core/tui.py`

#### Streaming Hang on Edge Devices (FIXED)
- **Issue**: UI showed "streaming" but nothing appeared, device warmed up, appeared frozen
- **Cause**: Status showed "streaming" before first token arrived; on edge devices, model computation can take 10-60+ seconds
- **Fix**: Status now shows "processing" while waiting for first token, switches to "streaming" once tokens arrive
- **Files**: `jerry_core/agent.py`

### ✨ New Features

#### Same-Port Default Configuration
- **Change**: Agent and Worker now use the SAME port (8080) by default
- **Benefit**: Reduces resource usage, simpler setup, matches common deployment patterns
- **Configuration**:
  ```bash
  # Same port (default)
  export JERRY_AGENT_PORT=8080
  export JERRY_WORKER_PORT=8080  # Or omit, defaults to agent port
  
  # Separate ports (optional)
  export JERRY_AGENT_PORT=8080
  export JERRY_WORKER_PORT=8081
  
  # Custom port (e.g., Ollama)
  export JERRY_AGENT_PORT=11434
  export JERRY_WORKER_PORT=11434
  ```
- **Files**: `jerry_core/config.py`, `README.md`

#### Distribution Cleanup Script
- **New**: `clean.sh` - Automated cleanup for distribution
- **Removes**: Logs, workspace data, Python cache, temp files
- **Preserves**: Source code, config, assets, directory structure
- **Files**: `clean.sh`, `DISTRIBUTION.md`

### 📋 Improvements

#### Better Status Indicators
- **"processing"**: Model is computing, waiting for first token
- **"streaming"**: Tokens are actively being received
- **"working"**: Tools are executing
- **"ready"**: Jerry is idle, waiting for input

#### Silent Failure Detection
- Logs warning if streaming ends with 0 chunks (model failed silently)
- Returns error message to conversation instead of hanging

#### User Interruption During Streaming
- Can now interrupt streaming by sending a message
- Jerry checks for inbox messages during stream loop
- Exits gracefully to process user interruption

### 📝 Documentation

#### Updated README.md
- New port configuration section
- Environment variable usage
- Configuration examples
- Updated troubleshooting

#### New DISTRIBUTION.md
- Cleanup instructions
- Distribution checklist
- Manual cleanup alternative
- Directory structure guide

#### New .gitignore
- Ignores logs, cache, workspace data
- Ignores large model files (.gguf)
- Standard Python + IDE ignores

### 🔧 Technical Changes

#### agent.py
- Added `first_token_received` flag for status tracking
- Added `chunks_received` counter for failure detection
- Added inbox check during streaming loop
- Improved status transitions: thinking → processing → streaming → working

#### config.py
- Added `AGENT_PORT` and `WORKER_PORT` constants
- `WORKER_PORT` defaults to `AGENT_PORT` value
- Environment variable support: `JERRY_AGENT_PORT`, `JERRY_WORKER_PORT`
- Dynamic URL construction

#### tui.py
- Removed debug/test code from render loop
- Simplified curses configuration
- Removed conflicting settings (halfdelay, leaveok, scrollok)
- Clean erase → draw → refresh flow

### 📊 Statistics

- **Files Changed**: 8
- **Lines Added**: ~250
- **Lines Removed**: ~50
- **Bugs Fixed**: 2 major
- **New Features**: 3
- **Documentation**: 3 new files

---

## Alpha 0.0.1 (Initial Release)

### Features
- Emotional ASCII face display
- Streaming output
- Tool calling system
- Todo/planning system
- Screen streaming mode
- Diary system
- Session archival

### Known Issues (Fixed in 0.0.2)
- ~~Screen flickering~~ ✓ FIXED
- ~~Streaming hang on edge devices~~ ✓ FIXED
- ~~Separate port requirement~~ ✓ FIXED (now optional)

---

## Upgrade Guide (0.0.1 → 0.0.2)

### Quick Upgrade
```bash
# Backup your workspace
cp -r jerry_workspace jerry_workspace_backup

# Pull latest changes
git pull origin main

# Run cleanup (optional)
./clean.sh

# Start Jerry
./jerry
```

### Configuration Changes

**Old (0.0.1)**:
```python
# config.py - Required separate ports
AGENT_URL  = "http://localhost:8080/v1/chat/completions"
WORKER_URL = "http://localhost:8081/v1/chat/completions"
```

**New (0.0.2)**:
```python
# config.py - Same port by default
AGENT_PORT   = int(os.environ.get("JERRY_AGENT_PORT", "8080"))
WORKER_PORT  = int(os.environ.get("JERRY_WORKER_PORT", str(AGENT_PORT)))

AGENT_URL    = f"http://localhost:{AGENT_PORT}/v1/chat/completions"
WORKER_URL   = f"http://localhost:{WORKER_PORT}/v1/chat/completions"
```

### Migration Notes

1. **Port Configuration**: If you were using separate ports, set environment variables:
   ```bash
   export JERRY_WORKER_PORT=8081
   ```

2. **No Breaking Changes**: All existing functionality preserved

3. **Workspace Compatible**: Your workspace data is fully compatible

---

## Reporting Issues

- **GitHub**: https://github.com/Dahl404/Jerry/issues
- **Logs**: Check `logs/jerry_stdout.log`
- **Debug Mode**: Run with verbose logging enabled

---

**Release Date**: March 30, 2026  
**Version**: Alpha 0.0.2  
**Commit**: "update alpha 002"  
**Author**: Dahl404
