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
    "smiling": "happy",
    "happy": "happy",
    "laughing": "happy",
    "mad": "grumpy",
    "angry": "grumpy",
    "bummed": "grumpy",
    "sad": "grumpy",
    "disappointed": "grumpy",
    "questioning": "neutral",
    "confused": "neutral",
    "wondering": "neutral",
    "thinking": "neutral",
    "pondering": "neutral",
    "surprise": "happy",
    "surprised": "happy",
    "shocked": "happy",
    "amazed": "happy",
}

# No fixed dimensions - adapt to terminal


class FaceDisplay:
    """Manages ASCII face display with emotion transitions."""

    def __init__(self):
        self.faces: Dict[str, List[str]] = {}
        self.colored_faces: Dict[str, dict] = {}  # JSON faces with colors
        self.current_emotion: str = "neutral"
        self.current_face: str = "neutral"  # Default to neutral face
        self.target_face: Optional[str] = None  # Face we're transitioning to
        self.in_transition: bool = False
        self.transition_progress: float = 0.0  # 0.0 to 1.0
        self._load_faces()

    def _load_faces(self):
        """Load all face files from the faces directory."""
        if not os.path.exists(FACES_DIR):
            return

        for filename in os.listdir(FACES_DIR):
            filepath = os.path.join(FACES_DIR, filename)
            if os.path.isfile(filepath):
                # Load JSON colored faces
                if filename.startswith('face_') and filename.endswith('.json'):
                    try:
                        import json
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        face_name = filename[5:-5]  # Remove 'face_' and '.json'
                        self.colored_faces[face_name] = data
                    except Exception:
                        pass
                # Load legacy text faces
                elif not filename.startswith('face_') and not filename.endswith('.json'):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            lines = f.read().splitlines()
                            self.faces[filename] = lines
                    except Exception:
                        pass

    def set_face(self, face_name: str):
        """Set the current colored face.
        
        Args:
            face_name: Face name (plain, unique, result, grumpy, happy, neutral)
        """
        if face_name in self.colored_faces:
            self.current_face = face_name

    def get_colored_face(self) -> Optional[dict]:
        """Get the current colored face data."""
        return self.colored_faces.get(self.current_face)

    def get_available_emotions(self) -> List[str]:
        """Return list of available emotion names."""
        return list(self.faces.keys())

    def set_emotion(self, emotion: str):
        """Set target emotion by switching to corresponding colored face with diffusion.

        Args:
            emotion: Emotion name (e.g., 'happy', 'sad', 'neutral')
        """
        # Map emotion to colored face name
        face_name = EMOTION_MAP.get(emotion.lower(), emotion.lower())

        # Check if this colored face exists and is different from current
        if face_name in self.colored_faces and face_name != self.current_face:
            # Start transition - keep particles, just morph to new face
            self.target_face = face_name
            self.current_emotion = face_name
            self.in_transition = True
            self.transition_progress = 0.0
            # Don't reset particles - they'll morph to new positions
        elif face_name in self.faces:
            # Fallback to legacy text face
            self.current_emotion = face_name

    def update_transition(self, delta: float = 0.05):
        """Update face transition progress.
        
        Args:
            delta: Progress increment per call (default 0.05 = 5%)
        """
        if self.in_transition and self.target_face:
            self.transition_progress += delta
            if self.transition_progress >= 1.0:
                self.transition_progress = 1.0
                self.current_face = self.target_face
                self.target_face = None
                self.in_transition = False

    def get_colored_face(self, term_width: int = 100, term_height: int = 50) -> tuple:
        """Get current colored face scaled to terminal size.
        
        Returns:
            Tuple of (lines, color_grid) where lines is list of strings
            and color_grid is 2D array of hex color codes
        """
        face_data = self.colored_faces.get(self.current_face)
        if not face_data:
            return [], []
        
        face_lines = face_data.get('lines', [])
        color_grid = face_data.get('colors', [])
        
        if not face_lines:
            return [], []
        
        # Get actual face dimensions
        orig_h = len(face_lines)
        orig_w = len(face_lines[0]) if face_lines else 0
        if orig_w == 0 or orig_h == 0:
            return face_lines, color_grid
        
        # Calculate scale
        margin = 2
        scale = (term_width - margin * 2) / orig_w if orig_w > 0 else 1
        
        # Scale face dimensions
        scaled_h = max(1, int(orig_h * scale))
        scaled_w = max(1, int(orig_w * scale))
        
        # Sample face at scaled resolution
        result_lines = []
        result_colors = []
        
        for new_row in range(scaled_h):
            orig_row = int(new_row * orig_h / scaled_h)
            if orig_row < len(face_lines):
                line = face_lines[orig_row]
                colors = color_grid[orig_row] if orig_row < len(color_grid) else []
                new_line = ""
                new_colors = []
                for new_col in range(scaled_w):
                    orig_col = int(new_col * orig_w / scaled_w)
                    if orig_col < len(line):
                        new_line += line[orig_col]
                        if orig_col < len(colors):
                            new_colors.append(colors[orig_col])
                        else:
                            new_colors.append('FFFFFF')
                    else:
                        new_line += " "
                        new_colors.append('000000')
                result_lines.append(new_line)
                result_colors.append(new_colors)
        
        return result_lines, result_colors

    def parse_emotion_tags(self, text: str) -> str:
        """Parse emotion tags from text and set face accordingly.

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
            self.set_emotion(last_tag)

        # Remove all emotion tags from text
        clean_text = re.sub(r'<\w+>', '', text)
        return clean_text

    def get_current_face(self, term_width: int = 100, term_height: int = 50) -> List[str]:
        """Get current face lines scaled to terminal size.

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
