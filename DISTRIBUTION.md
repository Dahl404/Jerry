# Jerry Distribution Package - Alpha 0.0.3

## Quick Start

```bash
# 1. Clean the project (optional - for redistribution)
./clean.sh

# 2. Install dependencies (Termux)
pkg update && pkg upgrade
pkg install python git tmux

# 3. Run Jerry
./jerry
```

## What Gets Cleaned

Running `./clean.sh` removes:

### ✓ Removed
- Application logs (`logs/`)
- Diary entries (`jerry_workspace/diary/`)
- Session summaries (`jerry_workspace/summaries/`)
- Persona documents (`jerry_workspace/persona/`)
- Scratchpad files (`jerry_workspace/scratchpad/`)
- Python cache (`__pycache__/`, `*.pyc`)
- Temporary files (`*.tmp`, `*.bak`, `*~`)

### ✓ Preserved
- Workspace directory structure
- Configuration files
- Source code
- Documentation
- Face assets

## Distribution Checklist

Before distributing Jerry:

- [ ] Run `./clean.sh` to remove logs and user data
- [ ] Verify no API keys or secrets in config
- [ ] Check `.gitignore` is present
- [ ] Update version in README.md
- [ ] Test fresh installation

## Manual Cleanup (Alternative)

If you prefer manual cleanup:

```bash
# Remove logs
rm -rf logs/

# Clean workspace (keeps directory structure)
rm -rf jerry_workspace/diary/*
rm -rf jerry_workspace/summaries/*
rm -rf jerry_workspace/persona/*
rm -rf jerry_workspace/scratchpad/*
rm -rf jerry_workspace/logs/*

# Clean Python cache
find . -name "__pycache__" -type d -exec rm -rf {} \;
find . -name "*.pyc" -delete

# Remove session state
rm -f jerry_workspace/.session_state
rm -f jerry_workspace/.last_run
```

## Fresh Start

To completely reset Jerry:

```bash
# Stop Jerry if running
# Press Ctrl+C in terminal

# Remove workspace entirely
rm -rf jerry_workspace/

# Remove logs
rm -rf logs/

# Remove Python cache
find . -name "__pycache__" -exec rm -rf {} \;

# Start fresh - workspace will be recreated
./jerry
```

## Directory Structure (After Cleanup)

```
jerry_alpha_002/
├── jerry                  # Launcher script
├── jerry.py               # Main entry point
├── jerry_core/            # Core package
│   ├── __init__.py
│   ├── agent.py
│   ├── config.py
│   ├── executor.py
│   ├── faces_display.py
│   ├── models.py
│   ├── screen_stream.py
│   ├── session.py
│   ├── terminal.py
│   ├── tools_minimal.py
│   └── tui.py
├── faces/                 # ASCII face assets
├── jerry_workspace/       # Empty workspace (created on first run)
│   ├── diary/
│   ├── summaries/
│   ├── persona/
│   ├── logs/
│   └── scratchpad/
├── clean.sh               # Cleanup script
├── .gitignore             # Git ignore rules
├── README.md              # Documentation
└── REVIEW_SUMMARY.md      # Code review notes
```

## License

MIT License - See LICENSE file for details.

## Support

Issues: https://github.com/Dahl404/Jerry/issues
Docs: README.md
