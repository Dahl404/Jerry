#!/data/data/com.termux/files/usr/bin/bash
# Jerry Alpha 0.0.3 - Cleanup Script
# Removes logs, workspace data, and generated files for distribution

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "╭──────────────────────────────────────────────────────────────╮"
echo "│  Jerry Cleanup Script - Alpha 0.0.3                         │"
echo "╰──────────────────────────────────────────────────────────────╯"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
REMOVED_DIRS=0
REMOVED_FILES=0
SKIPPED=0

# Function to safely remove directory
remove_dir() {
    local dir="$1"
    local desc="$2"
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}Removing:${NC} $desc"
        rm -rf "$dir"
        ((REMOVED_DIRS++))
        echo -e "${GREEN}  ✓ Removed:${NC} $dir"
    else
        echo -e "${BLUE}  Skipped:${NC} $dir (not found)"
        ((SKIPPED++))
    fi
}

# Function to safely remove file
remove_file() {
    local file="$1"
    local desc="$2"
    if [ -f "$file" ]; then
        echo -e "${YELLOW}Removing:${NC} $desc"
        rm -f "$file"
        ((REMOVED_FILES++))
        echo -e "${GREEN}  ✓ Removed:${NC} $file"
    else
        echo -e "${BLUE}  Skipped:${NC} $file (not found)"
        ((SKIPPED++))
    fi
}

# Function to clean directory contents but keep the directory
clean_dir_contents() {
    local dir="$1"
    local desc="$2"
    if [ -d "$dir" ]; then
        echo -e "${YELLOW}Cleaning:${NC} $desc"
        find "$dir" -mindepth 1 -delete 2>/dev/null || true
        echo -e "${GREEN}  ✓ Cleaned:${NC} $dir"
    else
        echo -e "${BLUE}  Skipped:${NC} $dir (not found)"
        ((SKIPPED++))
    fi
}

echo ""
echo "═══ Application Logs ═══════════════════════════════════════"
echo ""

# Remove application logs
remove_dir "logs" "Application logs (stdout/stderr)"

echo ""
echo "═══ Workspace Data ════════════════════════════════════════"
echo ""

# Clean workspace subdirectories (keep the directory structure)
if [ -d "jerry_workspace" ]; then
    clean_dir_contents "jerry_workspace/diary" "Diary entries"
    clean_dir_contents "jerry_workspace/summaries" "Session summaries"
    clean_dir_contents "jerry_workspace/persona" "Persona documents"
    clean_dir_contents "jerry_workspace/logs" "Workspace logs"
    clean_dir_contents "jerry_workspace/scratchpad" "Scratchpad files"
    
    # Remove workspace entirely if preferred
    # remove_dir "jerry_workspace" "Entire workspace"
    
    echo -e "${GREEN}  ✓ Workspace cleaned (directory structure preserved)${NC}"
else
    echo -e "${BLUE}  Skipped:${NC} jerry_workspace (not found)"
    ((SKIPPED++))
fi

echo ""
echo "═══ Python Cache ══════════════════════════════════════════"
echo ""

# Remove Python cache
remove_dir "__pycache__" "Root __pycache__"
remove_dir "jerry_core/__pycache__" "jerry_core __pycache__"

# Remove .pyc files
if [ -d "jerry_core" ]; then
    echo -e "${YELLOW}Removing:${NC} Python .pyc files"
    find jerry_core -name "*.pyc" -delete 2>/dev/null || true
    echo -e "${GREEN}  ✓ Removed .pyc files${NC}"
fi

echo ""
echo "═══ Session State ═════════════════════════════════════════"
echo ""

# Remove any session state files
remove_file "jerry_workspace/.session_state" "Session state file"
remove_file "jerry_workspace/.last_run" "Last run timestamp"

echo ""
echo "═══ Build Artifacts (if any) ══════════════════════════════"
echo ""

# Remove any build artifacts
remove_dir "build" "Build directory"
remove_dir "dist" "Distribution directory"
remove_file "*.egg-info" "Egg info files"

echo ""
echo "═══ Temporary Files ═══════════════════════════════════════"
echo ""

# Remove temporary files
remove_file "*.tmp" "Temporary files"
remove_file "*.bak" "Backup files"
remove_file "*.swp" "Vim swap files"
remove_file "*.swo" "Vim swap files"
remove_file "*~" "Tilde backup files"

echo ""
echo "═══ Git (Optional - Uncomment if needed) ══════════════════"
echo ""

# Uncomment to clean git artifacts (for distribution tarballs)
# remove_dir ".git" "Git repository"
# remove_file ".gitignore" "Git ignore file"
# remove_file ".gitattributes" "Git attributes"

echo ""
echo "╭──────────────────────────────────────────────────────────────╮"
echo "│  Cleanup Summary                                             │"
echo "╰──────────────────────────────────────────────────────────────╯"
echo ""
echo -e "${GREEN}Directories removed:${NC} $REMOVED_DIRS"
echo -e "${GREEN}Files removed:${NC}       $REMOVED_FILES"
echo -e "${BLUE}Skipped:${NC}             $SKIPPED"
echo ""

# Check what remains
echo "═══ Remaining Structure ═══════════════════════════════════"
echo ""

if [ -d "jerry_workspace" ]; then
    echo "Workspace directory structure:"
    find jerry_workspace -type d 2>/dev/null | head -20 || echo "  (empty)"
fi

echo ""
echo -e "${GREEN}✓ Cleanup complete!${NC}"
echo ""
echo "Jerry is now clean for distribution."
echo "To reset completely, delete jerry_workspace directory manually."
echo ""
