"""Hypothesis evaluator for Dormammu.

The evaluator scores hypotheses after a scenario branch has been simulated,
determining which branches were most narratively interesting, emergent, and
worth further exploration. Scores feed back into the DFS traversal order.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ese.engine.world_state import WorldState
    from ese.hypothesis.generator import Hypothesis

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Scores and rationale for an evaluated hypothesis branch."""

    hypothesis_title: str
    node_id: str

    # Scoring dimensions, each in [0, 1]
    character_fidelity_score: float = 0.0
    """원작 캐릭터의 성격/동기/말투 재현도"""
    fandom_resonance_score: float = 0.0
    """팬덤이 흥미로워할 만한 전개인가?"""
    emergence_score: float = 0.0
    """Did unexpected, unscripted events arise?"""
    diversity_score: float = 0.0
    """Did agents behave distinctly from one another?"""
    plausibility_score: float = 0.0
    """세계관 규칙 내 논리적 타당성"""
    foreshadowing_score: float = 0.0
    """복선의 품질 — 자연스러움, 회수율, 임팩트, 지연 거리, 필연성, 다층성"""

    rationale: str = ""
    """LLM-generated explanation of scores."""

    @property
    def composite_score(self) -> float:
        """Weighted composite across all dimensions."""
        weights = {
            "character_fidelity": 0.20,
            "fandom_resonance": 0.15,
            "emergence": 0.15,
            "diversity": 0.15,
            "plausibility": 0.15,
            "foreshadowing": 0.20,
        }
        return (
            self.character_fidelity_score * weights["character_fidelity"]
            + self.fandom_resonance_score * weights["fandom_resonance"]
            + self.emergence_score * weights["emergence"]
            + self.diversity_score * weights["diversity"]
            + self.plausibility_score * weights["plausibility"]
            + self.foreshadowing_score * weights["foreshadowing"]
        )

    @property
    def should_expand(self) -> bool:
        """True if this node should be expanded (explored deeper).

        Threshold is 0.3 — be generous with exploration to allow
        interesting branches to develop before pruning too aggressively.
        """
        return self.composite_score > 0.3

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_title": self.hypothesis_title,
            "node_id": self.node_id,
            "character_fidelity_score": self.character_fidelity_score,
            "fandom_resonance_score": self.fandom_resonance_score,
            "emergence_score": self.emergence_score,
            "diversity_score": self.diversity_score,
            "plausibility_score": self.plausibility_score,
            "foreshadowing_score": self.foreshadowing_score,
            "composite_score": self.composite_score,
            "rationale": self.rationale,
        }


class HypothesisEvaluator:
    """Scores simulated hypothesis branches via LLM analysis.

    Evaluation happens after a node's turns have been fully simulated.
    Results can be used to:
    - Rank sibling branches for reporting
    - Prune dead-end branches early in future runs
    - Surface the most emergent timelines for the human observer
    """

    def __init__(self, openai_model: str = "gpt-4o") -> None:
        self.openai_model = openai_model

    async def evaluate(
        self,
        hypothesis: "Hypothesis",
        node_id: str,
        final_world_state: "WorldState",
        turn_narratives: list[str],
        sibling_summaries: list[str] | None = None,
        evaluation_criteria: list[dict[str, str]] | None = None,
    ) -> EvaluationResult:
        """Evaluate a completed scenario branch.

        Args:
            hypothesis: The hypothesis that defined this branch.
            node_id: The scenario tree node ID.
            final_world_state: World state at the end of this branch.
            turn_narratives: Ordered list of per-turn narrative summaries.
            sibling_summaries: Brief summaries of sibling branches for novelty scoring.
            evaluation_criteria: User-defined criteria dicts with 'name' and 'description'.

        Returns:
            An EvaluationResult with scores and rationale.
        """
        logger.info("Evaluating hypothesis '%s' for node %s", hypothesis.title, node_id)

        from ese.config import config
        from ese.agents.interaction import AgentInteraction

        if not config.openai_api_key:
            # Offline fallback — return mid-range scores
            logger.debug("No API key; returning placeholder evaluation.")
            return EvaluationResult(
                hypothesis_title=hypothesis.title,
                node_id=node_id,
                character_fidelity_score=0.5,
                fandom_resonance_score=0.5,
                emergence_score=0.5,
                diversity_score=0.5,
                plausibility_score=0.5,
                foreshadowing_score=0.5,
                rationale=(
                    f"Placeholder evaluation for '{hypothesis.title}'. "
                    "Real scoring requires LLM analysis."
                ),
            )

        prompt = self._build_eval_prompt(
            hypothesis=hypothesis,
            final_world_state=final_world_state,
            turn_narratives=turn_narratives,
            sibling_summaries=sibling_summaries or [],
            evaluation_criteria=evaluation_criteria or [],
        )

        interaction = AgentInteraction(api_key=config.openai_api_key, model=self.openai_model)

        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are an expert evaluator for a novel/fiction simulation engine. "
                    "Score branches on character fidelity, fandom resonance, emergence, "
                    "agent diversity, world plausibility, and foreshadowing quality. Always respond with valid JSON."
                ),
                user_prompt=prompt,
                temperature=0.3,
            )
            return self._parse_response(response.content, hypothesis.title, node_id)

        except Exception as exc:
            logger.error("HypothesisEvaluator.evaluate failed: %s", exc)
            return EvaluationResult(
                hypothesis_title=hypothesis.title,
                node_id=node_id,
                character_fidelity_score=0.5,
                fandom_resonance_score=0.5,
                emergence_score=0.5,
                diversity_score=0.5,
                plausibility_score=0.5,
                foreshadowing_score=0.5,
                rationale=f"Evaluation failed due to error: {exc}",
            )

    def _build_eval_prompt(
        self,
        hypothesis: "Hypothesis",
        final_world_state: "WorldState",
        turn_narratives: list[str],
        sibling_summaries: list[str],
        evaluation_criteria: list[dict[str, str]] | None = None,
    ) -> str:
        """Build the LLM prompt for branch evaluation."""
        narratives_text = "\n".join(
            f"Turn {i+1}: {n}" for i, n in enumerate(turn_narratives[-10:])
        )
        siblings_text = (
            "\n".join(f"- {s}" for s in sibling_summaries)
            if sibling_summaries
            else "No sibling branches yet."
        )

        criteria_text = ""
        if evaluation_criteria:
            criteria_lines = "\n".join(
                f"- {c.get('name', '')}: {c.get('description', '')}"
                for c in evaluation_criteria
            )
            criteria_text = (
                f"\nAdditional evaluation criteria defined by the user:\n{criteria_lines}\n"
                "Factor these criteria into your rationale and scores.\n"
            )

        return (
            f"Hypothesis evaluated: {hypothesis.title}\n"
            f"Description: {hypothesis.description}\n\n"
            f"Final world state: {final_world_state.summary()}\n\n"
            f"Turn narratives (last 10):\n{narratives_text}\n\n"
            f"Sibling branches for comparison:\n{siblings_text}\n"
            f"{criteria_text}\n"
            "Score this branch on six dimensions (0.0-1.0 each):\n"
            "- character_fidelity_score: 원작 캐릭터의 성격/동기/말투 재현도 (how faithfully original characters' personality, motivation, and speech are reproduced)\n"
            "- fandom_resonance_score: 팬덤이 흥미로워할 전개인가 (how interesting and exciting the development would be to fans)\n"
            "- emergence_score: 예상치 못한 창발적 이벤트 (unexpected unscripted emergent events)\n"
            "- diversity_score: 분기 간 다양성 (distinctness of agent behaviours across branches)\n"
            "- plausibility_score: 세계관 규칙 내 논리적 타당성 (logical plausibility within the world's rules)\n"
            "- foreshadowing_score: quality of foreshadowing — naturalness of concealment, payoff rate, revelation impact, lag distance, retrospective inevitability, layeredness\n\n"
            "Respond with JSON:\n"
            '{"character_fidelity_score": 0.0, "fandom_resonance_score": 0.0, '
            '"emergence_score": 0.0, "diversity_score": 0.0, "plausibility_score": 0.0, '
            '"foreshadowing_score": 0.0, "rationale": "..."}'
        )

    def _parse_response(
        self, content: str, hypothesis_title: str, node_id: str
    ) -> EvaluationResult:
        """Parse LLM JSON response into an EvaluationResult."""
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError(f"Expected dict, got {type(data)}")

            def clamp(v: Any) -> float:
                try:
                    return max(0.0, min(1.0, float(v)))
                except (TypeError, ValueError):
                    return 0.5

            return EvaluationResult(
                hypothesis_title=hypothesis_title,
                node_id=node_id,
                character_fidelity_score=clamp(data.get("character_fidelity_score", 0.5)),
                fandom_resonance_score=clamp(data.get("fandom_resonance_score", 0.5)),
                emergence_score=clamp(data.get("emergence_score", 0.5)),
                diversity_score=clamp(data.get("diversity_score", 0.5)),
                plausibility_score=clamp(data.get("plausibility_score", 0.5)),
                foreshadowing_score=clamp(data.get("foreshadowing_score", 0.5)),
                rationale=str(data.get("rationale", "")),
            )

        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            logger.warning("Failed to parse evaluator LLM response: %s", exc)
            return EvaluationResult(
                hypothesis_title=hypothesis_title,
                node_id=node_id,
                character_fidelity_score=0.5,
                fandom_resonance_score=0.5,
                emergence_score=0.5,
                diversity_score=0.5,
                plausibility_score=0.5,
                foreshadowing_score=0.5,
                rationale=f"Parse error: {exc}",
            )
