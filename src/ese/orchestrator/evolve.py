"""Dormammu Evolve Orchestrator — /ese:evolve E2E improvement loop (D3).

The evolve loop runs multiple simulation cycles and iteratively improves
the scenario by passing best-scoring hypothesis context to the next cycle.

Architecture
------------
EvolveConfig   — all runtime parameters (parsed from CLI / defaults)
EvolveCycleResult — per-cycle outcome: scores, best node, narratives, cost
EvolveState    — accumulated state across all cycles; drives control flow
EvolveOrchestrator — top-level driver; wraps OrchestratorLoop per cycle

Control Flow
------------
for cycle in 1..max_iterations:
    1. [SIMULATE]  OrchestratorLoop.start_async(topic) → simulation_id
    2. [COLLECT]   DB → hypotheses, turns, evaluation scores
    3. [SCORE]     Aggregate composite scores; find best node
    4. [TERMINATE] Check all stop conditions (cost, convergence, failures)
    5. [EVOLVE]    Generate next topic from best branch context
    6. [TRANSFER]  Pass EvolveState to next cycle

Stop Conditions
---------------
- max_iterations reached
- total_cost_limit exhausted
- convergence: score improvement < threshold for ``convergence_patience`` cycles
- consecutive_failures >= MAX_CONSECUTIVE_FAILURES (3)
- KeyboardInterrupt (graceful shutdown)

State Transfer Between Stages
------------------------------
Each cycle produces an EvolveCycleResult that carries:
- best_hypothesis_title: title of the best-scoring branch
- best_composite_score: composite score of the best branch
- top_narratives: up to 5 narrative excerpts from the best branch
- metrics: 4-dim scores (emergence, narrative, diversity, novelty) averaged
- tree_snapshot: full scenario tree data for D1 visualization
- simulation_id: for DB lookup and API queries

These are accumulated in EvolveState.history and the last N best results
are injected as context when generating the topic for the next cycle.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ese.config import config
from ese.orchestrator.loop import OrchestratorLoop
from ese.storage.database import Database

logger = logging.getLogger(__name__)
console = Console()

# Maximum consecutive failures before the loop aborts
MAX_CONSECUTIVE_FAILURES = 3

# Minimum pause between cycles (seconds) to avoid API hammering
INTER_CYCLE_SLEEP_SECONDS = 1


# --------------------------------------------------------------------------- #
# Configuration dataclass
# --------------------------------------------------------------------------- #


@dataclass
class EvolveConfig:
    """All runtime parameters for the evolve loop.

    Created from CLI arguments and config defaults; passed to
    EvolveOrchestrator at construction time.
    """

    # Topic to simulate (may evolve each cycle)
    initial_topic: str

    # Loop control
    max_iterations: int = 10
    """Maximum number of evolve cycles to run."""

    # Per-cycle simulation params
    max_depth: int = field(default_factory=lambda: config.max_depth)
    node_years: int = field(default_factory=lambda: config.node_years)
    cost_limit_per_cycle: float = field(default_factory=lambda: config.cost_limit)
    language: str = field(default_factory=lambda: config.language)

    # Budget
    total_cost_limit: float = 50.0
    """Hard cap on total USD spend across all cycles."""

    # Convergence / early-stop
    convergence_threshold: float = 0.05
    """Stop when best-score improvement < this for ``convergence_patience`` cycles."""
    convergence_patience: int = 3
    """Number of consecutive non-improving cycles before declaring convergence."""

    # Output
    output_dir: Path = field(default_factory=lambda: config.data_dir)
    """Directory where per-run JSONL and Markdown reports are written."""

    # Dry-run
    dry_run: bool = False
    """If True, validate config and print plan without running any simulation."""

    # Improve step integration
    enable_improve: bool = False
    """If True, run the improve step between cycles to auto-tune parameters."""

    # Re-simulate step
    enable_re_simulate: bool = False
    """If True, re-simulate the best scenario after the improve step to validate improvement.

    Runs a short simulation (½ node_years, ½ cost budget) on the same topic with updated
    parameters and compares the score with the original cycle result. The delta feeds into
    convergence tracking independently of the main score history.
    """


# --------------------------------------------------------------------------- #
# Per-cycle result
# --------------------------------------------------------------------------- #


@dataclass
class EvolveCycleResult:
    """Captures all outcomes from a single evolve cycle.

    Stored in EvolveState.history and used to:
    - Drive convergence detection
    - Provide context for next-topic generation
    - Feed the D1 scenario tree visualization
    - Feed the D2 metrics dashboard
    """

    cycle: int
    topic: str
    simulation_id: str

    # Best hypothesis in this cycle
    best_hypothesis_title: str = ""
    best_composite_score: float = 0.0
    best_node_id: str = ""

    # Average 6-dim scores across all evaluated nodes in this cycle
    avg_character_fidelity_score: float = 0.0
    avg_fandom_resonance_score: float = 0.0
    avg_emergence_score: float = 0.0
    avg_diversity_score: float = 0.0
    avg_plausibility_score: float = 0.0
    avg_foreshadowing_score: float = 0.0

    # Top narratives from the best branch (for next-topic context)
    top_narratives: list[str] = field(default_factory=list)

    # Scenario tree snapshot (for D1 visualization API)
    tree_snapshot: dict[str, Any] = field(default_factory=dict)

    # Cost and exploration depth
    cost_usd: float = 0.0
    nodes_explored: int = 0
    turns_simulated: int = 0

    completed_at: str = ""

    # Whether this cycle ended in failure
    failed: bool = False
    error_message: str = ""

    # Optional re-simulate result (populated when enable_re_simulate=True)
    re_simulate_result: ReSimulateResult | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for JSONL logging."""
        return {
            "cycle": self.cycle,
            "topic": self.topic,
            "simulation_id": self.simulation_id,
            "best_hypothesis_title": self.best_hypothesis_title,
            "best_composite_score": self.best_composite_score,
            "best_node_id": self.best_node_id,
            "avg_character_fidelity_score": self.avg_character_fidelity_score,
            "avg_fandom_resonance_score": self.avg_fandom_resonance_score,
            "avg_emergence_score": self.avg_emergence_score,
            "avg_diversity_score": self.avg_diversity_score,
            "avg_plausibility_score": self.avg_plausibility_score,
            "avg_foreshadowing_score": self.avg_foreshadowing_score,
            "top_narratives": self.top_narratives,
            "cost_usd": self.cost_usd,
            "nodes_explored": self.nodes_explored,
            "turns_simulated": self.turns_simulated,
            "completed_at": self.completed_at,
            "failed": self.failed,
            "error_message": self.error_message,
            "re_simulate_result": (
                self.re_simulate_result.to_dict()
                if self.re_simulate_result is not None
                else None
            ),
        }


# --------------------------------------------------------------------------- #
# Re-simulate result
# --------------------------------------------------------------------------- #


@dataclass
class ReSimulateResult:
    """Captures the outcome of re-simulating the best scenario with improved parameters.

    The re-simulate step runs after the improve step (when ``enable_re_simulate=True``)
    to verify that the parameter adjustments actually improve scores. The score delta
    between the original simulation and the re-simulation feeds into convergence tracking.

    A positive ``score_delta`` indicates the improved parameters helped; zero or negative
    deltas that persist for ``convergence_patience`` cycles signal convergence.
    """

    cycle: int
    topic: str
    simulation_id: str

    # Score comparison
    original_score: float = 0.0
    """Best composite score from the original simulation in this cycle."""
    re_simulate_score: float = 0.0
    """Best composite score from the re-simulation with improved parameters."""

    # Cost and depth tracking
    cost_usd: float = 0.0
    nodes_explored: int = 0

    # Status
    failed: bool = False
    error_message: str = ""

    @property
    def score_delta(self) -> float:
        """Score improvement from re-simulation (positive = better, negative = worse)."""
        return self.re_simulate_score - self.original_score

    @property
    def improved(self) -> bool:
        """True if the re-simulation scored strictly higher than the original."""
        return self.score_delta > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "cycle": self.cycle,
            "topic": self.topic,
            "simulation_id": self.simulation_id,
            "original_score": self.original_score,
            "re_simulate_score": self.re_simulate_score,
            "score_delta": round(self.score_delta, 6),
            "improved": self.improved,
            "cost_usd": self.cost_usd,
            "nodes_explored": self.nodes_explored,
            "failed": self.failed,
            "error_message": self.error_message,
        }


# --------------------------------------------------------------------------- #
# Accumulated state
# --------------------------------------------------------------------------- #


@dataclass
class EvolveState:
    """Accumulated state across all evolve cycles.

    Drives termination decisions and provides the context window
    (last K cycle results) for next-topic generation.
    """

    config: EvolveConfig
    history: list[EvolveCycleResult] = field(default_factory=list)

    # Running totals
    total_cost: float = 0.0
    start_time: float = field(default_factory=time.time)

    # Streak counters for control flow
    consecutive_failures: int = 0
    non_improving_cycles: int = 0

    # The current-best composite score seen across all cycles
    global_best_score: float = 0.0

    # Termination cause (set on exit)
    termination_reason: str = ""

    # Re-simulate history — one entry per cycle when enable_re_simulate=True
    re_simulate_history: list[ReSimulateResult] = field(default_factory=list)

    @property
    def current_cycle(self) -> int:
        """1-based index of the next cycle to be run."""
        return len(self.history) + 1

    @property
    def successful_cycles(self) -> list[EvolveCycleResult]:
        return [r for r in self.history if not r.failed]

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    @property
    def score_deltas(self) -> list[float]:
        """Per-cycle score deltas between consecutive successful cycles.

        Each entry is (cycle_N_score - cycle_{N-1}_score). A consistently
        small delta list signals convergence without needing re-simulate.
        """
        scores = [r.best_composite_score for r in self.successful_cycles]
        return [scores[i] - scores[i - 1] for i in range(1, len(scores))]

    @property
    def re_simulate_score_deltas(self) -> list[float]:
        """Score deltas from re-simulate runs (original → re-simulated).

        Populated only when ``enable_re_simulate=True``. A series of small
        or negative deltas indicates the improve step is no longer effective.
        """
        return [r.score_delta for r in self.re_simulate_history if not r.failed]

    def record(self, result: EvolveCycleResult) -> None:
        """Append a cycle result and update running totals.

        Also registers any attached re_simulate_result in re_simulate_history.
        """
        self.history.append(result)

        if result.failed:
            self.consecutive_failures += 1
            return

        self.consecutive_failures = 0
        self.total_cost += result.cost_usd

        # Register re-simulate result if present
        if result.re_simulate_result is not None:
            self.re_simulate_history.append(result.re_simulate_result)

        # Convergence tracking — uses the re-simulated score when available
        # so that parameter improvements are reflected in convergence detection.
        effective_score = (
            result.re_simulate_result.re_simulate_score
            if result.re_simulate_result is not None and not result.re_simulate_result.failed
            else result.best_composite_score
        )

        improvement = effective_score - self.global_best_score
        if improvement >= self.config.convergence_threshold:
            self.global_best_score = effective_score
            self.non_improving_cycles = 0
        else:
            self.non_improving_cycles += 1

    def termination_check(self) -> str | None:
        """Return a reason string if the loop should stop, else None.

        Checks in priority order:
        1. Max iterations
        2. Total cost limit
        3. Consecutive failures
        4. Score convergence (main loop or re-simulate deltas)
        """
        completed = len(self.history)

        if completed >= self.config.max_iterations:
            return f"max_iterations={self.config.max_iterations} reached"

        if self.total_cost >= self.config.total_cost_limit:
            return (
                f"total_cost_limit=${self.config.total_cost_limit:.2f} reached "
                f"(spent ${self.total_cost:.4f})"
            )

        if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
            return f"{MAX_CONSECUTIVE_FAILURES} consecutive failures"

        if (
            self.non_improving_cycles >= self.config.convergence_patience
            and completed >= self.config.convergence_patience
        ):
            return (
                f"converged: no improvement > {self.config.convergence_threshold:.3f} "
                f"for {self.config.convergence_patience} consecutive cycles "
                f"(best score: {self.global_best_score:.3f})"
            )

        # Additional convergence check: re-simulate deltas are all tiny
        # (the improve step is no longer generating meaningful score gains)
        patience = self.config.convergence_patience
        re_deltas = self.re_simulate_score_deltas
        if (
            len(re_deltas) >= patience
            and all(d < self.config.convergence_threshold for d in re_deltas[-patience:])
            and completed >= patience
        ):
            return (
                f"converged: re-simulate score deltas < {self.config.convergence_threshold:.3f} "
                f"for last {patience} cycles "
                f"(deltas: {[round(d, 3) for d in re_deltas[-patience:]]})"
            )

        return None


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #


class EvolveOrchestrator:
    """Drives the /ese:evolve E2E improvement loop.

    Each cycle:
    1. Runs a full DFS simulation via OrchestratorLoop
    2. Collects metrics from the database
    3. Identifies the best-scoring hypothesis branch
    4. Checks all termination conditions
    5. Generates the next topic using the best branch context
    6. Transfers accumulated state to the next cycle

    Usage::

        cfg = EvolveConfig(initial_topic="Mars colony", max_iterations=5)
        orch = EvolveOrchestrator(cfg)
        orch.run()          # blocking
        # or
        await orch.run_async()
    """

    def __init__(self, cfg: EvolveConfig) -> None:
        self.cfg = cfg
        self.db = Database()
        self._report_path = cfg.output_dir / "evolve_log.jsonl"

    # ------------------------------------------------------------------ #
    # Public entry points
    # ------------------------------------------------------------------ #

    def run(self) -> EvolveState:
        """Blocking entry point. Returns the final EvolveState."""
        return asyncio.run(self.run_async())

    async def run_async(self) -> EvolveState:
        """Async entry point. Returns the final EvolveState."""
        state = EvolveState(config=self.cfg)

        if self.cfg.dry_run:
            self._print_dry_run_plan()
            state.termination_reason = "dry_run"
            return state

        self._print_start_banner(state)

        current_topic = self.cfg.initial_topic

        try:
            while True:
                # Check termination before starting a new cycle
                reason = state.termination_check()
                if reason:
                    state.termination_reason = reason
                    console.print(f"\n[yellow]Stopping: {reason}[/]")
                    break

                cycle = state.current_cycle
                self._print_cycle_header(cycle, current_topic, state)

                # Run one cycle
                result = await self._run_cycle(cycle, current_topic)
                state.record(result)
                self._log_cycle(result)

                if result.failed:
                    console.print(
                        f"[red]Cycle {cycle} failed:[/] {result.error_message}\n"
                        f"  (consecutive failures: "
                        f"{state.consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                    )
                    if state.consecutive_failures < MAX_CONSECUTIVE_FAILURES:
                        current_topic = self._fallback_topic(current_topic, cycle)
                    continue

                self._print_cycle_summary(result, state)

                # [IMPROVE] Run the improve step between cycles if enabled
                if self.cfg.enable_improve:
                    self.cfg = await self._run_improve_step(result, state)

                # [RE-SIMULATE] Validate improvement by re-running the best scenario
                # with the (possibly updated) config and comparing scores
                if self.cfg.enable_re_simulate and not result.failed:
                    re_sim = await self._run_re_simulate_step(
                        cycle=result.cycle,
                        topic=result.topic,
                        original_score=result.best_composite_score,
                        updated_cfg=self.cfg,
                    )
                    result.re_simulate_result = re_sim
                    # Re-record with re-simulate result attached so state picks it up
                    # (replace last entry since it was already appended by state.record)
                    state.re_simulate_history.append(re_sim)
                    self._print_re_simulate_summary(re_sim)
                    self._log_cycle(result)  # re-write log entry with re_simulate data

                # Check termination again after recording (catches budget/convergence)
                reason = state.termination_check()
                if reason:
                    state.termination_reason = reason
                    console.print(f"\n[yellow]Stopping: {reason}[/]")
                    break

                # Generate next topic from this cycle's best branch context
                next_topic = await self._generate_next_topic(result, state)
                console.print(f"  [dim]Next topic:[/] {next_topic}")
                current_topic = next_topic

                await asyncio.sleep(INTER_CYCLE_SLEEP_SECONDS)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted (Ctrl+C). Saving state...[/]")
            state.termination_reason = "keyboard_interrupt"

        if not state.termination_reason:
            state.termination_reason = "completed"

        self._print_final_summary(state)
        await self._write_final_report(state)
        return state

    # ------------------------------------------------------------------ #
    # Single cycle
    # ------------------------------------------------------------------ #

    async def _run_cycle(self, cycle: int, topic: str) -> EvolveCycleResult:
        """Run one full evolve cycle and return its result.

        Args:
            cycle: 1-based cycle index.
            topic: Topic for this cycle's simulation.

        Returns:
            EvolveCycleResult with all metrics and tree snapshot.
        """
        result = EvolveCycleResult(
            cycle=cycle,
            topic=topic,
            simulation_id="",
            completed_at=datetime.utcnow().isoformat(),
        )

        try:
            # Stage 1: Run simulation
            loop = OrchestratorLoop(
                max_depth=self.cfg.max_depth,
                node_years=self.cfg.node_years,
                cost_limit=self.cfg.cost_limit_per_cycle,
                language=self.cfg.language,
                db=self.db,
            )
            simulation_id = await loop.start_async(topic=topic)
            result.simulation_id = simulation_id

            # Stage 2: Collect metrics from DB
            await self._collect_cycle_metrics(result, simulation_id)

        except Exception as exc:
            logger.error("Cycle %d failed: %s", cycle, exc, exc_info=True)
            result.failed = True
            result.error_message = str(exc)

        result.completed_at = datetime.utcnow().isoformat()
        return result

    async def _collect_cycle_metrics(
        self, result: EvolveCycleResult, simulation_id: str
    ) -> None:
        """Populate result with metrics from the database.

        Args:
            result: The EvolveCycleResult to populate in-place.
            simulation_id: ID of the simulation to read from.
        """
        # Simulation-level data
        sim_data = self.db.get_simulation(simulation_id) or {}
        result.cost_usd = sim_data.get("total_cost_usd", 0.0)
        result.turns_simulated = sim_data.get("turns", 0)

        # Hypotheses / evaluation scores
        hypotheses = self.db.get_hypotheses(simulation_id)
        evaluated = [
            h for h in hypotheses
            if h.get("emergence_score") is not None
        ]

        result.nodes_explored = len(evaluated)

        if evaluated:
            # Compute per-cycle averages
            result.avg_character_fidelity_score = _mean(
                [h.get("character_fidelity_score", 0.0) for h in evaluated]
            )
            result.avg_fandom_resonance_score = _mean(
                [h.get("fandom_resonance_score", 0.0) for h in evaluated]
            )
            result.avg_emergence_score = _mean(
                [h.get("emergence_score", 0.0) for h in evaluated]
            )
            result.avg_diversity_score = _mean(
                [h.get("diversity_score", 0.0) for h in evaluated]
            )
            result.avg_plausibility_score = _mean(
                [h.get("plausibility_score", 0.0) for h in evaluated]
            )
            result.avg_foreshadowing_score = _mean(
                [h.get("foreshadowing_score", 0.0) for h in evaluated]
            )

            # Find best node by composite score
            best = max(evaluated, key=lambda h: _composite_score(h))
            result.best_node_id = best.get("node_id", "")
            result.best_hypothesis_title = best.get("title", "")
            result.best_composite_score = _composite_score(best)

        # Build tree snapshot for D1 visualization
        result.tree_snapshot = {
            "simulation_id": simulation_id,
            "topic": result.topic,
            "nodes": hypotheses,
        }

        # Collect narratives from turns for best branch context
        turns = self.db.get_turns(simulation_id)
        narratives = [t.get("narrative", "") for t in turns if t.get("narrative")]
        result.top_narratives = narratives[-5:]  # last 5 turns

    # ------------------------------------------------------------------ #
    # Re-simulate step
    # ------------------------------------------------------------------ #

    async def _run_re_simulate_step(
        self,
        cycle: int,
        topic: str,
        original_score: float,
        updated_cfg: EvolveConfig | None = None,
    ) -> ReSimulateResult:
        """Re-simulate the best scenario with improved parameters to validate improvement.

        Runs a lightweight simulation (½ ``node_years``, ½ cost budget) so the
        validation overhead is minimal. The resulting composite score is compared
        against ``original_score`` and the delta is stored in ``ReSimulateResult``.

        Args:
            cycle:          1-based cycle index (for logging).
            topic:          Topic to re-simulate.
            original_score: Best composite score from the original cycle simulation.
            updated_cfg:    Config with potentially improved parameters; falls back
                            to ``self.cfg`` when None.

        Returns:
            A ``ReSimulateResult`` with score comparison data.
        """
        result = ReSimulateResult(
            cycle=cycle,
            topic=topic,
            simulation_id="",
            original_score=original_score,
        )

        effective_cfg = updated_cfg or self.cfg

        try:
            # Use half node_years and half cost budget to limit validation overhead
            re_sim_node_years = max(10, effective_cfg.node_years // 2)
            re_sim_cost_limit = max(0.1, effective_cfg.cost_limit_per_cycle * 0.5)

            loop = OrchestratorLoop(
                max_depth=effective_cfg.max_depth,
                node_years=re_sim_node_years,
                cost_limit=re_sim_cost_limit,
                language=effective_cfg.language,
                db=self.db,
            )
            sim_id = await loop.start_async(topic=topic)
            result.simulation_id = sim_id

            # Collect metrics from the re-simulation
            hypotheses = self.db.get_hypotheses(sim_id)
            evaluated = [h for h in hypotheses if h.get("emergence_score") is not None]
            result.nodes_explored = len(evaluated)

            if evaluated:
                best = max(evaluated, key=lambda h: _composite_score(h))
                result.re_simulate_score = _composite_score(best)

            sim_data = self.db.get_simulation(sim_id) or {}
            result.cost_usd = sim_data.get("total_cost_usd", 0.0)

        except Exception as exc:
            logger.error(
                "Re-simulate step cycle %d failed: %s", cycle, exc, exc_info=True
            )
            result.failed = True
            result.error_message = str(exc)

        return result

    def _print_re_simulate_summary(self, re_sim: ReSimulateResult) -> None:
        """Print a one-line summary of the re-simulate result to the console."""
        if re_sim.failed:
            console.print(
                f"  [red][re-sim] cycle {re_sim.cycle} FAILED:[/] {re_sim.error_message}"
            )
            return

        delta_color = "green" if re_sim.improved else "red"
        delta_sign = "+" if re_sim.score_delta >= 0 else ""
        console.print(
            f"  [cyan][re-sim][/] "
            f"original={re_sim.original_score:.3f} → "
            f"re-sim={re_sim.re_simulate_score:.3f} "
            f"(delta: [{delta_color}]{delta_sign}{re_sim.score_delta:.3f}[/]) "
            f"| nodes={re_sim.nodes_explored} cost=${re_sim.cost_usd:.4f}"
        )

    # ------------------------------------------------------------------ #
    # Improve step
    # ------------------------------------------------------------------ #

    async def _run_improve_step(
        self,
        result: EvolveCycleResult,
        state: EvolveState,
    ) -> "EvolveConfig":
        """Run the improve step and return an updated EvolveConfig.

        Builds a mini benchmark report from the cycle result, runs diagnose,
        then applies improvements to the current config.

        Args:
            result: The just-completed cycle result.
            state:  Accumulated evolve state.

        Returns:
            A (possibly updated) EvolveConfig for the next cycle.
        """
        try:
            from ese.diagnose import diagnose as run_diagnose
            from ese.improve import generate_improvement_plan, apply_improvements

            # Build a lightweight report from the cycle scores
            scores = {
                "avg_character_fidelity": result.avg_character_fidelity_score,
                "avg_fandom_resonance": result.avg_fandom_resonance_score,
                "avg_emergence": result.avg_emergence_score,
                "avg_diversity": result.avg_diversity_score,
                "avg_plausibility": result.avg_plausibility_score,
                "avg_foreshadowing": result.avg_foreshadowing_score,
                "avg_composite": result.best_composite_score,
            }
            mini_report = {
                "scores": scores,
                "per_node_metrics": [],
                "bottlenecks": {
                    "unevaluated_nodes": [],
                    "low_score_nodes": [],
                    "high_cost_turns": [],
                    "depth_score_trend": {},
                    "summary": "",
                },
                "metadata": {"placeholder": False},
            }

            diagnosis = run_diagnose(mini_report)
            current_params = {
                "node_years": self.cfg.node_years,
                "max_depth": self.cfg.max_depth,
                "cost_limit_per_cycle": self.cfg.cost_limit_per_cycle,
                "convergence_threshold": self.cfg.convergence_threshold,
            }
            plan = generate_improvement_plan(diagnosis, current_params)
            new_cfg = apply_improvements(
                plan=plan,
                evolve_config=self.cfg,
                cycle=result.cycle,
                before_scores=scores,
                persist=True,
            )

            console.print(
                f"  [dim][improve] Focus: {plan.focus_dimension} "
                f"(score={plan.focus_score:.3f}) → "
                f"node_years={new_cfg.node_years}, "
                f"max_depth={new_cfg.max_depth}, "
                f"cost/cycle=${new_cfg.cost_limit_per_cycle:.2f}[/]"
            )
            return new_cfg

        except Exception as exc:
            logger.warning("Improve step failed (non-fatal): %s", exc)
            return self.cfg

    # ------------------------------------------------------------------ #
    # Next topic generation
    # ------------------------------------------------------------------ #

    async def _generate_next_topic(
        self, result: EvolveCycleResult, state: EvolveState
    ) -> str:
        """Generate the next cycle's topic from the current cycle's best branch.

        Uses LLM if API key is available, otherwise falls back to a
        structured heuristic based on the best hypothesis title.

        Args:
            result: The completed cycle result.
            state: Accumulated evolve state (for history context).

        Returns:
            Topic string for the next cycle.
        """
        if not config.openai_api_key:
            return self._fallback_topic(result.topic, result.cycle)

        from ese.agents.interaction import AgentInteraction
        from ese.hypothesis.inspiration import InspirationSystem

        interaction = AgentInteraction(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )
        inspiration = InspirationSystem()
        seeds = inspiration.pick(topic=result.topic, count=2)
        inspiration_text = inspiration.build_injection(seeds)

        narratives_text = "\n".join(f"- {n[:200]}" for n in result.top_narratives)
        prev_topics = [r.topic for r in state.history[-5:]]
        prev_text = "\n".join(f"- {t}" for t in prev_topics)

        best_info = (
            f"Best branch: '{result.best_hypothesis_title}' "
            f"(score={result.best_composite_score:.3f})"
            if result.best_hypothesis_title
            else "No evaluated branches yet."
        )

        prompt = (
            f"Previous simulation topic: {result.topic}\n"
            f"{best_info}\n\n"
            f"Key narratives from the simulation:\n{narratives_text}\n\n"
            f"Previous topics explored (AVOID repeating):\n{prev_text}\n\n"
            f"{inspiration_text}\n\n"
            "Based on the best-scoring branch from the previous cycle, "
            "propose a NEW scenario topic that:\n"
            "1. Deepens or extends the most interesting discovery\n"
            "2. Introduces a novel tension or 'what if' angle\n"
            "3. Is clearly different from all previous topics\n"
            "4. Is concise and self-contained\n\n"
            'Respond with JSON: {"topic": "...", "reasoning": "..."}'
        )

        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are a creative scenario designer for a world simulation engine. "
                    "Propose fascinating 'what if' scenarios. Respond with valid JSON only."
                ),
                user_prompt=prompt,
                temperature=0.9,
            )
            data = json.loads(response.content)
            new_topic = data.get("topic", "").strip()
            if new_topic:
                reasoning = data.get("reasoning", "")
                console.print(f"  [dim]Reasoning: {reasoning[:120]}[/]")
                return new_topic
        except Exception as exc:
            logger.warning("Failed to generate next topic via LLM: %s", exc)

        return self._fallback_topic(result.topic, result.cycle)

    def _fallback_topic(self, topic: str, cycle: int) -> str:
        """Return a heuristic fallback topic when LLM is unavailable.

        Appends an 'evolved' suffix that keeps the original topic
        recognisable while signaling progression.
        """
        from ese.hypothesis.inspiration import InspirationSystem

        inspiration = InspirationSystem()
        seeds = inspiration.pick(topic=topic, count=1)
        if seeds:
            fragment = seeds[0].prompt_fragment
            if ": " in fragment:
                scenario = fragment.split(": ", 1)[1].strip()
            else:
                scenario = fragment.strip()
            if scenario:
                return scenario[0].upper() + scenario[1:]
        return f"{topic} — evolved (cycle {cycle})"

    # ------------------------------------------------------------------ #
    # Reporting / display helpers
    # ------------------------------------------------------------------ #

    def _print_dry_run_plan(self) -> None:
        cfg = self.cfg
        console.print(
            Panel(
                f"[bold]DRY RUN — no simulation will be executed[/]\n\n"
                f"[bold]Topic:[/]               {cfg.initial_topic}\n"
                f"[bold]Max iterations:[/]      {cfg.max_iterations}\n"
                f"[bold]Max DFS depth:[/]       {cfg.max_depth}\n"
                f"[bold]Node years:[/]          {cfg.node_years}\n"
                f"[bold]Cost per cycle:[/]      ${cfg.cost_limit_per_cycle:.2f}\n"
                f"[bold]Total budget:[/]        ${cfg.total_cost_limit:.2f}\n"
                f"[bold]Convergence threshold:[/] {cfg.convergence_threshold:.3f}\n"
                f"[bold]Convergence patience:[/]  {cfg.convergence_patience}\n"
                f"[bold]Language:[/]            {cfg.language}\n"
                f"[bold]Output dir:[/]          {cfg.output_dir}",
                title="[cyan]/ese:evolve plan[/]",
                border_style="cyan",
            )
        )

    def _print_start_banner(self, state: EvolveState) -> None:
        cfg = self.cfg
        console.print(
            Panel(
                f"[bold cyan]Dormammu Evolve Loop[/]\n\n"
                f"[bold]Topic:[/]           {cfg.initial_topic}\n"
                f"[bold]Max iterations:[/]  {cfg.max_iterations}\n"
                f"[bold]Cost / cycle:[/]    ${cfg.cost_limit_per_cycle:.2f}\n"
                f"[bold]Total budget:[/]    ${cfg.total_cost_limit:.2f}\n"
                f"[bold]Convergence:[/]     threshold={cfg.convergence_threshold:.3f}, "
                f"patience={cfg.convergence_patience}\n"
                f"[bold]Max depth:[/]       {cfg.max_depth}\n"
                f"[bold]Language:[/]        {cfg.language}\n\n"
                "[dim]Press Ctrl+C to stop gracefully and save a report.[/]",
                title="[bold green]Starting /ese:evolve[/]",
                border_style="green",
            )
        )

    def _print_cycle_header(
        self, cycle: int, topic: str, state: EvolveState
    ) -> None:
        elapsed_h = state.elapsed_seconds / 3600
        console.print(
            Panel(
                f"[bold]Topic:[/]         {topic}\n"
                f"[bold]Elapsed:[/]       {elapsed_h:.2f}h\n"
                f"[bold]Cost so far:[/]   ${state.total_cost:.4f} / ${self.cfg.total_cost_limit:.2f}\n"
                f"[bold]Global best:[/]   {state.global_best_score:.3f}\n"
                f"[bold]Completed:[/]     {len(state.history)} cycle(s)",
                title=f"[cyan]Evolve Cycle {cycle} / {self.cfg.max_iterations}[/]",
                border_style="cyan",
            )
        )

    def _print_cycle_summary(
        self, result: EvolveCycleResult, state: EvolveState
    ) -> None:
        score_color = "green" if result.best_composite_score > 0.5 else "yellow"
        console.print(
            f"\n[green]Cycle {result.cycle} complete.[/] "
            f"Best score: [{score_color}]{result.best_composite_score:.3f}[/] | "
            f"Nodes: {result.nodes_explored} | "
            f"Turns: {result.turns_simulated} | "
            f"Cost: ${result.cost_usd:.4f}"
        )
        if result.best_hypothesis_title:
            console.print(
                f"  [dim]Best branch:[/] {result.best_hypothesis_title[:80]}"
            )

    def _print_final_summary(self, state: EvolveState) -> None:
        elapsed_h = state.elapsed_seconds / 3600
        successful = state.successful_cycles

        if not successful:
            console.print("\n[dim]No cycles completed successfully.[/]")
            return

        # Build summary table — include re-sim delta column if available
        has_re_sim = bool(state.re_simulate_history)
        table = Table(title="Evolve Loop Summary", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Topic", style="white", max_width=40)
        table.add_column("Best Score", justify="right", style="green")
        table.add_column("Nodes", justify="right")
        table.add_column("Cost", justify="right")
        if has_re_sim:
            table.add_column("Re-Sim Δ", justify="right")

        re_sim_by_cycle = {rs.cycle: rs for rs in state.re_simulate_history}

        for r in successful:
            row = [
                str(r.cycle),
                r.topic[:40],
                f"{r.best_composite_score:.3f}",
                str(r.nodes_explored),
                f"${r.cost_usd:.4f}",
            ]
            if has_re_sim:
                rs = re_sim_by_cycle.get(r.cycle)
                if rs and not rs.failed:
                    sign = "+" if rs.score_delta >= 0 else ""
                    delta_str = f"{sign}{rs.score_delta:.3f}"
                else:
                    delta_str = "—"
                row.append(delta_str)
            table.add_row(*row)

        console.print()
        console.print(table)

        # Build convergence info string
        convergence_info = f"[bold]Stopped:[/]     {state.termination_reason}"
        if state.re_simulate_score_deltas:
            avg_delta = _mean(state.re_simulate_score_deltas)
            improving = sum(1 for d in state.re_simulate_score_deltas if d > 0)
            convergence_info += (
                f"\n[bold]Re-Sim avg Δ:[/] {avg_delta:+.4f} "
                f"({improving}/{len(state.re_simulate_score_deltas)} cycles improved)"
            )

        console.print(
            Panel(
                f"[bold]Duration:[/]    {elapsed_h:.2f}h\n"
                f"[bold]Cycles:[/]      {len(successful)} successful / {len(state.history)} total\n"
                f"[bold]Total cost:[/]  ${state.total_cost:.4f}\n"
                f"[bold]Global best:[/] {state.global_best_score:.3f}\n"
                f"{convergence_info}\n"
                f"[bold]Log:[/]         {self._report_path}",
                title="[green]Evolve Complete[/]",
                border_style="green",
            )
        )

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def _log_cycle(self, result: EvolveCycleResult) -> None:
        """Append cycle result to the JSONL log file."""
        self._report_path.parent.mkdir(parents=True, exist_ok=True)
        with self._report_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

    async def _write_final_report(self, state: EvolveState) -> None:
        """Write a Markdown summary report after the loop completes."""
        if not state.successful_cycles:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = self.cfg.output_dir / f"evolve_report_{timestamp}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        elapsed_h = state.elapsed_seconds / 3600
        best_cycle = max(state.successful_cycles, key=lambda r: r.best_composite_score)

        lines: list[str] = []
        lines.append("# Dormammu Evolve Loop Report")
        lines.append(f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

        lines.append("## Configuration\n")
        cfg = self.cfg
        lines.append(f"| Parameter | Value |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| Initial topic | {cfg.initial_topic} |")
        lines.append(f"| Max iterations | {cfg.max_iterations} |")
        lines.append(f"| Max DFS depth | {cfg.max_depth} |")
        lines.append(f"| Cost per cycle | ${cfg.cost_limit_per_cycle:.2f} |")
        lines.append(f"| Total budget | ${cfg.total_cost_limit:.2f} |")
        lines.append(f"| Convergence threshold | {cfg.convergence_threshold:.3f} |")
        lines.append(f"| Language | {cfg.language} |")

        lines.append("\n## Overview\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Duration | {elapsed_h:.2f}h |")
        lines.append(f"| Successful cycles | {len(state.successful_cycles)} |")
        lines.append(f"| Total cost | ${state.total_cost:.4f} |")
        lines.append(f"| Global best score | {state.global_best_score:.3f} |")
        lines.append(f"| Termination reason | {state.termination_reason} |")

        lines.append("\n## Cycle History\n")
        lines.append("| # | Topic | Best Score | Nodes | Cost |")
        lines.append("|---|-------|-----------|-------|------|")
        for r in state.history:
            status = "FAILED" if r.failed else f"{r.best_composite_score:.3f}"
            lines.append(
                f"| {r.cycle} | {r.topic[:40]} | {status} | "
                f"{r.nodes_explored} | ${r.cost_usd:.4f} |"
            )

        # --- Score delta trend ---
        score_deltas = state.score_deltas
        if score_deltas:
            lines.append("\n## Score Delta Trend\n")
            lines.append(
                "Consecutive cycle score changes (positive = improving):\n"
            )
            lines.append("| Transition | Delta |")
            lines.append("|------------|-------|")
            successful = state.successful_cycles
            for i, delta in enumerate(score_deltas):
                from_cycle = successful[i].cycle
                to_cycle = successful[i + 1].cycle
                sign = "+" if delta >= 0 else ""
                lines.append(f"| Cycle {from_cycle} → {to_cycle} | {sign}{delta:.4f} |")

        # --- Re-simulate comparison table ---
        if state.re_simulate_history:
            lines.append("\n## Re-Simulate Comparison\n")
            lines.append(
                "Scores after re-running the best scenario with improved parameters:\n"
            )
            lines.append(
                "| Cycle | Topic | Original | Re-Sim | Delta | Improved? |"
            )
            lines.append(
                "|-------|-------|---------|--------|-------|-----------|"
            )
            for rs in state.re_simulate_history:
                if rs.failed:
                    lines.append(
                        f"| {rs.cycle} | {rs.topic[:30]} | {rs.original_score:.3f} "
                        f"| FAILED | — | — |"
                    )
                else:
                    sign = "+" if rs.score_delta >= 0 else ""
                    improved = "Yes" if rs.improved else "No"
                    lines.append(
                        f"| {rs.cycle} | {rs.topic[:30]} | {rs.original_score:.3f} "
                        f"| {rs.re_simulate_score:.3f} "
                        f"| {sign}{rs.score_delta:.4f} | {improved} |"
                    )

        # --- Convergence analysis ---
        lines.append("\n## Convergence Analysis\n")
        cfg = self.cfg
        lines.append(f"| Parameter | Value |")
        lines.append(f"|-----------|-------|")
        lines.append(f"| Convergence threshold | {cfg.convergence_threshold:.4f} |")
        lines.append(f"| Convergence patience | {cfg.convergence_patience} |")
        lines.append(f"| Non-improving cycles at end | {state.non_improving_cycles} |")
        lines.append(f"| Termination reason | {state.termination_reason} |")

        converged = "converged" in state.termination_reason.lower()
        lines.append(f"| Converged | {'Yes' if converged else 'No'} |")

        if state.re_simulate_score_deltas:
            avg_re_sim_delta = _mean(state.re_simulate_score_deltas)
            lines.append(
                f"| Avg re-sim score delta | {avg_re_sim_delta:+.4f} |"
            )
            improving_re_sims = sum(
                1 for d in state.re_simulate_score_deltas if d > 0
            )
            lines.append(
                f"| Re-sim cycles improved | "
                f"{improving_re_sims}/{len(state.re_simulate_score_deltas)} |"
            )

        lines.append("\n## Best Cycle\n")
        lines.append(
            f"**Cycle {best_cycle.cycle}** — Topic: _{best_cycle.topic}_\n\n"
            f"- Best hypothesis: _{best_cycle.best_hypothesis_title}_\n"
            f"- Composite score: **{best_cycle.best_composite_score:.3f}**\n"
            f"- CharFidelity: {best_cycle.avg_character_fidelity_score:.3f} | "
            f"FanResonance: {best_cycle.avg_fandom_resonance_score:.3f} | "
            f"Emergence: {best_cycle.avg_emergence_score:.3f} | "
            f"Diversity: {best_cycle.avg_diversity_score:.3f} | "
            f"Plausibility: {best_cycle.avg_plausibility_score:.3f} | "
            f"Foreshadowing: {best_cycle.avg_foreshadowing_score:.3f}\n"
        )

        if best_cycle.top_narratives:
            lines.append("### Key Narratives\n")
            for n in best_cycle.top_narratives:
                lines.append(f"> {n[:400]}\n")

        lines.append(
            f"\n---\n*Generated by /ese:evolve. "
            f"Full cycle log: `{self._report_path}`*\n"
        )

        report_path.write_text("\n".join(lines), encoding="utf-8")
        console.print(f"\n[bold green]Evolve report saved:[/] {report_path}")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _mean(values: list[float]) -> float:
    """Return the arithmetic mean of a list, or 0.0 if empty."""
    return sum(values) / len(values) if values else 0.0


def _composite_score(hyp: dict[str, Any]) -> float:
    """Compute the composite score for a hypothesis row from the DB.

    Mirrors the weights in HypothesisEvaluator / EvaluationResult.
    """
    return (
        (hyp.get("character_fidelity_score") or 0.0) * 0.20
        + (hyp.get("fandom_resonance_score") or 0.0) * 0.15
        + (hyp.get("emergence_score") or 0.0) * 0.15
        + (hyp.get("diversity_score") or 0.0) * 0.15
        + (hyp.get("plausibility_score") or 0.0) * 0.15
        + (hyp.get("foreshadowing_score") or 0.0) * 0.20
    )
