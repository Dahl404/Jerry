#!/usr/bin/env python3
"""Jerry — Path Utilities"""

import os
from typing import Tuple, List


def resolve_path(path: str, base_dir: str) -> str:
    """Resolve a path relative to base directory.
    
    Args:
        path: Path to resolve (can be absolute or relative)
        base_dir: Base directory for relative paths
        
    Returns:
        Absolute path
    """
    if os.path.isabs(path):
        return os.path.abspath(path)
    return os.path.abspath(os.path.join(base_dir, path))


def validate_path(path: str, allowed_dirs: List[str]) -> Tuple[bool, str, str]:
    """Validate path is within allowed directories.
    
    Args:
        path: Path to validate
        allowed_dirs: List of allowed directory prefixes
        
    Returns:
        Tuple of (is_valid, absolute_path, error_message)
    """
    try:
        abs_path = os.path.abspath(path)
        for prefix in allowed_dirs:
            if abs_path.startswith(os.path.abspath(prefix)):
                return (True, abs_path, "")
        return (False, "", f"Access denied - path outside allowed directories: {path}")
    except Exception as e:
        return (False, "", f"Invalid path: {e}")


def is_within_directory(path: str, directory: str) -> bool:
    """Check if path is within a directory.
    
    Args:
        path: Path to check
        directory: Directory to check against
        
    Returns:
        True if path is within directory
    """
    try:
        abs_path = os.path.abspath(path)
        abs_dir = os.path.abspath(directory)
        return abs_path.startswith(abs_dir)
    except Exception:
        return False
