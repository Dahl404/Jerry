#!/usr/bin/env python3
"""Dao — Autonomous Agent with Streaming"""

import time
import json
import requests
import threading
from typing import Dict, List
from .config import AGENT_URL, MAX_TOKENS, TEMPERATURE, CONV_TRIM, TOOLS, SYSTEM_PROMPT, CYCLE_SLEEP, DAO_BASE
from .worker import strip_think
from .models import State
from .executor import Executor


class Agent:
    """Autonomous agent with streaming output."""

    def __init__(self, state: State, executor: Executor, tui=None):
        self.state    = state
        self.executor = executor
        self.tui      = tui  # Optional: for updating token count
        # Format SYSTEM_PROMPT here so {dao_base} resolves to the actual path.
        # Without this the model sees the literal string "{dao_base}" in its prompt.
        self.conv:    List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT.format(dao_base=DAO_BASE)}]
        self._stop    = False
        self._is_thinking = False

    def stop(self):
        self._stop = True

    # ── Main loop (runs in background thread) ──────────────────────────────────
    def run(self):
        self.state.set_status("idle")
        self.state.set_phase("idle")
        last_action_time = time.time()  # Initialize to NOW, not 0.0 (prevents immediate idle trigger)
        min_cycle_gap = 3.0
        last_content = ""  # Track last activity for idle reflection
        last_task_text = None  # Track last task #0 to avoid duplicate prompts (BUG-C fix)

        while not self._stop:
            try:
                # Check inbox for user messages - always priority
                msgs = self.state.drain_inbox()
                if msgs:
                    for m in msgs:
                        # Check if there are any todos already
                        with self.state._lock:
                            has_pending = any(not t.done for t in self.state.todos)

                        if not has_pending:
                            # PHASE 1: No pending todos — ask model to plan and create todos.
                            # Combine user message + planning instructions into ONE user message
                            # to avoid consecutive user messages which break the API. (BUG-B fix)
                            combined = (
                                f"{m}\n\n"
                                f"[PHASE 1 - PLANNING] Please:\n"
                                f"1. Write a brief plain-text plan\n"
                                f"2. Add ALL tasks in ONE todo_add call: "
                                f"todo_add(tasks=[\"Task 1\", \"Task 2\", ...])\n"
                                f"Do NOT start executing yet."
                            )
                            self.conv.append({"role": "user", "content": combined})
                            last_task_text = None  # Reset task tracking on new user message
                            self.state.set_phase("planning")
                        else:
                            # Has pending todos — user is providing extra context; continue execution
                            pending_count = sum(1 for t in self.state.todos if not t.done)
                            exec_prompt = (
                                f"[user message] {m}\n\n"
                                f"You have {pending_count} pending todos. Continue working on task #0.\n"
                                f"Call todo_complete(index=0) when done."
                            )
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

                    # Only inject a new prompt when the task changes (BUG-C fix).
                    # This prevents flooding the conversation with duplicate
                    # "work on task #0" messages every cycle, which caused the
                    # model to re-plan and create looping duplicate todos.
                    if current_task != last_task_text:
                        last_task_text = current_task

                        if last_tool:
                            prompt = (
                                f"[todo] Task #0: {current_task}\n"
                                f"Last action: {last_tool}\n"
                                f"Pending: {len(pending)} | Completed: {completed_count}\n"
                                f"Continue working — take as many turns as needed.\n"
                                f"When COMPLETE, call todo_complete(index=0).\n"
                                f"Do NOT start new tasks until this one is done."
                            )
                        elif completed_count > 0:
                            prompt = (
                                f"[todo] ✓ Completed: {completed_count} tasks\n"
                                f"Current task #0: {current_task}\n"
                                f"Remaining: {len(pending)} tasks\n"
                                f"Continue working — unlimited turns allowed.\n"
                                f"Call todo_complete(index=0) when this task is done.\n"
                                f"Next task will automatically become #0."
                            )
                        else:
                            prompt = (
                                f"[todo] Task #0: {current_task}\n"
                                f"Total: {len(pending)} tasks\n"
                                f"Work on this task — take all the turns you need.\n"
                                f"CRITICAL: Call todo_complete(index=0) when finished.\n"
                                f"Do NOT add new todos — complete existing list first."
                            )

                        self.conv.append({"role": "user", "content": prompt})

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
                # Check for user interruption at start of each turn (don't drain - let main loop handle)
                with self.state._lock:
                    has_pending_msgs = len(self.state.inbox) > 0
                
                if has_pending_msgs:
                    # User wants to interrupt - exit cycle so main loop can handle it
                    # Main loop will drain inbox and add user message to conversation
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

                # No tool calls → text response (already streamed); add to conv and stop.
                if not tool_calls:
                    self.conv.append({"role": "assistant", "content": msg.get("content")})
                    self._update_token_count()  # Update after text response
                    break

                # Loop detection — returns True and breaks if stuck
                if self._check_tool_loop(tool_calls, recent_tool_calls):
                    return

                # Append the assistant turn (with tool_calls) to conversation
                self.conv.append({
                    "role":       "assistant",
                    "content":    msg.get("content"),
                    "tool_calls": tool_calls,
                })

                # Execute every tool call and append results
                self._execute_tool_calls(tool_calls)

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

    # ── Tool dispatch ─────────────────────────────────────────────────────────
    # Tools whose results are transient in stream mode (screen is shown live to
    # the user; storing full captures in the conversation wastes context).
    _STREAM_EPHEMERAL = frozenset({"capture_screen", "send_keys", "send_ctrl"})

    def _execute_tool_calls(self, tool_calls: List[Dict]):
        """Run every tool call in *tool_calls* and append result messages to conv."""
        in_stream = self.state.is_stream_mode()

        for tc in tool_calls:
            name         = tc["function"]["name"]
            tool_call_id = tc.get("id") or f"gen_{id(self)}_{time.time()}"

            try:
                args = json.loads(tc["function"]["arguments"])
            except Exception:
                error_msg = f"Malformed JSON arguments for {name}: {tc['function']['arguments'][:100]}"
                self.state.push_log("error", error_msg)
                self.conv.append({
                    "role":         "tool",
                    "tool_call_id": tool_call_id,
                    "content":      f"ERROR: {error_msg}. Please check your tool call syntax.",
                })
                continue

            self.state.set_status("working")
            result = self.executor.run(name, args)

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
        
        # Update token count after all tool calls executed
        self._update_token_count()

    # ── API call with streaming ────────────────────────────────────────────────
    def _call_model_streaming(self) -> Dict:
        """Call the model with streaming support for real-time output.
        
        Uses a 120 second timeout to prevent permanent hangs.
        """
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

            r = requests.post(
                AGENT_URL,
                json={
                    "messages":    messages,
                    "tools":       TOOLS,
                    "tool_choice": "auto",
                    "max_tokens":  MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "stream": True,
                    "enable_thinking": True,
                },
                stream=True,
            )
            r.raise_for_status()

            # Accumulate streaming chunks
            accumulated = {"role": "assistant", "content": "", "tool_calls": []}
            thinking_content = ""  # Accumulate thinking separately
            response_content = ""  # Accumulate response separately

            # Set status to streaming when we start receiving data
            self.state.set_status("streaming")

            for line in r.iter_lines():
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

                            # Handle normal response content
                            if delta.get('content'):
                                chunk = delta['content']
                                response_content += chunk
                                accumulated['content'] += chunk
                                # Stream response to chat normally
                                self.state.push_chat("dao", response_content, replace_last=True)

                                # Parse emotion tags from streaming content
                                # This will update the face display in real-time
                                try:
                                    from .faces_display import parse_and_set_emotion
                                    parse_and_set_emotion(chunk)
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
                                    if tc.get('id'):
                                        tc_acc['id'] = tc['id']
                                    if tc.get('function', {}).get('name'):
                                        tc_acc['function']['name'] = tc['function']['name']
                                    if tc.get('function', {}).get('arguments'):
                                        tc_acc['function']['arguments'] += tc['function']['arguments']
                        except json.JSONDecodeError as e:
                            self.state.push_log("error", f"Stream JSON decode error: {e}")
                            continue

            # Combine thinking and response for conversation history (without markers)
            accumulated['content'] = thinking_content + response_content

            # Return accumulated response - caller adds SINGLE message to self.conv
            # This prevents conversation explosion from streaming tokens
            return accumulated
        except Exception as e:
            self.state.push_log("info", f"Streaming failed, using fallback: {e}")
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
                    "enable_thinking": True,
                },
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]
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
