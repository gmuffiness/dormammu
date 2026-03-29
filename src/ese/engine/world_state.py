"""World state management for Dormammu.

WorldState captures the complete snapshot of the simulated world at a given
point in time: agents, resources, relationships, events, and any emergent
properties that arise from agent interactions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WorldState:
    """Immutable snapshot of the world at a specific simulation tick.

    Each turn produces a new WorldState derived from the previous one,
    preserving the full history of world evolution.
    """

    state_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    simulation_id: str = ""
    turn: int = 0
    year: int = 0

    # Core world data
    agents: dict[str, dict[str, Any]] = field(default_factory=dict)
    """agent_id -> agent snapshot dict"""

    relationships: dict[str, dict[str, float]] = field(default_factory=dict)
    """agent_id -> {other_agent_id -> affinity_score}"""

    events: list[dict[str, Any]] = field(default_factory=list)
    """Ordered list of events that occurred this turn"""

    resources: dict[str, float] = field(default_factory=dict)
    """Named world resources and their current levels"""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Arbitrary simulation-specific metadata"""

    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    # ------------------------------------------------------------------ #
    # Factory / serialization
    # ------------------------------------------------------------------ #

    @classmethod
    def initial(cls, simulation_id: str, topic: str) -> "WorldState":
        """Create the initial blank world state for a new simulation."""
        return cls(
            simulation_id=simulation_id,
            turn=0,
            year=0,
            metadata={"topic": topic, "phase": "genesis"},
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the world state to a plain dict for storage."""
        return {
            "state_id": self.state_id,
            "simulation_id": self.simulation_id,
            "turn": self.turn,
            "year": self.year,
            "agents": self.agents,
            "relationships": self.relationships,
            "events": self.events,
            "resources": self.resources,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        """Deserialize from a plain dict."""
        return cls(**data)

    # ------------------------------------------------------------------ #
    # Derived views
    # ------------------------------------------------------------------ #

    def summary(self) -> str:
        """Return a short human-readable summary for LLM prompts."""
        topic = self.metadata.get("topic", "")
        agent_names = [a.get("name", aid) for aid, a in self.agents.items()]
        event_summaries = [e.get("description", "") for e in self.events[-5:]]
        parts = []
        if topic:
            parts.append(f"Topic: {topic}")
        parts.append(f"Year {self.year}, Turn {self.turn}")
        if agent_names:
            parts.append(f"Agents: {', '.join(agent_names)}")
        if event_summaries:
            parts.append(f"Recent events: {'; '.join(event_summaries)}")
        resources_text = ", ".join(f"{k}: {v}" for k, v in self.resources.items())
        if resources_text:
            parts.append(f"Resources: {resources_text}")
        return ". ".join(parts) + "."

    def agent_count(self) -> int:
        return len(self.agents)

    def add_event(self, description: str, **kwargs: Any) -> None:
        """Append an event to this turn's event log."""
        self.events.append(
            {
                "turn": self.turn,
                "year": self.year,
                "description": description,
                "timestamp": datetime.utcnow().isoformat(),
                **kwargs,
            }
        )
