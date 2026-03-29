"""Agent base class for Dormammu.

An Agent is a stateful simulation entity that:
- Has a stable Persona (identity, goals, traits)
- Maintains a memory of past events
- Decides actions each turn via LLM
- Can interact with other agents
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from ese.agents.persona import Persona

if TYPE_CHECKING:
    from ese.agents.interaction import AgentInteraction
    from ese.engine.world_state import WorldState

logger = logging.getLogger(__name__)

# Maximum memory entries to include in the LLM context window
MAX_MEMORY_CONTEXT = 20


@dataclass
class Memory:
    """A single memory entry for an agent."""

    turn: int
    year: int
    description: str
    emotional_weight: float = 0.5
    """0 = trivial, 1 = life-defining. High-weight memories persist longer."""
    tags: list[str] = field(default_factory=list)


@dataclass
class Agent:
    """A simulation agent with persona, memory, and LLM-driven decision-making.

    State (mood, energy, relationship scores) evolves each turn.
    Memory is a rolling list capped at MAX_MEMORY_CONTEXT for LLM context efficiency.
    """

    agent_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    persona: Persona = field(default_factory=Persona)
    simulation_id: str = ""

    # Mutable state
    mood: float = 0.5
    """0 = miserable, 1 = elated"""
    energy: float = 1.0
    """0 = exhausted, 1 = fully rested"""
    alive: bool = True

    memories: list[Memory] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)
    """other_agent_id -> affinity score in [-1, 1]"""

    openai_model: str = "gpt-4o"
    language: str = "en"

    # Lazily initialized — not included in dataclass serialization
    _interaction_instance: Any = field(default=None, init=False, repr=False, compare=False)

    # ------------------------------------------------------------------ #
    # Core interface
    # ------------------------------------------------------------------ #

    @property
    def _interaction(self) -> "AgentInteraction":
        """Lazily create an AgentInteraction instance."""
        if self._interaction_instance is None:
            from ese.agents.interaction import AgentInteraction
            from ese.config import config

            self._interaction_instance = AgentInteraction(
                api_key=config.openai_api_key,
                model=config.openai_model or self.openai_model,
            )
        return self._interaction_instance

    async def decide_action(
        self, world_state: "WorldState"
    ) -> tuple[dict[str, Any], int]:
        """Choose an action for this turn given the current world state.

        Args:
            world_state: Current world snapshot.

        Returns:
            A tuple of (action_dict, tokens_used).
            action_dict must contain at least {"type": str}.
        """
        import json

        from ese.config import config

        fallback_action = {
            "type": "observe",
            "description": f"{self.persona.name} observes the world.",
            "target": None,
        }

        if not config.openai_api_key:
            logger.debug("Agent %s: no API key, returning fallback action.", self.agent_id)
            return fallback_action, 0

        system_prompt = self.persona.to_prompt_block()
        user_prompt = self._build_action_prompt(world_state)

        logger.debug("Agent %s calling LLM for action decision.", self.agent_id)
        try:
            response = await self._interaction.get_action(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
        except Exception as exc:
            logger.warning(
                "Agent %s: LLM call failed (%s), using fallback action.", self.agent_id, exc
            )
            return fallback_action, 0

        try:
            data = json.loads(response.content)
            action = {
                "type": str(data.get("type", "observe")),
                "target": data.get("target"),
                "description": str(data.get("description", "")),
            }
            if action["type"] not in {"interact", "observe", "idle"}:
                action["type"] = "observe"
        except (json.JSONDecodeError, AttributeError) as exc:
            logger.warning(
                "Agent %s: failed to parse action JSON (%s), using fallback.", self.agent_id, exc
            )
            action = fallback_action

        tokens_used = response.tokens_total
        logger.debug("Agent %s decided: %s (tokens=%d)", self.agent_id, action["type"], tokens_used)

        self.remember(
            description=action.get("description") or f"{self.persona.name} {action['type']}d.",
            turn=world_state.turn,
            year=world_state.year,
            emotional_weight=0.4,
            tags=[action["type"]],
        )

        return action, tokens_used

    def remember(self, description: str, turn: int, year: int, emotional_weight: float = 0.5, tags: list[str] | None = None) -> None:
        """Add a memory entry, pruning low-weight memories when over capacity."""
        self.memories.append(
            Memory(
                turn=turn,
                year=year,
                description=description,
                emotional_weight=emotional_weight,
                tags=tags or [],
            )
        )
        # Prune: keep all high-weight memories, drop oldest low-weight ones
        if len(self.memories) > MAX_MEMORY_CONTEXT * 2:
            self.memories.sort(key=lambda m: (-m.emotional_weight, -m.turn))
            self.memories = self.memories[:MAX_MEMORY_CONTEXT]

    def recent_memories(self, n: int = MAX_MEMORY_CONTEXT) -> list[Memory]:
        """Return the n most recent memories, biased toward high emotional weight."""
        sorted_mem = sorted(self.memories, key=lambda m: (-m.emotional_weight, -m.turn))
        return sorted_mem[:n]

    def update_relationship(self, other_id: str, delta: float) -> None:
        """Adjust affinity toward another agent by delta, clamped to [-1, 1]."""
        current = self.relationships.get(other_id, 0.0)
        self.relationships[other_id] = max(-1.0, min(1.0, current + delta))

    # ------------------------------------------------------------------ #
    # Prompt construction
    # ------------------------------------------------------------------ #

    def _build_action_prompt(self, world_state: "WorldState") -> str:
        """Build the LLM prompt for action decision."""
        memory_text = "\n".join(
            f"- [{m.year}] {m.description}" for m in self.recent_memories(10)
        )

        # Build list of other agents the agent can interact with
        other_agents = []
        for aid, adata in world_state.agents.items():
            if aid != self.agent_id:
                name = adata.get("name", aid) if isinstance(adata, dict) else aid
                other_agents.append(f"  - {aid} ({name})")
        agent_list_text = "\n".join(other_agents) if other_agents else "  (no other agents)"

        lang_instruction = ""
        if self.language != "en":
            lang_names = {"ko": "Korean", "ja": "Japanese", "zh": "Chinese", "es": "Spanish", "fr": "French", "de": "German"}
            lang_name = lang_names.get(self.language, self.language)
            lang_instruction = f"\nIMPORTANT: Write the description field in {lang_name}.\n"

        return (
            f"You are {self.persona.name}.\n"
            f"{self.persona.to_prompt_block()}\n\n"
            f"Current world state:\n{world_state.summary()}\n\n"
            f"Your recent memories:\n{memory_text or 'None'}\n\n"
            f"Available agents to interact with:\n{agent_list_text}\n\n"
            "When choosing \"interact\", the \"target\" field MUST be one of the agent IDs listed above "
            "(the UUID, not the name).\n\n"
            f"{lang_instruction}"
            "What do you do this turn? Respond with a JSON action object:\n"
            '{"type": "interact|observe|idle", "target": "<agent_id or null>", "description": "..."}'
        )

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "persona": self.persona.to_dict(),
            "simulation_id": self.simulation_id,
            "mood": self.mood,
            "energy": self.energy,
            "alive": self.alive,
            "relationships": self.relationships,
            "memory_count": len(self.memories),
        }
