#!/usr/bin/env python3
"""Jerry — Emotion Processing Utilities"""

import re
from typing import Optional


# Emotion normalization mapping
EMOTION_MAP = {
    "neutral": "neutral",
    "smiling": "smiling",
    "happy": "smiling",
    "laughing": "smiling",
    "mad": "mad",
    "angry": "mad",
    "bummed": "bummed",
    "sad": "bummed",
    "disappointed": "bummed",
    "questioning": "questioning",
    "confused": "questioning",
    "wondering": "questioning",
    "thinking": "thinking",
    "pondering": "thinking",
    "surprise": "surprise_1",
    "surprised": "surprise_1",
    "shocked": "surprise_2",
    "amazed": "surprise_2",
}


def parse_emotion_tags(text: str) -> Tuple[Optional[str], str]:
    """Parse emotion tags from text.
    
    Args:
        text: Text that may contain <emotion> tags
        
    Returns:
        Tuple of (last_emotion_or_None, text_without_tags)
    """
    # Find all emotion tags
    tags = re.findall(r'<(\w+)>', text.lower())
    
    # Get the last emotion tag
    last_emotion = None
    if tags:
        last_tag = tags[-1]
        last_emotion = normalize_emotion(last_tag)
    
    # Remove all emotion tags from text
    clean_text = re.sub(r'<\w+>', '', text)
    
    return (last_emotion, clean_text)


def normalize_emotion(emotion: str) -> Optional[str]:
    """Normalize emotion name to standard form.
    
    Args:
        emotion: Emotion name (e.g., 'happy', 'angry')
        
    Returns:
        Normalized emotion name or None if not recognized
    """
    return EMOTION_MAP.get(emotion.lower())


def extract_emotion_from_text(text: str) -> Optional[str]:
    """Extract and normalize the first emotion tag from text.
    
    Args:
        text: Text that may contain emotion tags
        
    Returns:
        Normalized emotion or None
    """
    match = re.search(r'<(\w+)>', text.lower())
    if match:
        return normalize_emotion(match.group(1))
    return None
