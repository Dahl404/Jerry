# Jerry Changelog

## Alpha 0.0.5 (Current)

### 🎯 Major Features

#### Interactive Question Tool (`ask_user`)
- **Multiple Choice Questions** — Jerry can ask questions with selectable options
- **Multi-Select Support** — Press Space to select multiple, Enter submits all
- **Beautiful UI Panel** — Centered popup with ●/✓/◉ option indicators
- **Keyboard Navigation** — ↑↓ navigate, Space select, Enter confirm
- **Custom Answers** — Type custom response or select from options
- **Non-Blocking** — Jerry waits for answer without freezing
- **Quit Support** — Ctrl+Q, q, or /quit even during questions

**Markers:**
- `○` = Unselected
- `●` = Currently highlighted (cursor)
- `✓` = Selected (checked with Space)
- `◉` = Both selected AND highlighted

**Usage:**
```python
# Single answer
ask_user(question="What task first?", options=["A", "B", "C"])
# → Select with ↑↓, press Enter

# Multiple answers
# → Select multiple with Space, press Enter
# → Submits: ["A", "B"]
```

#### Bracket-Style Tool Calls
- **New Syntax:** `[tool_name(arg="value", options=["A", "B"])]`
- **Array Support** — Options and array parameters parse correctly
- **Backward Compatible** — All existing formats still work

### 🐛 Critical Bug Fixes

#### Fixed: Options Not Showing in Question Panel
- **Issue:** `ask_user()` options parameter ignored in dispatcher (line 116)
- **Fix:** Changed `self._ask_user(a["question"])` → `self._ask_user(a["question"], a.get("options"))`
- **Result:** Options now display correctly in UI

#### Fixed: UI Deadlock on Question Answer
- **Issue:** `answer_question()` caused deadlock (lock → push_log → lock)
- **Fix:** Moved `push_log()` outside lock, removed unnecessary locking
- **Result:** No more freezes when pressing Enter

#### Fixed: Question Panel UI Issues
- **Removed** "Answer:" hint from panel (cleaner UI)
- **Fixed** panel positioning to avoid border collisions
- **Cleared** input buffer when question appears
- **Fixed** panel height calculation

#### Fixed: Todo Context Missing
- **Issue:** Model didn't see todo list, just got "[continue]"
- **Fix:** Inject full todo context with current task and pending list
- **Result:** Model knows exactly what to work on

### 🪙 Coin System Updates
- **Persistence** — Coins saved to `.coins.json` across sessions
- **Fixed Deadlock** — Coin operations no longer cause UI freezes
- **Better Logging** — Clear transaction history

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

### 📝 Documentation
- **debug.md** — Documents question tool UI and bracket syntax
- **README Updated** — All new features documented
- **CHANGELOG** — Comprehensive version history

### 📊 Statistics
- **Files Changed:** 8
- **Lines Added:** ~400
- **Lines Removed:** ~150
- **Bugs Fixed:** 6 major
- **New Features:** 4
- **New Tools:** 3 (`ask_user`, `worker_write_program`, `load_multiple_files`)

---

## Alpha 0.0.4 (March 30, 2026)

### Critical Fixes
- **Streaming Tool Call Fix** — Fixed llama-server compatibility (parsed JSON objects)
- **Fallback Parser Bug** — Handles all Qwen output formats
- **Same-Port Default** — Agent/Worker use port 8080 by default

### Features
- Tool error auto-help system
- Improved status indicators
- Silent failure detection
- User interruption during streaming

[See `jerry_release/CHANGELOG.md` for earlier versions]

---

## Reporting Issues

- **GitHub:** https://github.com/Dahl404/Jerry/issues
- **Logs:** Check `logs/jerry_stdout.log`
- **Debug Mode:** Run with verbose logging enabled

---

**Release Date:** Current
**Version:** Alpha 0.0.5
**Author:** Dahl404
