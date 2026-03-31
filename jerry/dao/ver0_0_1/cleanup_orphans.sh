#!/bin/bash
# Dao Cleanup Script - Kill orphaned processes and tmux sessions
# Run this if Dao didn't shut down cleanly

set -e

echo "🔍 Dao Cleanup Script"
echo "===================="
echo ""

# Kill orphaned Python processes running dao.py
echo "Checking for orphaned Dao Python processes..."
ORPHAN_PIDS=$(pgrep -f "dao.py" 2>/dev/null || true)
ORPHAN_PIDS+=$(pgrep -f "run.py" 2>/dev/null || true)

if [ -n "$ORPHAN_PIDS" ]; then
    echo "⚠️  Found orphaned processes: $ORPHAN_PIDS"
    echo "📝 Killing orphaned Python processes..."
    echo "$ORPHAN_PIDS" | xargs -r kill -9 2>/dev/null || true
    echo "✓ Killed orphaned processes"
else
    echo "✓ No orphaned Python processes found"
fi

echo ""

# List and optionally kill Dao tmux sessions
echo "Checking for Dao tmux sessions..."
DAO_SESSIONS=$(tmux list-sessions 2>/dev/null | grep -E "(dao|dao-control)" | cut -d: -f1 || true)

if [ -n "$DAO_SESSIONS" ]; then
    echo "⚠️  Found Dao tmux sessions:"
    echo "$DAO_SESSIONS" | while read -r session; do
        echo "   - $session"
    done
    
    echo ""
    echo "📝 Killing Dao tmux sessions..."
    echo "$DAO_SESSIONS" | while read -r session; do
        tmux kill-session -t "$session" 2>/dev/null || true
        echo "   ✓ Killed session: $session"
    done
    echo "✓ Killed tmux sessions"
else
    echo "✓ No Dao tmux sessions found"
fi

echo ""

# Clean up any zombie subprocesses
echo "Checking for zombie subprocesses..."
ZOMBIES=$(ps aux 2>/dev/null | grep -E "(python.*dao|tmux.*dao)" | grep -v grep | grep -v "$$" || true)

if [ -n "$ZOMBIES" ]; then
    echo "⚠️  Found potential zombie processes:"
    echo "$ZOMBIES"
    echo ""
    echo "📝 Cleaning up..."
    ps aux 2>/dev/null | grep -E "(python.*dao|tmux.*dao)" | grep -v grep | grep -v "$$" | awk '{print $2}' | xargs -r kill -9 2>/dev/null || true
    echo "✓ Cleaned up zombie processes"
else
    echo "✓ No zombie processes found"
fi

echo ""

# Clean up temp files
echo "Cleaning up temp files..."
rm -rf /tmp/dao_* 2>/dev/null || true
rm -rf /data/data/com.termux/cache/dao_* 2>/dev/null || true
echo "✓ Cleaned temp files"

echo ""
echo "===================="
echo "✅ Cleanup complete!"
echo ""
echo "Tip: To prevent orphaned processes in the future:"
echo "  1. Always exit Dao with /quit or Ctrl+C"
echo "  2. Run this script if Dao crashes or terminal closes unexpectedly"
echo "  3. Consider running Dao inside tmux: tmux new -s dao && python dao.py"
