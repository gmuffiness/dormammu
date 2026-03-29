"""Persona generation for Dormammu agents.

A Persona defines the stable identity of an agent: name, traits, goals,
backstory, and relationship tendencies. Personas are generated via LLM
at simulation initialization and remain constant throughout the run
(though an agent's *state* — mood, relationships, memories — evolves).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any


# Trait dimensions inspired by the Big Five personality model
TRAIT_DIMENSIONS = [
    "openness",        # curiosity, creativity
    "conscientiousness",  # diligence, self-discipline
    "extraversion",    # sociability, assertiveness
    "agreeableness",   # cooperativeness, empathy
    "neuroticism",     # emotional instability, anxiety
]


@dataclass
class Persona:
    """Stable identity of a simulation agent.

    Trait scores are floats in [0.0, 1.0] where 0 = low, 1 = high.
    Goals are ordered by priority (index 0 = highest priority).
    """

    persona_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    age: int = 30
    backstory: str = ""
    goals: list[str] = field(default_factory=list)
    traits: dict[str, float] = field(default_factory=dict)
    """Trait name -> score in [0, 1]"""
    fears: list[str] = field(default_factory=list)
    values: list[str] = field(default_factory=list)
    speech_style: str = "neutral"
    """Hint for the LLM on how this agent speaks."""

    # What-If 소설 창작용 확장 필드
    original_name: str = ""
    """원작에서의 이름 (원어)"""
    role: str = ""
    """역할 (e.g., 조사병단 단장, 마레 전사대장)"""
    catchphrases: list[str] = field(default_factory=list)
    """대표 대사"""
    relationships: list[dict[str, Any]] = field(default_factory=list)
    """관계 목록: [{"target": "이름", "type": "유형", "affinity": -1.0~1.0}]"""
    arc_in_original: str = ""
    """원작에서의 캐릭터 아크"""
    divergence_impact: str = ""
    """이 What-If에서 이 캐릭터가 받는 영향"""
    is_from_source: bool = False
    """원작 캐릭터 여부 (True = 리서치에서 생성, False = 자동 생성)"""

    @classmethod
    def default_traits(cls) -> dict[str, float]:
        """Return a balanced set of default trait scores."""
        return {dim: 0.5 for dim in TRAIT_DIMENSIONS}

    def trait_summary(self) -> str:
        """Return a short comma-separated trait description for LLM prompts."""
        high = [k for k, v in self.traits.items() if v >= 0.7]
        low = [k for k, v in self.traits.items() if v <= 0.3]
        parts = []
        if high:
            parts.append(f"high {', '.join(high)}")
        if low:
            parts.append(f"low {', '.join(low)}")
        return "; ".join(parts) or "balanced traits"

    def to_prompt_block(self) -> str:
        """Format this persona as a system-prompt block for LLM agent calls."""
        base = (
            f"Name: {self.name}\n"
            f"Age: {self.age}\n"
            f"Backstory: {self.backstory}\n"
            f"Goals: {'; '.join(self.goals)}\n"
            f"Traits: {self.trait_summary()}\n"
            f"Fears: {'; '.join(self.fears)}\n"
            f"Values: {'; '.join(self.values)}\n"
            f"Speech style: {self.speech_style}"
        )
        if self.is_from_source:
            source_info = (
                f"\nRole: {self.role}"
                f"\nOriginal arc: {self.arc_in_original}"
                f"\nDivergence impact: {self.divergence_impact}"
            )
            if self.catchphrases:
                source_info += f"\nCatchphrases: {'; '.join(self.catchphrases)}"
            if self.relationships:
                rel_lines = [
                    f"  {r['target']}: {r['type']} (affinity {r.get('affinity', 0)})"
                    for r in self.relationships
                ]
                source_info += f"\nRelationships:\n" + "\n".join(rel_lines)
            base += source_info
        return base

    def to_dict(self) -> dict[str, Any]:
        return {
            "persona_id": self.persona_id,
            "name": self.name,
            "age": self.age,
            "backstory": self.backstory,
            "goals": self.goals,
            "traits": self.traits,
            "fears": self.fears,
            "values": self.values,
            "speech_style": self.speech_style,
            "original_name": self.original_name,
            "role": self.role,
            "catchphrases": self.catchphrases,
            "relationships": self.relationships,
            "arc_in_original": self.arc_in_original,
            "divergence_impact": self.divergence_impact,
            "is_from_source": self.is_from_source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Persona":
        import dataclasses
        known_fields = {f.name for f in dataclasses.fields(cls)}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)


class PersonaGenerator:
    """Generates diverse, narratively interesting personas via LLM.

    Each call hits the OpenAI API when an API key is configured.
    Falls back to deterministic stubs when no key is available so
    that tests and offline runs continue to work.

    The `generate_batch` method produces a set of personas with distinct
    trait profiles to ensure emergent conflict and cooperation.
    """

    def __init__(self, openai_model: str | None = None) -> None:
        from ese.config import config

        self.openai_model = openai_model or config.openai_model
        self._api_key: str = config.openai_api_key

    def _get_interaction(self) -> Any:
        from ese.agents.interaction import AgentInteraction

        return AgentInteraction(api_key=self._api_key, model=self.openai_model)

    async def generate(
        self, topic: str, index: int = 0, count: int = 1, research_context: str = ""
    ) -> Persona:
        """Generate a single persona appropriate for the given topic.

        Args:
            topic: The simulation topic for contextual grounding.
            index: Ordinal index used to vary trait profiles.
            count: Total batch size (used in diversity hint when > 1).

        Returns:
            A Persona with LLM-generated backstory and goals.
        """
        import logging

        logger = logging.getLogger(__name__)

        if not self._api_key:
            # Offline fallback — unique names required by batch uniqueness test
            _NAMES = [
                "Alice", "Bruno", "Celia", "Dario", "Elena",
                "Felix", "Gina", "Hector", "Iris", "Jonas",
            ]
            name = _NAMES[index % len(_NAMES)] if index < len(_NAMES) else f"Agent_{index:02d}"
            return Persona(
                name=name,
                age=20 + (index * 7) % 50,
                backstory=f"A resident of the world described by: {topic}",
                goals=["survive", "thrive", "connect"],
                traits=Persona.default_traits(),
                fears=["isolation", "failure"],
                values=["community", "growth"],
                speech_style="direct",
            )

        diversity_hint = (
            f"Make each persona have contrasting traits and goals. "
            f"Persona {index + 1} of {count}."
            if count > 1
            else ""
        )
        system_prompt = (
            "You are a creative character designer for a social simulation. "
            "Generate realistic, internally consistent characters with contrasting "
            "personalities. Always respond with valid JSON."
        )
        research_text = f"\nDomain research:\n{research_context}\n" if research_context else ""
        user_prompt = (
            f"Create a character for a simulation about: {topic}\n"
            f"{research_text}"
            f"{diversity_hint}\n\n"
            "Return a JSON object with these fields:\n"
            "  name: string (unique full name)\n"
            "  age: integer (18-80)\n"
            "  backstory: string (2-3 sentences contextual to the simulation topic)\n"
            "  traits: object with keys openness, conscientiousness, extraversion, "
            "agreeableness, neuroticism — each a float in [0.0, 1.0]\n"
            "  goals: array of 2-4 short goal strings (ordered by priority)\n"
            "  fears: array of 2-3 short fear strings\n"
            "  values: array of 2-3 short value strings\n"
            "  speech_style: string (e.g. 'terse and blunt', 'warm and verbose')"
        )

        interaction = self._get_interaction()
        logger.info("PersonaGenerator.generate: making LLM call topic=%r index=%d", topic, index)
        response = await interaction.get_action(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.9,
        )
        logger.debug("PersonaGenerator.generate: raw response content=%r", response.content[:200])

        try:
            raw = json.loads(response.content)
            # Unwrap if LLM returned {"character": {...}} or any single-key wrapper
            if isinstance(raw, dict):
                # Check if this is already a persona dict (has 'name' key)
                if "name" in raw:
                    data = raw
                else:
                    # Try to find a nested dict value
                    dict_values = [v for v in raw.values() if isinstance(v, dict)]
                    data = dict_values[0] if dict_values else raw
            else:
                data = raw
            traits_raw = data.get("traits", {})
            # Clamp all trait values to [0.0, 1.0]
            traits = {
                k: max(0.0, min(1.0, float(v)))
                for k, v in traits_raw.items()
                if k in TRAIT_DIMENSIONS
            }
            # Fill missing trait dimensions with defaults
            for dim in TRAIT_DIMENSIONS:
                if dim not in traits:
                    traits[dim] = 0.5

            return Persona(
                name=str(data.get("name", f"Agent_{index:02d}")),
                age=int(data.get("age", 30 + index)),
                backstory=str(data.get("backstory", "")),
                goals=[str(g) for g in data.get("goals", ["survive"])],
                traits=traits,
                fears=[str(f) for f in data.get("fears", ["failure"])],
                values=[str(v) for v in data.get("values", ["growth"])],
                speech_style=str(data.get("speech_style", "neutral")),
            )
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "PersonaGenerator: failed to parse LLM response (index=%d): %s", index, exc
            )
            return Persona(
                name=f"Agent_{index:02d}",
                age=20 + (index * 7) % 50,
                backstory=f"A resident of the world described by: {topic}",
                goals=["survive", "thrive", "connect"],
                traits=Persona.default_traits(),
                fears=["isolation", "failure"],
                values=["community", "growth"],
                speech_style="direct",
            )

    async def generate_from_profile(self, profile: dict[str, Any]) -> Persona:
        """리서치 결과의 캐릭터 프로파일에서 Persona를 생성.

        Args:
            profile: research.json의 character_profiles 항목.
                     name, personality.big5, motivation, relationships 등을 포함.

        Returns:
            원작 캐릭터 기반 Persona.
        """
        big5 = profile.get("personality", {}).get("big5", {})
        traits = {dim: big5.get(dim, 0.5) for dim in TRAIT_DIMENSIONS}

        return Persona(
            name=profile.get("name", "Unknown"),
            original_name=profile.get("original_name", ""),
            age=profile.get("age", 30),
            role=profile.get("role", ""),
            backstory=profile.get("backstory", ""),
            goals=[profile.get("motivation", "survive")],
            traits=traits,
            fears=profile.get("fears", []),
            values=profile.get("values", []),
            speech_style=profile.get("personality", {}).get("speech_pattern", "neutral"),
            catchphrases=profile.get("personality", {}).get("catchphrases", []),
            relationships=profile.get("relationships", []),
            arc_in_original=profile.get("arc_in_original", ""),
            divergence_impact=profile.get("divergence_impact", ""),
            is_from_source=True,
        )

    async def generate_batch(
        self, topic: str, count: int = 5, research_context: str = ""
    ) -> list[Persona]:
        """Generate `count` diverse personas for the given topic."""
        import asyncio

        return list(
            await asyncio.gather(
                *[
                    self.generate(topic, i, count=count, research_context=research_context)
                    for i in range(count)
                ]
            )
        )
