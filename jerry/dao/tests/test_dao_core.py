#!/usr/bin/env python3
"""
Comprehensive Test Suite for Dao Core Modules
Tests for: config, models, worker, executor, agent
"""

import unittest
import unittest.mock as mock
import os
import sys
import tempfile
import threading
import time
from datetime import datetime
from io import StringIO

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dao_core.config import (
    AGENT_URL, WORKER_URL, MAX_TOKENS, TEMPERATURE, CYCLE_SLEEP,
    LOG_LIMIT, CONV_TRIM, TOOLS, SYSTEM_PROMPT
)
from dao_core.models import State, LogEntry, ChatMsg, Todo, ts
from dao_core.worker import Worker, strip_think
from dao_core.executor import Executor


# =============================================================================
# Test Utilities
# =============================================================================

class TestUtilities(unittest.TestCase):
    """Test utility functions."""

    def test_ts_format(self):
        """Test timestamp format."""
        timestamp = ts()
        self.assertIsInstance(timestamp, str)
        # Should be in HH:MM:SS format
        self.assertRegex(timestamp, r'^\d{2}:\d{2}:\d{2}$')

    def test_strip_think_empty(self):
        """Test strip_think with empty string."""
        self.assertEqual(strip_think(""), "")
        self.assertEqual(strip_think(None), "")

    def test_strip_think_no_think(self):
        """Test strip_think with no think blocks."""
        text = "Hello world"
        self.assertEqual(strip_think(text), text)

    def test_strip_think_single_block(self):
        """Test strip_think removes single think block."""
        text = "<think>thinking</think>response"
        self.assertEqual(strip_think(text), "response")

    def test_strip_think_multiple_blocks(self):
        """Test strip_think removes multiple think blocks."""
        text = "<think>first</think>hello<think>second</think>world"
        self.assertEqual(strip_think(text), "helloworld")

    def test_strip_think_multiline(self):
        """Test strip_think with multiline think blocks."""
        text = """<think>
This is a long
thinking block
</think>
Actual response"""
        self.assertEqual(strip_think(text), "Actual response")


# =============================================================================
# Test Config Module
# =============================================================================

class TestConfig(unittest.TestCase):
    """Test configuration constants and tool definitions."""

    def test_api_urls(self):
        """Test API URLs are properly formatted."""
        self.assertTrue(AGENT_URL.startswith("http"))
        self.assertTrue(WORKER_URL.startswith("http"))
        self.assertIn("8080", AGENT_URL)
        self.assertIn("8081", WORKER_URL)

    def test_model_parameters(self):
        """Test model parameters are within reasonable ranges."""
        self.assertGreater(MAX_TOKENS, 0)
        self.assertLessEqual(TEMPERATURE, 2.0)
        self.assertGreaterEqual(TEMPERATURE, 0.0)
        self.assertGreater(CYCLE_SLEEP, 0)

    def test_limits(self):
        """Test limits are positive integers."""
        self.assertGreater(LOG_LIMIT, 0)
        self.assertGreater(CONV_TRIM, 0)

    def test_tools_structure(self):
        """Test tools have correct structure."""
        self.assertIsInstance(TOOLS, list)
        self.assertGreater(len(TOOLS), 0)
        
        for tool in TOOLS:
            self.assertIn("type", tool)
            self.assertIn("function", tool)
            func = tool["function"]
            self.assertIn("name", func)
            self.assertIn("description", func)
            self.assertIn("parameters", func)

    def test_tool_names_unique(self):
        """Test all tool names are unique."""
        names = [t["function"]["name"] for t in TOOLS]
        self.assertEqual(len(names), len(set(names)))

    def test_required_tool_parameters(self):
        """Test tools have required parameters defined."""
        for tool in TOOLS:
            func = tool["function"]
            params = func["parameters"]
            required = params.get("required", [])
            properties = params.get("properties", {})
            
            # All required params should exist in properties
            for req in required:
                self.assertIn(req, properties)

    def test_system_prompt_not_empty(self):
        """Test system prompt is defined and non-empty."""
        self.assertIsInstance(SYSTEM_PROMPT, str)
        self.assertGreater(len(SYSTEM_PROMPT), 0)


# =============================================================================
# Test Models Module
# =============================================================================

class TestModels(unittest.TestCase):
    """Test data models."""

    def test_log_entry_creation(self):
        """Test LogEntry creation."""
        entry = LogEntry(kind="test", text="hello")
        self.assertEqual(entry.kind, "test")
        self.assertEqual(entry.text, "hello")
        self.assertIsInstance(entry.ts, str)

    def test_chat_msg_creation(self):
        """Test ChatMsg creation."""
        msg = ChatMsg(role="user", text="hello")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.text, "hello")
        self.assertEqual(msg.expression, "")

    def test_chat_msg_with_expression(self):
        """Test ChatMsg with expression."""
        msg = ChatMsg(role="dao", text="hi", expression="<smiling>")
        self.assertEqual(msg.expression, "<smiling>")

    def test_todo_creation(self):
        """Test Todo creation."""
        todo = Todo(text="test task")
        self.assertEqual(todo.text, "test task")
        self.assertEqual(todo.priority, "medium")
        self.assertFalse(todo.done)

    def test_todo_with_priority(self):
        """Test Todo with different priorities."""
        for priority in ["high", "medium", "low"]:
            todo = Todo(text="task", priority=priority)
            self.assertEqual(todo.priority, priority)

    def test_state_initialization(self):
        """Test State initialization."""
        state = State()
        self.assertIsInstance(state.log, list)
        self.assertIsInstance(state.chat, list)
        self.assertIsInstance(state.todos, list)
        self.assertIsInstance(state.inbox, list)  # deque
        self.assertEqual(state.status, "starting")
        self.assertFalse(state.quit)
        self.assertIsNone(state.wfile)
        self.assertEqual(state.expression, "")

    def test_state_push_log(self):
        """Test State push_log."""
        state = State()
        state.push_log("test", "message")
        self.assertEqual(len(state.log), 1)
        self.assertEqual(state.log[0].kind, "test")
        self.assertEqual(state.log[0].text, "message")

    def test_state_push_log_limit(self):
        """Test State log respects limit."""
        state = State()
        # Push more than LOG_LIMIT entries
        for i in range(LOG_LIMIT + 100):
            state.push_log("test", f"msg {i}")
        # Should be trimmed to LOG_LIMIT
        self.assertLessEqual(len(state.log), LOG_LIMIT)

    def test_state_push_chat(self):
        """Test State push_chat."""
        state = State()
        state.push_chat("user", "hello")
        self.assertEqual(len(state.chat), 1)
        self.assertEqual(state.chat[0].role, "user")

    def test_state_add_inbox(self):
        """Test State add_inbox."""
        state = State()
        state.add_inbox("message 1")
        state.add_inbox("message 2")
        self.assertEqual(len(state.inbox), 2)

    def test_state_drain_inbox(self):
        """Test State drain_inbox."""
        state = State()
        state.add_inbox("msg1")
        state.add_inbox("msg2")
        drained = state.drain_inbox()
        self.assertEqual(len(drained), 2)
        self.assertEqual(len(state.inbox), 0)

    def test_state_set_status(self):
        """Test State set_status."""
        state = State()
        state.set_status("running")
        self.assertEqual(state.status, "running")

    def test_state_set_expression(self):
        """Test State set_expression."""
        state = State()
        state.set_expression("<thinking>")
        self.assertEqual(state.expression, "<thinking>")

    def test_state_snapshot(self):
        """Test State snapshot returns all fields."""
        state = State()
        state.push_log("test", "msg")
        state.push_chat("user", "hi")
        state.set_status("ready")
        
        log, chat, todos, status, wfile, expression = state.snapshot()
        self.assertEqual(len(log), 1)
        self.assertEqual(len(chat), 1)
        self.assertEqual(status, "ready")
        self.assertEqual(expression, "")

    def test_state_thread_safety(self):
        """Test State operations are thread-safe."""
        state = State()
        errors = []

        def add_logs():
            try:
                for i in range(100):
                    state.push_log("test", f"msg {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_logs) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(state.log), 500)


# =============================================================================
# Test Worker Module
# =============================================================================

class TestWorker(unittest.TestCase):
    """Test Worker model manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.state = State()
        self.worker = Worker(self.state)

    @mock.patch('dao_core.worker.requests.post')
    def test_worker_reset(self, mock_post):
        """Test worker reset clears history."""
        self.worker.hist = [{"role": "user", "content": "test"}]
        self.state.wfile = "/some/file"
        self.worker.reset()
        self.assertEqual(self.worker.hist, [])
        self.assertIsNone(self.state.wfile)

    @mock.patch('dao_core.worker.requests.post')
    def test_worker_load(self, mock_post):
        """Test worker load file."""
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Acknowledged"}}]
        }
        mock_post.return_value = mock_response

        content = "line1\nline2\nline3"
        result = self.worker.load("/test/file.py", content)

        self.assertEqual(len(self.worker.hist), 2)  # user + assistant
        self.assertEqual(self.state.wfile, "/test/file.py")
        self.assertIsInstance(result, str)

    @mock.patch('dao_core.worker.requests.post')
    def test_worker_query(self, mock_post):
        """Test worker query."""
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer"}}]
        }
        mock_post.return_value = mock_response

        # First load a file
        self.worker.hist = [{"role": "user", "content": "test"}]
        result = self.worker.query("What is this?")

        self.assertEqual(len(self.worker.hist), 3)  # initial + question + answer
        self.assertIsInstance(result, str)

    @mock.patch('dao_core.worker.requests.post')
    def test_worker_query_with_extra(self, mock_post):
        """Test worker query with extra context."""
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Answer"}}]
        }
        mock_post.return_value = mock_response

        self.worker.hist = [{"role": "user", "content": "test"}]
        result = self.worker.query("Question", "Extra context")

        self.assertEqual(len(self.worker.hist), 4)  # initial + extra + question + answer

    @mock.patch('dao_core.worker.requests.post')
    def test_worker_error_handling(self, mock_post):
        """Test worker handles API errors gracefully."""
        mock_post.side_effect = Exception("Connection failed")

        result = self.worker.query("test")
        self.assertIn("Worker error", result)

    def test_worker_load_counts_lines(self):
        """Test worker correctly counts lines."""
        content = "line1\nline2\nline3\nline4"
        # 4 lines (3 newlines + 1)
        line_count = content.count("\n") + 1
        self.assertEqual(line_count, 4)


# =============================================================================
# Test Executor Module
# =============================================================================

class TestExecutor(unittest.TestCase):
    """Test Executor tool dispatcher."""

    def setUp(self):
        """Set up test fixtures."""
        self.state = State()
        self.worker = mock.Mock(spec=Worker)
        self.executor = Executor(self.state, self.worker)

    def test_executor_run_logs_tool_call(self):
        """Test executor logs tool calls."""
        self.executor.run("reply", {"message": "test"})
        # Should have logged the tool call
        self.assertGreater(len(self.state.log), 0)

    def test_executor_run_handles_exception(self):
        """Test executor handles exceptions gracefully."""
        with mock.patch.object(self.executor, '_dispatch', side_effect=Exception("Boom")):
            result = self.executor.run("test_tool", {})
            self.assertIn("ERROR", result)

    def test_execute_command_success(self):
        """Test execute_command tool."""
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(
                stdout="output",
                stderr="",
                returncode=0
            )
            result = self.executor._sh("echo test")
            self.assertEqual(result, "output")

    def test_execute_command_timeout(self):
        """Test execute_command timeout handling."""
        with mock.patch('subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 60)):
            result = self.executor._sh("slow_command", timeout=60)
            self.assertIn("timed out", result)

    def test_execute_command_with_cwd(self):
        """Test execute_command with working directory."""
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(
                stdout="out",
                stderr="",
                returncode=0
            )
            self.executor._sh("ls", cwd="/tmp")
            mock_run.assert_called_once()
            call_kwargs = mock_run.call_args[1]
            self.assertEqual(call_kwargs['cwd'], "/tmp")

    def test_write_file(self):
        """Test write_file tool."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name

        try:
            content = "test content"
            result = self.executor._write(temp_path, content)
            
            with open(temp_path, 'r') as f:
                read_content = f.read()
            
            self.assertEqual(read_content, content)
            self.assertIn("Wrote", result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_write_file_creates_directories(self):
        """Test write_file creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = os.path.join(tmpdir, "nested", "dir", "file.txt")
            content = "test"
            
            result = self.executor._write(temp_path, content)
            
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, 'r') as f:
                self.assertEqual(f.read(), content)

    def test_read_file(self):
        """Test read_file tool."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_path = f.name

        try:
            result = self.executor._read(temp_path, 1, 500)
            self.assertIn("line1", result)
            self.assertIn("line2", result)
            self.assertIn("line3", result)
            # Should have line numbers
            self.assertIn("│", result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_read_file_with_range(self):
        """Test read_file with line range."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            for i in range(10):
                f.write(f"line{i+1}\n")
            temp_path = f.name

        try:
            result = self.executor._read(temp_path, 3, 3)
            self.assertIn("line3", result)
            self.assertIn("line4", result)
            self.assertIn("line5", result)
            self.assertNotIn("line1", result)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_replace_lines(self):
        """Test replace_lines tool."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_path = f.name

        try:
            result = self.executor._replace(temp_path, 2, 2, "replaced\n")
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn("line1", content)
            self.assertIn("replaced", content)
            self.assertIn("line3", content)
            self.assertNotIn("line2", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_insert_lines(self):
        """Test insert_lines tool."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\n")
            temp_path = f.name

        try:
            result = self.executor._insert(temp_path, 1, "inserted\n")
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            lines = content.strip().split('\n')
            self.assertEqual(lines[0], "line1")
            self.assertEqual(lines[1], "inserted")
            self.assertEqual(lines[2], "line2")
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_delete_lines(self):
        """Test delete_lines tool."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\nline2\nline3\n")
            temp_path = f.name

        try:
            result = self.executor._delete(temp_path, 2, 2)
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn("line1", content)
            self.assertNotIn("line2", content)
            self.assertIn("line3", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_todo_add(self):
        """Test todo_add tool."""
        result = self.executor._tadd("test task", "high")
        self.assertIn("Added", result)
        self.assertEqual(len(self.state.todos), 1)
        self.assertEqual(self.state.todos[0].text, "test task")
        self.assertEqual(self.state.todos[0].priority, "high")

    def test_todo_complete(self):
        """Test todo_complete tool."""
        self.state.todos.append(Todo("task"))
        result = self.executor._tdone(0)
        self.assertIn("Completed", result)
        self.assertTrue(self.state.todos[0].done)

    def test_todo_complete_invalid_index(self):
        """Test todo_complete with invalid index."""
        result = self.executor._tdone(999)
        self.assertIn("No todo", result)

    def test_todo_remove(self):
        """Test todo_remove tool."""
        self.state.todos.append(Todo("task"))
        result = self.executor._trem(0)
        self.assertIn("Removed", result)
        self.assertEqual(len(self.state.todos), 0)

    def test_reply_tool(self):
        """Test reply tool."""
        result = self.executor._dispatch("reply", {"message": "hello"})
        self.assertEqual(result, "[message sent to user]")
        self.assertEqual(len(self.state.chat), 1)
        self.assertEqual(self.state.chat[0].role, "dao")

    def test_unknown_tool(self):
        """Test unknown tool handling."""
        result = self.executor._dispatch("nonexistent_tool", {})
        self.assertIn("Unknown tool", result)

    def test_list_directory(self):
        """Test list_directory tool."""
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(
                stdout="file1\nfile2\n",
                stderr="",
                returncode=0
            )
            result = self.executor._dispatch("list_directory", {"path": "/tmp"})
            self.assertIsInstance(result, str)

    def test_search_files(self):
        """Test search_files tool."""
        with mock.patch('subprocess.run') as mock_run:
            mock_run.return_value = mock.Mock(
                stdout="match found",
                stderr="",
                returncode=0
            )
            result = self.executor._dispatch("search_files", {"pattern": "test"})
            self.assertIsInstance(result, str)

    def test_reset_worker(self):
        """Test reset_worker tool."""
        result = self.executor._dispatch("reset_worker", {})
        self.assertEqual(result, "Worker context cleared.")
        self.worker.reset.assert_called_once()

    def test_query_worker(self):
        """Test query_worker tool."""
        self.worker.query.return_value = "response"
        result = self.executor._dispatch("query_worker", {"question": "test?"})
        self.worker.query.assert_called_once_with("test?", "")
        self.assertEqual(result, "response")


# =============================================================================
# Test Agent Module (Integration Tests)
# =============================================================================

class TestAgent(unittest.TestCase):
    """Test Agent class (integration tests)."""

    def setUp(self):
        """Set up test fixtures."""
        self.state = State()
        self.worker = mock.Mock(spec=Worker)
        self.executor = Executor(self.state, self.worker)
        
        # Import here to avoid circular imports
        from dao_core.agent import Agent
        self.Agent = Agent

    @mock.patch('dao_core.agent.requests.post')
    def test_agent_initialization(self, mock_post):
        """Test agent initializes correctly."""
        agent = self.Agent(self.state, self.executor)
        self.assertEqual(agent.state, self.state)
        self.assertEqual(agent.executor, self.executor)
        self.assertFalse(agent._stop)

    @mock.patch('dao_core.agent.requests.post')
    def test_agent_stop(self, mock_post):
        """Test agent stop method."""
        agent = self.Agent(self.state, self.executor)
        agent.stop()
        self.assertTrue(agent._stop)

    @mock.patch('dao_core.agent.requests.post')
    def test_agent_inject_message(self, mock_post):
        """Test agent message injection."""
        agent = self.Agent(self.state, self.executor)
        agent.inject_message("test message")
        self.assertEqual(agent._pending_injection, "test message")

    @mock.patch('dao_core.agent.CYCLE_SLEEP', 0.1)
    @mock.patch('dao_core.agent.requests.post')
    def test_agent_run_stops_when_requested(self, mock_post):
        """Test agent run loop respects stop flag."""
        agent = self.Agent(self.state, self.executor)
        
        def stop_agent():
            time.sleep(0.2)
            agent.stop()
        
        thread = threading.Thread(target=stop_agent)
        thread.start()
        agent.run()
        thread.join()
        
        self.assertTrue(agent._stop)


# =============================================================================
# Edge Cases and Boundary Tests
# =============================================================================

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions."""

    def test_empty_file_read(self):
        """Test reading empty file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            temp_path = f.name

        try:
            state = State()
            worker = mock.Mock(spec=Worker)
            executor = Executor(state, worker)
            result = executor._read(temp_path, 1, 500)
            self.assertIsInstance(result, str)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_replace_beyond_file_length(self):
        """Test replace_lines beyond file length."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\n")
            temp_path = f.name

        try:
            state = State()
            worker = mock.Mock(spec=Worker)
            executor = Executor(state, worker)
            # Try to replace lines that don't exist
            result = executor._replace(temp_path, 10, 20, "new\n")
            self.assertIsInstance(result, str)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_delete_beyond_file_length(self):
        """Test delete_lines beyond file length."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\n")
            temp_path = f.name

        try:
            state = State()
            worker = mock.Mock(spec=Worker)
            executor = Executor(state, worker)
            result = executor._delete(temp_path, 10, 20)
            self.assertIsInstance(result, str)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_insert_at_end_of_file(self):
        """Test insert_lines at end of file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
            f.write("line1\n")
            temp_path = f.name

        try:
            state = State()
            worker = mock.Mock(spec=Worker)
            executor = Executor(state, worker)
            result = executor._insert(temp_path, 100, "new\n")
            
            with open(temp_path, 'r') as f:
                content = f.read()
            
            self.assertIn("line1", content)
            self.assertIn("new", content)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_todo_index_negative(self):
        """Test todo operations with negative index."""
        state = State()
        worker = mock.Mock(spec=Worker)
        executor = Executor(state, worker)
        
        result = executor._tdone(-1)
        self.assertIn("No todo", result)
        
        result = executor._trem(-1)
        self.assertIn("No todo", result)

    def test_concurrent_state_access(self):
        """Test concurrent access to state."""
        state = State()
        errors = []

        def modify_state():
            try:
                for i in range(50):
                    state.push_log("test", f"msg {i}")
                    state.push_chat("user", f"chat {i}")
                    state.add_inbox(f"inbox {i}")
                    state.drain_inbox()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=modify_state) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)

    def test_strip_think_edge_cases(self):
        """Test strip_think with edge cases."""
        # Incomplete think block
        self.assertEqual(strip_think("<think>incomplete"), "<think>incomplete")
        
        # Nested think-like patterns
        text = "<think>outer<think>inner</think>outer"
        result = strip_think(text)
        self.assertNotIn("<think>", result)
        
        # Think at end
        self.assertEqual(strip_think("response<think>think</think>"), "response")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == '__main__':
    unittest.main(verbosity=2)
