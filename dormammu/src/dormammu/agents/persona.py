"""Persona schema for Dormammu agents.

A Persona defines the stable identity of a simulation agent: name, traits,
goals, backstory, and relationship tendencies. Skills generate personas
via Claude sub-agents; this module defines the data schema only.
"""

from __future__ import annotations

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
    """Hint for how this agent speaks."""

    # What-If 소설 창작용 확장 필드
    original_name: str = ""
    """원본 이름 (원작 캐릭터명 또는 실존 인물 본명)"""
    role: str = ""
    """역할 (e.g., 조사병단 단장, 마레 전사대장)"""
    catchphrases: list[str] = field(default_factory=list)
    """대표 대사"""
    relationships: list[dict[str, Any]] = field(default_factory=list)
    """관계 목록: [{"target": "이름", "type": "유형", "affinity": -1.0~1.0}]"""
    arc_in_original: str = ""
    """원본에서의 캐릭터/인물 아크"""
    divergence_impact: str = ""
    """이 What-If에서 이 캐릭터가 받는 영향"""
    is_from_source: bool = False
    """기존 캐릭터/인물 여부 (True = 원작 또는 실존, False = 시나리오용 신규 생성)"""

    @classmethod
    def default_traits(cls) -> dict[str, float]:
        """Return a balanced set of default trait scores."""
        return {dim: 0.5 for dim in TRAIT_DIMENSIONS}

    def trait_summary(self) -> str:
        """Return a short comma-separated trait description."""
        high = [k for k, v in self.traits.items() if v >= 0.7]
        low = [k for k, v in self.traits.items() if v <= 0.3]
        parts = []
        if high:
            parts.append(f"high {', '.join(high)}")
        if low:
            parts.append(f"low {', '.join(low)}")
        return "; ".join(parts) or "balanced traits"

    def to_prompt_block(self) -> str:
        """Format this persona as a prompt block for sub-agent calls."""
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
