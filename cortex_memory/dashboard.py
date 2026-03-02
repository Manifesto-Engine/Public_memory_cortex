"""Dashboard — Live Terminal Visualization of the Cortex.

Watch your cortex breathe in real-time. Memories form, decay,
dreams fire, mood shifts — all rendered in your terminal.

    from cortex_memory.dashboard import run_dashboard
    run_dashboard("my_agent.db")

Or run directly:
    python -m cortex_memory.dashboard [db_path]

Requires a terminal that supports curses (most Unix terminals).
"""
from __future__ import annotations

import curses
import time
import random
import math
import json
import sys
import os
from pathlib import Path

# Add parent to path for standalone execution
sys.path.insert(0, str(Path(__file__).parent.parent))

from cortex_memory.core import Cortex
from cortex_memory.memory import MemoryType, Emotion


# ── Color Pairs ───────────────────────────────────────────

COLOR_HEADER = 1
COLOR_GREEN = 2
COLOR_DIM = 3
COLOR_YELLOW = 4
COLOR_RED = 5
COLOR_CYAN = 6
COLOR_MAGENTA = 7
COLOR_MOOD = 8

# ── Emotion Symbols ──────────────────────────────────────

EMOTION_ICONS = {
    "fear": "⚠",
    "curiosity": "?",
    "satisfaction": "✓",
    "surprise": "!",
    "frustration": "✗",
    "neutral": "·",
}

MOOD_ICONS = {
    "vigilant": "◉ VIGILANT",
    "agitated": "◈ AGITATED",
    "exploratory": "◎ EXPLORATORY",
    "confident": "◉ CONFIDENT",
    "alert": "◆ ALERT",
    "neutral": "○ NEUTRAL",
}


class Dashboard:
    """Curses-based real-time cortex visualization."""

    def __init__(self, db_path: str = "/tmp/cortex_dashboard.db"):
        self.cortex = Cortex(db_path)
        self.tick = 0
        self.log: list[str] = []
        self.dream_log: list[str] = []
        self.heartbeat_phase = 0
        self._events = [
            ("System detected anomalous login pattern", "fear", 0.85, ["security"]),
            ("API response time improved by 23%", "satisfaction", 0.6, ["performance"]),
            ("New dependency vulnerability in serde v1.0.210", "fear", 0.9, ["security", "deps"]),
            ("User reported intermittent 503 errors", "frustration", 0.7, ["infra", "bugs"]),
            ("Discovered novel caching strategy in recent paper", "curiosity", 0.65, ["research"]),
            ("Unexpected traffic spike from SEA region", "surprise", 0.8, ["traffic"]),
            ("Successfully deployed hotfix for auth bypass", "satisfaction", 0.85, ["security"]),
            ("Build pipeline stable for 72 hours straight", "satisfaction", 0.5, ["ci"]),
            ("Memory usage trending upward — possible leak", "curiosity", 0.75, ["infra"]),
            ("Failed SSH key rotation on node-7", "frustration", 0.6, ["ops"]),
            ("Penetration test: all 12 vectors defended", "satisfaction", 0.9, ["security"]),
            ("Unknown binary detected in /tmp on worker-3", "fear", 0.95, ["security", "threat"]),
            ("GraphQL schema auto-generated from cortex model", "curiosity", 0.7, ["tech"]),
            ("Redundant pod scaled down — cost optimization", "satisfaction", 0.4, ["infra"]),
            ("Latency spike correlated with DNS resolver change", "surprise", 0.65, ["network"]),
        ]
        self._event_idx = 0

    def _init_colors(self):
        """Initialize color pairs."""
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(COLOR_HEADER, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_GREEN, curses.COLOR_GREEN, -1)
        curses.init_pair(COLOR_DIM, 8, -1)  # Bright black / gray
        curses.init_pair(COLOR_YELLOW, curses.COLOR_YELLOW, -1)
        curses.init_pair(COLOR_RED, curses.COLOR_RED, -1)
        curses.init_pair(COLOR_CYAN, curses.COLOR_CYAN, -1)
        curses.init_pair(COLOR_MAGENTA, curses.COLOR_MAGENTA, -1)
        curses.init_pair(COLOR_MOOD, curses.COLOR_BLACK, curses.COLOR_GREEN)

    def _heartbeat_bar(self, width: int) -> str:
        """Generate an animated heartbeat line."""
        self.heartbeat_phase = (self.heartbeat_phase + 1) % width
        pattern = "─" * width
        beat_pos = self.heartbeat_phase

        if beat_pos < width - 4:
            p = list(pattern)
            p[beat_pos] = "╱"
            p[beat_pos + 1] = "█"
            p[beat_pos + 2] = "█"
            p[beat_pos + 3] = "╲"
            pattern = "".join(p)

        return pattern

    def _importance_bar(self, importance: float, width: int = 20) -> str:
        """Render an importance gauge."""
        filled = int(importance * width)
        return "█" * filled + "░" * (width - filled)

    def _emotion_color(self, emotion: str) -> int:
        """Get color pair for an emotion."""
        mapping = {
            "fear": COLOR_RED,
            "frustration": COLOR_RED,
            "curiosity": COLOR_CYAN,
            "satisfaction": COLOR_GREEN,
            "surprise": COLOR_YELLOW,
            "neutral": COLOR_DIM,
        }
        return curses.color_pair(mapping.get(emotion, COLOR_DIM))

    def _safe_addstr(self, win, y: int, x: int, text: str, attr=0):
        """Write to window, silently truncating at boundaries."""
        h, w = win.getmaxyx()
        if y >= h or x >= w:
            return
        max_len = w - x - 1
        if max_len <= 0:
            return
        try:
            win.addstr(y, x, text[:max_len], attr)
        except curses.error:
            pass

    def _draw_header(self, win, width: int):
        """Draw the top header bar."""
        hb = self._heartbeat_bar(min(30, width - 50))
        title = " CORTEX MEMORY COMPLEX "
        mood_str = MOOD_ICONS.get(self.cortex.mood, "○ NEUTRAL")

        self._safe_addstr(win, 0, 0, "┌" + "─" * (width - 2) + "┐")
        self._safe_addstr(win, 1, 0, "│")
        self._safe_addstr(win, 1, 2, "🧠", curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
        self._safe_addstr(win, 1, 5, title, curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
        self._safe_addstr(win, 1, 5 + len(title) + 2, hb, curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, 1, width - len(mood_str) - 3, mood_str,
                         curses.color_pair(COLOR_GREEN) | curses.A_BOLD)
        self._safe_addstr(win, 1, width - 1, "│")
        self._safe_addstr(win, 2, 0, "├" + "─" * (width - 2) + "┤")

    def _draw_stats(self, win, y: int, width: int) -> int:
        """Draw the stats panel. Returns next y position."""
        stats = self.cortex.stats()

        self._safe_addstr(win, y, 0, "│")
        self._safe_addstr(win, y, 2, "MEMORIES", curses.color_pair(COLOR_GREEN))
        val = str(stats["total_memories"])
        self._safe_addstr(win, y, 14, val, curses.color_pair(COLOR_GREEN) | curses.A_BOLD)

        self._safe_addstr(win, y, 22, "AVG IMP", curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, y, 32, f"{stats['avg_importance']:.3f}",
                         curses.color_pair(COLOR_YELLOW))

        self._safe_addstr(win, y, 42, "CONFIDENCE", curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, y, 55, f"{stats['avg_confidence']:.3f}",
                         curses.color_pair(COLOR_CYAN))

        mood_conf = f"{self.cortex.mood_confidence:.0%}"
        self._safe_addstr(win, y, 65, "MOOD CONF", curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, y, 77, mood_conf, curses.color_pair(COLOR_GREEN))
        self._safe_addstr(win, y, width - 1, "│")

        y += 1
        # Type distribution
        self._safe_addstr(win, y, 0, "│")
        self._safe_addstr(win, y, 2, "TYPES", curses.color_pair(COLOR_DIM))
        x = 10
        for t, count in stats.get("by_type", {}).items():
            label = f"{t[:4]}:{count} "
            self._safe_addstr(win, y, x, label, curses.color_pair(COLOR_CYAN))
            x += len(label)

        # Emotion distribution
        self._safe_addstr(win, y, 45, "EMOTIONS", curses.color_pair(COLOR_DIM))
        x = 56
        for em, count in stats.get("by_emotion", {}).items():
            icon = EMOTION_ICONS.get(em, "·")
            label = f"{icon}{count} "
            self._safe_addstr(win, y, x, label, self._emotion_color(em))
            x += len(label)
        self._safe_addstr(win, y, width - 1, "│")

        y += 1
        self._safe_addstr(win, y, 0, "├" + "─" * (width - 2) + "┤")
        return y + 1

    def _draw_memory_ticker(self, win, y: int, width: int, height: int) -> int:
        """Draw the memory event ticker. Returns next y position."""
        self._safe_addstr(win, y, 0, "│")
        self._safe_addstr(win, y, 2, "◀ MEMORY STREAM ▶", curses.color_pair(COLOR_GREEN))
        self._safe_addstr(win, y, width - 1, "│")
        y += 1

        # Show last N log entries that fit
        max_entries = min(8, height - y - 12)
        visible = self.log[-max_entries:] if self.log else []

        for entry in visible:
            self._safe_addstr(win, y, 0, "│")
            self._safe_addstr(win, y, 2, entry[:width - 4])
            self._safe_addstr(win, y, width - 1, "│")
            y += 1

        # Fill remaining rows
        while y < height - 10:
            self._safe_addstr(win, y, 0, "│")
            self._safe_addstr(win, y, width - 1, "│")
            y += 1
            if y >= height - 10:
                break

        self._safe_addstr(win, y, 0, "├" + "─" * (width - 2) + "┤")
        return y + 1

    def _draw_dream_panel(self, win, y: int, width: int) -> int:
        """Draw the dream reconsolidation panel."""
        self._safe_addstr(win, y, 0, "│")
        self._safe_addstr(win, y, 2, "💤 DREAMS", curses.color_pair(COLOR_MAGENTA))
        self._safe_addstr(win, y, width - 1, "│")
        y += 1

        visible = self.dream_log[-3:] if self.dream_log else ["  (no dreams yet — waiting for idle cycle)"]
        for entry in visible:
            self._safe_addstr(win, y, 0, "│")
            self._safe_addstr(win, y, 2, entry[:width - 4], curses.color_pair(COLOR_DIM))
            self._safe_addstr(win, y, width - 1, "│")
            y += 1

        self._safe_addstr(win, y, 0, "├" + "─" * (width - 2) + "┤")
        return y + 1

    def _draw_footer(self, win, y: int, width: int):
        """Draw the bottom bar."""
        self._safe_addstr(win, y, 0, "│")
        pulse_str = f"  PULSE #{self.tick}  "
        elapsed = f"  {self.tick * 2}s elapsed  "
        self._safe_addstr(win, y, 2, pulse_str, curses.color_pair(COLOR_GREEN))
        self._safe_addstr(win, y, 2 + len(pulse_str) + 2,
                         "Press 'q' to exit",
                         curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, y, width - len(elapsed) - 2, elapsed,
                         curses.color_pair(COLOR_DIM))
        self._safe_addstr(win, y, width - 1, "│")
        y += 1
        self._safe_addstr(win, y, 0, "└" + "─" * (width - 2) + "┘")

    def _tick_simulation(self):
        """Run one simulation tick — encode, decay, dream, mood."""
        self.tick += 1

        # Every tick: maybe encode a new memory
        if self.tick % 2 == 0 and self._event_idx < len(self._events):
            content, emotion, importance, tags = self._events[self._event_idx]
            mem = self.cortex.remember(
                content, type="episodic",
                tags=tags, importance=importance, emotion=emotion,
            )
            icon = EMOTION_ICONS.get(emotion, "·")
            self.log.append(f"  {icon} ENCODE [{emotion:13s}] {content[:55]}")
            self._event_idx += 1

            # Link related memories (every 3rd)
            if self._event_idx >= 3 and self._event_idx % 3 == 0:
                recent = self.cortex.recall_recent(hours=1, limit=3)
                if len(recent) >= 2:
                    self.cortex.link(recent[0].id, recent[1].id)
                    self.log.append(f"  ↔ LINKED '{recent[0].content[:25]}' ↔ '{recent[1].content[:25]}'")

        # Every 5th tick: metabolism
        if self.tick % 5 == 0:
            self.cortex.metabolize()
            self.cortex.update_mood()
            self.log.append(f"  ⚙ METABOLIZE  mood={self.cortex.mood} ({self.cortex.mood_confidence:.0%})")

        # Every 7th tick: decay
        if self.tick % 7 == 0:
            decayed = self.cortex.decay()
            if decayed:
                self.log.append(f"  📉 DECAY  {decayed} memories faded below threshold")

        # Every 8th tick: dream
        if self.tick % 8 == 0:
            dreamed = self.cortex.dream(max_memories=2)
            for d in dreamed:
                self.dream_log.append(
                    f"  🌙 {d['content_preview'][:45]}  "
                    f"conf: {d['confidence_before']:.2f}→{d['confidence_after']:.2f}"
                )

        # Every 10th tick: consolidation
        if self.tick % 10 == 0:
            consolidated = self.cortex.consolidate()
            if consolidated:
                self.log.append(f"  🔄 CONSOLIDATED  {len(consolidated)} episodic → semantic")

        # Recycle events
        if self._event_idx >= len(self._events):
            self._event_idx = 0

        # Cap logs
        self.log = self.log[-30:]
        self.dream_log = self.dream_log[-10:]

    def run(self, stdscr):
        """Main dashboard loop."""
        curses.curs_set(0)
        stdscr.nodelay(True)
        stdscr.timeout(2000)  # 2-second refresh
        self._init_colors()

        while True:
            try:
                key = stdscr.getch()
                if key == ord("q") or key == ord("Q"):
                    break
            except Exception:
                pass

            # Simulate one tick
            self._tick_simulation()

            # Render
            stdscr.clear()
            height, width = stdscr.getmaxyx()

            if height < 20 or width < 60:
                self._safe_addstr(stdscr, 0, 0,
                                 "Terminal too small. Need 60x20 minimum.",
                                 curses.color_pair(COLOR_RED))
                stdscr.refresh()
                continue

            self._draw_header(stdscr, width)
            y = self._draw_stats(stdscr, 3, width)
            y = self._draw_memory_ticker(stdscr, y, width, height)
            y = self._draw_dream_panel(stdscr, y, width)
            self._draw_footer(stdscr, y, width)

            stdscr.refresh()

        self.cortex.close()


def run_dashboard(db_path: str = "/tmp/cortex_dashboard.db"):
    """Launch the live cortex dashboard.

    Args:
        db_path: Path to the cortex SQLite database.
    """
    dashboard = Dashboard(db_path)
    curses.wrapper(dashboard.run)


if __name__ == "__main__":
    db = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cortex_dashboard.db"
    print(f"Launching Cortex Dashboard → {db}")
    print("Press 'q' to exit.\n")
    run_dashboard(db)
