# Ultra-minimal tool definitions - only help has full params
# Matches Qwen-Code CLI tool naming conventions
TOOLS = [
    {"type": "function", "function": {"name": "help", "description": "Get tool info. Call help() for list, help(tool) for details.", "parameters": {"type": "object", "properties": {"tool_name": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {"name": "execute_command", "description": "Run shell command.", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "Full command as single string, e.g., 'ls -la'"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Read file (loads into worker context for analysis).", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "write_file", "description": "Write file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "list_directory", "description": "List directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": []}}},
    # Qwen-Code CLI style todo system
    {"type": "function", "function": {"name": "todo_write", "description": "Replace entire todo list. Pass array of {content, priority, completed}.", "parameters": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "priority": {"type": "string"}, "completed": {"type": "boolean"}}}}}, "required": ["todos"]}}},
    {"type": "function", "function": {"name": "todo_complete", "description": "Mark todo as complete by index or id.", "parameters": {"type": "object", "properties": {"index": {"type": "integer", "description": "0-based index (default: 0)"}, "id": {"type": "integer", "description": "Stable todo id"}}, "required": []}}},
    # Terminal streaming tools (for interactive programs)
    {"type": "function", "function": {"name": "send_keys", "description": "Send keystrokes to terminal.", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}},
    {"type": "function", "function": {"name": "run_program", "description": "Run program in stream mode (watch execution live).", "parameters": {"type": "object", "properties": {"command": {"type": "string", "description": "Full command, e.g., 'python game.py'"}}, "required": ["command"]}}},
    # Additional tools (use help(tool) for details)
    {"type": "function", "function": {"name": "replace_lines", "description": "Replace lines in file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}, "new_content": {"type": "string"}}, "required": ["path", "start_line", "end_line", "new_content"]}}},
    {"type": "function", "function": {"name": "insert_lines", "description": "Insert lines in file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "after_line": {"type": "integer"}, "content": {"type": "string"}}, "required": ["path", "after_line", "content"]}}},
    {"type": "function", "function": {"name": "delete_lines", "description": "Delete lines from file.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["path", "start_line", "end_line"]}}},
    {"type": "function", "function": {"name": "search_files", "description": "Search files with grep.", "parameters": {"type": "object", "properties": {"pattern": {"type": "string"}, "path": {"type": "string"}, "recursive": {"type": "boolean"}, "case_sensitive": {"type": "boolean"}}, "required": ["pattern"]}}},
    {"type": "function", "function": {"name": "query_worker", "description": "Ask worker AI about loaded file.", "parameters": {"type": "object", "properties": {"question": {"type": "string"}, "extra_context": {"type": "string"}}, "required": ["question"]}}},
    {"type": "function", "function": {"name": "reset_worker", "description": "Clear worker conversation history.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "enter", "description": "Change working directory.", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "pwd", "description": "Show current directory.", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "capture_screen", "description": "Capture terminal screen.", "parameters": {"type": "object", "properties": {"lines": {"type": "integer"}}, "required": []}}},
    {"type": "function", "function": {"name": "send_ctrl", "description": "Send Ctrl+key sequence.", "parameters": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}}},
    # Question tool for user interaction (Qwen-Code CLI style)
    {"type": "function", "function": {"name": "ask_user", "description": "Ask the user a question when you need clarification, input, or decisions. Use this instead of guessing.", "parameters": {"type": "object", "properties": {"question": {"type": "string", "description": "The question to ask the user"}}, "required": ["question"]}}},
    # Coin/reward system tools (Jerry CAN use these)
    {"type": "function", "function": {"name": "check_coins", "description": "Check Jerry's current coin balance", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "offer_coins", "description": "Offer coins to user in exchange for permission or help", "parameters": {"type": "object", "properties": {"amount": {"type": "integer", "description": "Number of coins to offer"}, "reason": {"type": "string", "description": "What Jerry wants permission for"}}, "required": ["amount", "reason"]}}},
    # Multi-file worker support
    {"type": "function", "function": {"name": "load_multiple_files", "description": "Load multiple files into worker context for cross-file analysis", "parameters": {"type": "object", "properties": {"files": {"type": "array", "items": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}}, "description": "Array of {path, content} objects"}}, "required": ["files"]}}},
    # NOTE: 'praise' tool removed - users praise Jerry via /praise command, not through AI
]
