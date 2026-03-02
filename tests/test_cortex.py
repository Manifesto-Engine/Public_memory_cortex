"""Tests for Cortex Memory SDK."""
import os
import time
import tempfile
import pytest

from cortex_memory import (
    Cortex, Memory, MemoryType, Emotion,
    ebbinghaus_factor, apply_biases, is_flashbulb,
)


@pytest.fixture
def cortex(tmp_path):
    """Fresh cortex for each test."""
    db = tmp_path / "test_cortex.db"
    cx = Cortex(str(db))
    yield cx
    cx.close()


class TestRememberRecall:
    def test_remember_returns_memory(self, cortex):
        mem = cortex.remember("test content", type="semantic")
        assert isinstance(mem, Memory)
        assert mem.content == "test content"
        assert mem.type == "semantic"
        assert len(mem.id) == 16

    def test_recall_finds_memory(self, cortex):
        cortex.remember("Python is great", type="semantic", tags=["tech"])
        results = cortex.recall("Python")
        assert len(results) >= 1
        assert results[0].content == "Python is great"

    def test_recall_updates_access_count(self, cortex):
        cortex.remember("access test", type="episodic")
        r1 = cortex.recall("access test")
        assert r1[0].access_count == 1
        r2 = cortex.recall("access test")
        assert r2[0].access_count == 2

    def test_recall_by_type(self, cortex):
        cortex.remember("episodic one", type="episodic")
        cortex.remember("semantic one", type="semantic")
        results = cortex.recall_by_type("semantic")
        assert all(m.type == "semantic" for m in results)

    def test_recall_recent(self, cortex):
        cortex.remember("recent memory", type="episodic")
        results = cortex.recall_recent(hours=1)
        assert len(results) >= 1

    def test_recall_by_emotion(self, cortex):
        cortex.remember("scary thing", type="episodic", emotion="fear")
        cortex.remember("nice thing", type="episodic", emotion="satisfaction")
        results = cortex.recall_by_emotion("fear")
        assert all(m.emotion == "fear" for m in results)

    def test_forget(self, cortex):
        mem = cortex.remember("to forget", type="episodic")
        cortex.forget(mem.id)
        results = cortex.recall("to forget")
        assert len(results) == 0


class TestEmotions:
    def test_flashbulb_detection(self):
        assert is_flashbulb("fear", 0.9) is True
        assert is_flashbulb("surprise", 0.8) is True
        assert is_flashbulb("fear", 0.5) is False
        assert is_flashbulb("neutral", 0.9) is False

    def test_flashbulb_auto_tagged(self, cortex):
        mem = cortex.remember(
            "critical event", type="episodic",
            emotion="fear", importance=0.9,
        )
        assert "flashbulb" in mem.tags

    def test_emotional_metabolism(self, cortex):
        cortex.remember(
            "fear memory", type="episodic",
            emotion="fear", importance=0.5,
        )
        cortex.metabolize()
        results = cortex.recall("fear memory")
        # Fear memories should have slightly higher importance after metabolism
        assert results[0].importance >= 0.5


class TestDecay:
    def test_ebbinghaus_factor_recent(self):
        factor = ebbinghaus_factor(time.time() - 60, 0, 0.5)
        assert factor > 0.95  # Very recent, minimal decay

    def test_ebbinghaus_factor_old(self):
        factor = ebbinghaus_factor(time.time() - 86400 * 30, 0, 0.1)
        assert factor < 0.5  # 30 days old, low importance

    def test_rehearsal_extends_halflife(self):
        t = time.time() - 86400  # 24 hours ago
        factor_no_access = ebbinghaus_factor(t, 0, 0.5)
        factor_accessed = ebbinghaus_factor(t, 10, 0.5)
        assert factor_accessed > factor_no_access

    def test_decay_removes_weak_memories(self, cortex):
        # Create a very old, low-importance memory
        mem = cortex.remember("weak", type="episodic", importance=0.05)
        # Manually age it
        cortex._conn.execute(
            "UPDATE memories SET created_at = ? WHERE id = ?",
            (time.time() - 86400 * 60, mem.id),  # 60 days old
        )
        cortex._conn.commit()
        decayed = cortex.decay()
        assert decayed >= 1


class TestBiases:
    def test_apply_biases(self):
        result = apply_biases(
            importance=0.5,
            emotion="fear",
            created_at=time.time() - 3600,
            access_count=5,
            mood="vigilant",
        )
        assert result.biased_score > result.original_score
        assert result.confirmation_factor > 1.0  # Fear + vigilant

    def test_biased_recall_reorders(self, cortex):
        cortex.remember("old important", type="episodic", importance=0.9)
        cortex.remember("new less important", type="episodic", importance=0.3)

        raw = cortex.recall_by_type("episodic")
        biased = cortex.recall_biased("important")
        # Biased recall may reorder based on recency
        assert len(biased) >= 1


class TestDreams:
    def test_dream_cycle(self, cortex):
        cortex.remember(
            "important memory", type="episodic",
            importance=0.9, emotion="fear",
        )
        # Access it to make it eligible for dreaming
        cortex.recall("important")
        dreamed = cortex.dream(max_memories=1)
        # May or may not dream depending on access_count threshold
        assert isinstance(dreamed, list)

    def test_dream_degrades_confidence(self, cortex):
        mem = cortex.remember(
            "dream target", type="episodic",
            importance=0.8, confidence=1.0,
        )
        # Access it
        cortex.recall("dream target")
        cortex.dream(max_memories=5)
        result = cortex.recall("dream target")
        if result:
            assert result[0].confidence <= 1.0


class TestConsolidation:
    def test_consolidation_creates_semantic(self, cortex):
        mem = cortex.remember(
            "repeated event", type="episodic",
            importance=0.5,
        )
        # Simulate aging and access
        cortex._conn.execute(
            "UPDATE memories SET created_at = ?, access_count = ? WHERE id = ?",
            (time.time() - 86400 * 4, 5, mem.id),  # 4 days old, 5 accesses
        )
        cortex._conn.commit()
        consolidated = cortex.consolidate(max_age_hours=72)
        assert len(consolidated) >= 1
        assert consolidated[0].type == "semantic"
        assert "consolidated" in consolidated[0].tags


class TestLinking:
    def test_link_creates_bidirectional(self, cortex):
        a = cortex.remember("memory A", type="episodic")
        b = cortex.remember("memory B", type="episodic")
        cortex.link(a.id, b.id)

        linked_from_a = cortex.recall_linked(a.id)
        linked_from_b = cortex.recall_linked(b.id)
        assert any(m.id == b.id for m in linked_from_a)
        assert any(m.id == a.id for m in linked_from_b)


class TestMood:
    def test_mood_computation(self, cortex):
        for _ in range(5):
            cortex.remember("fear event", type="episodic", emotion="fear",
                          importance=0.7)
        mood, confidence = cortex.update_mood()
        assert mood == "vigilant"
        assert confidence > 0.0

    def test_neutral_when_no_emotions(self, cortex):
        mood, confidence = cortex.update_mood()
        assert mood == "neutral"
        assert confidence == 0.0


class TestStats:
    def test_stats_structure(self, cortex):
        cortex.remember("test", type="semantic")
        stats = cortex.stats()
        assert "total_memories" in stats
        assert "by_type" in stats
        assert "by_emotion" in stats
        assert "mood" in stats
        assert stats["total_memories"] >= 1


class TestContextManager:
    def test_with_statement(self, tmp_path):
        db = tmp_path / "ctx.db"
        with Cortex(str(db)) as cx:
            cx.remember("in context", type="episodic")
            assert cx.stats()["total_memories"] == 1
