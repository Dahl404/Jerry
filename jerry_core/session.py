#!/usr/bin/env python3
"""Jerry — Session Manager for Shutdown, Summaries, and Archival"""

import os
import json
from datetime import datetime
from .models import State
from .config import SUMMARY_DIR, LOGS_DIR, PERSONA_DIR, JERRY_BASE


class SessionManager:
    """Manages session shutdown, context compression, and archival."""

    def __init__(self, state: State):
        self.state = state

    def on_shutdown(self):
        """Called when Jerry is shutting down. Compresses context, saves persona, archives logs."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Create directories
        os.makedirs(SUMMARY_DIR, exist_ok=True)
        os.makedirs(LOGS_DIR, exist_ok=True)
        os.makedirs(PERSONA_DIR, exist_ok=True)

        # 1. Compress context into dated summary
        self._save_summary(timestamp)

        # 2. Save persona document
        self._save_persona(timestamp)

        # 3. Archive raw logs
        self._archive_logs(timestamp)

    def _save_summary(self, timestamp: str):
        """Compress conversation and todos into a dated summary."""
        summary_lines = []
        summary_lines.append(f"=== Jerry Session Summary ===")
        summary_lines.append(f"Date: {datetime.now().isoformat()}")
        summary_lines.append(f"Session Start: {self.state.session_start}")
        summary_lines.append("")

        # Conversation summary
        summary_lines.append("━━━ Conversation Summary ━━━")
        chat = self.state.chat[:]
        if chat:
            summary_lines.append(f"Total messages: {len(chat)}")
            user_msgs = [m for m in chat if m.role == "user"]
            jerry_msgs = [m for m in chat if m.role == "jerry"]
            summary_lines.append(f"  User messages: {len(user_msgs)}")
            summary_lines.append(f"  Jerry messages: {len(jerry_msgs)}")
            summary_lines.append("")

            # Last 10 messages
            summary_lines.append("Recent messages:")
            for m in chat[-10:]:
                summary_lines.append(f"  [{m.ts}] {m.role}: {m.text[:100]}")
        else:
            summary_lines.append("No conversation in this session.")
        summary_lines.append("")

        # Todo summary
        summary_lines.append("━━━ Todo Summary ━━━")
        todos = self.state.todos[:]
        if todos:
            completed = [t for t in todos if t.done]
            pending = [t for t in todos if not t.done]
            summary_lines.append(f"Total todos: {len(todos)}")
            summary_lines.append(f"  Completed: {len(completed)}")
            summary_lines.append(f"  Pending: {len(pending)}")
            summary_lines.append("")
            
            if completed:
                summary_lines.append("Completed:")
                for t in completed:
                    summary_lines.append(f"  ✓ {t.text}")
            
            if pending:
                summary_lines.append("Pending:")
                for t in pending:
                    summary_lines.append(f"  · {t.text}")
        else:
            summary_lines.append("No todos in this session.")
        summary_lines.append("")

        # Activity summary
        summary_lines.append("━━━ Activity Summary ━━━")
        log = self.state.log[:]
        if log:
            summary_lines.append(f"Total log entries: {len(log)}")
            by_kind = {}
            for e in log:
                by_kind[e.kind] = by_kind.get(e.kind, 0) + 1
            for kind, count in sorted(by_kind.items()):
                summary_lines.append(f"  {kind}: {count}")
        else:
            summary_lines.append("No activity logged.")

        # Write summary
        filepath = f"{SUMMARY_DIR}/session_{timestamp}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(summary_lines))
        
        self.state.push_log("system", f"Session summary saved → {filepath}")

    def _save_persona(self, timestamp: str):
        """Save the agent's core persona document based on conversation patterns."""
        persona_lines = []
        persona_lines.append(f"=== Jerry Persona Document ===")
        persona_lines.append(f"Generated: {datetime.now().isoformat()}")
        persona_lines.append("")

        # Analyze conversation patterns
        chat = self.state.chat[:]
        todos = self.state.todos[:]
        log = self.state.log[:]

        persona_lines.append("━━━ Behavioral Patterns ━━━")

        # Communication style
        jerry_msgs = [m for m in chat if m.role == "jerry"]
        if jerry_msgs:
            avg_len = sum(len(m.text) for m in jerry_msgs) / len(jerry_msgs)
            persona_lines.append(f"Average response length: {avg_len:.0f} characters")
            if avg_len > 200:
                persona_lines.append("Style: Detailed and thorough")
            elif avg_len > 80:
                persona_lines.append("Style: Balanced and informative")
            else:
                persona_lines.append("Style: Concise and direct")
        
        # Task orientation
        completed = [t for t in todos if t.done]
        if todos:
            completion_rate = len(completed) / len(todos) * 100
            persona_lines.append(f"Task completion rate: {completion_rate:.0f}%")
            if completion_rate > 80:
                persona_lines.append("Trait: Highly task-oriented and productive")
            elif completion_rate > 50:
                persona_lines.append("Trait: Moderately productive")
            else:
                persona_lines.append("Trait: Exploratory, prefers investigation over completion")

        # Tool usage patterns
        tool_logs = [e for e in log if e.kind == "tool"]
        if tool_logs:
            tool_names = {}
            for e in tool_logs:
                # Extract tool name from log
                if "(" in e.text:
                    name = e.text.split("(")[0]
                    tool_names[name] = tool_names.get(name, 0) + 1
            
            persona_lines.append("")
            persona_lines.append("Most used tools:")
            for name, count in sorted(tool_names.items(), key=lambda x: -x[1])[:5]:
                persona_lines.append(f"  {name}: {count} uses")

        # Expression usage
        expressions_used = set()
        for m in chat:
            if m.expression:
                expressions_used.add(m.expression)
        if expressions_used:
            persona_lines.append("")
            persona_lines.append("Expressive states used:")
            for expr in sorted(expressions_used):
                persona_lines.append(f"  {expr}")

        # Write persona document
        filepath = f"{PERSONA_DIR}/persona_{timestamp}.md"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(persona_lines))
        
        self.state.push_log("system", f"Persona document saved → {filepath}")

    def _archive_logs(self, timestamp: str):
        """Archive all raw logs as JSON for future analysis."""
        raw_logs = self.state.raw_logs[:]
        
        archive = {
            "session_start": self.state.session_start,
            "session_end": datetime.now().isoformat(),
            "logs": raw_logs,
            "metadata": {
                "total_entries": len(raw_logs),
                "chat_messages": len(self.state.chat),
                "todos": len(self.state.todos),
            }
        }
        
        filepath = f"{LOGS_DIR}/raw_logs_{timestamp}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(archive, f, indent=2, ensure_ascii=False)
        
        self.state.push_log("system", f"Raw logs archived → {filepath}")
