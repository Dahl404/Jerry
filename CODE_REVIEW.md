# Jerry Alpha 0.0.3 — Code Review & Improvement Plan

**Review Date:** March 30, 2026  
**Version:** Alpha 0.0.3  
**Status:** Ready for development

---

## ✅ What's Working Well

### Core Functionality
- ✓ Agent loop runs smoothly in background thread
- ✓ Streaming output works with proper status indicators
- ✓ Tool calling system functional
- ✓ Todo system with stable IDs
- ✓ Face panel emotion display
- ✓ Screen streaming mode
- ✓ Session archival

### Code Quality
- ✓ No syntax errors
- ✓ Modular architecture (agent, executor, tui, worker)
- ✓ Thread-safe state management
- ✓ Good error handling in most places
- ✓ Clean separation of concerns

---

## 🐛 Known Bugs & Issues

### HIGH PRIORITY

#### BUG-A: Worker Context Lost on File Reload
**Severity:** Medium  
**Status:** Design limitation

**Issue:** Worker resets conversation history every time a new file is loaded.

**Location:** `jerry_core/worker.py:load()`

```python
def load(self, path: str, content: str) -> str:
    self.hist = [{  # ← Resets history completely
        "role": "user",
        "content": f"You are a text-processing... File: {path}..."
    }]
```

**Impact:** Cannot compare multiple files or maintain cross-file context.

**Fix Options:**
1. Add `preserve_context=True` parameter
2. Merge histories from multiple files
3. Implement multi-file awareness in worker prompt

---

#### BUG-B: Emotion Parsing Misses Tags in Long Responses
**Severity:** Low  
**Status:** Partially fixed

**Issue:** During streaming, emotion tags in long responses may be parsed from intermediate chunks rather than the final complete message.

**Location:** `jerry_core/tui.py:_parse_recent_emotions()`

**Current Behavior:** Parses tags from message chunks as they arrive.

**Impact:** Face may flicker between emotions during long responses.

**Fix:** Parse emotions only from complete messages, not streaming chunks.

---

#### BUG-C: Duplicate Task Prompts
**Severity:** Low  
**Status:** Partially fixed

**Issue:** When task #0 completes, the agent may prompt for the same task again.

**Location:** `jerry_core/agent.py:run()`

**Current Fix:** Added `last_task_text` tracking.

**Remaining Issue:** Edge cases when multiple tasks complete in rapid succession.

---

### MEDIUM PRIORITY

#### Tool Error Handling
**Status:** Needs improvement

**Issue:** Tool errors often fail silently or show generic error messages.

**Example:**
```python
try:
    result = execute_command("invalid-command")
except Exception as e:
    # Just logs error, no retry logic or helpful message
    state.push_log("error", f"Tool error: {e}")
```

**Fix:** Add retry logic, better error messages, user-friendly feedback.

---

#### Screen Capture Reliability
**Status:** Known limitation

**Issue:** tmux-based screen capture can fail with:
- Curses-based terminals (like Jerry itself)
- Low-RAM devices
- Non-tmux environments

**Current Workaround:** File-based screen capture fallback.

---

#### Memory Leaks
**Status:** Needs investigation

**Issue:** Long-running sessions (>1 hour) show increased memory usage.

**Suspected Causes:**
- State snapshots not garbage collected
- Log entries accumulating
- Thread-local storage not cleaned up

**Fix:** Implement periodic cleanup, limit log/state sizes.

---

### LOW PRIORITY

#### Emotion Transition Smoothing
**Status:** Feature request

**Issue:** Add fade/transition effects between emotion changes.

**Implementation:** Could use intermediate "neutral" frames or ASCII animation.

---

#### Chat Scroll Persistence
**Status:** Minor UX issue

**Issue:** Scroll position resets on some state changes.

**Fix:** Store scroll position in state, restore on render.

---

## 🔧 Code Quality Issues

### Debug Code Left in Production
**Location:** `jerry.py:147-149`

```python
state.push_log("debug", "DEBUG: About to call tui.setup()")
state.push_log("debug", "DEBUG: tui.setup() complete")
```

**Action:** Remove or convert to proper logging.

---

### Hardcoded Timeouts
**Location:** `jerry_core/worker.py:_call()`

```python
timeout=120  # Hardcoded
```

**Fix:** Move to config.py as `WORKER_TIMEOUT`.

---

### Magic Numbers
**Location:** Multiple files

Examples:
- `WORKER_HIST_LIMIT = 40` — Why 40?
- `CONV_TRIM = 60` — Document reasoning
- `CYCLE_SLEEP = 5.0` — Explain trade-offs

**Action:** Add comments explaining values or move to config.

---

## 📋 Todo System Review

### Current Implementation

**Tools Available:**
- `todo_write` — Replace entire todo list
- `todo_add` — Add tasks (backward compat with todo_write)
- `todo_complete` — Mark complete by index or ID
- `todo_remove` — Remove by index

**Strengths:**
- ✓ Stable IDs for tasks (never change)
- ✓ Can complete by ID or index
- ✓ Priority levels (high, medium, low)
- ✓ Thread-safe with locks

**Weaknesses:**
- ✗ No undo/redo
- ✗ No task dependencies
- ✗ No due dates or reminders
- ✗ No task categories/tags
- ✗ No search/filter

### Recommended Improvements

#### 1. Add Task Metadata
```python
class Todo:
    def __init__(self, text, priority="medium", 
                 created_at=None, due_date=None, tags=None):
        self.text = text
        self.priority = priority
        self.created_at = created_at or datetime.now()
        self.due_date = due_date
        self.tags = tags or []
        self.done = False
        self.id = next_id()
        self.completed_at = None  # Track when completed
```

#### 2. Add Task Search
```python
def _todo_search(self, query: str) -> str:
    """Search todos by text content."""
    matches = [t for t in self.state.todos 
               if query.lower() in t.text.lower()]
    return f"Found {len(matches)} matching tasks"
```

#### 3. Add Task Archive
```python
def _todo_archive(self) -> str:
    """Move completed tasks to archive."""
    with self.state._lock:
        archived = [t for t in self.state.todos if t.done]
        self.state.todos = [t for t in self.state.todos if not t.done]
    return f"Archived {len(archived)} completed tasks"
```

---

## 🏗 Architecture Recommendations

### 1. Separate Concerns Better
**Current:** TUI, agent, worker all tightly coupled.

**Recommendation:** 
- Add interfaces/abstract base classes
- Dependency injection for easier testing
- Event bus for state changes

---

### 2. Add Proper Logging
**Current:** Mix of `push_log()`, `print()`, and exceptions.

**Recommendation:**
- Use Python `logging` module
- Configurable log levels
- Structured logging for debugging

---

### 3. Error Recovery
**Current:** Many operations fail silently or crash.

**Recommendation:**
- Add retry decorators
- Circuit breaker pattern for API calls
- Graceful degradation

---

### 4. Testing Strategy
**Current:** No automated tests.

**Recommendation:**
- Unit tests for tools
- Integration tests for agent loop
- UI tests with pytest-curses

---

## ⚡ Performance Optimizations

### 1. Reduce API Calls
**Current:** Agent calls model every cycle (5s).

**Optimization:** 
- Adaptive cycle time based on workload
- Batch multiple tool calls per cycle
- Cache common responses

---

### 2. Optimize Rendering
**Current:** Full screen redraw every frame.

**Optimization:**
- Dirty-rectangle detection
- Panel-level caching
- Reduce frame rate when idle

---

### 3. Memory Management
**Current:** State grows unbounded.

**Optimization:**
- LRU cache for logs
- Trim conversation more aggressively
- Periodic garbage collection

---

## 🔒 Security Considerations

### 1. Command Injection Risk
**Location:** `jerry_core/executor.py:execute_command()`

```python
subprocess.run(command, shell=True, ...)
```

**Risk:** Arbitrary code execution if model is compromised.

**Mitigation:**
- Whitelist allowed commands
- Sandbox execution
- Validate command patterns

---

### 2. File System Access
**Current:** Unrestricted file access within workspace.

**Risk:** Model could read/write sensitive files.

**Mitigation:**
- Path validation
- Read-only mode option
- Audit log of file operations

---

## 📝 Documentation Gaps

### Missing Documentation
1. **Tool API Reference** — Full parameter docs for each tool
2. **Emotion System** — Complete list of supported emotions
3. **Configuration Guide** — All config options explained
4. **Troubleshooting** — Common issues and solutions
5. **Development Guide** — How to extend Jerry

### Outdated Documentation
- README mentions "display flickering" as known issue (fixed in 0.0.2)
- Port configuration docs updated (now supports same-port default)

---

## ✅ Testing Checklist

### Manual Testing Required
- [ ] Test same-port configuration (8080 for both)
- [ ] Test separate-port configuration (8080 + 8081)
- [ ] Test custom ports (e.g., 11434 for Ollama)
- [ ] Test emotion transitions during streaming
- [ ] Test worker file loading with large files
- [ ] Test screen streaming mode stability
- [ ] Test long-running session (>1 hour)
- [ ] Test memory usage over time
- [ ] Test tool error handling
- [ ] Test resume after network interruption

### Automated Tests Needed
- [ ] Unit tests for config parsing
- [ ] Unit tests for worker compression
- [ ] Integration tests for agent loop
- [ ] UI tests for TUI rendering
- [ ] Performance tests for rendering speed

---

## 🎯 Priority Action Items

### Immediate (Next Session)
1. [ ] Remove debug code from jerry.py
2. [ ] Add timeout configuration to config.py
3. [ ] Fix worker context persistence
4. [ ] Improve tool error messages

### Short-Term (1-2 Weeks)
1. [ ] Add retry logic for API calls
2. [ ] Implement dirty-rectangle rendering
3. [ ] Add memory usage monitoring
4. [ ] Create troubleshooting guide

### Medium-Term (1 Month)
1. [ ] Add proper logging framework
2. [ ] Implement unit tests
3. [ ] Add plugin system for tools
4. [ ] Improve worker context management
5. [ ] Add performance profiling

### Long-Term (Future)
1. [ ] C++ port for performance-critical code
2. [ ] RAG integration for long-term memory
3. [ ] Multi-modal support (images, code)
4. [ ] Persistent memory across sessions
5. [ ] Mobile app wrapper

---

## 📊 Summary

**Overall Assessment:** Jerry Alpha 0.0.3 is a solid foundation with:
- ✅ Clean architecture
- ✅ Working core features
- ✅ Good error handling (mostly)
- ⚠️ Some technical debt to address
- ⚠️ Needs automated testing
- ⚠️ Performance optimizations needed

**Recommended Next Steps:**
1. Fix high-priority bugs (worker context, emotion parsing)
2. Remove debug code
3. Add configuration for hardcoded values
4. Start writing unit tests
5. Document known issues and workarounds

---

**Review Completed:** Alpha 0.0.3  
**Reviewer:** AI Code Review Assistant  
**Status:** Ready for development
