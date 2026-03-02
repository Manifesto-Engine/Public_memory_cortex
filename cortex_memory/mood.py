"""Mood — Global Emotional State Computation.

The organism's mood is not a feeling — it's a computational bias.
A vigilant system surfaces threats first. An exploratory one seeks
new data. Mood shapes what the cortex recalls and how it acts.

Mood is computed by aggregating recent emotional memories and
finding the dominant emotional signal.
"""
from __future__ import annotations

import time

MOOD_MAP = {
    "fear":         "vigilant",
    "frustration":  "agitated",
    "curiosity":    "exploratory",
    "satisfaction": "confident",
    "surprise":     "alert",
    "neutral":      "neutral",
}

VALID_MOODS = set(MOOD_MAP.values())


def compute_mood(
    conn,
    window_seconds: int = 3600,
    sample_limit: int = 30,
) -> tuple[str, float]:
    """Compute current mood from recent emotional memory history.

    Scans the last `window_seconds` of emotional memories,
    counts dominant emotion, maps to mood state.

    Args:
        conn: SQLite connection.
        window_seconds: How far back to look (default: 1 hour).
        sample_limit: Max emotional memories to sample.

    Returns:
        Tuple of (mood_state, confidence). Confidence is the
        proportion of sampled memories matching the dominant emotion.
    """
    cutoff = time.time() - window_seconds

    rows = conn.execute("""
        SELECT emotion FROM memories
        WHERE created_at > ? AND emotion != 'neutral'
        ORDER BY created_at DESC LIMIT ?
    """, (cutoff, sample_limit)).fetchall()

    if not rows:
        return "neutral", 0.0

    counts: dict[str, int] = {}
    for row in rows:
        em = row["emotion"] if isinstance(row, dict) else row[0]
        counts[em] = counts.get(em, 0) + 1

    total = sum(counts.values())
    dominant = max(counts, key=counts.get)  # type: ignore[arg-type]
    confidence = counts[dominant] / total

    mood = MOOD_MAP.get(dominant, "neutral")
    return mood, round(confidence, 2)
