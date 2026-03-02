"""Consolidation — Episodic → Semantic Memory Promotion.

When an episodic memory (an event) is accessed frequently, it
graduates into semantic knowledge (a fact). The episode fades,
the lesson remains.

Like how you don't remember the exact day you learned that
fire is hot — you just know it.
"""
from __future__ import annotations

import time
import json
import logging

from .memory import Memory, MemoryType

logger = logging.getLogger("cortex.consolidation")


def consolidate(
    conn,
    max_age_hours: int = 72,
    min_access_count: int = 3,
    min_importance: float = 0.3,
) -> list[Memory]:
    """Promote frequently-accessed episodic memories to semantic knowledge.

    Criteria for promotion:
    - Episodic type
    - Older than `max_age_hours`
    - Accessed at least `min_access_count` times
    - Importance above `min_importance`

    The original episodic memory's importance is halved (it fades),
    and a new semantic memory is created with the distilled knowledge.

    Args:
        conn: SQLite connection.
        max_age_hours: Minimum age for consolidation eligibility.
        min_access_count: Minimum recalls before promotion.
        min_importance: Importance floor for promotion.

    Returns:
        List of newly created semantic Memory objects.
    """
    cutoff = time.time() - (max_age_hours * 3600)

    rows = conn.execute("""
        SELECT id, content, tags, importance, emotion, source
        FROM memories
        WHERE type = 'episodic'
        AND created_at < ?
        AND access_count >= ?
        AND importance >= ?
    """, (cutoff, min_access_count, min_importance)).fetchall()

    created = []

    for row in rows:
        rid = row["id"] if isinstance(row, dict) else row[0]
        content = row["content"] if isinstance(row, dict) else row[1]
        tags_raw = row["tags"] if isinstance(row, dict) else row[2]
        importance = row["importance"] if isinstance(row, dict) else row[3]
        emotion = row["emotion"] if isinstance(row, dict) else row[4]
        source = row["source"] if isinstance(row, dict) else row[5]

        # Parse tags
        if isinstance(tags_raw, str):
            try:
                tags = json.loads(tags_raw)
            except (json.JSONDecodeError, TypeError):
                tags = []
        else:
            tags = tags_raw or []

        # Create semantic memory from episodic
        semantic = Memory(
            type=MemoryType.SEMANTIC,
            content=f"[Consolidated] {content}",
            tags=tags + ["consolidated"],
            importance=min(1.0, importance * 1.2),
            source=f"consolidation:{source}",
            linked_ids=[rid],
            emotion=emotion,
            confidence=0.9,
            context=f"Consolidated from episodic memory {rid}",
        )

        # Insert the new semantic memory
        conn.execute("""
            INSERT INTO memories (id, type, content, tags, importance,
                                  created_at, last_accessed, access_count,
                                  source, linked_ids, emotion, confidence, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            semantic.id, semantic.type, semantic.content,
            json.dumps(semantic.tags), semantic.importance,
            semantic.created_at, semantic.last_accessed, 0,
            semantic.source, json.dumps(semantic.linked_ids),
            semantic.emotion, semantic.confidence, semantic.context,
        ))

        # Fade the original episodic memory
        conn.execute(
            "UPDATE memories SET importance = importance * 0.5 WHERE id = ?",
            (rid,),
        )

        created.append(semantic)
        logger.debug(f"Consolidated: {content[:60]}...")

    conn.commit()
    return created
