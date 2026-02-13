import os
import yaml
from typing import List, Optional, Dict
from pathlib import Path
from .schema import Persona

class PersonaManager:
    def __init__(self, personas_dir: str = "personas"):
        self.personas_dir = Path(personas_dir)
        self.personas: Dict[str, Persona] = {}
        self._load_all_personas()

    def _load_all_personas(self):
        """Scans the personas directory and loads all valid YAML files."""
        self.personas.clear()
        if not self.personas_dir.exists():
            print(f"Warning: Personas directory '{self.personas_dir}' not found.")
            return

        for file_path in self.personas_dir.glob("*.yaml"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    persona = Persona(**data)
                    self.personas[persona.metadata.id] = persona
            except Exception as e:
                print(f"Error loading persona from {file_path}: {e}")

    def get_persona(self, persona_id: str) -> Optional[Persona]:
        """Returns a specific persona by ID."""
        return self.personas.get(persona_id)

    def list_personas(self) -> List[dict]:
        """Returns a summary list of all available personas."""
        return [
            {
                "id": p.metadata.id,
                "version": p.metadata.version,
                "description": p.metadata.description,
                "tags": p.metadata.tags
            }
            for p in self.personas.values()
        ]

    def reload(self):
        """Reloads all personas from disk."""
        self._load_all_personas()
