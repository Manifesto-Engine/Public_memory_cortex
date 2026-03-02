"""Memory — The fundamental unit of cognition.

Every experience, fact, skill, and connection is stored as a Memory object
with emotional valence, confidence scoring, and temporal metadata.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum


class MemoryType(str, Enum):
    """The four pillars of memory."""
    EPISODIC = "episodic"       # What happened (events, outcomes)
    PROCEDURAL = "procedural"   # How to do things (skills, patterns)
    SEMANTIC = "semantic"       # What things mean (facts, knowledge)
    RELATIONAL = "relational"   # How things connect (associations)


class Emotion(str, Enum):
    """Six emotional states that weight memory storage and recall."""
    NEUTRAL = "neutral"
    FEAR = "fear"
    CURIOSITY = "curiosity"
    SATISFACTION = "satisfaction"
    SURPRISE = "surprise"
    FRUSTRATION = "frustration"


@dataclass
class Memory:
    """A single memory with emotional and temporal metadata.

    Attributes:
        id: Unique identifier.
        type: One of the four memory types.
        content: The memory's content (text).
        tags: Categorization labels for retrieval.
        importance: How significant this memory is (0.0–1.0).
        created_at: Unix timestamp of creation.
        last_accessed: Unix timestamp of last recall.
        access_count: How many times this memory has been recalled.
        source: Origin of the memory (e.g., "user", "system", "agent").
        linked_ids: IDs of related memories (graph edges).
        emotion: Emotional valence at time of encoding.
        confidence: How confident the system is in this memory (0.0–1.0).
        context: Situational context when memory was formed.
    """
    id: str = ""
    type: str = MemoryType.EPISODIC
    content: str = ""
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0
    source: str = ""
    linked_ids: list[str] = field(default_factory=list)
    emotion: str = Emotion.NEUTRAL
    confidence: float = 1.0
    context: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = uuid.uuid4().hex[:16]

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return asdict(self)

    def age_hours(self) -> float:
        """How old this memory is in hours."""
        return (time.time() - self.created_at) / 3600
