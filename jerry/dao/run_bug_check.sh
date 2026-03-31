#!/bin/bash
# Quick Bug Detection Runner for Dao
# Usage: ./run_bug_check.sh [output_file]

OUTPUT_FILE="${1:-bugs.md}"

echo "╔════════════════════════════════════════╗"
echo "║   Dao Automated Bug Detection Tool    ║"
echo "╚════════════════════════════════════════╝"
echo ""
echo "Running comprehensive analysis..."
echo ""

python3 tests/auto_bug_detector.py . -o "$OUTPUT_FILE"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Analysis complete - No critical bugs found!"
else
    echo ""
    echo "⚠️  Analysis complete - Bugs found (see $OUTPUT_FILE)"
fi

echo ""
echo "Report saved to: $OUTPUT_FILE"
echo ""

# Show summary
if [ -f "$OUTPUT_FILE" ]; then
    echo "📊 Quick Summary:"
    echo "─────────────────────────────────────"
    grep -A 7 "## Summary" "$OUTPUT_FILE" | head -8
fi
