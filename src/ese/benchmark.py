"""Benchmark system for Dormammu.

Runs a fixed, deterministic simulation and produces a reproducible score report.
Results are saved to data/benchmarks/ for tracking quality over time.

Usage
-----
    ese benchmark          # Run benchmark and print scores

Report Structure
----------------
Each benchmark report contains:
  - scores: per-dimension averages (character_fidelity, fandom_resonance, emergence, diversity, plausibility, composite)
  - per_node_metrics: per-hypothesis/node detailed breakdown
  - bottlenecks: nodes with low scores, high turn counts, or high cost
  - turn_stats: aggregate turn-level statistics (avg cost, token use)
  - metadata: simulation parameters, git hash, timestamps
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

# Fixed benchmark parameters — do not change without updating history baseline
BENCHMARK_TOPIC = "인류 최초의 화성 식민지 50년"
BENCHMARK_MAX_DEPTH = 1
BENCHMARK_COST_LIMIT = 0.5
BENCHMARK_NODE_YEARS = 100

# Composite score weights — mirror EvaluationResult.composite_score
_COMPOSITE_WEIGHTS = {
    "character_fidelity_score": 0.20,
    "fandom_resonance_score": 0.15,
    "emergence_score": 0.15,
    "diversity_score": 0.15,
    "plausibility_score": 0.15,
    "foreshadowing_score": 0.20,
}

# Threshold below which a node is considered "low quality"
LOW_SCORE_THRESHOLD = 0.4


def _get_git_hash() -> str:
    """Return short git hash of HEAD, or 'unknown' if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _benchmarks_dir() -> Path:
    """Return path to data/benchmarks/, creating it if needed."""
    from ese.config import config

    bench_dir = config.data_dir.parent / "data" / "benchmarks"
    bench_dir.mkdir(parents=True, exist_ok=True)
    return bench_dir


def _latest_benchmark_path() -> Path | None:
    """Return path to the most recently written benchmark JSON, or None."""
    bench_dir = _benchmarks_dir()
    files = sorted(bench_dir.glob("benchmark_*.json"), reverse=True)
    return files[0] if files else None


def _composite(hyp: dict[str, Any]) -> float:
    """Compute composite score from a hypothesis/node row."""
    return sum(
        (hyp.get(k) or 0.0) * w for k, w in _COMPOSITE_WEIGHTS.items()
    )


def run_benchmark() -> dict[str, Any]:
    """Run the fixed benchmark simulation and return a structured report.

    The simulation uses deterministic parameters so results are comparable
    across code changes. When no API key is available, placeholder scores
    are returned so the report structure is always valid.

    Returns:
        A report dict with keys: timestamp, git_hash, scores, per_node_metrics,
        bottlenecks, turn_stats, metadata.
    """
    import asyncio

    from ese.config import config
    from ese.orchestrator.loop import OrchestratorLoop

    timestamp = datetime.now(tz=timezone.utc).isoformat()
    git_hash = _get_git_hash()

    console.print(f"\n[bold cyan]Dormammu Benchmark[/] | {BENCHMARK_TOPIC}")
    console.print(
        f"  max_depth={BENCHMARK_MAX_DEPTH}, "
        f"node_years={BENCHMARK_NODE_YEARS}, "
        f"cost_limit=${BENCHMARK_COST_LIMIT:.2f}"
    )

    if not config.openai_api_key:
        console.print(
            "[yellow]No OPENAI_API_KEY found — returning placeholder scores.[/]"
        )
        report = _placeholder_report(timestamp, git_hash)
        _save_report(report)
        return report

    loop = OrchestratorLoop(
        max_depth=BENCHMARK_MAX_DEPTH,
        node_years=BENCHMARK_NODE_YEARS,
        cost_limit=BENCHMARK_COST_LIMIT,
    )

    try:
        sim_id = loop.start(topic=BENCHMARK_TOPIC)
    except Exception as exc:
        logger.error("Benchmark simulation failed: %s", exc)
        report = _placeholder_report(timestamp, git_hash, error=str(exc))
        _save_report(report)
        return report

    # Collect evaluation results from database
    from ese.storage.database import Database

    db = Database()
    sim_data = db.get_simulation(sim_id)
    hypotheses = db.get_hypotheses(sim_id)
    turns = db.get_turns(sim_id)

    scores = _aggregate_scores(hypotheses)
    per_node = _collect_per_node_metrics(hypotheses)
    bottlenecks = _detect_bottlenecks(hypotheses, turns)
    turn_stats = _collect_turn_stats(turns)

    report: dict[str, Any] = {
        "timestamp": timestamp,
        "git_hash": git_hash,
        "scores": scores,
        "per_node_metrics": per_node,
        "bottlenecks": bottlenecks,
        "turn_stats": turn_stats,
        "metadata": {
            "topic": BENCHMARK_TOPIC,
            "simulation_id": sim_id,
            "turns": sim_data.get("turns", 0) if sim_data else 0,
            "nodes": len(hypotheses),
            "cost_usd": sim_data.get("total_cost_usd", 0.0) if sim_data else 0.0,
            "agents": BENCHMARK_MAX_DEPTH + 3,  # approximate from loop default
            "max_depth": BENCHMARK_MAX_DEPTH,
            "node_years": BENCHMARK_NODE_YEARS,
            "cost_limit": BENCHMARK_COST_LIMIT,
        },
    }

    _save_report(report)
    return report


# --------------------------------------------------------------------------- #
# Metrics collection helpers
# --------------------------------------------------------------------------- #


def _aggregate_scores(hypotheses: list[dict[str, Any]]) -> dict[str, float]:
    """Compute per-dimension average scores across all evaluated hypotheses.

    A hypothesis is considered "evaluated" when its ``emergence_score`` is
    not None.  Falls back to mid-range placeholder scores when no evaluated
    hypotheses exist.

    Args:
        hypotheses: List of hypothesis rows from ``Database.get_hypotheses()``.

    Returns:
        Dict with avg_character_fidelity, avg_fandom_resonance, avg_emergence,
        avg_diversity, avg_plausibility, avg_composite keys, all floats in [0, 1].
    """
    evaluated = [h for h in hypotheses if h.get("emergence_score") is not None]

    if not evaluated:
        logger.warning("No evaluated hypotheses found; using placeholder scores.")
        return {
            "avg_character_fidelity": 0.5,
            "avg_fandom_resonance": 0.5,
            "avg_emergence": 0.5,
            "avg_diversity": 0.5,
            "avg_plausibility": 0.5,
            "avg_foreshadowing": 0.5,
            "avg_composite": 0.5,
        }

    def _mean(vals: list[float]) -> float:
        return round(sum(vals) / len(vals), 4) if vals else 0.5

    character_fidelity_vals = [float(h.get("character_fidelity_score") or 0.5) for h in evaluated]
    fandom_resonance_vals = [float(h.get("fandom_resonance_score") or 0.5) for h in evaluated]
    emergence_vals = [float(h.get("emergence_score") or 0.5) for h in evaluated]
    diversity_vals = [float(h.get("diversity_score") or 0.5) for h in evaluated]
    plausibility_vals = [float(h.get("plausibility_score") or 0.5) for h in evaluated]
    foreshadowing_vals = [float(h.get("foreshadowing_score") or 0.5) for h in evaluated]
    composite_vals = [_composite(h) for h in evaluated]

    return {
        "avg_character_fidelity": _mean(character_fidelity_vals),
        "avg_fandom_resonance": _mean(fandom_resonance_vals),
        "avg_emergence": _mean(emergence_vals),
        "avg_diversity": _mean(diversity_vals),
        "avg_plausibility": _mean(plausibility_vals),
        "avg_foreshadowing": _mean(foreshadowing_vals),
        "avg_composite": _mean(composite_vals),
    }


def _collect_per_node_metrics(
    hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a per-node metrics list sorted by composite score descending.

    Each entry exposes the four raw dimension scores plus composite,
    depth, title, and whether it was evaluated.

    Args:
        hypotheses: Rows from ``Database.get_hypotheses()``.

    Returns:
        List of dicts, one per hypothesis/node, ordered best-first.
    """
    nodes: list[dict[str, Any]] = []
    for h in hypotheses:
        evaluated = h.get("emergence_score") is not None
        comp = _composite(h) if evaluated else None
        nodes.append(
            {
                "node_id": h.get("node_id", ""),
                "title": h.get("title", ""),
                "depth": h.get("depth", 0),
                "evaluated": evaluated,
                "character_fidelity_score": h.get("character_fidelity_score"),
                "fandom_resonance_score": h.get("fandom_resonance_score"),
                "emergence_score": h.get("emergence_score"),
                "diversity_score": h.get("diversity_score"),
                "plausibility_score": h.get("plausibility_score"),
                "foreshadowing_score": h.get("foreshadowing_score"),
                "composite_score": comp,
                "probability": h.get("probability"),
                "sf_inspired": bool(h.get("sf_inspired")),
            }
        )
    # Sort evaluated nodes first, then by composite score desc
    nodes.sort(
        key=lambda n: (n["evaluated"], n["composite_score"] or 0.0),
        reverse=True,
    )
    return nodes


def _detect_bottlenecks(
    hypotheses: list[dict[str, Any]],
    turns: list[dict[str, Any]],
) -> dict[str, Any]:
    """Identify performance bottlenecks in the benchmark run.

    Bottleneck categories:
    - ``low_score_nodes``: nodes whose composite score is below
      ``LOW_SCORE_THRESHOLD`` — these reduce overall quality.
    - ``unevaluated_nodes``: nodes that were never evaluated (pruned early
      or skipped) — signal that the simulation may have hit the cost limit.
    - ``high_cost_turns``: the 3 most expensive turns by USD cost.
    - ``depth_score_trend``: average composite score per depth level;
      a declining trend signals that deeper nodes are worse.

    Args:
        hypotheses: Rows from ``Database.get_hypotheses()``.
        turns: Rows from ``Database.get_turns()``.

    Returns:
        Dict with keys: low_score_nodes, unevaluated_nodes,
        high_cost_turns, depth_score_trend, summary.
    """
    evaluated = [h for h in hypotheses if h.get("emergence_score") is not None]
    unevaluated = [h for h in hypotheses if h.get("emergence_score") is None]

    # Low-score nodes
    low_score_nodes = [
        {
            "node_id": h.get("node_id", ""),
            "title": h.get("title", ""),
            "depth": h.get("depth", 0),
            "composite_score": round(_composite(h), 4),
        }
        for h in evaluated
        if _composite(h) < LOW_SCORE_THRESHOLD
    ]

    # Unevaluated node summaries
    unevaluated_summaries = [
        {
            "node_id": h.get("node_id", ""),
            "title": h.get("title", ""),
            "depth": h.get("depth", 0),
        }
        for h in unevaluated
    ]

    # High-cost turns (top 3 by cost_usd)
    sorted_turns = sorted(
        turns, key=lambda t: t.get("cost_usd") or 0.0, reverse=True
    )
    high_cost_turns = [
        {
            "turn_number": t.get("turn_number"),
            "year": t.get("year"),
            "cost_usd": t.get("cost_usd"),
            "tokens_used": t.get("tokens_used"),
        }
        for t in sorted_turns[:3]
    ]

    # Depth → average composite score
    depth_scores: dict[int, list[float]] = {}
    for h in evaluated:
        depth = int(h.get("depth", 0))
        depth_scores.setdefault(depth, []).append(_composite(h))

    depth_score_trend = {
        depth: round(sum(vals) / len(vals), 4)
        for depth, vals in sorted(depth_scores.items())
    }

    # Narrative summary of findings
    issues: list[str] = []
    if unevaluated:
        issues.append(
            f"{len(unevaluated)} node(s) were not evaluated "
            "(possibly pruned or cost-limited)"
        )
    if low_score_nodes:
        issues.append(
            f"{len(low_score_nodes)} node(s) scored below "
            f"{LOW_SCORE_THRESHOLD:.1f} composite"
        )
    if len(depth_score_trend) >= 2:
        depths = sorted(depth_score_trend)
        first_score = depth_score_trend[depths[0]]
        last_score = depth_score_trend[depths[-1]]
        if last_score < first_score - 0.1:
            issues.append(
                "Quality degrades at deeper tree levels "
                f"(depth {depths[0]}: {first_score:.3f} → "
                f"depth {depths[-1]}: {last_score:.3f})"
            )

    summary = "; ".join(issues) if issues else "No bottlenecks detected."

    return {
        "low_score_nodes": low_score_nodes,
        "unevaluated_nodes": unevaluated_summaries,
        "high_cost_turns": high_cost_turns,
        "depth_score_trend": depth_score_trend,
        "summary": summary,
    }


def _collect_turn_stats(turns: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate turn-level statistics from a simulation run.

    Args:
        turns: Rows from ``Database.get_turns()``.

    Returns:
        Dict with total_turns, total_cost_usd, total_tokens,
        avg_cost_per_turn, avg_tokens_per_turn, max_cost_turn,
        min_cost_turn fields.
    """
    if not turns:
        return {
            "total_turns": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "avg_cost_per_turn": 0.0,
            "avg_tokens_per_turn": 0.0,
            "max_cost_turn": None,
            "min_cost_turn": None,
        }

    costs = [float(t.get("cost_usd") or 0.0) for t in turns]
    tokens = [int(t.get("tokens_used") or 0) for t in turns]

    total_cost = sum(costs)
    total_tokens = sum(tokens)
    n = len(turns)

    max_cost_idx = costs.index(max(costs))
    min_cost_idx = costs.index(min(c for c in costs if c > 0), 0) if any(costs) else 0

    return {
        "total_turns": n,
        "total_cost_usd": round(total_cost, 6),
        "total_tokens": total_tokens,
        "avg_cost_per_turn": round(total_cost / n, 6),
        "avg_tokens_per_turn": round(total_tokens / n, 1),
        "max_cost_turn": {
            "turn_number": turns[max_cost_idx].get("turn_number"),
            "cost_usd": costs[max_cost_idx],
            "tokens_used": tokens[max_cost_idx],
        },
        "min_cost_turn": {
            "turn_number": turns[min_cost_idx].get("turn_number"),
            "cost_usd": costs[min_cost_idx],
            "tokens_used": tokens[min_cost_idx],
        },
    }


# --------------------------------------------------------------------------- #
# Placeholders and persistence
# --------------------------------------------------------------------------- #


def _placeholder_report(
    timestamp: str, git_hash: str, error: str | None = None
) -> dict[str, Any]:
    """Return a placeholder report for offline/error scenarios."""
    report: dict[str, Any] = {
        "timestamp": timestamp,
        "git_hash": git_hash,
        "scores": {
            "avg_character_fidelity": 0.5,
            "avg_fandom_resonance": 0.5,
            "avg_emergence": 0.5,
            "avg_diversity": 0.5,
            "avg_plausibility": 0.5,
            "avg_foreshadowing": 0.5,
            "avg_composite": 0.5,
        },
        "per_node_metrics": [],
        "bottlenecks": {
            "low_score_nodes": [],
            "unevaluated_nodes": [],
            "high_cost_turns": [],
            "depth_score_trend": {},
            "summary": "No data available (placeholder).",
        },
        "turn_stats": {
            "total_turns": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "avg_cost_per_turn": 0.0,
            "avg_tokens_per_turn": 0.0,
            "max_cost_turn": None,
            "min_cost_turn": None,
        },
        "metadata": {
            "topic": BENCHMARK_TOPIC,
            "simulation_id": None,
            "turns": 0,
            "nodes": 0,
            "cost_usd": 0.0,
            "agents": 0,
            "max_depth": BENCHMARK_MAX_DEPTH,
            "node_years": BENCHMARK_NODE_YEARS,
            "cost_limit": BENCHMARK_COST_LIMIT,
            "placeholder": True,
        },
    }
    if error:
        report["metadata"]["error"] = error
    return report


def _save_report(report: dict[str, Any]) -> None:
    """Save benchmark report to timestamped JSON and append to history JSONL.

    Args:
        report: The benchmark report dict.
    """
    bench_dir = _benchmarks_dir()

    # Timestamped snapshot
    ts_safe = report["timestamp"].replace(":", "-").replace("+", "Z")[:19]
    snapshot_path = bench_dir / f"benchmark_{ts_safe}.json"
    snapshot_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    logger.info("Benchmark report saved to %s", snapshot_path)

    # Append to history
    history_path = bench_dir / "history.jsonl"
    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")
    logger.info("Benchmark history appended to %s", history_path)


# --------------------------------------------------------------------------- #
# Display
# --------------------------------------------------------------------------- #


def print_report(report: dict[str, Any]) -> None:
    """Print a benchmark report to the console as Rich tables.

    Displays:
    1. Score summary table (5 dimensions + composite)
    2. Per-node metrics table (if any nodes were evaluated)
    3. Bottleneck summary
    4. Turn statistics
    5. Metadata

    Args:
        report: The benchmark report dict returned by run_benchmark().
    """
    scores = report.get("scores", {})
    metadata = report.get("metadata", {})
    per_node = report.get("per_node_metrics", [])
    bottlenecks = report.get("bottlenecks", {})
    turn_stats = report.get("turn_stats", {})

    # --- Score table ---
    table = Table(title="Dormammu Benchmark Results", show_lines=True)
    table.add_column("Dimension", style="cyan")
    table.add_column("Score", justify="right", style="green")

    dimension_labels = {
        "avg_character_fidelity": "Character Fidelity",
        "avg_fandom_resonance": "Fandom Resonance",
        "avg_emergence": "Emergence",
        "avg_diversity": "Diversity",
        "avg_plausibility": "Plausibility",
        "avg_foreshadowing": "Foreshadowing",
        "avg_composite": "Composite (weighted)",
    }

    for key, label in dimension_labels.items():
        score = scores.get(key, 0.0)
        color = "green" if score >= 0.6 else ("yellow" if score >= 0.4 else "red")
        table.add_row(label, f"[{color}]{score:.4f}[/{color}]")

    console.print(table)

    # --- Per-node table (top 5 evaluated) ---
    evaluated_nodes = [n for n in per_node if n.get("evaluated")]
    if evaluated_nodes:
        node_table = Table(title="Top Evaluated Nodes", show_lines=False, box=None)
        node_table.add_column("Title", style="white", max_width=35)
        node_table.add_column("Depth", justify="right", style="dim")
        node_table.add_column("CharFid", justify="right")
        node_table.add_column("FanRes", justify="right")
        node_table.add_column("Emerge", justify="right")
        node_table.add_column("Divers", justify="right")
        node_table.add_column("Plaus", justify="right")
        node_table.add_column("Foreshadow", justify="right")
        node_table.add_column("Composite", justify="right", style="bold")

        for node in evaluated_nodes[:5]:
            comp = node.get("composite_score") or 0.0
            comp_color = "green" if comp >= 0.6 else ("yellow" if comp >= 0.4 else "red")
            node_table.add_row(
                (node.get("title") or "")[:35],
                str(node.get("depth", 0)),
                f"{node.get('character_fidelity_score', 0.0) or 0.0:.3f}",
                f"{node.get('fandom_resonance_score', 0.0) or 0.0:.3f}",
                f"{node.get('emergence_score', 0.0) or 0.0:.3f}",
                f"{node.get('diversity_score', 0.0) or 0.0:.3f}",
                f"{node.get('plausibility_score', 0.0) or 0.0:.3f}",
                f"{node.get('foreshadowing_score', 0.0) or 0.0:.3f}",
                f"[{comp_color}]{comp:.3f}[/{comp_color}]",
            )
        console.print(node_table)

    # --- Bottleneck summary ---
    bn_summary = bottlenecks.get("summary", "")
    if bn_summary and bn_summary != "No bottlenecks detected.":
        console.print(f"\n[bold yellow]Bottlenecks:[/] {bn_summary}")
    else:
        console.print(f"\n[dim]Bottlenecks:[/] {bn_summary}")

    # --- Turn stats ---
    if turn_stats.get("total_turns", 0) > 0:
        ts_table = Table(title="Turn Statistics", show_lines=False, box=None)
        ts_table.add_column("Metric", style="dim")
        ts_table.add_column("Value", justify="right")
        ts_table.add_row("Total turns", str(turn_stats["total_turns"]))
        ts_table.add_row("Total cost", f"${turn_stats['total_cost_usd']:.6f}")
        ts_table.add_row("Avg cost/turn", f"${turn_stats['avg_cost_per_turn']:.6f}")
        ts_table.add_row("Total tokens", str(turn_stats["total_tokens"]))
        ts_table.add_row(
            "Avg tokens/turn", f"{turn_stats['avg_tokens_per_turn']:.1f}"
        )
        console.print(ts_table)

    # --- Metadata ---
    meta_table = Table(title="Metadata", show_lines=False, box=None)
    meta_table.add_column("Key", style="dim")
    meta_table.add_column("Value")

    meta_display = {
        "Git hash": report.get("git_hash", "unknown"),
        "Timestamp": report.get("timestamp", ""),
        "Turns": str(metadata.get("turns", 0)),
        "Nodes": str(metadata.get("nodes", 0)),
        "Cost USD": f"${metadata.get('cost_usd', 0.0):.4f}",
        "Agents": str(metadata.get("agents", 0)),
        "Simulation ID": str(metadata.get("simulation_id", "N/A")),
    }
    for k, v in meta_display.items():
        meta_table.add_row(k, v)

    console.print(meta_table)

    if metadata.get("placeholder"):
        console.print(
            "[dim]Note: placeholder scores returned (no API key or simulation error).[/]"
        )
