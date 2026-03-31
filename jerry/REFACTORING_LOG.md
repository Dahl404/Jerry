# Jerry Refactoring — Bug Log & Issues Found

## Date: 2025-05-XX
## Refactoring: DAO → Jerry rename + path portability improvements

---

## 🐛 Bugs Found During Refactoring

### 1. **Hardcoded Termux-Specific Paths** (FIXED)
**Location:** `config.py`, `screen_stream.py`, `executor.py`
**Issue:** Multiple files had hardcoded paths like `/data/data/com.termux/files/home/dao/dao_workspace`
**Impact:** Code was not portable to other platforms (Linux, macOS, Windows WSL)
**Fix:** Changed to relative path resolution using `os.path.dirname(os.path.abspath(__file__))`
```python
# Before
DAO_BASE = "/data/data/com.termux/files/home/dao/dao_workspace"

# After
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
JERRY_BASE = os.path.dirname(SCRIPT_DIR)
WORKSPACE_DIR = os.path.join(JERRY_BASE, "jerry_workspace")
```

### 2. **Inconsistent Session Naming** (FIXED)
**Location:** `executor.py`, `terminal.py`, `screen_stream.py`, `jerry.py`
**Issue:** Default tmux session was "dao-control" in some places, inconsistent naming
**Impact:** Could cause session conflicts or confusion
**Fix:** Standardized to "jerry-control" across all files

### 3. **Role Name Inconsistency** (FIXED)
**Location:** `models.py`, `agent.py`, `tui.py`, `session.py`
**Issue:** Chat message role was "dao" but agent is now "Jerry"
**Impact:** Minor inconsistency in logs and UI
**Fix:** Changed role from "dao" to "jerry" throughout

### 4. **Missing Cross-Platform Install Instructions** (FIXED)
**Location:** `terminal.py`, `executor.py`
**Issue:** Only showed Termux install command for tmux
**Impact:** Users on Linux/macOS wouldn't know how to install tmux
**Fix:** Added multi-platform install instructions:
```
pkg install tmux  # On Termux
brew install tmux  # On macOS
apt install tmux   # On Debian/Ubuntu
```

### 5. **Log File Naming** (FIXED)
**Location:** `jerry.py`
**Issue:** Log files named `dao_stdout_*.log` 
**Impact:** Confusing when debugging Jerry
**Fix:** Changed to `jerry_stdout_*.log`

---

## ⚠️ Potential Issues to Watch

### 1. **Backward Compatibility**
- Old tmux sessions named "dao-control" won't be auto-killed
- Old log files in `/data/data/com.termux/files/home/dao/logs/` won't be migrated
- **Recommendation:** Manual cleanup if needed

### 2. **Environment Variable Change**
- Changed from `DAO_BASE` to using relative paths
- Old environment variable `DAO_BASE` will be ignored
- **Recommendation:** Update any external scripts using `DAO_BASE`

### 3. **User Workspace Files**
- `jerry_workspace/` was renamed from `dao_workspace/`
- Any symlinks or external references to old path will break
- **Recommendation:** Update external references

---

## ✅ Improvements Made

1. **Portable Paths:** Now works on any platform with Python 3
2. **Consistent Naming:** All "dao" references changed to "jerry"
3. **Better Error Messages:** More helpful tmux installation instructions
4. **Cleaner Code:** Removed platform-specific hardcoded paths

---

## 📝 Files Modified

- `jerry.py` (main entry point)
- `jerry_core/__init__.py`
- `jerry_core/config.py`
- `jerry_core/models.py`
- `jerry_core/agent.py`
- `jerry_core/executor.py`
- `jerry_core/tui.py`
- `jerry_core/session.py`
- `jerry_core/terminal.py`
- `jerry_core/screen_stream.py`

---

## 🧪 Testing Status

- [x] Syntax check passed (`python3 -m py_compile`)
- [ ] Runtime test (needs model servers running)
- [ ] Integration test (full session)

---

## 📋 Next Steps (Modularization Plan)

After renaming complete, proceed with:

1. **Create `utils/` package** - Extract shared utilities
2. **Split `config/` package** - Separate config, tools, prompts
3. **Split `executor/` package** - Organize tools by category
4. **Split `ui/` package** - Break down 1525-line tui.py
5. **Add unit tests** - For isolated components

See refactoring plan for detailed structure.
