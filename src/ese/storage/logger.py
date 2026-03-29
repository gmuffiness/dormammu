"""Full turn logging for Dormammu.

The TurnLogger captures everything that happens in a turn — world state,
agent actions, events, narrative — and persists it to the database and
optionally to a JSONL file for easy post-hoc analysis.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ese.engine.turn import TurnResult
    from ese.storage.database import Database

logger = logging.getLogger(__name__)


class TurnLogger:
    """Records each simulation turn to both SQLite and a JSONL log file.

    The JSONL file provides a human-readable audit trail and is suitable
    for streaming to external tools (e.g., a web dashboard).
    """

    def __init__(
        self,
        simulation_id: str,
        db: "Database",
        log_dir: Path | None = None,
    ) -> None:
        self.simulation_id = simulation_id
        self.db = db
        self.log_dir = log_dir
        self._jsonl_path: Path | None = None

        if log_dir is not None:
            log_dir.mkdir(parents=True, exist_ok=True)
            self._jsonl_path = log_dir / f"{simulation_id}.jsonl"
            logger.info("Turn log file: %s", self._jsonl_path)

    def log_turn(self, result: "TurnResult") -> None:
        """Persist a TurnResult to the database and JSONL log.

        Args:
            result: The completed TurnResult from TurnExecutor.
        """
        created_at = datetime.utcnow().isoformat()

        # Build the record dict
        record: dict[str, Any] = {
            "simulation_id": self.simulation_id,
            "turn_number": result.turn_number,
            "year": result.year,
            "narrative": result.narrative,
            "tokens_used": result.tokens_used,
            "cost_usd": result.cost_usd,
            "events": result.events,
            "agent_actions": result.agent_actions,
            "created_at": created_at,
        }

        # Persist world state snapshot
        if result.world_state is not None:
            self.db.save_world_state(result.world_state.to_dict())

        # Persist turn record
        self.db.insert_turn(simulation_id=self.simulation_id, turn_data=record)

        # Append to JSONL file
        if self._jsonl_path is not None:
            with self._jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        logger.info(
            "Logged turn %d (year %d) | tokens=%d cost=$%.4f",
            result.turn_number,
            result.year,
            result.tokens_used,
            result.cost_usd,
        )

    def log_event(self, event: dict[str, Any]) -> None:
        """Log a standalone event outside of a full turn (e.g., simulation start/end).

        Args:
            event: Arbitrary dict describing the event.
        """
        if self._jsonl_path is not None:
            event_record = {
                "simulation_id": self.simulation_id,
                "type": "event",
                "created_at": datetime.utcnow().isoformat(),
                **event,
            }
            with self._jsonl_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event_record, ensure_ascii=False) + "\n")
