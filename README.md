# 🧠 Cortex Memory

**Persistent, human-like memory for AI agents.**

Your agent doesn't just store data — it *remembers*, *forgets*, *dreams*, and *feels*.

```
pip install cortex-memory
```

Zero dependencies. Pure Python. Drop it into any agent.

---

## Quickstart

```python
from cortex_memory import Cortex

cortex = Cortex("my_agent.db")

# Remember with emotional valence
cortex.remember(
    "Server crash at 3AM — lost 2 hours of work",
    type="episodic",
    tags=["incident", "server"],
    importance=0.9,
    emotion="fear",
)

cortex.remember(
    "Deploy pipeline reduced errors by 40%",
    type="episodic",
    tags=["deploy", "success"],
    importance=0.7,
    emotion="satisfaction",
)

# Recall — fear memories surface first when mood is vigilant
memories = cortex.recall_biased("server", mood="vigilant")

# Forget naturally — Ebbinghaus curves thin the herd
cortex.decay()

# Dream — reconsolidate during idle cycles
dreamed = cortex.dream()

# Check the mood
cortex.update_mood()
print(f"Mood: {cortex.mood} ({cortex.mood_confidence:.0%} confidence)")
```

---

## Features

### 🧬 Four Memory Types
| Type | Purpose | Example |
|------|---------|---------|
| **Episodic** | What happened | "Deploy failed at 2:30 AM" |
| **Semantic** | What things mean | "Redis typically uses port 6379" |
| **Procedural** | How to do things | "Run tests before merging" |
| **Relational** | How things connect | "Service A depends on Service B" |

### 💔 Emotional Valence
Six emotional states that weight how memories are stored and recalled:

- **Fear** — memories decay 50% slower (preserved for survival)
- **Satisfaction** — memories consolidate faster into knowledge
- **Surprise** — creates flashbulb memories immune to decay
- **Curiosity** — biases recall toward novel information
- **Frustration** — surfaces during agitated mood states
- **Neutral** — baseline processing

### 📉 Ebbinghaus Forgetting Curves
Memories don't just disappear — they fade according to the same curves discovered in 1885. Rehearsal (accessing a memory) extends its half-life. Important memories resist decay. Flashbulb memories are immune.

### 💤 Dream Reconsolidation
During idle cycles, the cortex replays high-importance memories:
- Confidence degrades slightly (reconsolidation is lossy, like human sleep)
- Linked memory connections strengthen
- Pattern discovery across the memory graph

### 🎭 Mood-Biased Recall
Three cognitive biases shape retrieval:
1. **Recency Bias** — recent memories get exponential boost (24h half-life)
2. **Confirmation Bias** — mood-congruent memories feel more relevant
3. **Availability Heuristic** — frequently accessed memories seem more significant

### 🔗 Memory Linking
Bidirectional connections between memories form a knowledge graph:

```python
cortex.link(memory_a.id, memory_b.id)
related = cortex.recall_linked(memory_a.id)
```

### 📊 Consolidation
Episodic memories that are accessed frequently graduate into semantic knowledge. The episode fades, the lesson remains.

---

## API Reference

### `Cortex(db_path: str)`
Create or connect to a memory database.

### `.remember(content, type, tags, importance, emotion, confidence, context) → Memory`
Store a memory with optional emotional valence.

### `.recall(query, limit, type) → list[Memory]`
Search memories by keyword (FTS5-powered).

### `.recall_biased(query, limit, mood) → list[Memory]`
Recall with cognitive biases applied.

### `.recall_by_type(type, limit) → list[Memory]`
Filter by memory type.

### `.recall_recent(hours, limit) → list[Memory]`
Time-windowed recall.

### `.recall_by_emotion(emotion, limit) → list[Memory]`
Filter by emotional valence.

### `.recall_linked(memory_id) → list[Memory]`
Traverse memory graph connections.

### `.forget(memory_id) → bool`
Targeted memory deletion.

### `.link(id_a, id_b)`
Create bidirectional memory link.

### `.decay(base_half_life_hours) → int`
Apply Ebbinghaus forgetting curves. Returns count of fully decayed memories.

### `.dream(max_memories) → list[dict]`
Run dream reconsolidation cycle.

### `.consolidate(max_age_hours) → list[Memory]`
Promote episodic → semantic memories.

### `.metabolize()`
Full lifecycle: emotional processing + decay + consolidation + mood update.

### `.update_mood() → (str, float)`
Recompute mood state from recent emotional history.

### `.stats() → dict`
Memory counts, type distribution, emotional distribution, mood, DB size.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                  Cortex                     │
│  ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ Remember │ │  Recall  │ │   Forget   │  │
│  └────┬─────┘ └────┬─────┘ └─────┬──────┘  │
│       │            │              │         │
│  ┌────▼────────────▼──────────────▼──────┐  │
│  │          SQLite + FTS5                │  │
│  └────┬─────────┬──────────┬─────────────┘  │
│       │         │          │                │
│  ┌────▼───┐ ┌───▼───┐ ┌───▼──────┐         │
│  │ Decay  │ │Dreams │ │ Emotions │         │
│  │Ebbing- │ │Recon- │ │ Valence  │         │
│  │haus    │ │solidat│ │ Layer    │         │
│  └────────┘ └───────┘ └──────────┘         │
│  ┌────────┐ ┌───────┐ ┌──────────┐         │
│  │Consolid│ │ Mood  │ │Cognitive │         │
│  │ation   │ │Engine │ │ Biases   │         │
│  └────────┘ └───────┘ └──────────┘         │
└─────────────────────────────────────────────┘
```

---

## The Full System

This SDK is the memory layer extracted from the **Manifesto Engine** — a living AI organism with 9 organ systems, a heartbeat, immune patrol, DNA-based pipeline breeding, and an LLM-powered brain.

Want the full living runtime? [Watch it in action →](https://youtube.com/@Gallix)

---

## License

MIT — use it anywhere, modify it freely, build something sovereign.

Built by [Manifesto Engine](https://manifesto-engine.com).
