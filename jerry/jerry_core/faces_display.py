#!/usr/bin/env python3
"""Jerry — ASCII Face Display Module

Displays emotion-based ASCII art faces from the faces directory.
Supports smooth transitions between emotions via neutral state.
"""

import os
from typing import Dict, Optional, List

# Default faces directory - now inside jerry_core
FACES_DIR = os.path.join(os.path.dirname(__file__), "faces")

# Emotion tag mapping (from <tag> to face file name)
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

# Face display dimensions
FACE_WIDTH = 100  # Characters wide
FACE_HEIGHT = 50  # Lines tall (based on face files)


class FaceDisplay:
    """Manages ASCII face display with emotion transitions."""

    def __init__(self):
        self.faces: Dict[str, List[str]] = {}
        self.current_emotion: str = "neutral"
        self.target_emotion: Optional[str] = None
        self.in_transition: bool = False
        self.transition_stage: int = 0  # 0=done, 1=going to neutral, 2=going to target
        self._load_faces()

    def _load_faces(self):
        """Load all face files from the faces directory."""
        if not os.path.exists(FACES_DIR):
            return

        for filename in os.listdir(FACES_DIR):
            filepath = os.path.join(FACES_DIR, filename)
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        lines = f.read().splitlines()
                        # Pad or trim to FACE_HEIGHT lines
                        while len(lines) < FACE_HEIGHT:
                            lines.append("")
                        lines = lines[:FACE_HEIGHT]
                        self.faces[filename] = lines
                except Exception:
                    pass

    def get_available_emotions(self) -> List[str]:
        """Return list of available emotion names."""
        return list(self.faces.keys())

    def set_emotion(self, emotion: str):
        """Set target emotion. Will transition through neutral first.
        
        Args:
            emotion: Emotion name (e.g., 'happy', 'sad', 'neutral')
        """
        # Map emotion to face file name
        face_name = EMOTION_MAP.get(emotion.lower(), emotion.lower())
        
        # Check if this face exists
        if face_name not in self.faces:
            return
        
        # If already at this emotion, no transition needed
        if face_name == self.current_emotion and not self.in_transition:
            return
        
        # Start transition
        self.target_emotion = face_name
        self.in_transition = True
        self.transition_stage = 1  # Start by going to neutral

    def parse_emotion_tags(self, text: str) -> str:
        """Parse emotion tags from text and set emotion accordingly.
        
        Args:
            text: Text that may contain <emotion> tags
            
        Returns:
            Text with emotion tags removed
        """
        import re
        
        # Find all emotion tags
        tags = re.findall(r'<(\w+)>', text.lower())
        
        if tags:
            # Use the last emotion tag found
            last_tag = tags[-1]
            if last_tag in EMOTION_MAP or last_tag in self.faces:
                self.set_emotion(last_tag)
        
        # Remove all emotion tags from text
        clean_text = re.sub(r'<\w+>', '', text)
        return clean_text

    def get_current_face(self) -> List[str]:
        """Get current face lines for display.
        
        Returns:
            List of 50 face lines, each 100 characters wide
        """
        # If transitioning, handle state machine
        if self.in_transition:
            if self.transition_stage == 1:
                # Going to neutral first
                self.current_emotion = "neutral"
                self.transition_stage = 2
            elif self.transition_stage == 2:
                # Now going to target
                if self.target_emotion:
                    self.current_emotion = self.target_emotion
                    self.target_emotion = None
                self.in_transition = False
                self.transition_stage = 0
        
        # Get face lines
        face_lines = self.faces.get(self.current_emotion, self.faces.get("neutral", []))
        
        if not face_lines:
            # Return empty face if none loaded
            return [" " * FACE_WIDTH] * FACE_HEIGHT
        
        # Ensure each line is exactly FACE_WIDTH characters
        result = []
        for line in face_lines:
            # Pad or trim to FACE_WIDTH
            if len(line) < FACE_WIDTH:
                line = line + " " * (FACE_WIDTH - len(line))
            else:
                line = line[:FACE_WIDTH]
            result.append(line)
        
        return result

    def render_face(self, width: int = FACE_WIDTH) -> str:
        """Render face as a single string.
        
        Args:
            width: Terminal width to fit (default: 100)
            
        Returns:
            Face as newline-separated string
        """
        face_lines = self.get_current_face()
        
        # If terminal is too small, show warning
        if width < FACE_WIDTH:
            warning = f"⚠️  Terminal too narrow! Need {FACE_WIDTH} chars, have {width}. Please resize."
            warning_lines = [warning.center(width) for _ in range(FACE_HEIGHT)]
            return "\n".join(warning_lines)
        
        return "\n".join(face_lines)


# Global face display instance
_face_display: Optional[FaceDisplay] = None


def get_face_display() -> FaceDisplay:
    """Get or create the global face display instance."""
    global _face_display
    if _face_display is None:
        _face_display = FaceDisplay()
    return _face_display


def parse_and_set_emotion(text: str) -> str:
    """Convenience function to parse emotion tags from text.
    
    Args:
        text: Text containing optional <emotion> tags
        
    Returns:
        Text with tags removed, emotion set in global display
    """
    return get_face_display().parse_emotion_tags(text)


def get_current_face_lines() -> List[str]:
    """Get current face lines for rendering.
    
    Returns:
        List of face lines
    """
    return get_face_display().get_current_face()


def get_available_emotions() -> List[str]:
    """Get list of available emotions.
    
    Returns:
        List of emotion names
    """
    return get_face_display().get_available_emotions()
