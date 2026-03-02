"""Cortex Memory — Persistent, Human-Like Memory for AI Agents.

Give your agent a brain that remembers, forgets, dreams, and feels.

    from cortex_memory import Cortex

    cortex = Cortex("my_agent.db")
    cortex.remember("User prefers dark mode", type="semantic",
                    tags=["preference"], importance=0.8)

    memories = cortex.recall("dark mode")
    cortex.decay()   # Ebbinghaus forgetting curves
    cortex.dream()   # Reconsolidate during idle

Zero dependencies. Pure Python. MIT licensed.
Built by the Manifesto Engine project.
"""

__version__ = "0.1.0"

from .core import Cortex
from .memory import Memory, MemoryType, Emotion
from .biases import BiasResult, apply_biases, biased_recall, attention_gate
from .decay import ebbinghaus_factor
from .mood import compute_mood, MOOD_MAP
from .emotions import emotional_metabolism, is_flashbulb
from .dreams import dream_cycle
from .consolidation import consolidate
from .dashboard import run_dashboard

__all__ = [
    "Cortex",
    "Memory",
    "MemoryType",
    "Emotion",
    "BiasResult",
    "apply_biases",
    "biased_recall",
    "attention_gate",
    "ebbinghaus_factor",
    "compute_mood",
    "MOOD_MAP",
    "emotional_metabolism",
    "is_flashbulb",
    "dream_cycle",
    "consolidate",
    "run_dashboard",
]
