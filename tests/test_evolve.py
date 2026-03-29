"""Tests for the /ese:evolve orchestrator (Sub-AC 3a).

Covers:
- EvolveConfig construction and defaults
- EvolveState termination conditions (all branches)
- EvolveCycleResult serialization
- EvolveOrchestrator dry-run path
- _composite_score and _mean helpers
- CLI `evolve` command availability
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from ese.orchestrator.evolve import (
    EvolveConfig,
    EvolveCycleResult,
    EvolveOrchestrator,
    EvolveState,
    _composite_score,
    _mean,
)


# --------------------------------------------------------------------------- #
# EvolveConfig
# --------------------------------------------------------------------------- #


def test_evolve_config_defaults():
    """EvolveConfig sets sensible defaults from the global config."""
    cfg = EvolveConfig(initial_topic="Mars colony")

    assert cfg.initial_topic == "Mars colony"
    assert cfg.max_iterations == 10
    assert cfg.convergence_threshold == 0.05
    assert cfg.convergence_patience == 3
    assert cfg.total_cost_limit == 50.0
    assert cfg.dry_run is False


def test_evolve_config_custom():
    """EvolveConfig respects custom values."""
    cfg = EvolveConfig(
        initial_topic="Test topic",
        max_iterations=3,
        max_depth=2,
        node_years=50,
        cost_limit_per_cycle=1.0,
        total_cost_limit=5.0,
        convergence_threshold=0.10,
        convergence_patience=2,
        language="ko",
        dry_run=True,
    )

    assert cfg.max_iterations == 3
    assert cfg.max_depth == 2
    assert cfg.node_years == 50
    assert cfg.cost_limit_per_cycle == 1.0
    assert cfg.total_cost_limit == 5.0
    assert cfg.convergence_threshold == 0.10
    assert cfg.convergence_patience == 2
    assert cfg.language == "ko"
    assert cfg.dry_run is True


# --------------------------------------------------------------------------- #
# EvolveState — termination logic
# --------------------------------------------------------------------------- #


def _make_state(max_iterations=5, total_cost_limit=10.0, patience=3, threshold=0.05):
    cfg = EvolveConfig(
        initial_topic="test",
        max_iterations=max_iterations,
        total_cost_limit=total_cost_limit,
        convergence_patience=patience,
        convergence_threshold=threshold,
    )
    return EvolveState(config=cfg)


def _make_result(cycle: int, score: float = 0.6, cost: float = 0.5) -> EvolveCycleResult:
    return EvolveCycleResult(
        cycle=cycle,
        topic=f"topic-{cycle}",
        simulation_id=f"sim-{cycle}",
        best_composite_score=score,
        cost_usd=cost,
    )


def test_state_no_termination_initially():
    state = _make_state()
    assert state.termination_check() is None


def test_state_terminates_at_max_iterations():
    state = _make_state(max_iterations=2)
    state.record(_make_result(1))
    state.record(_make_result(2))

    reason = state.termination_check()
    assert reason is not None
    assert "max_iterations" in reason


def test_state_terminates_at_cost_limit():
    state = _make_state(total_cost_limit=1.0)
    # Single cycle that exhausts the budget
    state.record(_make_result(1, cost=1.5))

    reason = state.termination_check()
    assert reason is not None
    assert "total_cost_limit" in reason


def test_state_terminates_on_consecutive_failures():
    state = _make_state()
    for i in range(1, 4):
        failed = EvolveCycleResult(
            cycle=i, topic=f"t{i}", simulation_id=f"s{i}", failed=True
        )
        state.record(failed)

    reason = state.termination_check()
    assert reason is not None
    assert "consecutive failures" in reason


def test_state_terminates_on_convergence():
    state = _make_state(patience=3, threshold=0.05)

    # First cycle sets global best to 0.8
    state.record(_make_result(1, score=0.8))
    # Next 3 cycles do not improve by >= 0.05
    state.record(_make_result(2, score=0.82))  # +0.02 < 0.05 → non-improving
    state.record(_make_result(3, score=0.83))  # +0.01 < 0.05 → non-improving
    state.record(_make_result(4, score=0.84))  # +0.01 < 0.05 → non-improving

    reason = state.termination_check()
    assert reason is not None
    assert "converged" in reason


def test_state_no_convergence_if_improving():
    state = _make_state(patience=3, threshold=0.05)

    # Each cycle improves by > 0.05
    state.record(_make_result(1, score=0.3))
    state.record(_make_result(2, score=0.4))  # +0.10 ≥ 0.05 → improving
    state.record(_make_result(3, score=0.5))  # +0.10 ≥ 0.05 → improving

    assert state.termination_check() is None


def test_state_current_cycle_counter():
    state = _make_state()
    assert state.current_cycle == 1
    state.record(_make_result(1))
    assert state.current_cycle == 2


def test_state_successful_cycles_filters_failures():
    state = _make_state()
    state.record(_make_result(1, score=0.7))
    failed = EvolveCycleResult(cycle=2, topic="t2", simulation_id="s2", failed=True)
    state.record(failed)
    state.record(_make_result(3, score=0.8))

    assert len(state.successful_cycles) == 2


# --------------------------------------------------------------------------- #
# EvolveCycleResult serialization
# --------------------------------------------------------------------------- #


def test_evolve_cycle_result_to_dict():
    r = EvolveCycleResult(
        cycle=1,
        topic="Mars",
        simulation_id="abc-123",
        best_hypothesis_title="Terraforming begins",
        best_composite_score=0.75,
        avg_character_fidelity_score=0.8,
        avg_fandom_resonance_score=0.7,
        avg_emergence_score=0.6,
        avg_diversity_score=0.5,
        avg_plausibility_score=0.65,
        cost_usd=1.23,
        nodes_explored=5,
        turns_simulated=20,
        top_narratives=["event 1", "event 2"],
        completed_at="2026-01-01T00:00:00",
    )
    d = r.to_dict()

    assert d["cycle"] == 1
    assert d["topic"] == "Mars"
    assert d["simulation_id"] == "abc-123"
    assert d["best_composite_score"] == pytest.approx(0.75)
    assert d["cost_usd"] == pytest.approx(1.23)
    assert d["top_narratives"] == ["event 1", "event 2"]
    assert d["failed"] is False

    # Must be JSON-serializable
    serialized = json.dumps(d)
    restored = json.loads(serialized)
    assert restored["cycle"] == 1


def test_evolve_cycle_result_failed_dict():
    r = EvolveCycleResult(
        cycle=2, topic="test", simulation_id="", failed=True, error_message="timeout"
    )
    d = r.to_dict()
    assert d["failed"] is True
    assert d["error_message"] == "timeout"


# --------------------------------------------------------------------------- #
# Helper functions
# --------------------------------------------------------------------------- #


def test_mean_empty():
    assert _mean([]) == 0.0


def test_mean_values():
    assert _mean([0.2, 0.4, 0.6]) == pytest.approx(0.4)


def test_composite_score_all_zeros():
    hyp = {
        "character_fidelity_score": 0.0,
        "fandom_resonance_score": 0.0,
        "emergence_score": 0.0,
        "diversity_score": 0.0,
        "plausibility_score": 0.0,
    }
    assert _composite_score(hyp) == pytest.approx(0.0)


def test_composite_score_all_ones():
    hyp = {
        "character_fidelity_score": 1.0,
        "fandom_resonance_score": 1.0,
        "emergence_score": 1.0,
        "diversity_score": 1.0,
        "plausibility_score": 1.0,
    }
    # 0.25 + 0.20 + 0.20 + 0.15 + 0.20 = 1.0
    assert _composite_score(hyp) == pytest.approx(1.0)


def test_composite_score_none_values():
    """None values (unevaluated nodes) should be treated as 0."""
    hyp = {
        "character_fidelity_score": None,
        "fandom_resonance_score": None,
        "emergence_score": None,
        "diversity_score": None,
        "plausibility_score": None,
    }
    assert _composite_score(hyp) == pytest.approx(0.0)


def test_composite_score_partial():
    hyp = {
        "character_fidelity_score": 1.0,
        "fandom_resonance_score": 0.0,
        "emergence_score": 0.0,
        "diversity_score": 0.0,
        "plausibility_score": 0.0,
    }
    assert _composite_score(hyp) == pytest.approx(0.25)


# --------------------------------------------------------------------------- #
# EvolveOrchestrator — dry-run
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_evolve_orchestrator_dry_run(tmp_path):
    """Dry-run should return immediately without touching the DB."""
    cfg = EvolveConfig(
        initial_topic="Dry run topic",
        max_iterations=3,
        dry_run=True,
        output_dir=tmp_path,
    )
    orch = EvolveOrchestrator(cfg)
    state = await orch.run_async()

    assert state.termination_reason == "dry_run"
    assert len(state.history) == 0
    assert state.total_cost == 0.0


def test_evolve_orchestrator_dry_run_blocking(tmp_path):
    """Blocking run() should work identically to run_async() in dry-run mode."""
    cfg = EvolveConfig(
        initial_topic="Blocking dry run",
        max_iterations=2,
        dry_run=True,
        output_dir=tmp_path,
    )
    orch = EvolveOrchestrator(cfg)
    state = orch.run()

    assert state.termination_reason == "dry_run"


# --------------------------------------------------------------------------- #
# CLI smoke test
# --------------------------------------------------------------------------- #


def test_cli_evolve_command_exists():
    """The `evolve` subcommand must be registered with the CLI group."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["evolve", "--help"])
    assert result.exit_code == 0
    assert "evolve" in result.output.lower() or "TOPIC" in result.output


def test_cli_evolve_dry_run(tmp_path):
    """Dry-run via CLI should exit 0 and print the plan."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "evolve",
            "Test topic",
            "--max-iterations", "2",
            "--dry-run",
            "--output-dir", str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output
    # Dry-run banner should mention the plan
    assert "DRY RUN" in result.output or "dry" in result.output.lower()


def test_cli_evolve_max_iterations_option():
    """--max-iterations option must be parsed correctly."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["evolve", "--help"])
    assert "--max-iterations" in result.output
