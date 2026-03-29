"""Turn execution for Dormammu.

A "turn" represents one discrete time step in the simulation.
Each turn:
  1. Collects agent actions via LLM calls
  2. Resolves interactions between agents
  3. Updates the world state
  4. Records events and logs
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ese.agents.agent import Agent
    from ese.agents.interaction import AgentInteraction, LLMResponse
    from ese.engine.world_state import WorldState

logger = logging.getLogger(__name__)


@dataclass
class TurnResult:
    """Output produced by executing a single turn."""

    turn_number: int
    year: int
    world_state: "WorldState"
    agent_actions: dict[str, dict[str, Any]] = field(default_factory=dict)
    """agent_id -> action dict"""
    events: list[dict[str, Any]] = field(default_factory=list)
    narrative: str = ""
    """LLM-generated narrative summary of this turn"""
    tokens_used: int = 0
    cost_usd: float = 0.0


class TurnExecutor:
    """Executes a single simulation turn.

    Responsibilities:
    - Ask each agent what it wants to do given the current world state
    - Resolve conflicts and side effects between agent actions
    - Produce an updated WorldState and a narrative summary
    """

    def __init__(self, openai_model: str | None = None, language: str = "en") -> None:
        from ese.config import config

        self.openai_model = openai_model or config.openai_model
        self.language = language
        self._api_key: str = config.openai_api_key
        self._interaction_instance: "AgentInteraction | None" = None

    @property
    def _interaction(self) -> "AgentInteraction":
        """Lazily create a shared AgentInteraction for turn-level LLM calls."""
        if self._interaction_instance is None:
            from ese.agents.interaction import AgentInteraction

            self._interaction_instance = AgentInteraction(
                api_key=self._api_key, model=self.openai_model
            )
        return self._interaction_instance

    async def execute(
        self,
        turn_number: int,
        world_state: "WorldState",
        agents: list["Agent"],
    ) -> TurnResult:
        """Execute one turn and return the result.

        Args:
            turn_number: The sequential turn index.
            world_state: The world state at the start of this turn.
            agents: All active agents in the simulation.

        Returns:
            A TurnResult containing the updated world state and narrative.
        """
        import copy

        logger.info("Executing turn %d (year %d)", turn_number, world_state.year)

        new_state = copy.deepcopy(world_state)
        new_state.turn = turn_number
        new_state.events = []

        agent_actions: dict[str, dict[str, Any]] = {}
        total_tokens = 0

        # Phase 1: Collect agent actions
        for agent in agents:
            action, tokens = await agent.decide_action(world_state)
            agent_actions[agent.agent_id] = action
            total_tokens += tokens
            logger.debug("Agent %s chose action: %s", agent.agent_id, action.get("type"))

        # Phase 2: Resolve interactions
        events, interaction_tokens = await self._resolve_interactions(
            agent_actions, new_state, agents
        )
        total_tokens += interaction_tokens
        for event in events:
            new_state.add_event(**event)

        # Phase 3: Generate narrative summary
        narrative, narrative_tokens = await self._generate_narrative(new_state, agent_actions)
        total_tokens += narrative_tokens

        # Advance the world year based on simulation scale (1 turn = 1 year by default)
        new_state.year += 1

        # Compute cost using LLMResponse helper if available
        try:
            from ese.agents.interaction import LLMResponse

            dummy = LLMResponse(
                content="", tokens_prompt=total_tokens, tokens_completion=0, model=self.openai_model
            )
            total_cost = dummy.cost_usd(self.openai_model)
        except Exception:
            total_cost = (total_tokens / 1000) * 0.005

        return TurnResult(
            turn_number=turn_number,
            year=new_state.year,
            world_state=new_state,
            agent_actions=agent_actions,
            events=new_state.events,
            narrative=narrative,
            tokens_used=total_tokens,
            cost_usd=total_cost,
        )

    async def _resolve_interactions(
        self,
        agent_actions: dict[str, dict[str, Any]],
        world_state: "WorldState",
        agents: list["Agent"],
    ) -> tuple[list[dict[str, Any]], int]:
        """Apply agent actions and compute emergent events.

        When two agents target each other, uses the LLM to determine the
        interaction outcome: what happened, how each participant felt, and
        whether relationships changed.

        Returns:
            (events list, tokens_used)
        """
        events: list[dict[str, Any]] = []
        total_tokens = 0

        # Build a quick lookup from agent_id -> Agent object
        agent_map: dict[str, "Agent"] = {a.agent_id: a for a in agents}

        # Build a name -> agent_id lookup for fallback resolution
        name_to_id: dict[str, str] = {}
        for a in agents:
            name_to_id[a.persona.name.lower()] = a.agent_id

        for agent_id, action in agent_actions.items():
            action_type = action.get("type", "idle")
            target = action.get("target")

            # Resolve target by name if it's not a valid agent ID
            if target and target not in agent_actions:
                resolved = name_to_id.get(target.lower())
                if resolved is None:
                    # Partial match: check if target appears in any agent name
                    for name_lower, aid in name_to_id.items():
                        if target.lower() in name_lower or name_lower in target.lower():
                            resolved = aid
                            break
                if resolved is not None:
                    logger.debug(
                        "Agent %s: resolved target name %r to UUID %s", agent_id, target, resolved
                    )
                    target = resolved

            if action_type == "interact" and target and target in agent_actions:
                # Use LLM to determine outcome when we have an API key
                outcome_desc, tokens = await self._llm_resolve_interaction(
                    agent_id, target, action, agent_actions[target], world_state, agent_map
                )
                total_tokens += tokens
                events.append(
                    {
                        "description": outcome_desc,
                        "type": "interaction",
                        "participants": [agent_id, target],
                    }
                )
            elif action_type == "interact":
                # Target was invalid and could not be resolved — record the attempt
                events.append(
                    {
                        "description": action.get("description") or f"{agent_id} attempted to interact.",
                        "type": "attempted_interact",
                        "participants": [agent_id],
                    }
                )
            elif action_type == "observe":
                events.append(
                    {
                        "description": f"{agent_id} observed the world.",
                        "type": "observation",
                        "participants": [agent_id],
                    }
                )

        return events, total_tokens

    async def _llm_resolve_interaction(
        self,
        agent_a_id: str,
        agent_b_id: str,
        action_a: dict[str, Any],
        action_b: dict[str, Any],
        world_state: "WorldState",
        agent_map: dict[str, "Agent"],
    ) -> tuple[str, int]:
        """Use LLM to resolve an agent-to-agent interaction.

        Returns (outcome_description, tokens_used).
        Falls back to a plain-text description if no API key or on error.
        """
        agent_a = agent_map.get(agent_a_id)
        agent_b = agent_map.get(agent_b_id)

        fallback = (
            f"{agent_a_id} interacted with {agent_b_id}: "
            f"{action_a.get('description', '')}"
        )

        if not self._api_key or agent_a is None or agent_b is None:
            return fallback, 0

        system_prompt = (
            "You are a simulation narrator resolving an interaction between two characters. "
            "Respond with a JSON object only."
        )
        user_prompt = (
            f"World context: {world_state.summary()}\n\n"
            f"Character A ({agent_a.persona.name}): {agent_a.persona.to_prompt_block()}\n"
            f"Character A's action: {action_a.get('description', '')}\n\n"
            f"Character B ({agent_b.persona.name}): {agent_b.persona.to_prompt_block()}\n"
            f"Character B's action: {action_b.get('description', '')}\n\n"
            "Determine the outcome. Return JSON:\n"
            '{"outcome": "short description of what happened", '
            '"mood_delta_a": float in [-0.3, 0.3], '
            '"mood_delta_b": float in [-0.3, 0.3], '
            '"energy_delta_a": float in [-0.2, 0.2], '
            '"energy_delta_b": float in [-0.2, 0.2], '
            '"relationship_delta": float in [-0.3, 0.3]}'
        )

        logger.debug(
            "Resolving interaction: %s <-> %s", agent_a.persona.name, agent_b.persona.name
        )
        try:
            response = await self._interaction.get_action(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.7,
            )
            data = json.loads(response.content)
            outcome = str(data.get("outcome", fallback))

            # Apply mood, energy, and relationship deltas
            def _clamp(v: float, lo: float, hi: float) -> float:
                return max(lo, min(hi, v))

            agent_a.mood = _clamp(
                agent_a.mood + float(data.get("mood_delta_a", 0.0)), 0.0, 1.0
            )
            agent_b.mood = _clamp(
                agent_b.mood + float(data.get("mood_delta_b", 0.0)), 0.0, 1.0
            )
            agent_a.energy = _clamp(
                agent_a.energy + float(data.get("energy_delta_a", 0.0)), 0.0, 1.0
            )
            agent_b.energy = _clamp(
                agent_b.energy + float(data.get("energy_delta_b", 0.0)), 0.0, 1.0
            )
            rel_delta = float(data.get("relationship_delta", 0.0))
            agent_a.update_relationship(agent_b_id, rel_delta)
            agent_b.update_relationship(agent_a_id, rel_delta)

            return outcome, response.tokens_total
        except Exception as exc:
            logger.warning("_llm_resolve_interaction failed: %s", exc)
            return fallback, 0

    async def _generate_narrative(
        self,
        world_state: "WorldState",
        agent_actions: dict[str, dict[str, Any]],
    ) -> tuple[str, int]:
        """Produce a short narrative summary of this turn via LLM.

        Returns (narrative_text, tokens_used).
        Falls back to a placeholder when no API key is available.
        """
        event_count = len(world_state.events)
        agent_count = world_state.agent_count()

        fallback = (
            f"Year {world_state.year}, Turn {world_state.turn}: "
            f"{agent_count} agents acted, {event_count} events occurred."
        )

        if not self._api_key:
            return fallback, 0

        event_descriptions = [e.get("description", "") for e in world_state.events]

        logger.debug("Generating narrative for turn %d.", world_state.turn)
        lang_instruction = ""
        if self.language != "en":
            lang_names = {"ko": "Korean", "ja": "Japanese", "zh": "Chinese", "es": "Spanish", "fr": "French", "de": "German"}
            lang_name = lang_names.get(self.language, self.language)
            lang_instruction = f" Write entirely in {lang_name}."

        try:
            narrative = await self._interaction.generate_narrative(
                world_summary=world_state.summary(),
                events=event_descriptions,
                style=f"omniscient.{lang_instruction}",
            )
            # generate_narrative doesn't return token count; estimate from length
            # (actual tracking would require refactoring generate_narrative to return LLMResponse)
            estimated_tokens = len(narrative) // 4
            return narrative, estimated_tokens
        except Exception as exc:
            logger.warning("_generate_narrative failed: %s", exc)
            return fallback, 0
