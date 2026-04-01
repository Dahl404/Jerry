#!/usr/bin/env python3
"""Jerry — Autonomous Agent with Streaming"""

import time
import json
import re
import requests
import threading
from typing import Dict, List
from .config import AGENT_URL, MAX_TOKENS, TEMPERATURE, CONV_TRIM, TOOLS, SYSTEM_PROMPT, CYCLE_SLEEP, JERRY_BASE
from .worker import strip_think
from .models import State
from .executor import Executor

class Agent:
    """Autonomous agent with streaming output."""

    def __init__(self, state: State, executor: Executor, tui=None):
        self.state    = state
        self.executor = executor
        self.tui      = tui  # Optional: for updating token count
        # Format SYSTEM_PROMPT here so {jerry_base} resolves to the actual path.
        # Without this the model sees the literal string "{jerry_base}" in its prompt.
        tool_list = "\n".join([f"- `{t['function']['name']}`: {t['function']['description']}" for t in TOOLS[:10]])
        self.conv:    List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT.format(jerry_base=JERRY_BASE, tool_list=tool_list)}]
        self._stop    = False
        self._is_thinking = False

    def stop(self):
        self._stop = True

    # ── Main loop (runs in background thread) ──────────────────────────────────
    def run(self):
        self.state.set_status("idle")
        self.state.set_phase("idle")
        last_action_time = time.time()  # Initialize to NOW, not 0.0 (prevents immediate idle trigger)
        last_content = ""  # Track last activity for idle reflection
        last_task_text = None  # Track last task #0 to avoid duplicate prompts (BUG-C fix)

        while not self._stop:
            try:
                # Get current minimum cycle gap from state (user-configurable via /gap)
                min_cycle_gap = self.state.get_cycle_gap()
                # Check inbox for user messages - always priority
                msgs = self.state.drain_inbox()
                if msgs:
                    for m in msgs:
                        # Check if there are any todos already
                        with self.state._lock:
                            has_pending = any(not t.done for t in self.state.todos)

                        if not has_pending:
                            # No pending todos — create tasks for the user's request
                            # Just pass the user message through, model will create todos naturally
                            self.conv.append({"role": "user", "content": m})
                            last_task_text = None  # Reset task tracking on new user message
                            self.state.set_phase("planning")
                        else:
                            # Has pending todos — user is providing extra context; continue execution
                            # Build full todo context so model knows what it's working on
                            pending_todos = [t for t in self.state.todos if not t.done]
                            current_task = pending_todos[0].text if pending_todos else "unknown"
                            
                            pending_list = "\n".join([
                                f"  {'✓' if t.done else '○'} #{t.id}: {t.text}"
                                for t in pending_todos[:5]
                            ])
                            
                            exec_prompt = f"""\
[user message] {m}

**Current Task:** {current_task}

**Pending Tasks:**
{pending_list}

**Instructions:**
- Consider the user's message above
- Continue working on the current task
- Call todo_complete() with no arguments to complete the first pending task
"""
                            self.conv.append({"role": "user", "content": exec_prompt})
                            last_task_text = None  # Reset so a fresh prompt is injected next cycle
                            self.state.set_phase("executing")

                    # Execute the cycle
                    self._cycle(max_turns=50)
                    self._update_token_count()  # Update after user message processing
                    last_action_time = time.time()
                    continue

                # Check for pending todos
                with self.state._lock:
                    pending = [t for t in self.state.todos if not t.done]
                    completed_count = sum(1 for t in self.state.todos if t.done)

                # Get context from recent conversation (used in both branches)
                recent = self.conv[-5:] if len(self.conv) > 5 else self.conv
                last_tool = ""
                for msg in reversed(recent):
                    if msg.get("role") == "assistant":
                        if msg.get("tool_calls"):
                            last_tool = msg["tool_calls"][0]["function"]["name"]
                        if msg.get("content"):
                            last_content = msg["content"][:100]
                        break

                if pending:
                    # Respect minimum gap between cycles
                    if time.time() - last_action_time < min_cycle_gap:
                        time.sleep(0.3)
                        continue

                    self.state.set_phase("executing")
                    current_task = pending[0].text
                    
                    # Build todo context for the model
                    # Include current task #0 and all pending tasks so model knows what to work on
                    pending_list = "\n".join([
                        f"  {'✓' if t.done else '○'} #{t.id}: {t.text}"
                        for t in pending[:5]  # Show first 5 pending tasks
                    ])
                    remaining = len(pending) - 5
                    if remaining > 0:
                        pending_list += f"\n  ... and {remaining} more tasks"
                    
                    # Inject [continue] with full todo context
                    # This ensures the model knows exactly what to work on
                    continue_prompt = f"""\
[continue]

**Current Task:** {current_task}

**Pending Tasks:**
{pending_list}

**Instructions:**
- Continue working on the current task above
- Use tools to complete the task
- Call todo_complete() with no arguments to complete the first pending task
- If blocked, ask for clarification with ask_user()
"""

                    self.conv.append({"role": "user", "content": continue_prompt})

                    self._cycle(max_turns=50)
                    last_action_time = time.time()
                else:
                    # No todos - idle reflection mode
                    last_task_text = None  # Reset task tracking when idle
                    self.state.set_phase("idle")
                    # After quiet period, prompt self to reflect and decide next action
                    idle_time = time.time() - last_action_time
                    if idle_time > 30:  # Reflect after 30 seconds of inactivity
                        reflection_prompt = (
                            f"[idle reflection] You've been idle for {idle_time:.0f} seconds.\n"
                            f"Last activity: {last_content[:80] if last_content else 'none'}\n\n"
                            
                            f"**Reflect efficiently:**\n"
                            f"1. **What were you last working on?** (check recent conversation above)\n"
                            f"2. **Do you have active projects?** (only check scratchpad if unsure)\n"
                            f"3. **What's the ONE next valuable action?**\n\n"
                            
                            f"**Decide with purpose - pick ONE:**\n"
                            f"- **Continue** previous work? → Resume where you left off\n"
                            f"- **Verify** last changes? → Test what you built\n"
                            f"- **Explore** for a SPECIFIC thing? → Know what you're looking for first\n"
                            f"- **Create** something new? → Start with a clear goal\n"
                            f"- **Wait** for user input? → If no clear direction\n\n"

                            f"**Rules:**\n"
                            f"- Don't explore aimlessly - know WHAT you're looking for\n"
                            f"- Don't check every folder - check only RELEVANT ones\n"
                            f"- Don't gather context forever - act after 1-2 checks max\n"
                            f"- Use scratchpad for working memory, diary for patterns only\n"
                            f"- Test every change before marking complete\n"
                            f"\nThen execute your decision."
                        )
                        self.conv.append({"role": "user", "content": reflection_prompt})
                        self._cycle(max_turns=10)
                        last_action_time = time.time()
                    else:
                        time.sleep(0.5)

            except Exception as e:
                self.state.push_log("error", f"Agent loop: {e}")
                self.state.set_status("error")
                time.sleep(3.0)

    # ── Reasoning cycle (tool-calling loop) ────────────────────────────────────
    def _cycle(self, max_turns: int = 30):
        self.state.set_status("thinking")
        self._is_thinking = True
        # Per-cycle list for loop detection — passed into _check_tool_loop by reference
        recent_tool_calls: List[str] = []

        try:
            for turn in range(max_turns):
                # Check for pending question - BLOCKS until answered
                question = self.state.get_pending_question()
                
                if question and question.get("active"):
                    # Question is pending - STOP processing and wait
                    # Don't call model, don't continue loop
                    self.state.set_status("waiting for answer...")
                    time.sleep(0.3)  # Small sleep
                    continue  # Keep checking, but don't do anything
                
                # Check for user interruption at start of each turn
                has_pending_msgs = False
                try:
                    self.state._lock.acquire()
                    has_pending_msgs = len(self.state.inbox) > 0
                    # Clear the question if answer was submitted
                    if has_pending_msgs:
                        self.state.clear_pending_question()
                finally:
                    self.state._lock.release()

                if has_pending_msgs:
                    self._update_token_count()
                    return  # Exit cycle - main loop will process the interruption

                self._trim_conv()

                try:
                    # Keep status as "thinking" while waiting for model response
                    # The streaming call itself will update status internally if needed
                    msg = self._call_model_streaming()
                except Exception as e:
                    self.state.push_log("error", f"Model call failed: {e}")
                    self.state.set_status("error")
                    return

                tool_calls = msg.get("tool_calls") or []
                
                # Debug: Log what we got from API
                self.state.push_log("debug", f"API returned {len(tool_calls)} structured tool_calls")
                if msg.get("content"):
                    self.state.push_log("debug", f"Content preview: {msg['content'][:200]}...")

                # FALLBACK: Parse tool calls from content if not in structured format
                if not tool_calls and msg.get("content"):
                    tool_calls = self._parse_tool_calls_fallback(msg["content"])
                    if tool_calls:
                        self.state.push_log("debug", f"Fallback parser found {len(tool_calls)} tool calls")
                elif tool_calls and msg.get("content"):
                    # ALSO check content for bracket-style calls (might have more params)
                    bracket_calls = self._parse_tool_calls_fallback(msg["content"])
                    if bracket_calls:
                        # Prefer bracket calls - they might have options array etc.
                        self.state.push_log("debug", f"Found {len(bracket_calls)} bracket-style tool calls, using instead of structured")
                        tool_calls = bracket_calls

                # Loop detection — returns True and breaks if stuck
                if self._check_tool_loop(tool_calls, recent_tool_calls):
                    return

                # Append the assistant turn (with tool_calls) to conversation
                # CRITICAL FIX: content must be "" not None when tool_calls exist (llama-server requirement)
                # Also validate tool_calls before saving to prevent 400 errors
                valid_tool_calls = []
                seen_names = set()  # Deduplicate tool calls
                
                for tc in tool_calls:
                    # Validate tool call has required fields
                    tc_id = tc.get('id', '')
                    tc_name = tc.get('function', {}).get('name', '')
                    tc_args = tc.get('function', {}).get('arguments')

                    # Generate ID if missing (fallback parser doesn't create unique IDs)
                    if not tc_id:
                        tc_id = f"call_{int(time.time()*1000)}_{len(valid_tool_calls)}"
                        tc['id'] = tc_id
                        self.state.push_log("debug", f"Generated tool call ID: {tc_id}")

                    # Skip invalid tool calls (empty name is fatal)
                    if not tc_name:
                        self.state.push_log("debug", f"Skipping invalid tool call: id='{tc_id}', name='{tc_name}'")
                        continue
                    
                    # Skip duplicate tool calls (model sometimes outputs same call twice)
                    if tc_name in seen_names:
                        self.state.push_log("debug", f"Skipping duplicate tool call: {tc_name}")
                        continue
                    seen_names.add(tc_name)

                    # Ensure arguments is at least an empty dict if missing
                    if tc_args is None:
                        tc['function']['arguments'] = {}

                    valid_tool_calls.append(tc)

                # Only save tool_calls if we have valid ones
                if valid_tool_calls:
                    self.conv.append({
                        "role":       "assistant",
                        "content":    "",  # MUST be empty string, not None (llama-server requirement)
                        "tool_calls": valid_tool_calls,
                    })
                    self.state.push_log("debug", f"Saved assistant message with {len(valid_tool_calls)} valid tool calls")

                    # Execute every tool call and append results
                    self._execute_tool_calls(valid_tool_calls)
                else:
                    # No valid tool calls - save as text response
                    # CRITICAL: Don't include "tool_calls": None - omit the key entirely
                    self.conv.append({
                        "role":       "assistant",
                        "content":    msg.get("content", ""),
                    })
                    self.state.push_log("debug", "Saved assistant message as text response (no valid tool calls)")

                    # CRITICAL: Break the cycle! The main run() loop will
                    # check for pending todos and inject [continue] if needed.
                    # This prevents 400 errors from assistant replying to assistant.
                    break

                # Update token count after each turn
                self._update_token_count()

        finally:
            self._is_thinking = False
            self.state.set_status("ready")

    # ── Token count update ─────────────────────────────────────────────────────
    def _update_token_count(self):
        """Update TUI with current context token count."""
        try:
            # Count actual conversation tokens (what's sent to model)
            total_chars = 0
            for msg in self.conv:
                content = msg.get("content", "")
                if content:
                    total_chars += len(content)
            
            token_count = total_chars // 4
            self.tui.update_tokens(token_count)
        except Exception:
            pass

    # ── Loop detection ────────────────────────────────────────────────────────
    def _check_tool_loop(self, tool_calls: List[Dict], recent: List[str],
                         max_repeats: int = 5) -> bool:
        """Append current call signatures to *recent* and return True if looping.

        Detects REAL loops: same tool + same arguments repeated.
        Allows same tool with DIFFERENT arguments (e.g., todo_add for different tasks).
        
        Mutates *recent* in-place so the caller's list accumulates across turns.
        """
        for tc in tool_calls:
            name     = tc["function"]["name"]
            args_str = tc["function"].get("arguments", "{}")
            # Use FULL arguments for signature, not truncated
            # This allows same tool with different args (not a loop)
            sig      = f"{name}:{args_str}"

            recent.append(sig)
            if len(recent) > max_repeats:
                recent.pop(0)

            # Only flag as loop if EXACT same call (tool + args) repeated
            if len(recent) >= max_repeats and len(set(recent)) == 1:
                self.state.push_log("error", f"Tool call loop detected: {sig}")
                self.state.push_chat("dao", f"⚠️ I got stuck repeating `{name}`. Let me try a different approach.")
                self._is_thinking = False
                self.state.set_status("ready")
                return True
        return False

    # ── Fallback tool call parser ──────────────────────────────────────────────
    def _parse_tool_calls_fallback(self, content: str) -> List[Dict]:
        """Parse tool calls from content when not in structured format.

        Handles multiple patterns:
        0. Bracket style: [ask_user(question="...")]
        1. function_name with JSON args in tags: <function_name>{...}</function_name>
        2. XML-style: <function_name><param>value</param></function_name>
        3. Qwen format: <function=name> <parameter=key>val</parameter> </function>
        """
        tool_calls = []

        # ── Pattern 0: Bracket style [tool_name(arg="value", arg2=123)] ────────
        # Matches: [ask_user(question="What?")] or [capture_screen(lines=50)]
        bracket_pattern = r'\[(\w+)\(([^)]*)\)\]'
        for match in re.finditer(bracket_pattern, content):
            func_name = match.group(1)
            args_str = match.group(2)

            # Parse arguments - handle strings, numbers, and arrays
            params = {}
            if args_str.strip():
                # Match: arg="value" or arg='value' or arg=123 or arg=["a","b"]
                # More flexible pattern to handle arrays
                arg_pattern = r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\d+)|\[([^\]]*)\])'
                for arg_match in re.finditer(arg_pattern, args_str):
                    arg_name = arg_match.group(1)
                    # Get whichever group matched
                    str_val = arg_match.group(2) or arg_match.group(3)
                    num_val = arg_match.group(4)
                    array_val = arg_match.group(5)
                    
                    if array_val is not None:
                        # Parse array - extract quoted strings
                        array_items = re.findall(r'"([^"]*)"', array_val)
                        if not array_items:
                            array_items = re.findall(r"'([^']*)'", array_val)
                        params[arg_name] = array_items
                    elif num_val is not None:
                        params[arg_name] = int(num_val)
                    elif str_val is not None:
                        params[arg_name] = str_val
                    # Ignore params that don't match any pattern (like reply="ask_user")

            tool_calls.append({
                "id": f"call_{int(time.time()*1000)}_{len(tool_calls)}",
                "type": "function",
                "function": {
                    "name": func_name,
                    "arguments": json.dumps(params),
                },
            })
        
        # Pattern 1: <function_name>{JSON}</function_name>
        pattern1 = r'<(\w+)>\s*(\{[^}]+\})\s*</\1>'
        for match in re.finditer(pattern1, content, re.DOTALL):
            func_name = match.group(1)
            args_str = match.group(2)
            try:
                # Validate JSON
                json.loads(args_str)
                tool_calls.append({
                    "id": f"call_{id(self)}_{int(time.time()*1000)}",
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": args_str,
                    },
                })
            except json.JSONDecodeError:
                continue
        
        # Pattern 2: <function_name><param>value</param>...</function_name>
        pattern2 = r'<(\w+)>(.+?)</\1>'
        for match in re.finditer(pattern2, content, re.DOTALL):
            func_name = match.group(1)
            inner = match.group(2)
            
            # Skip if it looks like Pattern 1 (JSON)
            if inner.strip().startswith('{'):
                continue
            
            # Extract parameters
            params = {}
            param_matches = re.findall(r'<(\w+)>([^<]+)</\1>', inner)
            for param_name, param_value in param_matches:
                params[param_name] = param_value.strip()
            
            if params:  # Only add if we found parameters
                tool_calls.append({
                    "id": f"call_{id(self)}_{int(time.time()*1000)}",
                    "type": "function",
                    "function": {
                        "name": func_name,
                        "arguments": json.dumps(params),
                    },
                })

        # Pattern 3: Qwen format - <function=name> <parameter=key>val</parameter> </function>
        qwen_pattern = r'\<function=\w+\>\s*(?:<parameter=\w+>([^<]*)</parameter>)+\s*</function>'
        for match in re.finditer(qwen_pattern, content, re.DOTALL):
            func_name_match = re.search(r'\<function=(\w+)\>', match.group(0))
            if func_name_match:
                func_name = func_name_match.group(1)
                params = {}
                for param_match in re.finditer(r'<parameter=(\w+)>([^<]*)</parameter>', match.group(0)):
                    params[param_match.group(1)] = param_match.group(2).strip()
                if params:
                    tool_calls.append({
                        "id": f"call_{id(self)}_{int(time.time()*1000)}",
                        "type": "function",
                        "function": {
                            "name": func_name,
                            "arguments": json.dumps(params),
                        },
                    })
        
        return tool_calls

    # ── Tool dispatch ─────────────────────────────────────────────────────────
    # Tools whose results are transient in stream mode (screen is shown live to
    # the user; storing full captures in the conversation wastes context).
    _STREAM_EPHEMERAL = frozenset({"capture_screen", "send_keys", "send_ctrl"})

    def _execute_tool_calls(self, tool_calls: List[Dict]):
        """Run every tool call in *tool_calls* and append result messages to conv.

        VERIFICATION: Checks that tools actually succeeded before marking complete.
        """
        in_stream = self.state.is_stream_mode()
        execution_results = []  # Track success/failure for verification

        for tc in tool_calls:
            name = tc["function"]["name"]
            
            # Debug: Log what we're executing
            self.state.push_log("debug", f"Executing tool: {name}")
            self.state.push_log("debug", f"  Arguments raw: {tc['function'].get('arguments')}")

            # Fix: Generate and save ID back to tc dictionary
            if not tc.get("id"):
                tc["id"] = f"call_{id(self)}_{int(time.time()*1000)}"
            tool_call_id = tc["id"]

            # Fix: Handle both string and already-parsed dict arguments
            args_raw = tc["function"]["arguments"]
            try:
                if isinstance(args_raw, str):
                    args = json.loads(args_raw)
                else:
                    args = args_raw  # Already parsed
            except Exception:
                error_msg = f"Malformed JSON arguments for {name}: {str(args_raw)[:100]}"
                self.state.push_log("error", error_msg)
                self.conv.append({
                    "role":         "tool",
                    "tool_call_id": tool_call_id,
                    "content":      f"ERROR: {error_msg}. Please check your tool call syntax.",
                })
                execution_results.append((name, False, error_msg))
                continue
            
            # Debug: Log parsed arguments
            self.state.push_log("debug", f"  Arguments parsed: {args}")

            self.state.set_status("working")
            result = self.executor.run(name, args)

            # VERIFICATION: Check if tool actually succeeded
            success = not result.startswith("ERROR:")
            execution_results.append((name, success, result[:200]))

            # In stream mode, screen/interaction results are shown live to the user.
            # Truncate them aggressively so they don't balloon the context window.
            if in_stream and name in self._STREAM_EPHEMERAL:
                result_content = str(result)[:300] + "\n[full output shown live in stream view — omitted from context]"
            else:
                result_content = str(result)[:8000]

            self.conv.append({
                "role":         "tool",
                "tool_call_id": tool_call_id,
                "content":      result_content,
            })

            # Log verification result
            if success:
                self.state.push_log("info", f"✓ Tool '{name}' executed successfully")
            else:
                self.state.push_log("error", f"✗ Tool '{name}' FAILED: {result[:100]}")
                # Push warning to chat so Jerry knows it failed
                self.state.push_chat("dao", f"⚠️ Tool '{name}' failed. I need to try again or use a different approach.", expression="bummed")

        # Update token count after all tool calls executed
        self._update_token_count()
        
        # Return execution summary for verification
        return execution_results

    # ── Multi-modal message processing ─────────────────────────────────────────
    def _process_multimodal_messages(self, messages: List[Dict]) -> List[Dict]:
        """Process messages to handle image data for multi-modal models.
        
        Converts tool results with [IMAGE: ...] markers into multi-modal format.
        llama-server expects images as data URLs in the content array.
        
        Args:
            messages: List of conversation messages
        
        Returns:
            Messages with images converted to multi-modal format
        """
        import re
        
        processed = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content", "")
            
            # Check if this is a tool result with image data
            if role == "tool" and isinstance(content, str) and "[IMAGE:" in content:
                # Extract image path and base64 data
                image_match = re.search(r'\[IMAGE: ([^\]]+)\]', content)
                base64_match = re.search(r'Base64 data: ([a-zA-Z0-9+/=]+)', content)
                format_match = re.search(r'Format: (\w+)', content)
                
                if image_match and base64_match:
                    image_path = image_match.group(1)
                    image_data = base64_match.group(1)
                    image_format = format_match.group(1).lower() if format_match else "png"
                    
                    # Convert to multi-modal format for llama-server
                    # Content becomes an array with text and image_url objects
                    msg = {
                        "role": "tool",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Image loaded: {image_path}"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_data}"
                                }
                            }
                        ],
                        "tool_call_id": msg.get("tool_call_id")
                    }
            
            processed.append(msg)
        
        return processed

    # ── API call with streaming ────────────────────────────────────────────────
    def _call_model_streaming(self) -> Dict:
        """Call the model with streaming support for real-time output.
        
        Includes retry logic for 400 errors with conversation cleanup.
        """
        max_retries = 2
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Always inject cwd so the model knows its filesystem position.
                # After a conversation trim the model would otherwise lose track of
                # which directory the executor is currently in.
                cwd = self.state.get_cwd()
                context_note = f"\n[cwd: {cwd}]"

                # If in stream mode, also append the live screen capture
                if self.state.is_stream_mode():
                    try:
                        from .screen_stream import get_screen_streamer
                        streamer = get_screen_streamer()
                        if streamer:
                            screen = streamer.capture_screen()
                            # Check if screen has actual content (not error message or empty)
                            if screen and len(screen) > 50 and not screen.startswith("ERROR"):
                                context_note += (
                                    f"\n\n[CURRENT TERMINAL SCREEN - View only, don't save to memory:]\n"
                                    f"{screen}\n[END SCREEN]\n"
                                )
                    except Exception:
                        pass

                # Build messages — append context note to the last user message only
                # (not saved to self.conv, so it doesn't pollute history)
                messages = self.conv[:]
                if context_note and messages and messages[-1].get("role") == "user":
                    messages[-1] = {
                        "role":    "user",
                        "content": messages[-1]["content"] + context_note,
                    }

                # Process messages for multi-modal support (images)
                messages = self._process_multimodal_messages(messages)

                # DEBUG: Log what we're sending on retry
                if attempt > 0:
                    self.state.push_log("debug", f"API call retry attempt {attempt + 1}/{max_retries}")

                # Log conversation state for debugging
                tool_call_count = sum(1 for m in messages if m.get('tool_calls'))
                self.state.push_log("debug", f"Sending {len(messages)} messages ({tool_call_count} with tool_calls), tools={len(TOOLS)}")
                
                # DEBUG: Log tools being sent
                tool_names = [t['function']['name'] for t in TOOLS[:5]]
                self.state.push_log("debug", f"First 5 tools: {', '.join(tool_names)}...")
                
                # DEBUG: Log first/last few messages to see what we're sending
                if messages:
                    first_msg = messages[0].get('role', 'unknown')
                    last_msg = messages[-1].get('role', 'unknown')
                    last_content = messages[-1].get('content', '')[:200] if messages else ''
                    self.state.push_log("debug", f"First msg role: {first_msg}, Last msg role: {last_msg}")
                    self.state.push_log("debug", f"Last msg content preview: {last_content}...")
                
                r = requests.post(
                    AGENT_URL,
                    json={
                        "messages":    messages,
                        "tools":       TOOLS,
                        "tool_choice": "auto",
                        "max_tokens":  MAX_TOKENS,
                        "temperature": TEMPERATURE,
                        "stream": True,
                    },
                    stream=True,
                )
                r.raise_for_status()
                
                self.state.push_log("debug", "API request sent successfully, waiting for response...")

                # Accumulate streaming chunks
                accumulated = {"role": "assistant", "content": "", "tool_calls": []}
                thinking_content = ""  # Accumulate thinking separately
                response_content = ""  # Accumulate response separately

                # Set status to streaming when we start receiving data
                self.state.set_status("streaming")

                # Iterate over streaming chunks
                for line in r.iter_lines():
                    # Check for user interrupt after each chunk
                    # Quick lock/unlock to avoid deadlock with UI render
                    has_inbox = False
                    try:
                        self.state._lock.acquire()
                        has_inbox = len(self.state.inbox) > 0
                    finally:
                        self.state._lock.release()
                    
                    if has_inbox:
                        self.state.push_log("debug", "User interrupted streaming!")
                        self.state.set_status("interrupted by user")
                        try:
                            r.close()  # Stop the stream
                        except:
                            pass
                        return accumulated  # Return partial response

                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str.strip() == '[DONE]':
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data.get('choices', [{}])[0].get('delta', {})

                                # Handle thinking/reasoning tokens (Qwen3.5 enable_thinking)
                                if delta.get('reasoning_content'):
                                    thinking_chunk = delta['reasoning_content']
                                    thinking_content += thinking_chunk
                                    # Stream thinking to chat in thinking color
                                    self.state.push_chat("dao", thinking_content, expression="thinking", replace_last=True)
                                    # Set thinking face
                                    try:
                                        from .faces_display import get_face_display
                                        face = get_face_display()
                                        face.set_emotion("thinking")
                                    except Exception:
                                        pass  # Ignore if face not available

                                # Handle normal response content
                                if delta.get('content'):
                                    chunk = delta['content']
                                    response_content += chunk
                                    accumulated['content'] += chunk

                                    # Reset face to neutral when response starts
                                    if thinking_content:
                                        try:
                                            from .faces_display import get_face_display
                                            face = get_face_display()
                                            face.set_emotion("neutral")
                                        except Exception:
                                            pass

                                    # Stream response to chat normally
                                    self.state.push_chat("dao", response_content, replace_last=True)

                                    # Parse emotion tags from streaming content
                                    # This will update the face display in real-time
                                    try:
                                        from .faces_display import get_face_display
                                        face = get_face_display()
                                        face.parse_emotion_tags(chunk)
                                    except Exception:
                                        pass  # Ignore face parsing errors during stream

                                # Accumulate tool calls
                                if delta.get('tool_calls'):
                                    for tc in delta['tool_calls']:
                                        idx = tc.get('index', 0)
                                        if len(accumulated['tool_calls']) <= idx:
                                            accumulated['tool_calls'].append({
                                                'id': '',
                                                'type': 'function',
                                                'function': {'name': '', 'arguments': ''},
                                            })
                                        tc_acc = accumulated['tool_calls'][idx]
                                        # Fix: Use += for accumulation (not =), handle None values safely
                                        tc_id = tc.get('id')
                                        if tc_id:
                                            tc_acc['id'] += str(tc_id)
                                        tc_name = tc.get('function', {}).get('name')
                                        if tc_name:
                                            tc_acc['function']['name'] += str(tc_name)
                                        # Fix: Handle both string and dict/list arguments (llama-server sends parsed objects)
                                        if tc.get('function', {}).get('arguments'):
                                            args_val = tc['function']['arguments']
                                            if isinstance(args_val, str):
                                                tc_acc['function']['arguments'] += args_val
                                            elif isinstance(args_val, (dict, list)):
                                                tc_acc['function']['arguments'] = json.dumps(args_val)

                            except json.JSONDecodeError as e:
                                self.state.push_log("error", f"Stream JSON decode error: {e}")
                                continue

                # Combine thinking and response for conversation history (without markers)
                accumulated['content'] = thinking_content + response_content

                # CRITICAL: Filter out incomplete tool calls (missing id or name)
                # These cause 400 errors when sent back to llama-server
                valid_tool_calls = []
                for tc in accumulated['tool_calls']:
                    tc_id = tc.get('id', '')
                    tc_name = tc.get('function', {}).get('name', '')

                    # Generate ID if missing (streaming sometimes doesn't send id in first chunk)
                    if not tc_id:
                        tc_id = f"call_{int(time.time()*1000)}_{len(valid_tool_calls)}"
                        tc['id'] = tc_id

                    if not tc_name:
                        self.state.push_log("debug", f"Filtering incomplete tool call: id='{tc_id}', name='{tc_name}'")
                        continue

                    # Ensure arguments exists (empty dict if missing)
                    if 'arguments' not in tc.get('function', {}):
                        tc['function']['arguments'] = {}

                    valid_tool_calls.append(tc)

                accumulated['tool_calls'] = valid_tool_calls

                # Log what we're returning
                self.state.push_log("debug", f"Returning: {len(accumulated['content'])} chars, {len(accumulated['tool_calls'])} valid tool calls")

                # Return accumulated response - caller adds SINGLE message to self.conv
                # This prevents conversation explosion from streaming tokens
                return accumulated

            except Exception as e:
                error_msg = str(e)
                last_error = e

                # Log the error
                self.state.push_log("info", f"Streaming failed (attempt {attempt + 1}/{max_retries}): {error_msg}")

                # If it's a 400 error, try cleaning conversation and retrying
                if "400" in error_msg and attempt < max_retries - 1:
                    self.state.push_log("info", "400 error - cleaning conversation and retrying...")
                    # Trim conversation more aggressively on 400 errors
                    self._trim_conv_aggressive()
                    continue  # Retry with cleaned conversation

                # For other errors or final attempt, use fallback
                if attempt == max_retries - 1:
                    self.state.push_log("error", f"All {max_retries} retry attempts failed, using fallback")
                    return self._call_model()

                # Wait before retry
                time.sleep(1.0 * (attempt + 1))

        # Should not reach here, but just in case
        self.state.push_log("error", f"Streaming failed after retries, using fallback")
        return self._call_model()

    # ── API call (fallback) ────────────────────────────────────────────────────
    def _call_model(self) -> Dict:
        """Call the model without streaming."""
        try:
            r = requests.post(
                AGENT_URL,
                json={
                    "messages":    self.conv,
                    "tools":       TOOLS,
                    "tool_choice": "auto",
                    "max_tokens":  MAX_TOKENS,
                    "temperature": TEMPERATURE,
                },
            )
            r.raise_for_status()
            msg = r.json()["choices"][0]["message"]
            
            # Validate tool calls in non-streaming response too
            tool_calls = msg.get("tool_calls") or []
            valid_tool_calls = []
            for tc in tool_calls:
                tc_id = tc.get('id', '')
                tc_name = tc.get('function', {}).get('name', '')
                if tc_id and tc_name:
                    valid_tool_calls.append(tc)
                else:
                    self.state.push_log("debug", f"Fallback: filtering incomplete tool call: id='{tc_id}', name='{tc_name}'")
            
            if valid_tool_calls:
                msg["tool_calls"] = valid_tool_calls
                self.state.push_log("debug", f"Fallback: {len(valid_tool_calls)} valid tool calls")
            else:
                msg["tool_calls"] = []
            
            return msg
        except Exception as e:
            self.state.push_log("error", f"Model call failed: {e}")
            raise

    # ── Trim conversation to avoid context overflow ────────────────────────────
    def _trim_conv(self):
        """Trim conversation history to prevent context overflow.

        Keeps system prompt + last CONV_TRIM messages.
        Handles the case where a multi-tool assistant turn was cut: all orphaned
        tool results at the start of the retained window share the same parent
        assistant message, which is prepended so the API never sees bare tool
        results without their matching call.
        """
        if len(self.conv) > CONV_TRIM + 1:
            trimmed = [self.conv[0]]          # Always keep system prompt
            recent  = self.conv[-CONV_TRIM:]  # Window we want to keep

            # Collect the tool_call_ids of every orphaned tool result at the start
            # of `recent` — a multi-tool response can produce several consecutive
            # tool messages that all belong to one assistant turn.
            orphan_ids: set = set()
            i = 0
            while i < len(recent) and recent[i].get("role") == "tool":
                cid = recent[i].get("tool_call_id")
                if cid:
                    orphan_ids.add(cid)
                i += 1

            # Find the single assistant message that owns all those orphaned results
            # and prepend it, keeping `recent` fully intact.
            if orphan_ids:
                for j in range(len(self.conv) - len(recent) - 1, -1, -1):
                    msg = self.conv[j]
                    if msg.get("role") == "assistant" and msg.get("tool_calls"):
                        owned = {tc.get("id") for tc in msg["tool_calls"]}
                        if orphan_ids & owned:   # Any overlap → this is the parent
                            trimmed.append(msg)
                            break

            trimmed.extend(recent)
            self.conv = trimmed

    def _trim_conv_aggressive(self, keep_last=20):
        """Aggressive conversation trim for error recovery.
        
        Used when 400 errors occur - trims to keep_last messages plus system prompt.
        This is more aggressive than normal _trim_conv to recover from bad state.
        
        Args:
            keep_last: Number of recent messages to keep (default: 20)
        """
        if len(self.conv) <= keep_last + 1:
            return  # Already small enough
        
        self.state.push_log("debug", f"Aggressive trim: keeping last {keep_last} messages")
        
        # Keep system prompt + last N messages
        trimmed = [self.conv[0]] + self.conv[-keep_last:]
        self.conv = trimmed