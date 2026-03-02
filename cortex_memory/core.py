"""Cortex — Persistent AI Memory Engine.

Give your agent a brain that remembers, forgets, dreams, and feels.

    from cortex_memory import Cortex

    cortex = Cortex("my_agent.db")
    cortex.remember("User prefers dark mode", type="semantic",
                    tags=["preference"], importance=0.8)

    memories = cortex.recall("dark mode")
    cortex.decay()   # Ebbinghaus forgetting curves
    cortex.dream()   # Reconsolidate during idle

Zero dependencies. Pure Python. Just sqlite3 and math.
"""
from __future__ import annotations

import json
import math
import sqlite3
import time
import logging
from pathlib import Path

from .memory import Memory, MemoryType, Emotion
from .decay import apply_decay, ebbinghaus_factor
from .emotions import emotional_metabolism, is_flashbulb
from .mood import compute_mood
from .dreams import dream_cycle
from .consolidation import consolidate
from .biases import biased_recall, apply_biases, attention_gate

logger = logging.getLogger("cortex")


class Cortex:
    """Persistent AI memory engine with human-like characteristics.

    Features:
        - Four memory types: episodic, semantic, procedural, relational
        - Six emotional states that weight storage and recall
        - Ebbinghaus forgetting curves with flashbulb immunity
        - Dream reconsolidation during idle cycles
        - Mood-biased recall via cognitive biases
        - Memory consolidation (episodic → semantic promotion)
        - Bidirectional memory linking (graph structure)
        - Full-text search via SQLite FTS5

    Args:
        db_path: Path to SQLite database file. Created if doesn't exist.
    """

    def __init__(self, db_path: str | Path = "cortex.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._init_schema()
        self._has_fts = self._init_fts()
        self._mood: str = "neutral"
        self._mood_confidence: float = 0.0

    def _init_schema(self):
        """Create the memories table if it doesn't exist."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT DEFAULT '[]',
                importance REAL DEFAULT 0.5,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 0,
                source TEXT DEFAULT '',
                linked_ids TEXT DEFAULT '[]',
                emotion TEXT DEFAULT 'neutral',
                confidence REAL DEFAULT 1.0,
                context TEXT DEFAULT ''
            )
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_type
            ON memories(type)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_importance
            ON memories(importance DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_created
            ON memories(created_at DESC)
        """)
        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_emotion
            ON memories(emotion)
        """)
        self._conn.commit()

    def _init_fts(self) -> bool:
        """Initialize FTS5 full-text search. Returns True if available."""
        try:
            self._conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(content, tags, id UNINDEXED)
            """)
            self._conn.commit()
            return True
        except sqlite3.OperationalError:
            logger.debug("FTS5 not available — falling back to LIKE queries")
            return False

    # ── Remember ──────────────────────────────────────

    def remember(
        self,
        content: str,
        type: str | MemoryType = MemoryType.EPISODIC,
        tags: list[str] | None = None,
        importance: float = 0.5,
        source: str = "",
        emotion: str | Emotion = Emotion.NEUTRAL,
        confidence: float = 1.0,
        context: str = "",
    ) -> Memory:
        """Store a memory.

        Args:
            content: The memory content (text).
            type: Memory type (episodic, semantic, procedural, relational).
            tags: Categorization labels.
            importance: Significance score (0.0–1.0).
            source: Origin identifier.
            emotion: Emotional valence at encoding time.
            confidence: How confident in this memory (0.0–1.0).
            context: Situational context.

        Returns:
            The created Memory object.
        """
        tags = tags or []
        mem = Memory(
            type=str(type) if isinstance(type, MemoryType) else type,
            content=content,
            tags=tags,
            importance=max(0.0, min(1.0, importance)),
            source=source,
            emotion=str(emotion) if isinstance(emotion, Emotion) else emotion,
            confidence=max(0.0, min(1.0, confidence)),
            context=context,
        )

        # Check for flashbulb status
        if is_flashbulb(mem.emotion, mem.importance):
            mem.tags = list(set(mem.tags + ["flashbulb"]))

        self._conn.execute("""
            INSERT INTO memories (id, type, content, tags, importance,
                                  created_at, last_accessed, access_count,
                                  source, linked_ids, emotion, confidence, context)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            mem.id, mem.type, mem.content, json.dumps(mem.tags),
            mem.importance, mem.created_at, mem.last_accessed, 0,
            mem.source, json.dumps(mem.linked_ids),
            mem.emotion, mem.confidence, mem.context,
        ))

        # Index in FTS
        if self._has_fts:
            self._conn.execute(
                "INSERT INTO memories_fts (id, content, tags) VALUES (?, ?, ?)",
                (mem.id, mem.content, " ".join(mem.tags)),
            )

        self._conn.commit()
        return mem

    # ── Recall ────────────────────────────────────────

    def recall(
        self,
        query: str,
        limit: int = 10,
        type: str | MemoryType | None = None,
    ) -> list[Memory]:
        """Search memories by keyword query. Updates access counts.

        Uses FTS5 if available, falls back to LIKE queries.
        """
        if self._has_fts:
            sql = """
                SELECT m.* FROM memories m
                JOIN memories_fts f ON m.id = f.id
                WHERE memories_fts MATCH ?
            """
            params: list = [query]
        else:
            sql = "SELECT * FROM memories WHERE content LIKE ?"
            params = [f"%{query}%"]

        if type is not None:
            type_str = str(type) if isinstance(type, MemoryType) else type
            sql += " AND m.type = ?" if self._has_fts else " AND type = ?"
            params.append(type_str)

        sql += " ORDER BY importance DESC LIMIT ?"
        params.append(limit)

        rows = self._conn.execute(sql, params).fetchall()
        memories = [self._row_to_memory(r) for r in rows]

        # Update access metadata
        now = time.time()
        for m in memories:
            self._conn.execute("""
                UPDATE memories
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (now, m.id))
            m.last_accessed = now
            m.access_count += 1

        self._conn.commit()
        return memories

    def recall_by_type(
        self,
        type: str | MemoryType,
        limit: int = 20,
    ) -> list[Memory]:
        """Get all memories of a specific type, ordered by importance."""
        type_str = str(type) if isinstance(type, MemoryType) else type
        rows = self._conn.execute("""
            SELECT * FROM memories WHERE type = ?
            ORDER BY importance DESC LIMIT ?
        """, (type_str, limit)).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def recall_recent(self, hours: int = 24, limit: int = 20) -> list[Memory]:
        """Get recent memories within a time window."""
        cutoff = time.time() - (hours * 3600)
        rows = self._conn.execute("""
            SELECT * FROM memories WHERE created_at > ?
            ORDER BY created_at DESC LIMIT ?
        """, (cutoff, limit)).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def recall_by_emotion(
        self,
        emotion: str | Emotion,
        limit: int = 10,
    ) -> list[Memory]:
        """Get memories with a specific emotional valence."""
        em_str = str(emotion) if isinstance(emotion, Emotion) else emotion
        rows = self._conn.execute("""
            SELECT * FROM memories WHERE emotion = ?
            ORDER BY importance DESC LIMIT ?
        """, (em_str, limit)).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def recall_biased(
        self,
        query: str,
        limit: int = 10,
        mood: str | None = None,
    ) -> list[Memory]:
        """Recall with cognitive biases applied.

        Applies recency bias, confirmation bias, and availability
        heuristic to sort results by perceived importance rather
        than raw importance.
        """
        raw = self.recall(query, limit=limit * 2)
        effective_mood = mood or self._mood
        return biased_recall(raw, mood=effective_mood)[:limit]

    def recall_linked(self, memory_id: str) -> list[Memory]:
        """Get all memories linked to a given memory."""
        row = self._conn.execute(
            "SELECT linked_ids FROM memories WHERE id = ?",
            (memory_id,),
        ).fetchone()

        if not row:
            return []

        linked_raw = row["linked_ids"]
        try:
            linked_ids = json.loads(linked_raw)
        except (json.JSONDecodeError, TypeError):
            return []

        if not linked_ids:
            return []

        placeholders = ",".join("?" * len(linked_ids))
        rows = self._conn.execute(
            f"SELECT * FROM memories WHERE id IN ({placeholders})",
            linked_ids,
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    # ── Forget ────────────────────────────────────────

    def forget(self, memory_id: str) -> bool:
        """Delete a specific memory."""
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if self._has_fts:
            self._conn.execute(
                "DELETE FROM memories_fts WHERE id = ?", (memory_id,)
            )
        self._conn.commit()
        return True

    # ── Link ──────────────────────────────────────────

    def link(self, memory_id_a: str, memory_id_b: str):
        """Create a bidirectional link between two memories."""
        for src, dst in [(memory_id_a, memory_id_b), (memory_id_b, memory_id_a)]:
            row = self._conn.execute(
                "SELECT linked_ids FROM memories WHERE id = ?", (src,)
            ).fetchone()
            if row:
                try:
                    linked = json.loads(row["linked_ids"])
                except (json.JSONDecodeError, TypeError):
                    linked = []
                if dst not in linked:
                    linked.append(dst)
                    self._conn.execute(
                        "UPDATE memories SET linked_ids = ? WHERE id = ?",
                        (json.dumps(linked), src),
                    )
        self._conn.commit()

    # ── Lifecycle ─────────────────────────────────────

    def decay(self, base_half_life_hours: float = 72.0) -> int:
        """Apply Ebbinghaus forgetting curves to all memories.

        Memories that decay below minimum importance are removed.
        Flashbulb memories (fear/surprise + high importance) are immune.

        Returns:
            Number of memories that fully decayed and were removed.
        """
        return apply_decay(
            self._conn,
            base_half_life_hours=base_half_life_hours,
        )

    def dream(self, max_memories: int = 5) -> list[dict]:
        """Run one dream reconsolidation cycle.

        Like human sleep: replays important memories, slightly
        degrades confidence, strengthens linked connections.

        Returns:
            List of dicts describing what was dreamed about.
        """
        return dream_cycle(self._conn, max_memories=max_memories)

    def consolidate(self, max_age_hours: int = 72) -> list[Memory]:
        """Promote frequently-accessed episodic memories to semantic knowledge.

        The episode fades, the lesson remains.

        Returns:
            List of newly created semantic memories.
        """
        return consolidate(self._conn, max_age_hours=max_age_hours)

    def metabolize(self):
        """Full metabolism cycle: emotional processing + decay + consolidation.

        Call this periodically (e.g., every few minutes) to keep the
        memory system healthy. This is the "breathing" of the cortex.
        """
        emotional_metabolism(self._conn)
        self.decay()
        self.consolidate()
        self.update_mood()

    # ── Mood ──────────────────────────────────────────

    def update_mood(self) -> tuple[str, float]:
        """Recompute mood from recent emotional memory history.

        Returns:
            Tuple of (mood_state, confidence).
        """
        self._mood, self._mood_confidence = compute_mood(self._conn)
        return self._mood, self._mood_confidence

    @property
    def mood(self) -> str:
        """Current mood state."""
        return self._mood

    @property
    def mood_confidence(self) -> float:
        """Confidence in the current mood (0.0–1.0)."""
        return self._mood_confidence

    # ── Stats ─────────────────────────────────────────

    def stats(self) -> dict:
        """Get cortex statistics."""
        total = self._conn.execute(
            "SELECT COUNT(*) FROM memories"
        ).fetchone()[0]

        by_type = {}
        for row in self._conn.execute(
            "SELECT type, COUNT(*) as cnt FROM memories GROUP BY type"
        ).fetchall():
            by_type[row["type"]] = row["cnt"]

        by_emotion = {}
        for row in self._conn.execute(
            "SELECT emotion, COUNT(*) as cnt FROM memories GROUP BY emotion"
        ).fetchall():
            by_emotion[row["emotion"]] = row["cnt"]

        avg_importance = self._conn.execute(
            "SELECT AVG(importance) FROM memories"
        ).fetchone()[0] or 0.0

        avg_confidence = self._conn.execute(
            "SELECT AVG(confidence) FROM memories"
        ).fetchone()[0] or 0.0

        return {
            "total_memories": total,
            "by_type": by_type,
            "by_emotion": by_emotion,
            "avg_importance": round(avg_importance, 3),
            "avg_confidence": round(avg_confidence, 3),
            "mood": self._mood,
            "mood_confidence": self._mood_confidence,
            "db_size_mb": round(
                self.db_path.stat().st_size / (1024 * 1024), 2
            ) if self.db_path.exists() else 0.0,
        }

    # ── Internal ──────────────────────────────────────

    def _row_to_memory(self, row) -> Memory:
        """Convert a database row to a Memory object."""
        tags = json.loads(row["tags"]) if isinstance(row["tags"], str) else row["tags"]
        linked = json.loads(row["linked_ids"]) if isinstance(row["linked_ids"], str) else row["linked_ids"]

        return Memory(
            id=row["id"],
            type=row["type"],
            content=row["content"],
            tags=tags or [],
            importance=row["importance"],
            created_at=row["created_at"],
            last_accessed=row["last_accessed"],
            access_count=row["access_count"],
            source=row["source"],
            linked_ids=linked or [],
            emotion=row["emotion"],
            confidence=row["confidence"],
            context=row["context"],
        )

    def close(self):
        """Close the database connection."""
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def __repr__(self) -> str:
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        return f"<Cortex memories={total} mood={self._mood} db={self.db_path}>"
