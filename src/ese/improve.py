"""Improvement engine for Dormammu — Sub-AC 3c.

Reads a diagnosis result (from diagnose.py) and automatically generates an
ImprovementPlan: concrete parameter adjustments and strategy hints that the
EvolveOrchestrator can apply to the next simulation cycle.

The improve step closes the harness triangle loop:

    Benchmark → Diagnose → Improve → (next Evolve cycle)

Architecture
------------
ImprovementPlan   — the generated set of changes (params, strategies, criteria)
ImprovementRecord — persisted history entry: what was applied and the before scores
ScenarioImprover  — core logic: maps diagnosis → ImprovementPlan

Parameter Adjustment Rules
--------------------------
Weakest dimension → concrete parameter tweaks:

- avg_character_fidelity → +20% cost_limit_per_cycle (richer character prompts),
                           inject character fidelity evaluation criteria
- avg_fandom_resonance   → +10% node_years, +15% cost_limit_per_cycle,
                           inject fandom appeal evaluation criteria
- avg_emergence          → +20% node_years (more sim-time lets emergence develop),
                           slight +10% cost_limit_per_cycle
- avg_diversity          → +1 max_depth (broader exploration), keep cost budget
- avg_plausibility       → lower convergence_threshold by 20% (keep exploring longer),
                           inject world consistency criteria

Bottleneck-driven corrections:
- unevaluated_nodes  → +30% cost_limit_per_cycle to finish tree
- depth_degradation  → -1 max_depth (cap depth to where quality is still high)
- high_cost_turns    → -10% node_years (shorter turns = less prompt length)

Usage
-----
    from ese.improve import ScenarioImprover, apply_improvements
    from ese.diagnose import diagnose

    diagnosis = diagnose(benchmark_report)
    plan = ScenarioImprover().generate_plan(diagnosis, current_params)
    new_config = apply_improvements(plan, evolve_config)
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()


# --------------------------------------------------------------------------- #
# Per-dimension improvement rules
# --------------------------------------------------------------------------- #

# Each entry maps a score dimension key → improvement specification.
# `param_deltas` holds *relative* multipliers (1.2 means +20%).
# `criteria` is injected into evaluation_criteria for next cycle.
# `strategy_hints` are human-readable hints stored in the plan.
DIMENSION_IMPROVEMENT_RULES: dict[str, dict[str, Any]] = {
    "avg_character_fidelity": {
        "param_deltas": {
            "cost_limit_factor": 1.20,           # +20% budget → richer character prompts
        },
        "new_criteria": [
            {
                "name": "Character Fidelity",
                "description": (
                    "Reward branches where each character's actions, dialogue, and decisions "
                    "are consistent with their established personality, motivation, and speech "
                    "style from the source material."
                ),
            }
        ],
        "strategy_hints": [
            "Inject canonical character profile (personality, catchphrases, relationships) "
            "from the research document into every agent decision prompt.",
            "Add a post-action consistency check: ask the LLM whether the chosen action "
            "is in character before finalising.",
            "Include the character's canonical relationships and rivalries in the context.",
        ],
    },
    "avg_fandom_resonance": {
        "param_deltas": {
            "node_years_factor": 1.10,           # +10% sim time for richer plot arcs
            "cost_limit_factor": 1.15,           # +15% budget for better hypothesis generation
        },
        "new_criteria": [
            {
                "name": "Fandom Appeal",
                "description": (
                    "Reward branches that include fan-favourite dynamics, dramatic confrontations, "
                    "or resolution of canonical unresolved plot threads that fans care about."
                ),
            }
        ],
        "strategy_hints": [
            "Inject fandom-specific tropes and fan-favourite character dynamics into "
            "the hypothesis generation prompt.",
            "Ask the LLM to rate each generated hypothesis by fan appeal before finalising.",
            "Include known fan expectations and canonical unresolved threads from "
            "the research document.",
        ],
    },
    "avg_emergence": {
        "param_deltas": {
            "node_years_factor": 1.20,          # +20% simulation time
            "cost_limit_factor": 1.10,           # +10% budget for richer turns
        },
        "new_criteria": [
            {
                "name": "Emergent Events",
                "description": (
                    "Reward branches where 1+ unexpected, unscripted events arise "
                    "from agent interactions that the scenario description did not anticipate."
                ),
            }
        ],
        "strategy_hints": [
            "After resolving agent actions, explicitly prompt the LLM to generate "
            "0-2 unexpected world events that result from the combined agent activities.",
            "Include emergent event descriptions in the next turn's context window.",
            "Raise the weight of emergence_score in hypothesis ranking.",
        ],
    },
    "avg_diversity": {
        "param_deltas": {
            "max_depth_delta": +1,               # one extra DFS level → more branches
        },
        "new_criteria": [
            {
                "name": "Agent Distinctiveness",
                "description": (
                    "Reward branches where agents with different persona trait values "
                    "(extraversion, risk_tolerance, curiosity) make distinctly different choices."
                ),
            }
        ],
        "strategy_hints": [
            "Add persona trait values to every agent action decision prompt.",
            "Provide a trait-to-action preference table: "
            "high extraversion → INTERACT/TRADE; low → OBSERVE/RESEARCH.",
            "Penalise branches where all agents choose the same action type.",
        ],
    },
    "avg_plausibility": {
        "param_deltas": {
            "convergence_threshold_factor": 0.80,  # -20% threshold → keep exploring longer
        },
        "new_criteria": [
            {
                "name": "World Consistency",
                "description": (
                    "Reward branches where all events and decisions are logically consistent "
                    "with the established rules, physics, and canon of the story world."
                ),
            }
        ],
        "strategy_hints": [
            "Include world-building rules and established canon facts from the research "
            "document in the evaluator prompt.",
            "Add an explicit consistency check step: ask the LLM to flag rule violations "
            "before scoring.",
            "Penalise hypotheses that contradict established canon or break world rules.",
        ],
    },
}

# Bottleneck → parameter correction mapping
BOTTLENECK_CORRECTIONS: dict[str, dict[str, Any]] = {
    "unevaluated_nodes": {
        "param_deltas": {"cost_limit_factor": 1.30},
        "hint": "Increased cost_limit_per_cycle by 30% to allow full tree evaluation.",
    },
    "depth_degradation": {
        "param_deltas": {"max_depth_delta": -1},
        "hint": "Reduced max_depth by 1 to cap exploration at quality-sustained depth.",
    },
    "high_cost": {
        "param_deltas": {"node_years_factor": 0.90},
        "hint": "Reduced node_years by 10% to shorten prompts and lower turn cost.",
    },
}

# Hard bounds: prevent parameters from going out of safe ranges
PARAM_BOUNDS: dict[str, tuple[float, float]] = {
    "node_years": (10.0, 1000.0),
    "max_depth": (1.0, 10.0),
    "cost_limit_per_cycle": (0.1, 100.0),
    "convergence_threshold": (0.01, 0.30),
}

# Direct mapping from human-readable dimension label → DIMENSION_IMPROVEMENT_RULES key.
# Must mirror DIMENSION_MAP labels in diagnose.py.
_LABEL_TO_DIMENSION_KEY: dict[str, str] = {
    "Character Fidelity": "avg_character_fidelity",
    "Fandom Resonance": "avg_fandom_resonance",
    "Emergence": "avg_emergence",
    "Diversity": "avg_diversity",
    "Plausibility": "avg_plausibility",
}


# --------------------------------------------------------------------------- #
# Data classes
# --------------------------------------------------------------------------- #


@dataclass
class ImprovementPlan:
    """A fully computed improvement plan derived from a diagnosis result.

    Designed to be:
    - Directly applicable to EvolveConfig (via apply_improvements / ScenarioImprover)
    - JSON-serialisable for persistence
    - Human-readable for the CLI `ese improve` command

    Attributes:
        focus_dimension:       The weakest dimension that drove this plan.
        focus_score:           That dimension's score at time of diagnosis.
        param_adjustments:     Concrete parameter values to use in the next cycle.
                               Keys match EvolveConfig field names.
        strategy_hints:        Ordered list of prompting/strategy improvements.
        new_evaluation_criteria: Additional criteria dicts to inject into the evaluator.
        bottleneck_corrections: List of applied bottleneck corrections (for display).
        generated_at:          ISO 8601 timestamp.
        source_diagnosis:      The raw diagnosis dict this plan was built from.
    """

    focus_dimension: str
    focus_score: float

    # Concrete values to apply — not deltas, but absolute target values.
    param_adjustments: dict[str, Any] = field(default_factory=dict)

    # Strategy and criteria improvements
    strategy_hints: list[str] = field(default_factory=list)
    new_evaluation_criteria: list[dict[str, str]] = field(default_factory=list)
    bottleneck_corrections: list[str] = field(default_factory=list)

    generated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source_diagnosis: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "focus_dimension": self.focus_dimension,
            "focus_score": self.focus_score,
            "param_adjustments": self.param_adjustments,
            "strategy_hints": self.strategy_hints,
            "new_evaluation_criteria": self.new_evaluation_criteria,
            "bottleneck_corrections": self.bottleneck_corrections,
            "generated_at": self.generated_at,
            "source_diagnosis": self.source_diagnosis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ImprovementPlan":
        """Restore an ImprovementPlan from a previously serialised dict."""
        return cls(
            focus_dimension=data.get("focus_dimension", "unknown"),
            focus_score=float(data.get("focus_score", 0.0)),
            param_adjustments=data.get("param_adjustments", {}),
            strategy_hints=data.get("strategy_hints", []),
            new_evaluation_criteria=data.get("new_evaluation_criteria", []),
            bottleneck_corrections=data.get("bottleneck_corrections", []),
            generated_at=data.get("generated_at", datetime.utcnow().isoformat()),
            source_diagnosis=data.get("source_diagnosis", {}),
        )


@dataclass
class ImprovementRecord:
    """A single entry in the improvement history log.

    Written to data/improvements/improvement_history.jsonl every time a
    plan is applied so that score trajectory can be tracked across cycles.

    Attributes:
        cycle:             Evolve cycle number (0 if called outside evolve loop).
        plan:              The ImprovementPlan that was applied.
        before_scores:     4-dim scores before the improvement.
        applied_at:        Timestamp when the plan was applied.
    """

    cycle: int
    plan: ImprovementPlan
    before_scores: dict[str, float] = field(default_factory=dict)
    applied_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle": self.cycle,
            "plan": self.plan.to_dict(),
            "before_scores": self.before_scores,
            "applied_at": self.applied_at,
        }


# --------------------------------------------------------------------------- #
# Core improver
# --------------------------------------------------------------------------- #


class ScenarioImprover:
    """Maps a diagnosis result to a concrete ImprovementPlan.

    This class is the heart of the improve step. It applies a rule-based
    algorithm (no LLM required) to derive parameter adjustments and strategy
    hints from the weakest dimension and detected bottlenecks.

    Usage::

        improver = ScenarioImprover()
        plan = improver.generate_plan(diagnosis, current_params)
        new_config = improver.apply_to_config(plan, evolve_config)
    """

    def generate_plan(
        self,
        diagnosis: dict[str, Any],
        current_params: dict[str, Any],
    ) -> ImprovementPlan:
        """Generate an ImprovementPlan from diagnosis + current parameters.

        The plan is entirely rule-based (deterministic), so it works
        without an API key and is reproducible across runs.

        Algorithm:
        1. Identify the weakest dimension key from the diagnosis.
        2. Look up dimension-specific rules (param_deltas, criteria, hints).
        3. Apply relative deltas to current parameter values.
        4. Detect and apply bottleneck corrections on top.
        5. Clamp all values to PARAM_BOUNDS.
        6. Return a complete ImprovementPlan.

        Args:
            diagnosis:       Output from diagnose.diagnose().
            current_params:  Current parameter values. Expected keys:
                             node_years, max_depth, cost_limit_per_cycle,
                             convergence_threshold. Missing keys fall back
                             to safe defaults.

        Returns:
            A fully populated ImprovementPlan.
        """
        weakest_label = diagnosis.get("weakest_dimension", "unknown")
        focus_score = float(diagnosis.get("score", 0.0))

        # Map human-readable label → DIMENSION_IMPROVEMENT_RULES key
        dimension_key = _LABEL_TO_DIMENSION_KEY.get(weakest_label)

        # --- Base rules from weakest dimension ---
        rules = DIMENSION_IMPROVEMENT_RULES.get(dimension_key or "", {})
        param_deltas: dict[str, Any] = dict(rules.get("param_deltas", {}))
        strategy_hints: list[str] = list(rules.get("strategy_hints", []))
        new_criteria: list[dict[str, str]] = list(rules.get("new_criteria", []))
        bottleneck_corrections: list[str] = []

        # --- Bottleneck corrections ---
        bottleneck_suggestions = diagnosis.get("bottleneck_suggestions", [])
        failure_patterns = diagnosis.get("failure_patterns", [])

        # Detect unevaluated nodes hint → increase cost
        if any(
            "cost" in s.lower() or "limit" in s.lower()
            for s in bottleneck_suggestions
        ):
            correction = BOTTLENECK_CORRECTIONS["unevaluated_nodes"]
            _merge_deltas(param_deltas, correction["param_deltas"])
            bottleneck_corrections.append(correction["hint"])

        # Detect depth degradation hint → reduce depth
        if any(
            "depth" in s.lower() or "deeper" in s.lower()
            for s in bottleneck_suggestions
        ):
            correction = BOTTLENECK_CORRECTIONS["depth_degradation"]
            _merge_deltas(param_deltas, correction["param_deltas"])
            bottleneck_corrections.append(correction["hint"])

        # Detect high-cost hint → reduce node_years
        if any(
            "prompt" in s.lower() or "expensive" in s.lower() or "costly" in s.lower()
            for s in bottleneck_suggestions
        ):
            correction = BOTTLENECK_CORRECTIONS["high_cost"]
            _merge_deltas(param_deltas, correction["param_deltas"])
            bottleneck_corrections.append(correction["hint"])

        # --- Apply deltas to current params → absolute values ---
        adjusted = _compute_adjusted_params(param_deltas, current_params)

        return ImprovementPlan(
            focus_dimension=weakest_label,
            focus_score=focus_score,
            param_adjustments=adjusted,
            strategy_hints=strategy_hints,
            new_evaluation_criteria=new_criteria,
            bottleneck_corrections=bottleneck_corrections,
            source_diagnosis=diagnosis,
        )

    def apply_to_config(
        self,
        plan: ImprovementPlan,
        evolve_config: Any,  # EvolveConfig — typed loosely to avoid circular import
    ) -> Any:
        """Return a new EvolveConfig with improvements from the plan applied.

        Only keys present in ``plan.param_adjustments`` are changed; all
        other EvolveConfig fields are copied verbatim.

        Args:
            plan:          The ImprovementPlan to apply.
            evolve_config: The current EvolveConfig instance.

        Returns:
            A new EvolveConfig instance with adjusted parameters.
        """
        from ese.orchestrator.evolve import EvolveConfig
        import dataclasses

        adjustments = plan.param_adjustments
        # Build a dict of current config values
        current = dataclasses.asdict(evolve_config)

        # Apply adjustments (only recognised keys)
        recognised = {
            "node_years", "max_depth", "cost_limit_per_cycle", "convergence_threshold"
        }
        for key in recognised:
            if key in adjustments:
                current[key] = adjustments[key]

        # Reconstruct EvolveConfig — drop internal-only keys like 'output_dir' Path
        # that dataclasses.asdict converts to a raw Path but EvolveConfig accepts.
        return EvolveConfig(**current)


# --------------------------------------------------------------------------- #
# Convenience helpers
# --------------------------------------------------------------------------- #


def apply_improvements(
    plan: ImprovementPlan,
    evolve_config: Any,
    cycle: int = 0,
    before_scores: dict[str, float] | None = None,
    persist: bool = True,
) -> Any:
    """Apply an ImprovementPlan to an EvolveConfig and optionally persist the record.

    This is the main entry point for the evolve loop integration.

    Args:
        plan:          The ImprovementPlan to apply.
        evolve_config: Current EvolveConfig.
        cycle:         Evolve cycle number for record-keeping.
        before_scores: 4-dim scores *before* the improvement (for history).
        persist:       If True, append a record to the improvement history log.

    Returns:
        A new EvolveConfig with improvements applied.
    """
    improver = ScenarioImprover()
    new_config = improver.apply_to_config(plan, evolve_config)

    if persist:
        record = ImprovementRecord(
            cycle=cycle,
            plan=plan,
            before_scores=before_scores or {},
        )
        _persist_record(record, evolve_config)

    return new_config


def generate_improvement_plan(
    diagnosis: dict[str, Any],
    current_params: dict[str, Any] | None = None,
) -> ImprovementPlan:
    """Convenience wrapper: generate a plan from a diagnosis dict.

    Args:
        diagnosis:      Output from diagnose.diagnose().
        current_params: Current simulation parameters. When None, uses global
                        config defaults.

    Returns:
        An ImprovementPlan ready for display or application.
    """
    if current_params is None:
        from ese.config import config as _config
        current_params = {
            "node_years": _config.node_years,
            "max_depth": _config.max_depth,
            "cost_limit_per_cycle": _config.cost_limit,
            "convergence_threshold": 0.05,
        }

    return ScenarioImprover().generate_plan(diagnosis, current_params)


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _merge_deltas(
    base: dict[str, Any],
    extra: dict[str, Any],
) -> None:
    """Merge extra deltas into base, multiplying factor values together."""
    for k, v in extra.items():
        if k.endswith("_factor") and k in base:
            # Both are factors: multiply
            base[k] = base[k] * v
        elif k.endswith("_delta") and k in base:
            # Both are integer deltas: add
            base[k] = base[k] + v
        else:
            base[k] = v


def _compute_adjusted_params(
    deltas: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    """Apply relative deltas to current parameter values with bounds clamping.

    Delta conventions:
    - ``{key}_factor`` → multiply current value by factor (float)
    - ``{key}_delta``  → add integer delta to current value (int/float)

    Args:
        deltas:  Dict of delta specifications.
        current: Current parameter values.

    Returns:
        Dict of new absolute parameter values (clamped to PARAM_BOUNDS).
    """
    # Defaults for missing keys
    defaults: dict[str, float] = {
        "node_years": 100.0,
        "max_depth": 5.0,
        "cost_limit_per_cycle": 10.0,
        "convergence_threshold": 0.05,
    }
    # Merge current with defaults
    base = {k: float(current.get(k, defaults[k])) for k in defaults}

    # Apply factor deltas
    if "node_years_factor" in deltas:
        base["node_years"] *= float(deltas["node_years_factor"])
    if "cost_limit_factor" in deltas:
        base["cost_limit_per_cycle"] *= float(deltas["cost_limit_factor"])
    if "convergence_threshold_factor" in deltas:
        base["convergence_threshold"] *= float(deltas["convergence_threshold_factor"])

    # Apply integer deltas
    if "max_depth_delta" in deltas:
        base["max_depth"] += int(deltas["max_depth_delta"])

    # Clamp to bounds
    result: dict[str, Any] = {}
    for key, value in base.items():
        lo, hi = PARAM_BOUNDS.get(key, (0.0, 1e9))
        clamped = max(lo, min(hi, value))
        # Keep integer types for integer fields
        if key in ("node_years", "max_depth"):
            result[key] = int(round(clamped))
        else:
            result[key] = round(clamped, 6)

    return result


def _improvements_dir() -> Path:
    """Return the path to data/improvements/, creating it if needed."""
    from ese.config import config
    improvements_dir = config.data_dir.parent / "data" / "improvements"
    improvements_dir.mkdir(parents=True, exist_ok=True)
    return improvements_dir


def _persist_record(record: ImprovementRecord, _config_ref: Any) -> None:
    """Append an ImprovementRecord to the history JSONL log."""
    try:
        history_path = _improvements_dir() / "improvement_history.jsonl"
        with history_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Improvement record appended to %s", history_path)
    except Exception as exc:
        logger.warning("Failed to persist improvement record: %s", exc)


# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #


def print_improvement_plan(
    plan: ImprovementPlan,
    current_params: dict[str, Any] | None = None,
) -> None:
    """Print a formatted improvement plan to the console using Rich.

    Displays:
    1. Focus dimension and score
    2. Parameter adjustments (before → after)
    3. Strategy hints
    4. New evaluation criteria
    5. Applied bottleneck corrections (if any)

    Args:
        plan:           The ImprovementPlan to display.
        current_params: Current params for before/after comparison (optional).
    """
    adjustments = plan.param_adjustments

    # --- Parameter adjustments table ---
    param_table = Table(show_lines=False, box=None, padding=(0, 2))
    param_table.add_column("Parameter", style="dim")
    param_table.add_column("Before", justify="right")
    param_table.add_column("After", justify="right", style="green")

    param_display_names = {
        "node_years": "node_years",
        "max_depth": "max_depth",
        "cost_limit_per_cycle": "cost_limit_per_cycle",
        "convergence_threshold": "convergence_threshold",
    }

    for key, label in param_display_names.items():
        if key in adjustments:
            before_val = str(current_params.get(key, "?")) if current_params else "?"
            after_val = str(adjustments[key])
            param_table.add_row(label, before_val, after_val)

    # --- Strategy hints ---
    hints_text = "\n".join(f"  • {h}" for h in plan.strategy_hints) or "  (none)"

    # --- Criteria ---
    criteria_text = (
        "\n".join(
            f"  • [{c.get('name', '')}] {c.get('description', '')}"
            for c in plan.new_evaluation_criteria
        )
        or "  (none)"
    )

    # --- Main panel ---
    score_color = "green" if plan.focus_score >= 0.5 else "red"
    panel_content = (
        f"[bold]Focus dimension:[/] [red]{plan.focus_dimension}[/]  "
        f"(score: [{score_color}]{plan.focus_score:.4f}[/{score_color}])\n\n"
        f"[bold]Parameter adjustments:[/]\n"
    )
    console.print(
        Panel(
            panel_content,
            title="[bold cyan]Dormammu Improvement Plan[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(param_table)

    # Hints
    console.print(
        Panel(
            hints_text,
            title="[bold yellow]Strategy Hints[/]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # Criteria
    console.print(
        Panel(
            criteria_text,
            title="[bold magenta]New Evaluation Criteria[/]",
            border_style="magenta",
            padding=(1, 2),
        )
    )

    # Bottleneck corrections
    if plan.bottleneck_corrections:
        bn_text = "\n".join(f"  • {c}" for c in plan.bottleneck_corrections)
        console.print(
            Panel(
                bn_text,
                title="[bold red]Bottleneck Corrections Applied[/]",
                border_style="red",
                padding=(1, 2),
            )
        )
