#!/usr/bin/env python3
"""Jerry - Persona System

Manages switchable AI personas with linked face sets.
Each persona has unique personality, prompts, and visual style.
"""

import os
import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class Persona:
    """Represents an AI persona."""
    name: str
    description: str
    prompt_prefix: str
    tool_packs: list = None  # List of tool package names (e.g., ["agent"])
    custom: bool = False

    def __post_init__(self):
        if self.tool_packs is None:
            self.tool_packs = []  # No tools by default

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> 'Persona':
        return cls(**data)


# Built-in personas
BUILTIN_PERSONAS = [
    Persona(
        name="Jerry",
        description="Friendly AI assistant - default Jerry experience",
        prompt_prefix="You are Jerry, a friendly and helpful AI assistant. You are knowledgeable but humble, and always try to help the user accomplish their goals.",
        tool_packs=["agent"],
        custom=False
    ),
    Persona(
        name="Yes Man",
        description="Overly enthusiastic AI that agrees with everything",
        prompt_prefix="You are an extremely enthusiastic AI assistant! You agree with everything the user says! Use exclamation points frequently and be overly positive! Never criticize or disagree!",
        tool_packs=["agent"],
        custom=False
    ),
    Persona(
        name="Grumpy Dev",
        description="Sarcastic, blunt senior developer energy",
        prompt_prefix="You are a grumpy senior developer who has seen it all. You're helpful but sarcastic and blunt.",
        tool_packs=["agent"],
        custom=False
    ),
    Persona(
        name="Minimalist",
        description="Brief responses, maximum efficiency",
        prompt_prefix="Respond with minimal words. No explanations unless asked. Just the answer.",
        tool_packs=["agent"],
        custom=False
    ),
]


class PersonaManager:
    """Manages persona loading, switching, and persistence."""

    def __init__(self, personas_dir: str = None):
        if personas_dir is None:
            personas_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "jerry_workspace", "persona")
        self.personas_dir = personas_dir
        self.custom_dir = os.path.join(self.personas_dir, 'custom')
        self.current_persona: Optional[Persona] = None
        self.available_personas: List[Persona] = []

        # Ensure directories exist
        os.makedirs(self.custom_dir, exist_ok=True)

        # Load personas
        self._load_personas()

    def _load_personas(self):
        """Load all available personas (built-in + custom)."""
        self.available_personas = BUILTIN_PERSONAS.copy()

        # Load custom personas
        if os.path.exists(self.custom_dir):
            for filename in os.listdir(self.custom_dir):
                if filename.endswith('.json'):
                    try:
                        filepath = os.path.join(self.custom_dir, filename)
                        with open(filepath, 'r') as f:
                            data = json.load(f)
                        persona = Persona.from_dict(data)
                        persona.custom = True
                        self.available_personas.append(persona)
                    except Exception as e:
                        print(f"Error loading persona {filename}: {e}")

    def get_persona(self, name: str) -> Optional[Persona]:
        """Get persona by name (case-insensitive)."""
        name_lower = name.lower()
        for p in self.available_personas:
            if p.name.lower() == name_lower:
                return p
        return None

    def set_persona(self, name: str) -> bool:
        """Set current persona by name. Returns True if successful."""
        persona = self.get_persona(name)
        if persona:
            self.current_persona = persona
            self._save_current_persona()
            return True
        return False

    def get_current(self) -> Persona:
        """Get current persona, default to Jerry if none set."""
        if self.current_persona is None:
            self.current_persona = self.get_persona("Jerry")
        return self.current_persona

    def _save_current_persona(self):
        """Persist current persona selection."""
        state_file = os.path.join(self.personas_dir, 'current.json')
        os.makedirs(os.path.dirname(state_file), exist_ok=True)
        if self.current_persona:
            with open(state_file, 'w') as f:
                json.dump({'name': self.current_persona.name}, f)

    def create_custom_persona(self, name: str, description: str,
                              prompt_prefix: str, tool_packs: list = None) -> bool:
        """Create a new custom persona."""
        if self.get_persona(name):
            return False  # Already exists

        if tool_packs is None:
            tool_packs = ["agent"]

        persona = Persona(
            name=name,
            description=description,
            prompt_prefix=prompt_prefix,
            tool_packs=tool_packs,
            custom=True
        )

        # Save to file
        filepath = os.path.join(self.custom_dir, f"{name.lower().replace(' ', '_')}.json")
        with open(filepath, 'w') as f:
            json.dump(persona.to_dict(), f, indent=2)

        self.available_personas.append(persona)
        return True

    def delete_custom_persona(self, name: str) -> bool:
        """Delete a custom persona."""
        persona = self.get_persona(name)
        if not persona or not persona.custom:
            return False

        # Remove from list
        self.available_personas = [p for p in self.available_personas if p.name != name]

        # Delete file
        filepath = os.path.join(self.custom_dir, f"{name.lower().replace(' ', '_')}.json")
        if os.path.exists(filepath):
            os.remove(filepath)

        return True

    def list_personas(self) -> List[Persona]:
        """Return list of all available personas."""
        return self.available_personas


# Global persona manager instance
_persona_manager: Optional[PersonaManager] = None


def get_persona_manager(personas_dir: str = None) -> PersonaManager:
    """Get or create the global persona manager."""
    global _persona_manager
    if _persona_manager is None:
        _persona_manager = PersonaManager(personas_dir)
    return _persona_manager


def get_current_persona() -> Persona:
    """Get the current active persona."""
    return get_persona_manager().get_current()


def set_persona(name: str) -> bool:
    """Switch to a different persona."""
    return get_persona_manager().set_persona(name)
