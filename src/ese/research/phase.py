"""Pre-simulation research phase.

Generates a structured research document about the simulation topic
before hypotheses and agents are created. The research context is then
referenced throughout the simulation pipeline.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ese.agents.interaction import AgentInteraction
from ese.config import config

logger = logging.getLogger(__name__)


@dataclass
class ResearchDocument:
    """Structured research output for a simulation topic."""

    topic: str
    summary: str = ""
    key_characters: list[dict[str, str]] = field(default_factory=list)
    key_factions: list[dict[str, str]] = field(default_factory=list)
    world_setting: str = ""
    conflict_structure: str = ""
    historical_context: str = ""
    fan_theories: list[str] = field(default_factory=list)
    thematic_elements: list[str] = field(default_factory=list)
    topic_specific_metrics: list[dict[str, str]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "summary": self.summary,
            "key_characters": self.key_characters,
            "key_factions": self.key_factions,
            "world_setting": self.world_setting,
            "conflict_structure": self.conflict_structure,
            "historical_context": self.historical_context,
            "fan_theories": self.fan_theories,
            "thematic_elements": self.thematic_elements,
            "topic_specific_metrics": self.topic_specific_metrics,
            "sources": self.sources,
            "created_at": self.created_at,
        }

    def to_prompt_context(self) -> str:
        """Convert research to a concise prompt context string."""
        parts = [f"[Research Context for: {self.topic}]"]
        if self.summary:
            parts.append(f"Summary: {self.summary}")
        if self.world_setting:
            parts.append(f"World Setting: {self.world_setting}")
        if self.conflict_structure:
            parts.append(f"Conflict Structure: {self.conflict_structure}")
        if self.key_characters:
            chars = ", ".join(f"{c['name']} ({c.get('role', 'unknown')})" for c in self.key_characters)
            parts.append(f"Key Characters: {chars}")
        if self.key_factions:
            factions = ", ".join(f"{f['name']} ({f.get('stance', 'unknown')})" for f in self.key_factions)
            parts.append(f"Key Factions: {factions}")
        if self.historical_context:
            parts.append(f"Historical Context: {self.historical_context}")
        if self.thematic_elements:
            parts.append(f"Themes: {', '.join(self.thematic_elements)}")
        if self.topic_specific_metrics:
            metrics = ", ".join(m["name"] for m in self.topic_specific_metrics)
            parts.append(f"Domain-specific evaluation metrics: {metrics}")
        return "\n".join(parts)


class ResearchPhase:
    """Performs pre-simulation research on a topic."""

    def __init__(self, openai_model: str | None = None) -> None:
        self.model = openai_model or config.openai_model
        self._interaction = AgentInteraction(
            api_key=config.openai_api_key,
            model=self.model,
        )

    async def research(self, topic: str) -> ResearchDocument:
        """Research a topic and return a structured document."""
        logger.info("Starting research phase for: %s", topic)

        system_prompt = (
            "You are a research analyst preparing background material for a simulation engine. "
            "Your job is to deeply analyze the given topic and provide structured research that will "
            "inform hypothesis generation, character creation, and evaluation criteria.\n\n"
            "You must respond with a valid JSON object (no markdown, no code fences) with these fields:\n"
            "- summary: comprehensive overview of the topic (2-3 paragraphs)\n"
            "- key_characters: array of {name, role, description, motivations} for important figures\n"
            "- key_factions: array of {name, stance, goals, resources} for groups/organizations\n"
            "- world_setting: description of the physical/political/social environment\n"
            "- conflict_structure: analysis of core conflicts, power dynamics, tensions\n"
            "- historical_context: real-world historical parallels or relevant background\n"
            "- fan_theories: array of interesting speculative theories or alternative interpretations\n"
            "- thematic_elements: array of recurring themes (power, freedom, identity, etc.)\n"
            "- topic_specific_metrics: array of {name, description, weight} — domain-specific "
            "evaluation metrics that should be used alongside the standard metrics "
            "(emergence, narrative, diversity, novelty). Weight should be 0.0-1.0.\n"
            "- sources: array of source descriptions (e.g. 'Attack on Titan manga/anime canon')\n"
        )

        user_prompt = (
            f"Research topic: {topic}\n\n"
            "Analyze this topic comprehensively. If it references fiction, cover the source material, "
            "fan analysis, and real-world parallels. If it's a historical/scientific what-if, cover "
            "the factual basis, expert opinions, and speculative possibilities.\n\n"
            "Provide thorough, specific research — not generic summaries. Include names, dates, "
            "specific events, and detailed analysis. The simulation needs rich, grounded context."
        )

        try:
            response = await self._interaction.get_action(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )

            # Parse JSON response
            # Strip markdown code fences if present
            cleaned = response.content.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            data = json.loads(cleaned)

            doc = ResearchDocument(
                topic=topic,
                summary=data.get("summary", ""),
                key_characters=data.get("key_characters", []),
                key_factions=data.get("key_factions", []),
                world_setting=data.get("world_setting", ""),
                conflict_structure=data.get("conflict_structure", ""),
                historical_context=data.get("historical_context", ""),
                fan_theories=data.get("fan_theories", []),
                thematic_elements=data.get("thematic_elements", []),
                topic_specific_metrics=data.get("topic_specific_metrics", []),
                sources=data.get("sources", []),
            )
            logger.info(
                "Research complete: %d characters, %d factions, %d metrics",
                len(doc.key_characters),
                len(doc.key_factions),
                len(doc.topic_specific_metrics),
            )
            return doc

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to parse research response: %s. Using fallback.", e)
            return ResearchDocument(
                topic=topic,
                summary=f"Research on: {topic} (fallback — LLM response could not be parsed)",
            )
        except Exception as e:
            logger.warning("Research phase failed: %s. Continuing without research.", e)
            return ResearchDocument(
                topic=topic,
                summary=f"Research on: {topic} (fallback — research phase encountered an error)",
            )

    def save(self, doc: ResearchDocument, simulation_id: str) -> Path:
        """Save research document to data/research/ directory."""
        research_dir = config.data_dir.parent / "research"
        research_dir.mkdir(parents=True, exist_ok=True)

        filepath = research_dir / f"{simulation_id}.json"
        filepath.write_text(
            json.dumps(doc.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("Research document saved: %s", filepath)
        return filepath

    @staticmethod
    def load(simulation_id: str) -> ResearchDocument | None:
        """Load a previously saved research document."""
        research_dir = config.data_dir.parent / "research"
        filepath = research_dir / f"{simulation_id}.json"
        if not filepath.exists():
            return None
        data = json.loads(filepath.read_text(encoding="utf-8"))
        return ResearchDocument(**data)
