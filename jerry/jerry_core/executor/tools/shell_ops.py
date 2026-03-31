#!/usr/bin/env python3
"""Jerry Executor — Shell Operations"""

import os
import subprocess
from typing import Optional


class ShellOperations:
    """Mixin for shell command operations."""

    def _sh(self, cmd: str, cwd: Optional[str] = None, timeout: int = 60) -> str:
        """Execute shell command with timeout to prevent freezing.

        Args:
            cmd: Shell command to execute
            cwd: Working directory (default: self.cwd)
            timeout: Timeout in seconds (default: 60, max: 300)
        """
        try:
            # Use cwd from args, or fall back to self.cwd
            workdir = cwd if cwd else self.cwd
            # Cap timeout at 5 minutes to prevent permanent hangs
            timeout = min(timeout, 300) if timeout else 60
            r = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=workdir,
                timeout=timeout,
            )
            out = (r.stdout + r.stderr).strip()
            return out or f"[exit {r.returncode}]"
        except subprocess.TimeoutExpired:
            return f"ERROR: Command timed out after {timeout}s (use longer timeout if needed)"
        except Exception as e:
            return f"ERROR: {e}"
