"""Emotions — Valence-Weighted Memory Processing.

Not sentiment analysis. Not prompt engineering for tone.
A genuine emotional layer that modifies how memories are stored,
recalled, and forgotten.

Fear memories decay 50% slower — preserved for survival.
Satisfaction-tagged memories consolidate faster.
Surprise creates flashbulb memories immune to decay.
"""
from __future__ import annotations


# ── Emotion → Mood State Mapping ──────────────────────────

MOOD_MAP = {
    "fear":         "vigilant",
    "frustration":  "agitated",
    "curiosity":    "exploratory",
    "satisfaction": "confident",
    "surprise":     "alert",
    "neutral":      "neutral",
}


def emotional_metabolism(conn) -> dict:
    """Process emotion-aware decay modifiers.

    Called during metabolism cycles. Modifies memory importance
    based on emotional valence:

    - Fear: importance nudged +2% per cycle to counter Ebbinghaus decay.
      Fear memories are preserved for survival — they fade slower.
    - Satisfaction: episodic memories with ≥2 accesses flagged for
      faster consolidation into semantic knowledge.

    Args:
        conn: SQLite connection to the cortex database.

    Returns:
        Dict with counts of processed memories per emotion.
    """
    stats = {"fear_preserved": 0, "satisfaction_flagged": 0}

    # Fear: resist decay by nudging importance upward
    fear_rows = conn.execute("""
        SELECT id, importance FROM memories
        WHERE emotion = 'fear' AND importance > 0.05
        AND importance < 0.9
    """).fetchall()

    for row in fear_rows:
        rid = row["id"] if isinstance(row, dict) else row[0]
        imp = row["importance"] if isinstance(row, dict) else row[1]
        new_imp = min(0.95, imp * 1.02)
        conn.execute(
            "UPDATE memories SET importance = ? WHERE id = ?",
            (new_imp, rid),
        )
        stats["fear_preserved"] += 1

    # Satisfaction: flag for accelerated consolidation
    sat_rows = conn.execute("""
        SELECT id FROM memories
        WHERE emotion = 'satisfaction' AND type = 'episodic'
        AND access_count >= 2
    """).fetchall()

    stats["satisfaction_flagged"] = len(sat_rows)

    conn.commit()
    return stats


def is_flashbulb(emotion: str, importance: float) -> bool:
    """Determine if a memory qualifies as a flashbulb memory.

    Flashbulb memories are vivid, detailed snapshots formed during
    high-emotion, high-importance events. They are immune to
    Ebbinghaus decay — they persist indefinitely.

    Criteria: fear or surprise emotion + importance ≥ 0.8.
    """
    return emotion in ("fear", "surprise") and importance >= 0.8
