#!/usr/bin/env python3
"""Jerry — ASCII Face Display Module

Displays emotion-based ASCII art faces from the faces directory.
Supports smooth transitions between emotions via neutral state.
Lightweight rendering with dynamic sizing.
"""

import os
from typing import Dict, Optional, List
from .config import JERRY_BASE

# Default faces directory
FACES_DIR = os.path.join(os.path.dirname(JERRY_BASE), "faces")

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

# No fixed dimensions - adapt to terminal


class FaceDisplay:
    """Manages ASCII face display with emotion transitions."""

    def __init__(self):
        self.faces: Dict[str, List[str]] = {}
        self.current_emotion: str = "neutral"
        self.target_emotion: Optional[str] = None
        self.in_transition: bool = False
        self.transition_stage: int = 0
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

        # If already in transition, just update target
        if self.in_transition:
            self.target_emotion = face_name
            return

        # Start new transition
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

    def get_current_face(self, term_width: int = 100, term_height: int = 50) -> List[str]:
        """Get current face lines scaled to terminal size.

        Uses same scaling as splash_screen.py:
            scale = (width - margin * 2) / orig_width

        Face scales relative to screen size.
        Particle resolution scales with the face.

        Args:
            term_width: Terminal width
            term_height: Terminal height

        Returns:
            List of scaled face lines
        """
        # Handle transition
        if self.in_transition:
            if self.transition_stage == 1:
                self.current_emotion = "neutral"
                self.transition_stage = 2
            elif self.transition_stage == 2:
                if self.target_emotion:
                    self.current_emotion = self.target_emotion
                    self.target_emotion = None
                self.in_transition = False
                self.transition_stage = 0

        face_lines = self.faces.get(self.current_emotion, self.faces.get("neutral", []))
        if not face_lines:
            return []

        # Get actual face dimensions
        orig_h = len(face_lines)
        orig_w = max(len(line) for line in face_lines) if face_lines else 0
        if orig_w == 0 or orig_h == 0:
            return face_lines

        # Calculate scale like splash_screen.py does
        # Face scales relative to screen size
        margin = 2
        scale = (term_width - margin * 2) / orig_w if orig_w > 0 else 1

        # Scale face dimensions by the scale factor
        scaled_h = max(1, int(orig_h * scale))
        scaled_w = max(1, int(orig_w * scale))

        # Sample face at scaled resolution
        result = []
        for new_row in range(scaled_h):
            orig_row = int(new_row * orig_h / scaled_h)
            if orig_row < len(face_lines):
                line = face_lines[orig_row]
                new_line = ""
                for new_col in range(scaled_w):
                    orig_col = int(new_col * orig_w / scaled_w)
                    if orig_col < len(line):
                        new_line += line[orig_col]
                    else:
                        new_line += " "
                result.append(new_line)

        return result

    def render_face(self, width: int = 100, height: int = 50) -> str:
        """Render face scaled to terminal."""
        face_lines = self.get_current_face(width, height)
        if not face_lines:
            return ""
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
