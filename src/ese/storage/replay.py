"""Replay system for Dormammu.

The replay system reads a completed simulation from the database and
re-presents it turn by turn, optionally at different speeds. Useful for:
- Reviewing what happened in a long simulation
- Generating highlight reels
- Debugging unexpected agent behavior
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ese.storage.database import Database

logger = logging.getLogger(__name__)
console = Console()


class ReplaySystem:
    """Replays a simulation from the SQLite database.

    Usage
    -----
    replayer = ReplaySystem()
    replayer.replay("sim-uuid-1234", speed=2.0)
    """

    def __init__(self, db: Database | None = None) -> None:
        self.db = db or Database()

    def replay(self, simulation_id: str, speed: float = 1.0) -> None:
        """Replay all turns of a simulation.

        Args:
            simulation_id: The simulation to replay.
            speed: Playback speed multiplier. 1.0 = 1 second per turn,
                   2.0 = 0.5 seconds per turn, 0 = no delay (instant).
        """
        sim = self.db.get_simulation(simulation_id)
        if sim is None:
            console.print(f"[red]Simulation not found:[/] {simulation_id}")
            return

        turns = self.db.get_turns(simulation_id)
        if not turns:
            console.print("[yellow]No turns recorded for this simulation.[/]")
            return

        console.rule(f"[bold cyan]Replay: {sim.get('topic', simulation_id)}")
        console.print(
            f"Total turns: {len(turns)}  |  "
            f"Speed: {speed}x  |  "
            f"Total cost: ${sim.get('total_cost_usd', 0):.4f}"
        )
        console.print()

        delay = (1.0 / speed) if speed > 0 else 0.0

        for turn in turns:
            self._render_turn(turn)
            if delay > 0:
                time.sleep(delay)

        console.rule("[bold green]Replay complete")

    def _render_turn(self, turn: dict[str, Any]) -> None:
        """Render a single turn to the console."""
        turn_number = turn.get("turn_number", "?")
        year = turn.get("year", "?")
        narrative = turn.get("narrative", "(no narrative)")
        cost = turn.get("cost_usd", 0.0)

        # Parse events from JSON string if needed
        events_raw = turn.get("events_json", turn.get("events", "[]"))
        if isinstance(events_raw, str):
            try:
                events = json.loads(events_raw)
            except json.JSONDecodeError:
                events = []
        else:
            events = events_raw or []

        header = Text(f"Turn {turn_number}  |  Year {year}  |  ${cost:.4f}", style="bold blue")
        body_lines = [narrative, ""]
        if events:
            body_lines.append("Events:")
            for event in events[:5]:
                desc = event.get("description", str(event))
                body_lines.append(f"  - {desc}")

        panel = Panel(
            "\n".join(body_lines),
            title=str(header),
            border_style="blue",
        )
        console.print(panel)

    def export_jsonl(self, simulation_id: str, output_path: str) -> None:
        """Export all turns to a JSONL file.

        Args:
            simulation_id: The simulation to export.
            output_path: Destination file path.
        """
        turns = self.db.get_turns(simulation_id)
        with open(output_path, "w", encoding="utf-8") as f:
            for turn in turns:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
        console.print(f"Exported {len(turns)} turns to [cyan]{output_path}[/]")

    def get_highlights(
        self, simulation_id: str, top_n: int = 5
    ) -> list[dict[str, Any]]:
        """Return the top N turns ranked by event count (proxy for drama).

        Args:
            simulation_id: The simulation to analyze.
            top_n: Number of highlight turns to return.

        Returns:
            List of turn dicts sorted by event count descending.
        """
        turns = self.db.get_turns(simulation_id)

        def event_count(turn: dict[str, Any]) -> int:
            raw = turn.get("events_json", turn.get("events", "[]"))
            if isinstance(raw, str):
                try:
                    return len(json.loads(raw))
                except json.JSONDecodeError:
                    return 0
            return len(raw) if raw else 0

        return sorted(turns, key=event_count, reverse=True)[:top_n]
