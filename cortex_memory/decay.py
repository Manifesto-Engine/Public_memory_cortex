"""Decay — Ebbinghaus Forgetting Curves.

Memories don't just disappear. They fade according to the same curves
Hermann Ebbinghaus discovered in 1885. Unused memories lose importance
over time. Important, frequently accessed memories resist decay.

The curve: retention = e^(-t/S) where S = stability factor.
Stability grows with repetition (access_count) and importance.
"""
from __future__ import annotations

import math
import time


def ebbinghaus_factor(
    created_at: float,
    access_count: int,
    importance: float,
    base_half_life_hours: float = 72.0,
) -> float:
    """Calculate retention factor using Ebbinghaus forgetting curve.

    Returns a value between 0.0 and 1.0 representing how much of the
    memory's original importance should be retained.

    Higher access_count and importance extend the effective half-life,
    simulating how rehearsal and significance strengthen memories.

    Args:
        created_at: Unix timestamp when memory was created.
        access_count: Number of times the memory has been recalled.
        importance: Original importance score (0.0–1.0).
        base_half_life_hours: Base half-life before modifiers.

    Returns:
        Retention factor (0.0–1.0).
    """
    age_hours = (time.time() - created_at) / 3600

    if age_hours <= 0:
        return 1.0

    # Rehearsal bonus: each access extends the half-life
    rehearsal_factor = 1.0 + math.log1p(access_count) * 0.5

    # Importance bonus: critical memories resist decay
    importance_factor = 0.5 + importance * 1.5

    effective_half_life = base_half_life_hours * rehearsal_factor * importance_factor

    # Exponential decay: retention = 2^(-t/half_life)
    retention = math.pow(2, -age_hours / effective_half_life)

    return max(0.0, min(1.0, retention))


def apply_decay(
    conn,
    min_importance: float = 0.02,
    base_half_life_hours: float = 72.0,
    flashbulb_immune: bool = True,
) -> int:
    """Apply Ebbinghaus decay to all memories in the database.

    Args:
        conn: SQLite connection.
        min_importance: Memories decayed below this are deleted.
        base_half_life_hours: Base forgetting curve half-life.
        flashbulb_immune: If True, flashbulb memories skip decay.

    Returns:
        Number of memories that decayed below threshold and were removed.
    """
    query = "SELECT id, created_at, access_count, importance, emotion FROM memories"
    rows = conn.execute(query).fetchall()

    decayed_count = 0
    to_delete = []

    for row in rows:
        # Flashbulb immunity: high-emotion + high-importance memories don't decay
        if flashbulb_immune:
            emotion = row["emotion"] if isinstance(row, dict) else row[4]
            importance = row["importance"] if isinstance(row, dict) else row[3]
            if emotion in ("fear", "surprise") and importance >= 0.8:
                continue

        rid = row["id"] if isinstance(row, dict) else row[0]
        created = row["created_at"] if isinstance(row, dict) else row[1]
        access = row["access_count"] if isinstance(row, dict) else row[2]
        imp = row["importance"] if isinstance(row, dict) else row[3]

        retention = ebbinghaus_factor(
            created, access, imp, base_half_life_hours
        )
        new_importance = imp * retention

        if new_importance < min_importance:
            to_delete.append(rid)
            decayed_count += 1
        else:
            conn.execute(
                "UPDATE memories SET importance = ? WHERE id = ?",
                (new_importance, rid),
            )

    for rid in to_delete:
        conn.execute("DELETE FROM memories WHERE id = ?", (rid,))

    conn.commit()
    return decayed_count
