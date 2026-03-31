# Jerry Alpha 0.0.5 — Debug Notes

## Question Tool UI

### Features

#### Multi-Select Support
- **Space Bar** — Toggle selection on/off for current option
- **Enter** — Submit all selected options (or single highlighted if none selected)
- **Visual Feedback**:
  - `○` = Unselected
  - `●` = Currently highlighted (cursor position)
  - `✓` = Selected (permanently checked)
  - `◉` = Both selected AND highlighted

#### Single Answer
- Navigate with ↑↓
- Press Enter on highlighted option
- Or type custom answer

#### Multiple Answers
- Navigate with ↑↓
- Press **Space** to toggle selection (✓)
- Select multiple options
- Press **Enter** to submit all selected

#### Custom Answer
- Navigate to "Type custom answer below" option
- Type any response (including spaces)
- Press Enter to submit

### Expected Behavior
When Jerry calls `ask_user()` with options, a centered panel should appear:

```
╭────────────────────────────────────╮
│  ❓ What should I do?              │
│  ↑↓ scroll, Space select, Enter    │
│    ✓ Option A                      │
│    ◉ Option B                      │
│    ○ Option C                      │
│    ○ ── Type custom answer below ──│
│  Answer: my custom answer          │
╰────────────────────────────────────╯
```

**Example Submission:**
- Select Option A (Space) → `✓ Option A`
- Highlight Option B → `◉ Option B`
- Press Enter → Submits: `["Option A", "Option B"]`

### Panel Layout
```
Row 0:  ╭────────────────────────────────╮
Row 1:  │ ❓ Question title              │
Row 2:  │ ↑↓ scroll, Space select, Enter │
Row 3:  │   ✓ Option 1                   │
Row 4:  │   ◉ Option 2                   │
Row 5:  │   ○ Option 3                   │
Row 6:  │   ○ Option 4                   │
Row 7:  │   ○ ── Type custom answer ──   │
Row 8:  │ Answer: user input here        │
Row 9:  │                                │
Row 10: ╰────────────────────────────────╯
```

**Key Features:**
- Fixed height (11 rows)
- Solid background (no bleed-through)
- Scrollable options (shows 4 at a time)
- Custom answer always visible at bottom
- Input displayed inside panel

---

## Bracket-Style Tool Calls (Python/LFM Style)

### Syntax
```python
[tool_name(arg1="value", arg2=123, options=["A", "B", "C"])]
```

### Parser Location
`agent.py` → `_parse_tool_calls_fallback()` → Pattern 0

### Supported Types
- **Strings:** `arg="value"` or `arg='value'`
- **Numbers:** `arg=123`
- **Arrays:** `arg=["A", "B", "C"]` or `arg=[{'path': 'a.py'}, {'path': 'b.py'}]`

### Examples
```python
# Simple call with options
[ask_user(question="Continue?", options=["Yes", "No"])]

# Multiple arguments
[worker_write_program(path='test.py', spec='A test script', language='python')]

# Array of objects
[load_multiple_files(files=[{'path': 'a.py', 'content': '...'}, {'path': 'b.py'}])]

# Numeric argument
[capture_screen(lines=50)]

# Mixed types
[execute_command(command='ls -la', timeout=30)]
```

### Example Output
```python
# Model output:
[ask_user(question="What?", options=["A", "B"])]

# Parsed as:
{
    "name": "ask_user",
    "arguments": {
        "question": "What?",
        "options": ["A", "B"]
    }
}
```

### Regex Pattern
```python
bracket_pattern = r'\[(\w+)\(([^)]*)\)\]'
arg_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\d+)|\[([^\]]*)\])'
```

---

## Common Issues & Fixes

### 1. Options Not Showing
**Symptom:** Panel shows "Type your answer:" instead of options

**Cause:** Dispatcher not passing options parameter (line 116, executor.py)

**Fix:**
```python
# BEFORE (wrong):
elif name == "ask_user": return self._ask_user(a["question"])

# AFTER (fixed):
elif name == "ask_user": return self._ask_user(a["question"], a.get("options"))
```

### 2. UI Freeze on Enter
**Symptom:** Everything locks when pressing Enter

**Cause:** Deadlock in `answer_question()` - calling `push_log()` while holding lock

**Fix:**
```python
# BEFORE (deadlock):
def answer_question(self, answer: str):
    with self._lock:
        self.pending_question["active"] = False
        self.inbox.append(f"[answer] {answer}")
        self.push_log("info", "✓ Answer submitted")  # ← DEADLOCK!

# AFTER (fixed):
def answer_question(self, answer):
    with self._lock:
        if self.pending_question and self.pending_question.get("active"):
            self.pending_question["answer"] = answer
            self.pending_question["active"] = False
            self.inbox.append(f"[answer] {answer}")
    # Log outside lock!
    self.push_log("info", "✓ Answer submitted")
```

### 3. Background Bleed-Through
**Symptom:** Content behind panel visible through panel

**Cause:** Panel doesn't fill background

**Fix:**
```python
# Fill panel background before drawing content
bgattr = curses.color_pair(_C["border"])
for i in range(1, panel_h - 1):
    self.stdscr.addstr(panel_y + i, panel_x + 1, " " * (panel_w - 2), bgattr)
```

### 4. Space Bar Not Working in Custom Answer
**Symptom:** Can't type spaces in custom answer field

**Cause:** Space captured for multi-select even when on custom option

**Fix:**
```python
elif key == ord(' '):
    # Only capture Space when on actual options
    if options and selected < len(options):
        # ... toggle selection ...
        return True
    # Fall through to text input when on custom option
```

### 5. Enter Key Lock
**Symptom:** Pressing Enter with no selection causes lock

**Cause:** No fallback submission

**Fix:**
```python
elif key in (10, 13, curses.KEY_ENTER):
    if raw:
        self.state.answer_question(raw)
    elif selected_indices:
        self.state.answer_question([options[i] for i in sorted(selected_indices)])
    elif selected < len(options):
        self.state.answer_question(options[selected])  # ← Fallback!
    else:
        self.state.answer_question("")  # ← Prevent lock!
```

### 6. Duplicate Tool Calls
**Symptom:** Same tool executes twice

**Cause:** Model outputs duplicate tool calls, both get executed

**Fix:**
```python
seen_names = set()
for tc in tool_calls:
    tc_name = tc.get('function', {}).get('name', '')
    if tc_name in seen_names:
        continue  # Skip duplicate
    seen_names.add(tc_name)
```

---

## Todo Context Injection

### Problem
Model received just `[continue]` without knowing what task it's on.

### Solution
Inject full todo context:

```python
continue_prompt = f"""\
[continue]

**Current Task:** {current_task}

**Pending Tasks:**
  ○ #1: Write code
  ○ #2: Test it
  ○ #3: Deploy

**Instructions:**
- Continue working on the current task
- Call todo_complete() to complete the first pending task
"""
```

### Location
`agent.py` → `run()` method → lines ~105-125

---

## Coin Persistence

### File Location
`jerry_workspace/.coins.json`

### Format
```json
{
  "coins": 25,
  "history": [
    {"type": "earn", "amount": 5, "reason": "Great work!", "ts": "16:30:45"},
    {"type": "spend", "amount": -10, "reason": "Permission granted", "ts": "16:35:12"}
  ]
}
```

### Load/Save
- **Load:** On `State.__init__()` → `_load_coins()`
- **Save:** On every coin change → `_save_coins()`

---

## Debugging Tips

### Check Logs
```bash
tail -100 jerry_workspace/logs/jerry_stdout.log | grep -E "(ask_user|options|Question)"
```

### Test Question Tool Directly
```
# Type directly in chat:
ask_user(question="Test?", options=["A", "B", "C"])
```

### Verify Options Parsed
Check logs for:
```
❓ ask_user called
  question=Test?
  options=['A', 'B', 'C'] (type=list)
  → Final options: ['A', 'B', 'C']
  → Stored in pending_question: {...}
```

---

## Known Quirks

1. **Model calls ask_user twice** - Sometimes outputs duplicate tool calls. Parser deduplicates.
2. **`reply="ask_user"` parameter** - Invalid param, parser ignores it.
3. **Session killed before logs flush** - Use Ctrl+C, check timestamped log files.

---

**Last Updated:** Alpha 0.0.5
**Status:** Question tool fully functional with multi-select support
