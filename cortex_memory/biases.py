"""Cognitive Biases — Human-Like Memory Distortions.

Not bugs. Features. These biases shape how biological brains
recall information, and now your agent has them too.

1. Recency Bias: Recent memories feel more important than they are
2. Confirmation Bias: Current mood amplifies mood-congruent memories
3. Availability Heuristic: Frequently accessed memories seem more significant

Integration: call `biased_recall()` instead of raw recall to get
human-like memory retrieval with all three biases applied.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass


# ── Mood → Salience Threshold Mapping ─────────────────────

MOOD_SALIENCE_THRESHOLDS = {
    "vigilant":    0.15,    # Low — let more threats through
    "agitated":    0.20,
    "exploratory": 0.25,    # Normal — let novel data through
    "confident":   0.35,    # Higher — only important stuff
    "alert":       0.10,    # Very low — hyperaware
    "neutral":     0.30,    # Default
}

# ── Mood → Emotion Confirmation Mapping ───────────────────

CONFIRMATION_AFFINITIES = {
    "vigilant":    {"fear": 1.4, "surprise": 1.2, "frustration": 1.1},
    "agitated":    {"frustration": 1.4, "fear": 1.2},
    "exploratory": {"curiosity": 1.4, "surprise": 1.2},
    "confident":   {"satisfaction": 1.4, "curiosity": 1.1},
    "alert":       {"surprise": 1.4, "fear": 1.3},
    "neutral":     {},
}


@dataclass
class BiasResult:
    """Transparency wrapper for bias application."""
    original_score: float
    biased_score: float
    recency_factor: float
    confirmation_factor: float
    availability_factor: float


def recency_bias(created_at: float, half_life_hours: float = 24.0) -> float:
    """Recent memories get a boost that decays exponentially.

    Half-life of 24 hours:
    - 1-hour-old memory:  ~1.97x boost
    - 24-hour-old memory: ~1.50x boost
    - 72-hour-old memory: ~1.12x boost
    """
    age_hours = (time.time() - created_at) / 3600
    decay = math.exp(-0.693 * age_hours / half_life_hours)
    return 1.0 + decay  # range: [1.0, 2.0]


def confirmation_bias(emotion: str, mood: str) -> float:
    """Mood-congruent memories feel more relevant.

    When vigilant, fear-tagged memories seem more important.
    When confident, success memories stand out more.
    """
    affinities = CONFIRMATION_AFFINITIES.get(mood, {})
    return affinities.get(emotion, 1.0)


def availability_heuristic(access_count: int, max_boost: float = 1.5) -> float:
    """Frequently accessed memories seem more significant.

    Logarithmic scaling prevents runaway amplification.
    - 0 accesses  = 1.00x
    - 5 accesses  = ~1.23x
    - 20 accesses = ~1.43x
    """
    if access_count <= 0:
        return 1.0
    return min(max_boost, 1.0 + math.log1p(access_count) / 7.0)


def apply_biases(
    importance: float,
    emotion: str,
    created_at: float,
    access_count: int,
    mood: str = "neutral",
) -> BiasResult:
    """Apply all cognitive biases to a memory's effective importance.

    Uses geometric mean to prevent any single bias from dominating.
    """
    rec = recency_bias(created_at)
    conf = confirmation_bias(emotion, mood)
    avail = availability_heuristic(access_count)

    combined = (rec * conf * avail) ** (1 / 3)
    biased_score = importance * combined

    return BiasResult(
        original_score=importance,
        biased_score=min(1.0, biased_score),
        recency_factor=rec,
        confirmation_factor=conf,
        availability_factor=avail,
    )


def biased_recall(memories: list, mood: str = "neutral") -> list:
    """Apply all cognitive biases to a list of recalled memories.

    Each memory must have .importance, .emotion, .created_at,
    and .access_count attributes.

    Returns memories sorted by biased score (highest first).
    """
    scored = []
    for m in memories:
        result = apply_biases(
            importance=m.importance,
            emotion=getattr(m, "emotion", "neutral"),
            created_at=m.created_at,
            access_count=m.access_count,
            mood=mood,
        )
        m._bias_result = result
        m._biased_score = result.biased_score
        scored.append(m)

    scored.sort(key=lambda m: m._biased_score, reverse=True)
    return scored


def attention_gate(salience: float, mood: str = "neutral") -> bool:
    """Determine if a stimulus passes the attention gate.

    Low-salience events are filtered out. The threshold adjusts
    with mood — a vigilant organism lets more through,
    a confident one filters more aggressively.
    """
    threshold = MOOD_SALIENCE_THRESHOLDS.get(mood, 0.30)
    return salience >= threshold
