#!/data/data/com.termux/files/usr/bin/bash
# Dao Cleanup Script
# Closes all Dao-related tmux sessions and kills orphaned processes

echo "🧹 Cleaning up Dao sessions and processes..."
echo

# Kill all tmux sessions starting with "dao"
echo "📦 Closing tmux sessions..."
for session in $(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep '^dao'); do
    echo "   Killing session: $session"
    tmux kill-session -t "$session" 2>/dev/null
done

# Kill orphaned python processes running dao.py or related scripts
echo "🔍 Checking for orphaned Python processes..."
for pid in $(pgrep -f "python.*dao" 2>/dev/null); do
    echo "   Killing process: $pid"
    kill -9 "$pid" 2>/dev/null
done

# Clean up temp files
echo "🗑️  Cleaning temp files..."
rm -f /data/data/com.termux/files/home/dao/dao_workspace/.screen_capture.txt 2>/dev/null

echo
echo "✓ Cleanup complete!"
echo
echo "To start Dao: ./dao"
