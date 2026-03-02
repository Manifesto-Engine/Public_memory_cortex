"""Dreaming Agent — Full Memory Lifecycle Demo.

Watch an agent remember, feel, decay, dream, and shift mood
in real-time. This is not a metaphor. This is architecture.

Run: python examples/dreaming_agent.py
"""
import sys
import time
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cortex_memory import Cortex, Emotion


def banner(text: str):
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def main():
    cortex = Cortex("/tmp/dreaming_agent.db")

    banner("🧠 CORTEX MEMORY — LIFECYCLE DEMO")
    print(f"  {cortex}")

    # ── Phase 1: Encoding memories with emotion ──────
    banner("Phase 1: Encoding Memories")
    events = [
        ("System detected unauthorized access attempt", "fear", 0.95,
         ["security", "threat"]),
        ("Successfully patched vulnerability CVE-2026-1337", "satisfaction", 0.8,
         ["security", "patch"]),
        ("New framework released — looks promising", "curiosity", 0.6,
         ["tech", "framework"]),
        ("Build failed 3 times in a row", "frustration", 0.7,
         ["build", "ci"]),
        ("Unexpected spike in traffic from unknown region", "surprise", 0.85,
         ["traffic", "anomaly"]),
        ("Routine log rotation completed", "neutral", 0.2,
         ["maintenance"]),
        ("Another unauthorized access from same IP", "fear", 0.9,
         ["security", "threat"]),
        ("Deployed honeypot — caught attacker's toolkit", "satisfaction", 0.85,
         ["security", "honeypot"]),
    ]

    memories = []
    for content, emotion, importance, tags in events:
        mem = cortex.remember(
            content, type="episodic",
            tags=tags, importance=importance, emotion=emotion,
        )
        emoji = {"fear": "😨", "satisfaction": "😊", "curiosity": "🤔",
                 "frustration": "😤", "surprise": "😲", "neutral": "😐"}
        print(f"  {emoji.get(emotion, '·')} [{emotion:13s}] {content}")
        memories.append(mem)

    # ── Phase 2: Link related memories ───────────────
    banner("Phase 2: Linking Related Memories")
    # Link the two fear/security memories
    cortex.link(memories[0].id, memories[6].id)
    print(f"  Linked: '{memories[0].content[:40]}...'")
    print(f"      ↔   '{memories[6].content[:40]}...'")

    # Link the security patch to the honeypot
    cortex.link(memories[1].id, memories[7].id)
    print(f"  Linked: '{memories[1].content[:40]}...'")
    print(f"      ↔   '{memories[7].content[:40]}...'")

    # ── Phase 3: Mood computation ────────────────────
    banner("Phase 3: Computing Mood")
    mood, confidence = cortex.update_mood()
    print(f"  Mood: {mood} ({confidence:.0%} confidence)")
    print(f"  (Dominant emotion from last {len(events)} memories)")

    # ── Phase 4: Biased recall ───────────────────────
    banner("Phase 4: Biased Recall — 'security'")
    print(f"  Current mood: {cortex.mood}")
    print(f"  Biases active: recency, confirmation ({cortex.mood}), availability")
    print()
    biased = cortex.recall_biased("security", mood=cortex.mood)
    for i, m in enumerate(biased, 1):
        score = getattr(m, "_biased_score", m.importance)
        result = getattr(m, "_bias_result", None)
        bias_info = ""
        if result:
            bias_info = (
                f" [rec={result.recency_factor:.2f} "
                f"conf={result.confirmation_factor:.2f} "
                f"avail={result.availability_factor:.2f}]"
            )
        print(f"  {i}. [{m.emotion:13s}] score={score:.3f}{bias_info}")
        print(f"     {m.content}")

    # ── Phase 5: Dream reconsolidation ───────────────
    banner("Phase 5: Dreaming... 💤")
    dreamed = cortex.dream(max_memories=3)
    if dreamed:
        for d in dreamed:
            print(f"  🌙 Dreamed about: {d['content_preview']}")
            print(f"     Emotion: {d['emotion']}")
            print(f"     Confidence: {d['confidence_before']:.3f} → "
                  f"{d['confidence_after']:.3f} (reconsolidation loss)")
            print(f"     Links strengthened: {d['links_strengthened']}")
            print()
    else:
        print("  No dreams this cycle (need more high-importance memories)")

    # ── Phase 6: Decay ───────────────────────────────
    banner("Phase 6: Ebbinghaus Decay")
    print("  Applying forgetting curves...")
    print("  (Flashbulb memories are immune — fear+high importance)")
    decayed = cortex.decay()
    print(f"  Memories fully decayed: {decayed}")
    print(f"  Remaining: {cortex.stats()['total_memories']}")

    # ── Phase 7: Graph traversal ─────────────────────
    banner("Phase 7: Memory Graph Traversal")
    linked = cortex.recall_linked(memories[0].id)
    print(f"  Starting from: '{memories[0].content[:50]}...'")
    print(f"  Connected memories:")
    for m in linked:
        print(f"    → [{m.emotion}] {m.content[:60]}...")

    # ── Phase 8: Stats ───────────────────────────────
    banner("Phase 8: Cortex Stats")
    stats = cortex.stats()
    for key, val in stats.items():
        print(f"  {key:20s}: {val}")

    banner("✅ LIFECYCLE COMPLETE")
    print(f"  {cortex}")
    print(f"  Database: /tmp/dreaming_agent.db")
    print(f"\n  This is not a chatbot. This is a memory system.")
    print(f"  Built by Manifesto Engine — manifesto-engine.com\n")

    cortex.close()


if __name__ == "__main__":
    main()
