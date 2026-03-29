"""Diagnosis system for Dormammu.

Reads the latest benchmark result, identifies the weakest score dimension,
detects bottleneck and failure patterns, and maps findings to specific
modules and methods with actionable suggestions.

Usage
-----
    ese diagnose           # Print diagnosis based on latest benchmark
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()

# Mapping from score dimension to diagnosis details.
# Each entry describes which code location to look at and what to change.
DIMENSION_MAP: dict[str, dict[str, str]] = {
    "avg_character_fidelity": {
        "label": "Character Fidelity",
        "target_module": "src/ese/agents/agent.py",
        "target_method": "Agent.decide_action",
        "suggestion": (
            "Characters are not faithfully reproducing the original's personality, "
            "motivation, or speech style. Add character profile data (from the research "
            "phase) to the agent decision prompt. Include canonical traits, catchphrases, "
            "and known relationships so the LLM grounds each action in established canon."
        ),
    },
    "avg_fandom_resonance": {
        "label": "Fandom Resonance",
        "target_module": "src/ese/hypothesis/generator.py",
        "target_method": "HypothesisGenerator.generate",
        "suggestion": (
            "Generated branches lack the dramatic hooks that fans find exciting. "
            "Improve by: (1) injecting fandom-specific tropes and fan-favourite "
            "character dynamics into the hypothesis prompt; (2) including research "
            "context about key fan expectations and canonical unresolved plot threads; "
            "(3) explicitly asking the LLM to rate each hypothesis by fan appeal before "
            "finalising the list."
        ),
    },
    "avg_emergence": {
        "label": "Emergence",
        "target_module": "src/ese/engine/turn.py",
        "target_method": "TurnExecutor.execute",
        "suggestion": (
            "The turn execution prompt doesn't generate enough unscripted events. "
            "Add a dedicated 'emergent event' generation step: after resolving agent "
            "actions, ask the LLM to produce 0-2 unexpected world events that result "
            "from the combined agent activities. Include these in TurnResult.impact_events "
            "and reference them in the next turn's context."
        ),
    },
    "avg_diversity": {
        "label": "Diversity",
        "target_module": "src/ese/agents/agent.py",
        "target_method": "Agent.decide_action",
        "suggestion": (
            "The action decision prompt doesn't differentiate by persona. "
            "Add persona trait values to the prompt: 'Your extraversion is 0.8 — "
            "you prefer to initiate conversations and form alliances.' "
            "Provide a trait-to-action preference table and instruct the LLM to "
            "select actions consistent with the agent's personality. "
            "High extraversion → INTERACT/TRADE; low → OBSERVE/RESEARCH."
        ),
    },
    "avg_plausibility": {
        "label": "Plausibility",
        "target_module": "src/ese/hypothesis/evaluator.py",
        "target_method": "HypothesisEvaluator._build_eval_prompt",
        "suggestion": (
            "Branches violate the world's established rules or internal logic. "
            "Improve by: (1) including world-building rules and established canon facts "
            "from the research document in the evaluator prompt; (2) adding an explicit "
            "consistency check step asking the LLM to flag rule violations before scoring; "
            "(3) penalising hypotheses that contradict established canon."
        ),
    },
    "avg_composite": {
        "label": "Composite Score",
        "target_module": "src/ese/hypothesis/evaluator.py",
        "target_method": "HypothesisEvaluator.evaluate",
        "suggestion": (
            "The composite score is the weighted average of all dimensions. "
            "Improve the weakest sub-dimension first. If all dimensions are balanced "
            "but low, the evaluation criteria may not align with the simulation content. "
            "Ensure evaluation_criteria are passed to the evaluator and feature "
            "prominently in the scoring prompt."
        ),
    },
}

# Bottleneck pattern → suggestion mapping
BOTTLENECK_MAP: dict[str, str] = {
    "unevaluated_nodes": (
        "Several nodes were not evaluated. This typically means the simulation hit "
        "the cost limit before completing. Consider increasing cost_limit or reducing "
        "max_depth / node_years so each node can be fully evaluated."
    ),
    "low_score_nodes": (
        "Multiple nodes scored below 0.4 composite. These drag down the average. "
        "Check whether evaluation_criteria are too strict, or whether agent personas "
        "are too similar to produce interesting interactions."
    ),
    "depth_degradation": (
        "Quality declines at deeper tree levels. This suggests hypotheses at deeper "
        "depths are less interesting. Review HypothesisGenerator.generate to ensure "
        "deeper hypotheses build meaningfully on parent context, and consider "
        "increasing the SF inspiration injection frequency."
    ),
    "high_cost": (
        "Some turns are disproportionately expensive. This may indicate overly long "
        "prompts or very large world-state summaries. Consider capping "
        "WorldState.events to the last 20 entries and truncating narrative length."
    ),
}


def _benchmarks_dir() -> Path:
    """Return path to data/benchmarks/."""
    from ese.config import config

    return config.data_dir.parent / "data" / "benchmarks"


def load_latest_benchmark() -> dict[str, Any] | None:
    """Load the most recently saved benchmark report.

    Returns:
        The benchmark report dict, or None if no benchmarks exist.
    """
    bench_dir = _benchmarks_dir()
    if not bench_dir.exists():
        return None

    files = sorted(bench_dir.glob("benchmark_*.json"), reverse=True)
    if not files:
        return None

    try:
        return json.loads(files[0].read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error("Failed to read benchmark file %s: %s", files[0], exc)
        return None


def diagnose(report: dict[str, Any]) -> dict[str, Any]:
    """Identify the weakest score dimension and produce a structured diagnosis.

    In addition to identifying the weakest dimension, this function analyses
    the bottleneck and failure patterns present in the report's ``bottlenecks``
    and ``per_node_metrics`` sections.

    Args:
        report: A benchmark report dict (as returned by run_benchmark()).

    Returns:
        A diagnosis dict with keys:
          - weakest_dimension: label of the lowest-scoring dimension
          - score: its average score value
          - target_module: source file to look at
          - target_method: specific method to improve
          - suggestion: actionable improvement text
          - failure_patterns: list of detected failure pattern descriptions
          - bottleneck_suggestions: list of bottleneck-specific suggestions
    """
    scores = report.get("scores", {})

    # Exclude avg_composite from weakest detection — it's derived
    dimension_keys = [
        "avg_character_fidelity",
        "avg_fandom_resonance",
        "avg_emergence",
        "avg_diversity",
        "avg_plausibility",
    ]
    available = {k: scores[k] for k in dimension_keys if k in scores}

    if not available:
        return {
            "weakest_dimension": "unknown",
            "score": 0.0,
            "target_module": "src/ese/",
            "target_method": "N/A",
            "suggestion": "No score data found. Run `ese benchmark` first.",
            "failure_patterns": [],
            "bottleneck_suggestions": [],
        }

    weakest_key = min(available, key=lambda k: available[k])
    weakest_score = available[weakest_key]

    detail = DIMENSION_MAP.get(weakest_key, DIMENSION_MAP["avg_composite"])

    failure_patterns = detect_failure_patterns(report)
    bottleneck_suggestions = detect_bottleneck_suggestions(report)

    return {
        "weakest_dimension": detail["label"],
        "score": round(weakest_score, 4),
        "target_module": detail["target_module"],
        "target_method": detail["target_method"],
        "suggestion": detail["suggestion"],
        "failure_patterns": failure_patterns,
        "bottleneck_suggestions": bottleneck_suggestions,
    }


def detect_failure_patterns(report: dict[str, Any]) -> list[str]:
    """Detect failure patterns from a benchmark report.

    Failure patterns include:
    - Nodes that were never evaluated (skipped/pruned before scoring)
    - All nodes sharing the same score (LLM returned placeholder values)
    - Simulation ended due to cost limit before tree was fully explored

    Args:
        report: A benchmark report dict.

    Returns:
        List of human-readable failure pattern descriptions.
    """
    patterns: list[str] = []

    bottlenecks = report.get("bottlenecks", {})
    per_node = report.get("per_node_metrics", [])
    metadata = report.get("metadata", {})
    scores = report.get("scores", {})

    # Pattern 1: Unevaluated nodes
    unevaluated = bottlenecks.get("unevaluated_nodes", [])
    if unevaluated:
        patterns.append(
            f"{len(unevaluated)} node(s) were not evaluated — "
            "the simulation may have been cut short by the cost limit or an error."
        )

    # Pattern 2: Placeholder scores (all dimensions exactly 0.5)
    dimension_values = [
        scores.get(k, 0.0)
        for k in (
            "avg_character_fidelity",
            "avg_fandom_resonance",
            "avg_emergence",
            "avg_diversity",
            "avg_plausibility",
        )
    ]
    if all(abs(v - 0.5) < 1e-9 for v in dimension_values) and dimension_values:
        patterns.append(
            "All dimension scores are exactly 0.5 — this typically means no real "
            "LLM evaluation occurred (placeholder mode or API key missing)."
        )

    # Pattern 3: Zero evaluated nodes
    evaluated_count = sum(1 for n in per_node if n.get("evaluated"))
    total_count = len(per_node)
    if total_count > 0 and evaluated_count == 0:
        patterns.append(
            f"None of the {total_count} node(s) were evaluated — "
            "check that OPENAI_API_KEY is set and the evaluator is not erroring."
        )

    # Pattern 4: Very low evaluation coverage (< 50%)
    elif total_count > 0 and evaluated_count / total_count < 0.5:
        patterns.append(
            f"Only {evaluated_count}/{total_count} nodes were evaluated "
            f"({100 * evaluated_count // total_count}% coverage) — "
            "simulation likely hit cost limit or time out early."
        )

    # Pattern 5: Placeholder flag in metadata
    if metadata.get("placeholder"):
        patterns.append(
            "Report was generated in placeholder mode (no API key or simulation error)."
        )

    return patterns


def detect_bottleneck_suggestions(report: dict[str, Any]) -> list[str]:
    """Generate actionable suggestions for detected bottlenecks.

    Analyses ``bottlenecks`` section of the report and maps each finding
    to a concrete improvement suggestion from ``BOTTLENECK_MAP``.

    Args:
        report: A benchmark report dict.

    Returns:
        List of actionable suggestion strings.
    """
    suggestions: list[str] = []
    bottlenecks = report.get("bottlenecks", {})
    turn_stats = report.get("turn_stats", {})

    # Unevaluated nodes → cost limit issue
    if bottlenecks.get("unevaluated_nodes"):
        suggestions.append(BOTTLENECK_MAP["unevaluated_nodes"])

    # Low-score nodes
    if bottlenecks.get("low_score_nodes"):
        suggestions.append(BOTTLENECK_MAP["low_score_nodes"])

    # Depth degradation
    depth_trend = bottlenecks.get("depth_score_trend", {})
    if len(depth_trend) >= 2:
        depths = sorted(depth_trend.keys())
        first = depth_trend[depths[0]]
        last = depth_trend[depths[-1]]
        if last < first - 0.1:
            suggestions.append(BOTTLENECK_MAP["depth_degradation"])

    # High per-turn cost (any turn costs more than 0.05 USD)
    high_cost = bottlenecks.get("high_cost_turns", [])
    if high_cost and (high_cost[0].get("cost_usd") or 0.0) > 0.05:
        suggestions.append(BOTTLENECK_MAP["high_cost"])

    return suggestions


def print_diagnosis(diagnosis: dict[str, Any], report: dict[str, Any]) -> None:
    """Print diagnosis to console with context from the full report.

    Displays:
    1. Score summary table with weakest dimension highlighted
    2. Main diagnosis panel (weakest dimension + suggestion)
    3. Failure pattern panel (if patterns were detected)
    4. Bottleneck suggestion panel (if bottlenecks were found)

    Args:
        diagnosis: Diagnosis dict from diagnose().
        report: Full benchmark report for context display.
    """
    scores = report.get("scores", {})
    git_hash = report.get("git_hash", "unknown")
    timestamp = report.get("timestamp", "")

    # Score summary table
    from rich.table import Table

    score_table = Table(show_lines=False, box=None, padding=(0, 2))
    score_table.add_column("Dimension", style="dim")
    score_table.add_column("Score", justify="right")

    labels = {
        "avg_character_fidelity": "Character Fidelity",
        "avg_fandom_resonance": "Fandom Resonance",
        "avg_emergence": "Emergence",
        "avg_diversity": "Diversity",
        "avg_plausibility": "Plausibility",
        "avg_composite": "Composite",
    }

    weakest_label = diagnosis["weakest_dimension"]

    for key, label in labels.items():
        score = scores.get(key, 0.0)
        is_weakest = label == weakest_label and key != "avg_composite"
        color = "red" if is_weakest else ("green" if score >= 0.6 else "yellow")
        indicator = " ← weakest" if is_weakest else ""
        score_table.add_row(
            f"[{color}]{label}[/{color}]{indicator}",
            f"[{color}]{score:.4f}[/{color}]",
        )

    console.print(f"\n[dim]Benchmark: {timestamp[:19]} | git: {git_hash}[/]")
    console.print(score_table)

    # Main diagnosis panel
    panel_content = (
        f"[bold]Weakest dimension:[/] [red]{diagnosis['weakest_dimension']}[/] "
        f"(score: {diagnosis['score']:.4f})\n\n"
        f"[bold]Target module:[/] [cyan]{diagnosis['target_module']}[/]\n"
        f"[bold]Target method:[/] [cyan]{diagnosis['target_method']}[/]\n\n"
        f"[bold]Suggestion:[/]\n{diagnosis['suggestion']}"
    )

    console.print(
        Panel(
            panel_content,
            title="[bold yellow]Dormammu Diagnosis[/]",
            border_style="yellow",
            padding=(1, 2),
        )
    )

    # Failure patterns panel
    failure_patterns = diagnosis.get("failure_patterns", [])
    if failure_patterns:
        failure_text = "\n".join(f"• {p}" for p in failure_patterns)
        console.print(
            Panel(
                failure_text,
                title="[bold red]Failure Patterns Detected[/]",
                border_style="red",
                padding=(1, 2),
            )
        )

    # Bottleneck suggestions panel
    bn_suggestions = diagnosis.get("bottleneck_suggestions", [])
    if bn_suggestions:
        bn_text = "\n\n".join(f"[bold]→[/] {s}" for s in bn_suggestions)
        console.print(
            Panel(
                bn_text,
                title="[bold magenta]Bottleneck Suggestions[/]",
                border_style="magenta",
                padding=(1, 2),
            )
        )
