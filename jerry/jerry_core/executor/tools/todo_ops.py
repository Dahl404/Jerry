#!/usr/bin/env python3
"""Jerry Executor — Todo Operations"""

from jerry_core.models import Todo


class TodoOperations:
    """Mixin for todo list operations."""

    def _tadd(self, task: str = None, tasks: list = None, priority: str = "medium") -> str:
        """Add todo(s). Accepts single task or array of tasks."""
        with self.state._lock:
            if tasks and isinstance(tasks, list):
                # Batch add multiple tasks
                for t in tasks:
                    if t.strip():
                        self.state.todos.append(Todo(t.strip(), priority))
                return f"Added {len(tasks)} tasks"
            elif task:
                # Single task
                self.state.todos.append(Todo(task, priority))
                return f"Added: {task}"
            else:
                return "ERROR: No task(s) provided"

    def _tdone(self, idx: int = None, todo_id: int = None) -> str:
        """Mark a todo complete by stable id (preferred) or positional index."""
        with self.state._lock:
            # Prefer stable ID lookup — immune to index shifts from concurrent adds
            if todo_id is not None:
                for t in self.state.todos:
                    if t.id == todo_id:
                        t.done = True
                        return f"Completed (id={todo_id}): {t.text}"
                return f"No todo with id={todo_id}"
            # Fallback: positional index (model default: index=0)
            if idx is not None and 0 <= idx < len(self.state.todos):
                self.state.todos[idx].done = True
                return f"Completed #{idx}: {self.state.todos[idx].text}"
            return f"No todo at index {idx}"

    def _trem(self, idx: int) -> str:
        """Remove todo by index."""
        with self.state._lock:
            if 0 <= idx < len(self.state.todos):
                t = self.state.todos.pop(idx)
                return f"Removed: {t.text}"
            return f"No todo at index {idx}"

    def _todo_write(self, todos: list) -> str:
        """Add new tasks to the todo list (doesn't replace existing)."""
        try:
            if not todos or not isinstance(todos, list):
                return "ERROR: todo_write requires a list of todos"

            with self.state._lock:
                # Add new tasks (existing tasks keep their IDs)
                for i, todo in enumerate(todos):
                    if isinstance(todo, str):
                        self.state.todos.append(Todo(todo, "medium"))
                    elif isinstance(todo, dict):
                        content = todo.get("content", "Untitled task")
                        priority = todo.get("priority", "medium")
                        completed = todo.get("completed", False)
                        self.state.todos.append(Todo(content, priority))
                        if completed:
                            self.state.todos[-1].done = True

            # Show tasks with their stable IDs
            task_list = []
            for i, t in enumerate(self.state.todos):
                status = "✓" if t.done else "○"
                task_list.append(f"  {status} #{t.id}: {t.text}")

            return f"✓ Todo list:\n" + "\n".join(task_list)
        except Exception as e:
            return f"ERROR: {e}"

    def _todo_complete(self, index: int = None, id: int = None) -> str:
        """Mark a todo as complete by ID (preferred) or index."""
        try:
            with self.state._lock:
                if not self.state.todos:
                    return "ERROR: No todos to complete"

                # If id is specified, use it (preferred method)
                if id is not None:
                    for todo in self.state.todos:
                        if todo.id == id:
                            todo.done = True
                            return f"✓ Completed task #{id}: {todo.text}"
                    return f"ERROR: No task with id={id}"

                # If index specified, find the task at that position
                if index is not None:
                    if index < 0 or index >= len(self.state.todos):
                        return f"ERROR: Invalid index {index}"
                    self.state.todos[index].done = True
                    return f"✓ Completed task #{self.state.todos[index].id}: {self.state.todos[index].text}"

                # No index or id - find first pending task
                for todo in self.state.todos:
                    if not todo.done:
                        todo.done = True
                        return f"✓ Completed task #{todo.id}: {todo.text}"

                return "✓ All tasks already complete!"
        except Exception as e:
            return f"ERROR: {e}"
