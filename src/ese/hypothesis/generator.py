"""Hypothesis generator for Dormammu scenario tree branching.

At each non-leaf node the generator produces a set of "what if" hypotheses
that define the child branches. Each hypothesis represents a plausible
divergence from the current timeline (e.g., a technological breakthrough,
a social upheaval, a natural disaster).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Hypothesis:
    """A single branching hypothesis for the scenario tree.

    Attributes
    ----------
    title:       Short label, e.g. "The Great Collapse"
    description: Detailed description of what changes in this branch.
    probability: Estimated likelihood [0, 1] (used for ordering, not sampling).
    tags:        Thematic tags for filtering/analysis.
    sf_inspired: Whether this hypothesis was seeded by an SF inspiration source.
    """

    title: str
    description: str
    probability: float = 0.5
    tags: list[str] = field(default_factory=list)
    sf_inspired: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "description": self.description,
            "probability": self.probability,
            "tags": self.tags,
            "sf_inspired": self.sf_inspired,
        }


class HypothesisGenerator:
    """Generates branching hypotheses for a scenario node via LLM.

    The generator takes the current world state summary and topic, then
    produces N diverse hypotheses for the next branch level. Hypotheses
    are ordered by estimated probability (most likely first) so the DFS
    explores the most plausible timelines before exotic ones.
    """

    def __init__(self, openai_model: str = "gpt-4o") -> None:
        self.openai_model = openai_model

    async def generate(
        self,
        topic: str,
        world_summary: str,
        depth: int,
        count: int = 3,
        sibling_hypotheses: list[str] | None = None,
        sf_inspired: bool = False,
        inspiration_injection: str = "",
        research_context: str = "",
    ) -> list[Hypothesis]:
        """Generate `count` branching hypotheses.

        Args:
            topic: The original simulation topic for thematic grounding.
            world_summary: Current world state in plain text.
            depth: Current DFS depth (deeper = more specific hypotheses).
            count: Number of hypotheses to generate.
            sibling_hypotheses: Titles of existing sibling branches to avoid duplication.
            sf_inspired: If True, inject SF inspiration seeds into the prompt.
            inspiration_injection: Pre-built injection string from InspirationSystem.

        Returns:
            List of Hypothesis objects, ordered by probability descending.
        """
        logger.info(
            "Generating %d hypotheses at depth %d for topic: %s", count, depth, topic
        )

        from ese.config import config
        from ese.agents.interaction import AgentInteraction

        if not config.openai_api_key:
            # Offline fallback — return deterministic stubs without API access
            logger.debug("No API key; returning placeholder hypotheses.")
            stubs = [
                Hypothesis(
                    title=f"Branch {depth}-{i}: Divergence",
                    description=(
                        f"A significant change occurs at depth {depth}, "
                        f"variant {i}, in '{topic}'."
                    ),
                    probability=1.0 - (i * 0.2),
                    tags=["placeholder"],
                )
                for i in range(count)
            ]
            return sorted(stubs, key=lambda h: -h.probability)

        prompt = self._build_prompt(
            topic=topic,
            world_summary=world_summary,
            depth=depth,
            count=count,
            sibling_hypotheses=sibling_hypotheses or [],
            sf_inspired=sf_inspired,
            inspiration_injection=inspiration_injection,
            research_context=research_context,
        )

        interaction = AgentInteraction(api_key=config.openai_api_key, model=self.openai_model)

        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are a creative narrative designer for a world simulation. "
                    "Generate diverse, plausible yet surprising 'what if' scenario branches. "
                    "Always respond with valid JSON."
                ),
                user_prompt=prompt,
                temperature=0.9,
            )
            hypotheses = self._parse_response(response.content, sf_inspired=sf_inspired)
            if not hypotheses:
                logger.warning("LLM returned no parseable hypotheses; using stubs.")
                return self._stub_hypotheses(topic, depth, count)

            # Ensure we have exactly `count` hypotheses
            if len(hypotheses) < count:
                stubs = self._stub_hypotheses(topic, depth, count - len(hypotheses))
                hypotheses.extend(stubs)

            return sorted(hypotheses[:count], key=lambda h: -h.probability)

        except Exception as exc:
            logger.error("HypothesisGenerator.generate failed: %s", exc)
            return self._stub_hypotheses(topic, depth, count)

    def _build_prompt(
        self,
        topic: str,
        world_summary: str,
        depth: int,
        count: int,
        sibling_hypotheses: list[str],
        sf_inspired: bool,
        inspiration_injection: str,
        research_context: str = "",
    ) -> str:
        """Build the LLM prompt for hypothesis generation."""
        specificity = "broad societal" if depth <= 1 else "specific individual or group"
        siblings_text = ""
        if sibling_hypotheses:
            siblings_text = (
                "\nExisting sibling branches to AVOID duplicating:\n"
                + "\n".join(f"- {h}" for h in sibling_hypotheses)
                + "\n"
            )

        inspiration_text = ""
        if sf_inspired and inspiration_injection:
            inspiration_text = f"\n{inspiration_injection}\n"

        research_text = ""
        if research_context:
            research_text = f"\nDomain research:\n{research_context}\n"

        return (
            f"Simulation topic: {topic}\n"
            f"{research_text}"
            f"Current world state: {world_summary}\n"
            f"DFS depth: {depth}\n"
            f"{siblings_text}"
            f"{inspiration_text}\n"
            f"Generate EXACTLY {count} {specificity}-level 'what if' hypotheses that diverge "
            "from the current world state. Each should be plausible yet surprising, "
            "and maximally distinct from one another. "
            "Use creative, specific, evocative titles — NOT generic names like 'Branch X'.\n\n"
            f"You MUST respond with a JSON object containing a 'hypotheses' key whose value is "
            f"an array of exactly {count} objects with this shape:\n"
            '{"hypotheses": [{"title": "evocative short label", '
            '"description": "2-3 sentence explanation of what changes", '
            '"probability": 0.0-1.0, "tags": ["theme1", "theme2"]}, ...]}'
        )

    def _parse_response(self, content: str, sf_inspired: bool = False) -> list[Hypothesis]:
        """Parse LLM JSON response into Hypothesis objects."""
        try:
            # The response may be wrapped in a JSON object due to json_object mode
            data = json.loads(content)
            # Handle both array and {"hypotheses": [...]} shapes
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common wrapper keys first
                items = None
                for key in ("hypotheses", "branches", "scenarios", "items"):
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                # Fallback: if exactly one key has a list value, use it
                if items is None:
                    list_values = [v for v in data.values() if isinstance(v, list)]
                    if len(list_values) == 1:
                        items = list_values[0]
                    else:
                        # Treat single dict as one hypothesis
                        items = [data]
            else:
                logger.warning("Unexpected LLM response shape: %r", type(data))
                return []

            hypotheses = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = str(item.get("title", "Unknown Branch"))
                description = str(item.get("description", ""))
                try:
                    probability = float(item.get("probability", 0.5))
                    probability = max(0.0, min(1.0, probability))
                except (TypeError, ValueError):
                    probability = 0.5
                tags = [str(t) for t in item.get("tags", [])]
                hypotheses.append(
                    Hypothesis(
                        title=title,
                        description=description,
                        probability=probability,
                        tags=tags,
                        sf_inspired=sf_inspired,
                    )
                )
            return hypotheses

        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            logger.warning("Failed to parse hypothesis LLM response: %s", exc)
            return []

    def _stub_hypotheses(self, topic: str, depth: int, count: int) -> list[Hypothesis]:
        """Return deterministic placeholder hypotheses."""
        return [
            Hypothesis(
                title=f"Branch {depth}-{i}: Divergence",
                description=(
                    f"A significant change occurs at depth {depth}, "
                    f"variant {i}, in '{topic}'."
                ),
                probability=1.0 - (i * 0.2),
                tags=["placeholder"],
            )
            for i in range(count)
        ]
