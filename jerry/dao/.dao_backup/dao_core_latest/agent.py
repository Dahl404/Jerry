#!/usr/bin/env python3
"""Dao — Autonomous Agent with Streaming"""

import time
import json
import requests
import threading
from typing import Dict, List
from .config import AGENT_URL, MAX_TOKENS, TEMPERATURE, CONV_TRIM, TOOLS, SYSTEM_PROMPT, CYCLE_SLEEP
from .worker import strip_think
from .models import State
from .executor import Executor


class Agent:
    """Autonomous agent with streaming output."""

    def __init__(self, state: State, executor: Executor):
        self.state    = state
        self.executor = executor
        self.conv:    List[Dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._stop    = False
        self._is_thinking = False

    def stop(self):
        self._stop = True

    # ── Main loop (runs in background thread) ──────────────────────────────────
    def run(self):
        self.state.set_status("ready")
        last_action_time = 0.0
        min_cycle_gap = 3.0  # Minimum seconds between autonomous cycles

        while not self._stop:
            try:
                # Check inbox for user messages - always priority
                msgs = self.state.drain_inbox()
                if msgs:
                    for m in msgs:
                        self.conv.append({"role": "user", "content": m})
                    self._cycle()
                    last_action_time = time.time()
                    continue

                # Check for pending todos
                with self.state._lock:
                    pending = [t for t in self.state.todos if not t.done]
                    completed_count = sum(1 for t in self.state.todos if t.done)

                if pending:
                    # Respect minimum gap between cycles
                    if time.time() - last_action_time < min_cycle_gap:
                        time.sleep(0.3)
                        continue

                    # Get context from recent conversation
                    recent = self.conv[-5:] if len(self.conv) > 5 else self.conv
                    last_tool = ""
                    last_content = ""
                    for msg in reversed(recent):
                        if msg.get("role") == "assistant":
                            if msg.get("tool_calls"):
                                last_tool = msg["tool_calls"][0]["function"]["name"]
                            if msg.get("content"):
                                last_content = msg["content"][:100]
                            break

                    # Build continuation prompt with full context
                    current_task = pending[0].text
                    tasks_str = " | ".join(f"#{i}: {t.text}" for i, t in enumerate(pending[:5]))
                    
                    if last_tool:
                        prompt = (
                            f"[todo] Current task: #{0} - {current_task}\n"
                            f"Last action: {last_tool}\n"
                            f"Remaining ({len(pending)}): {tasks_str}\n"
                            f"Continue working on current task. You can use multiple tools. "
                            f"When this task is complete, call todo_complete with index 0."
                        )
                    elif completed_count > 0:
                        prompt = (
                            f"[todo] Completed: {completed_count} tasks\n"
                            f"Current task: #{0} - {current_task}\n"
                            f"Remaining ({len(pending)}): {tasks_str}\n"
                            f"Continue working. Use as many tools as needed. "
                            f"Mark complete with todo_complete(index=0) when done."
                        )
                    else:
                        prompt = (
                            f"[todo] Starting work.\n"
                            f"Current task: #{0} - {current_task}\n"
                            f"All tasks ({len(pending)}): {tasks_str}\n"
                            f"Begin working on current task. Plan your approach, "
                            f"use tools as needed, mark complete when finished."
                        )

                    self.conv.append({"role": "user", "content": prompt})
                    self._cycle(max_turns=50)  # Allow more turns for complex tasks
                    last_action_time = time.time()
                else:
                    # No todos - idle
                    time.sleep(0.5)

            except Exception as e:
                self.state.push_log("error", f"Agent loop: {e}")
                self.state.set_status("error — retrying")
                time.sleep(3.0)

    # ── Reasoning cycle (tool-calling loop) ────────────────────────────────────
    def _cycle(self, max_turns: int = 30):
        self.state.set_status("thinking…")
        self._is_thinking = True

        try:
            for turn in range(max_turns):
                self._trim_conv()

                # ── Call model ───────────────────────────────────────────────────
                try:
                    msg = self._call_model_streaming()
                except Exception as e:
                    self.state.push_log("error", f"Model call failed: {e}")
                    self.state.set_status("model error")
                    return

                content    = strip_think(msg.get("content") or "")
                tool_calls = msg.get("tool_calls") or []

                # No tool calls → text response to chat
                if not tool_calls:
                    if content:
                        self.state.push_chat("dao", content)
                    self.conv.append({"role": "assistant", "content": msg.get("content")})
                    break

                # Has tool calls → log and execute
                self.conv.append({
                    "role":       "assistant",
                    "content":    msg.get("content"),
                    "tool_calls": tool_calls,
                })

                for tc in tool_calls:
                    name = tc["function"]["name"]
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except Exception:
                        args = {}
                    self.state.set_status(f"→ {name}")
                    result = self.executor.run(name, args)
                    tool_call_id = tc.get("id") or f"gen_{id(self)}_{time.time()}"
                    self.conv.append({
                        "role":         "tool",
                        "tool_call_id": tool_call_id,
                        "content":      str(result)[:8000],
                    })

        finally:
            self._is_thinking = False
            self.state.set_status("ready")

    # ── API call with streaming ────────────────────────────────────────────────
    def _call_model_streaming(self) -> Dict:
        """Call the model with streaming support for real-time output."""
        try:
            r = requests.post(
                AGENT_URL,
                json={
                    "messages":    self.conv,
                    "tools":       TOOLS,
                    "tool_choice": "auto",
                    "max_tokens":  MAX_TOKENS,
                    "temperature": TEMPERATURE,
                    "stream": True,
                },
                stream=True,
            )
            r.raise_for_status()

            # Accumulate streaming chunks
            accumulated = {"role": "assistant", "content": "", "tool_calls": []}

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

                            # Accumulate content
                            if delta.get('content'):
                                accumulated['content'] += delta['content']

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

            return accumulated
        except Exception as e:
            self.state.push_log("info", f"Streaming failed, using fallback: {e}")
            return self._call_model()

    # ── API call (fallback) ────────────────────────────────────────────────────
    def _call_model(self) -> Dict:
        """Call the model without streaming.

        No timeout - holds connection indefinitely until response or closure.
        """
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
        return r.json()["choices"][0]["message"]

    # ── Trim conversation to avoid context overflow ────────────────────────────
    def _trim_conv(self):
        if len(self.conv) > CONV_TRIM + 1:
            self.conv = [self.conv[0]] + self.conv[-CONV_TRIM:]
