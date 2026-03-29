"""SQLite database management for Dormammu.

All simulation data is persisted to a local SQLite database via sqlite-utils.
Tables:
  simulations   — top-level simulation metadata
  turns         — per-turn results and narratives
  world_states  — serialized world state snapshots
  agents        — agent snapshots per turn
  hypotheses    — hypothesis records per scenario node
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import sqlite_utils

from ese.config import config

logger = logging.getLogger(__name__)


class Database:
    """Thin wrapper around sqlite-utils for Dormammu persistence.

    All methods are synchronous; they should be called from a thread
    executor if used inside async code.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or config.db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._open_db()
        except Exception:
            # DB is corrupted — remove and recreate
            logger.warning("Database corrupted at %s — recreating", self.db_path)
            for suffix in ("", "-wal", "-shm"):
                p = Path(str(self.db_path) + suffix)
                if p.exists():
                    p.unlink()
            self._open_db()
        logger.debug("Database opened at %s", self.db_path)

    def _open_db(self) -> None:
        """Open the SQLite database with WAL mode and busy timeout."""
        self._db = sqlite_utils.Database(str(self.db_path))
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.execute("PRAGMA busy_timeout=30000")
        self._ensure_tables()

    # ------------------------------------------------------------------ #
    # Schema
    # ------------------------------------------------------------------ #

    def _ensure_tables(self) -> None:
        """Create tables if they don't exist and apply migrations."""
        if "simulations" not in self._db.table_names():
            self._db["simulations"].create(
                {
                    "id": str,
                    "topic": str,
                    "status": str,
                    "max_depth": int,
                    "node_years": int,
                    "cost_limit": float,
                    "openai_model": str,
                    "total_cost_usd": float,
                    "turns": int,
                    "current_node_id": str,
                    "evaluation_criteria": str,
                    "created_at": str,
                    "updated_at": str,
                },
                pk="id",
            )

        if "turns" not in self._db.table_names():
            self._db["turns"].create(
                {
                    "id": int,
                    "simulation_id": str,
                    "turn_number": int,
                    "year": int,
                    "narrative": str,
                    "tokens_used": int,
                    "cost_usd": float,
                    "events_json": str,
                    "agent_actions_json": str,
                    "created_at": str,
                },
                pk="id",
            )

        if "world_states" not in self._db.table_names():
            self._db["world_states"].create(
                {
                    "state_id": str,
                    "simulation_id": str,
                    "turn": int,
                    "year": int,
                    "state_json": str,
                    "created_at": str,
                },
                pk="state_id",
            )

        if "hypotheses" not in self._db.table_names():
            self._db["hypotheses"].create(
                {
                    "node_id": str,
                    "simulation_id": str,
                    "parent_id": str,
                    "depth": int,
                    "title": str,
                    "description": str,
                    "probability": float,
                    "tags_json": str,
                    "sf_inspired": int,
                    "character_fidelity_score": float,
                    "fandom_resonance_score": float,
                    "emergence_score": float,
                    "diversity_score": float,
                    "plausibility_score": float,
                    "foreshadowing_score": float,
                    "created_at": str,
                },
                pk="node_id",
            )
        else:
            # Migration: add evaluation score columns if they don't exist
            table = self._db["hypotheses"]
            existing_columns = {col.name for col in table.columns}
            for col in [
                "character_fidelity_score",
                "fandom_resonance_score",
                "emergence_score",
                "diversity_score",
                "plausibility_score",
                "foreshadowing_score",
            ]:
                if col not in existing_columns:
                    logger.info("Migrating: adding column '%s' to hypotheses table", col)
                    table.add_column(col, float)

    # ------------------------------------------------------------------ #
    # Simulations
    # ------------------------------------------------------------------ #

    def upsert_simulation(self, data: dict[str, Any]) -> None:
        """Insert or update a simulation record."""
        row = {"id": data["simulation_id"], **data}
        # Remove simulation_id since the DB uses 'id' as the primary key
        row.pop("simulation_id", None)
        # Serialize evaluation_criteria list to JSON string for SQLite
        if "evaluation_criteria" in row and not isinstance(row["evaluation_criteria"], str):
            row["evaluation_criteria"] = json.dumps(row["evaluation_criteria"], ensure_ascii=False)
        self._db["simulations"].upsert(row, pk="id")

    def get_simulation(self, simulation_id: str) -> dict[str, Any] | None:
        """Fetch a simulation by ID, or None if not found."""
        try:
            return dict(self._db["simulations"].get(simulation_id))
        except sqlite_utils.db.NotFoundError:
            return None

    def list_simulations(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return recent simulations ordered by created_at descending."""
        return [
            dict(row)
            for row in self._db["simulations"].rows_where(
                order_by="created_at desc", limit=limit
            )
        ]

    # ------------------------------------------------------------------ #
    # Turns
    # ------------------------------------------------------------------ #

    def insert_turn(self, simulation_id: str, turn_data: dict[str, Any]) -> None:
        """Append a turn record to the database."""
        self._db["turns"].insert(
            {
                "simulation_id": simulation_id,
                "turn_number": turn_data["turn_number"],
                "year": turn_data.get("year", 0),
                "narrative": turn_data.get("narrative", ""),
                "tokens_used": turn_data.get("tokens_used", 0),
                "cost_usd": turn_data.get("cost_usd", 0.0),
                "events_json": json.dumps(turn_data.get("events", []), ensure_ascii=False),
                "agent_actions_json": json.dumps(
                    turn_data.get("agent_actions", {}), ensure_ascii=False
                ),
                "created_at": turn_data.get("created_at", ""),
            }
        )

    def get_turns(self, simulation_id: str) -> list[dict[str, Any]]:
        """Return all turns for a simulation, ordered by turn_number."""
        return [
            dict(row)
            for row in self._db["turns"].rows_where(
                "simulation_id = ?", [simulation_id], order_by="turn_number"
            )
        ]

    # ------------------------------------------------------------------ #
    # World states
    # ------------------------------------------------------------------ #

    def save_world_state(self, world_state_dict: dict[str, Any]) -> None:
        """Persist a world state snapshot."""
        self._db["world_states"].insert(
            {
                "state_id": world_state_dict["state_id"],
                "simulation_id": world_state_dict["simulation_id"],
                "turn": world_state_dict["turn"],
                "year": world_state_dict["year"],
                "state_json": json.dumps(world_state_dict, ensure_ascii=False),
                "created_at": world_state_dict.get("created_at", ""),
            },
            replace=True,
        )

    def get_world_state(self, state_id: str) -> dict[str, Any] | None:
        """Fetch a world state by ID."""
        try:
            row = dict(self._db["world_states"].get(state_id))
            return json.loads(row["state_json"])
        except (sqlite_utils.db.NotFoundError, KeyError):
            return None

    def get_world_state_by_turn(self, simulation_id: str, turn: int) -> dict[str, Any] | None:
        """Fetch the world state for a specific turn of a simulation."""
        rows = list(
            self._db["world_states"].rows_where(
                "simulation_id = ? AND turn = ?",
                [simulation_id, turn],
                limit=1,
            )
        )
        if not rows:
            return None
        try:
            return json.loads(rows[0]["state_json"])
        except (KeyError, json.JSONDecodeError):
            return None

    def get_hypotheses(self, simulation_id: str) -> list[dict[str, Any]]:
        """Return all hypotheses for a simulation."""
        return [
            dict(row)
            for row in self._db["hypotheses"].rows_where(
                "simulation_id = ?", [simulation_id], order_by="depth"
            )
        ]

    # ------------------------------------------------------------------ #
    # Hypotheses
    # ------------------------------------------------------------------ #

    def save_hypothesis(self, node_id: str, simulation_id: str, hyp_data: dict[str, Any]) -> None:
        """Persist a hypothesis record."""
        self._db["hypotheses"].insert(
            {
                "node_id": node_id,
                "simulation_id": simulation_id,
                "parent_id": hyp_data.get("parent_id", ""),
                "depth": hyp_data.get("depth", 0),
                "title": hyp_data.get("title", ""),
                "description": hyp_data.get("description", ""),
                "probability": hyp_data.get("probability", 0.5),
                "tags_json": json.dumps(hyp_data.get("tags", []), ensure_ascii=False),
                "sf_inspired": int(hyp_data.get("sf_inspired", False)),
                "character_fidelity_score": hyp_data.get("character_fidelity_score"),
                "fandom_resonance_score": hyp_data.get("fandom_resonance_score"),
                "emergence_score": hyp_data.get("emergence_score"),
                "diversity_score": hyp_data.get("diversity_score"),
                "plausibility_score": hyp_data.get("plausibility_score"),
                "foreshadowing_score": hyp_data.get("foreshadowing_score"),
                "created_at": hyp_data.get("created_at", ""),
            },
            replace=True,
        )
