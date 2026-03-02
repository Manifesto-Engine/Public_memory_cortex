"""Basic Agent — Cortex Memory in 20 lines.

Run: python examples/basic_agent.py
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cortex_memory import Cortex

cortex = Cortex("/tmp/basic_agent.db")

# Store some memories
cortex.remember("Python is the primary language", type="semantic",
                tags=["tech"], importance=0.8)
cortex.remember("Deployed v2.1 successfully", type="episodic",
                tags=["deploy"], importance=0.7, emotion="satisfaction")
cortex.remember("Database crashed during migration", type="episodic",
                tags=["incident", "database"], importance=0.9, emotion="fear")

# Recall by keyword
print("=== Recall: 'database' ===")
for m in cortex.recall("database"):
    print(f"  [{m.emotion}] {m.content} (importance={m.importance})")

# Recall by emotion
print("\n=== Fear memories ===")
for m in cortex.recall_by_emotion("fear"):
    print(f"  {m.content}")

# Stats
print(f"\n=== Stats ===")
stats = cortex.stats()
print(f"  Total memories: {stats['total_memories']}")
print(f"  By type: {stats['by_type']}")
print(f"  By emotion: {stats['by_emotion']}")

cortex.close()
print("\nDone. Database at /tmp/basic_agent.db")
