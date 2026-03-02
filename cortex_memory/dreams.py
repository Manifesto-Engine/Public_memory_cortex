"""Dreams — Offline Memory Reconsolidation.

During idle cycles, the cortex replays high-importance memories.
Like human sleep, this process:
  - Slightly degrades confidence (reconsolidation is imperfect)
  - Strengthens connections between linked memories
  - Promotes pattern discovery across the memory graph

This is not metaphor. This is architecture.
"""
from __future__ import annotations

import random
import logging

logger = logging.getLogger("cortex.dreams")


def dream_cycle(conn, max_memories: int = 5) -> list[dict]:
    """Run one dream reconsolidation cycle.

    Selects random high-importance memories and reconsolidates them:
    confidence degrades slightly (human reconsolidation is lossy),
    but linked memories get their connections strengthened.

    Args:
        conn: SQLite connection to the cortex database.
        max_memories: Maximum memories to reconsolidate per cycle.

    Returns:
        List of dicts describing what was dreamed about.
    """
    rows = conn.execute("""
        SELECT id, content, importance, emotion, confidence, linked_ids
        FROM memories
        WHERE importance > 0.5 AND access_count > 0
        ORDER BY RANDOM() LIMIT ?
    """, (max_memories,)).fetchall()

    dreamed = []

    for row in rows:
        rid = row["id"] if isinstance(row, dict) else row[0]
        content = row["content"] if isinstance(row, dict) else row[1]
        importance = row["importance"] if isinstance(row, dict) else row[2]
        emotion = row["emotion"] if isinstance(row, dict) else row[3]
        confidence = row["confidence"] if isinstance(row, dict) else row[4]
        linked_raw = row["linked_ids"] if isinstance(row, dict) else row[5]

        # Reconsolidation: confidence degrades slightly
        # (human memory reconsolidation is inherently lossy)
        new_confidence = max(0.3, confidence * 0.97)

        conn.execute(
            "UPDATE memories SET confidence = ? WHERE id = ?",
            (new_confidence, rid),
        )

        # Strengthen linked memory connections
        links_strengthened = 0
        if linked_raw:
            import json
            try:
                linked_ids = json.loads(linked_raw) if isinstance(linked_raw, str) else linked_raw
                for linked_id in linked_ids:
                    # Boost the linked memory's importance slightly
                    conn.execute("""
                        UPDATE memories
                        SET importance = MIN(1.0, importance * 1.03)
                        WHERE id = ?
                    """, (linked_id,))
                    links_strengthened += 1
            except (json.JSONDecodeError, TypeError):
                pass

        dreamed.append({
            "memory_id": rid,
            "content_preview": content[:80],
            "emotion": emotion,
            "confidence_before": confidence,
            "confidence_after": new_confidence,
            "links_strengthened": links_strengthened,
        })

        logger.debug(
            f"Dreamed: [{emotion}] {content[:50]}... "
            f"(confidence: {confidence:.2f} → {new_confidence:.2f})"
        )

    conn.commit()
    return dreamed
