"""Core simulation engine for Dormammu.

The Simulation class is the top-level coordinator for a single simulation run.
It owns the scenario tree, the current world state, and the list of active agents,
and delegates turn execution to TurnExecutor.
"""

from __future__ import annotations

import asyncio
import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ese.engine.scenario_tree import ScenarioNode, ScenarioTree
from ese.engine.turn import TurnExecutor, TurnResult
from ese.engine.world_state import WorldState

logger = logging.getLogger(__name__)


class SimulationStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class SimulationConfig:
    """Immutable configuration for a single simulation run."""

    topic: str
    max_depth: int = 5
    node_years: int = 100
    cost_limit: float = 10.0
    openai_model: str = "gpt-4o"
    language: str = "en"


@dataclass
class Simulation:
    """Represents a single, complete simulation run.

    Lifecycle
    ---------
    1. Created with a topic and config.
    2. `initialize()` sets up root world state and agents.
    3. `run()` drives the DFS loop until complete or cost-limited.
    4. Results are persisted to SQLite via the Storage layer.
    """

    simulation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    config: SimulationConfig = field(default_factory=lambda: SimulationConfig(topic=""))
    status: SimulationStatus = SimulationStatus.CREATED

    scenario_tree: ScenarioTree | None = None
    current_world_state: WorldState | None = None
    agents: list[Any] = field(default_factory=list)

    turn_results: list[TurnResult] = field(default_factory=list)
    total_cost_usd: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # DFS node tracking
    current_node_id: str | None = None
    """ID of the node currently being simulated."""

    evaluation_criteria: list[dict[str, str]] = field(default_factory=list)
    """User-defined evaluation criteria: [{'name': str, 'description': str}]"""

    # Per-node world state snapshots keyed by node_id
    _node_world_states: dict[str, WorldState] = field(default_factory=dict)

    # ------------------------------------------------------------------ #
    # Lifecycle
    # ------------------------------------------------------------------ #

    def initialize(self) -> None:
        """Set up the initial world state, scenario tree, and agents."""
        logger.info("Initializing simulation %s: %s", self.simulation_id, self.config.topic)

        self.scenario_tree = ScenarioTree(
            simulation_id=self.simulation_id,
            max_depth=self.config.max_depth,
        )
        root = self.scenario_tree.create_root(hypothesis=f"Genesis: {self.config.topic}")

        self.current_world_state = WorldState.initial(
            simulation_id=self.simulation_id,
            topic=self.config.topic,
        )

        # Store the genesis world state for the root node
        self._node_world_states[root.node_id] = copy.deepcopy(self.current_world_state)

        self.status = SimulationStatus.CREATED
        logger.info(
            "Simulation initialized with root world state %s", self.current_world_state.state_id
        )

    def get_world_state_for_node(self, node: ScenarioNode) -> WorldState:
        """Return the entry world state for a node, inheriting from parent if needed.

        Args:
            node: The scenario node to get the world state for.

        Returns:
            A deep copy of the appropriate WorldState for this node.
        """
        if node.node_id in self._node_world_states:
            return copy.deepcopy(self._node_world_states[node.node_id])

        # Fall back to parent's final world state
        if node.parent_id and node.parent_id in self._node_world_states:
            parent_state = copy.deepcopy(self._node_world_states[node.parent_id])
            # Stamp with node context
            parent_state.metadata["node_id"] = node.node_id
            parent_state.metadata["hypothesis"] = node.hypothesis
            return parent_state

        # Ultimate fallback: fresh world state
        logger.warning(
            "No parent world state found for node %s; using fresh state.", node.node_id
        )
        return WorldState.initial(
            simulation_id=self.simulation_id,
            topic=self.config.topic,
        )

    def snapshot_node_exit_state(self, node_id: str, world_state: WorldState) -> None:
        """Record the final world state after completing a node's turns.

        This state is inherited by child nodes when expanding.

        Args:
            node_id: The completed node's ID.
            world_state: The world state at the end of this node's simulation.
        """
        self._node_world_states[node_id] = copy.deepcopy(world_state)
        logger.debug("Snapshotted exit state for node %s", node_id)

    # ------------------------------------------------------------------ #
    # Turn execution (used by OrchestratorLoop per-node)
    # ------------------------------------------------------------------ #

    async def run_turn(self) -> TurnResult | None:
        """Execute the next pending turn.

        This method is retained for backward compatibility and simple use cases.
        The OrchestratorLoop uses run_turn_for_node() for DFS-aware execution.

        Returns:
            The TurnResult, or None if there are no more turns to run.
        """
        if self.scenario_tree is None or self.current_world_state is None:
            raise RuntimeError("Simulation not initialized. Call initialize() first.")

        next_node = self.scenario_tree.next_pending()
        if next_node is None:
            logger.info("No pending nodes. Simulation complete.")
            self.status = SimulationStatus.COMPLETE
            return None

        if self.total_cost_usd >= self.config.cost_limit:
            logger.warning(
                "Cost limit $%.2f reached (spent $%.2f). Pausing.",
                self.config.cost_limit,
                self.total_cost_usd,
            )
            self.status = SimulationStatus.PAUSED
            return None

        self.status = SimulationStatus.RUNNING
        executor = TurnExecutor(openai_model=self.config.openai_model, language=self.config.language)

        turn_number = len(self.turn_results) + 1
        result = await executor.execute(
            turn_number=turn_number,
            world_state=self.current_world_state,
            agents=self.agents,
        )

        self.turn_results.append(result)
        self.current_world_state = result.world_state
        self.total_cost_usd += result.cost_usd
        self.updated_at = datetime.utcnow().isoformat()

        logger.info(
            "Turn %d complete. Cost: $%.4f (total: $%.4f)",
            turn_number,
            result.cost_usd,
            self.total_cost_usd,
        )
        return result

    async def run_turn_for_node(
        self,
        node: ScenarioNode,
        world_state: WorldState,
        turn_number: int,
        years_per_turn: int = 1,
    ) -> TurnResult | None:
        """Execute a single turn within the context of a specific node.

        Args:
            node: The scenario node being simulated.
            world_state: Current world state for this turn.
            turn_number: Sequential turn index (global across the simulation).
            years_per_turn: How many simulated years advance per turn.

        Returns:
            TurnResult, or None if cost limit reached.
        """
        if self.total_cost_usd >= self.config.cost_limit:
            logger.warning(
                "Cost limit $%.2f reached (spent $%.2f). Pausing.",
                self.config.cost_limit,
                self.total_cost_usd,
            )
            self.status = SimulationStatus.PAUSED
            return None

        self.status = SimulationStatus.RUNNING
        self.current_node_id = node.node_id

        executor = TurnExecutor(openai_model=self.config.openai_model, language=self.config.language)
        result = await executor.execute(
            turn_number=turn_number,
            world_state=world_state,
            agents=self.agents,
        )

        # Advance the simulated year on the resulting state
        result.world_state.year = world_state.year + years_per_turn
        result.world_state.turn = turn_number

        self.turn_results.append(result)
        self.total_cost_usd += result.cost_usd
        self.updated_at = datetime.utcnow().isoformat()

        logger.info(
            "Node %s | Turn %d | Year %d | Cost: $%.4f (total: $%.4f)",
            node.node_id[:8],
            turn_number,
            result.world_state.year,
            result.cost_usd,
            self.total_cost_usd,
        )
        return result

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "topic": self.config.topic,
            "status": self.status.value,
            "max_depth": self.config.max_depth,
            "node_years": self.config.node_years,
            "cost_limit": self.config.cost_limit,
            "openai_model": self.config.openai_model,
            "total_cost_usd": self.total_cost_usd,
            "turns": len(self.turn_results),
            "current_node_id": self.current_node_id,
            "evaluation_criteria": self.evaluation_criteria,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
