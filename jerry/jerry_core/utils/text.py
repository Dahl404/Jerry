#!/usr/bin/env python3
"""Jerry — Text Processing Utilities"""

import re
from typing import List


def strip_think(text: str) -> str:
    """Remove <think>...</think> blocks (Qwen3 reasoning tokens).
    
    Args:
        text: Text that may contain reasoning blocks
        
    Returns:
        Text with reasoning blocks removed
    """
    return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()


def wrap_text(text: str, width: int = 80) -> List[str]:
    """Wrap text to specified width, preserving existing line breaks.
    
    Args:
        text: Text to wrap
        width: Maximum line width
        
    Returns:
        List of wrapped lines
    """
    lines = []
    for paragraph in text.split('\n'):
        if len(paragraph) <= width:
            lines.append(paragraph)
        else:
            # Word-aware wrapping
            words = paragraph.split()
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= width:
                    current_line += (" " if current_line else "") + word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
    return lines


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
