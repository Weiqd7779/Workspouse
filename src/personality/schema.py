from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class PersonaMetadata(BaseModel):
    id: str = Field(..., description="Unique identifier for the persona (e.g., 'tsundere_wife')")
    version: str = Field(..., description="Semantic version of this persona file (e.g., '1.0.0')")
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    target_model: str = Field("model", description="The LLM model this persona is optimized for")
    author: str = Field("User", description="Creator of this persona")
    description: str = Field("", description="Brief description of the persona's personality")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization (e.g., 'shy', 'aggressive')")

class PersonaPrompts(BaseModel):
    system: str = Field(..., description=" The core system prompt defining the personality")
    greeting: str = Field(..., description="Initial message sent when chat starts")
    uncensored_mode: bool = Field(False, description="Whether to bypass certain safety filters (if supported)")

class PersonaConfig(BaseModel):
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(1000, gt=0)
    top_p: float = Field(1.0)
    stop: Optional[List[str]] = Field(default=None, description="List of stop words to halt generation")
    
class Persona(BaseModel):
    metadata: PersonaMetadata
    prompts: PersonaPrompts
    config: PersonaConfig = Field(default_factory=PersonaConfig)
