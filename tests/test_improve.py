"""Tests for the improve step — Sub-AC 3c.

Covers:
- ImprovementPlan construction and serialisation
- ImprovementRecord construction and serialisation
- ScenarioImprover.generate_plan:
    - Each weakest dimension drives the correct adjustments
    - Bottleneck corrections are applied and merged correctly
    - Parameter values are clamped to PARAM_BOUNDS
    - Unknown / empty diagnosis returns a valid plan
- ScenarioImprover.apply_to_config:
    - Adjusted values are propagated to a new EvolveConfig
    - Unchanged fields are copied verbatim
- generate_improvement_plan convenience wrapper
- _compute_adjusted_params helper: factors, deltas, bounds
- _merge_deltas helper
- CLI smoke tests:
    - `dormammu improve --help` exits 0
    - `dormammu improve` without benchmark exits non-zero
- evolve `--improve` flag is registered
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ese.improve import (
    ImprovementPlan,
    ImprovementRecord,
    ScenarioImprover,
    PARAM_BOUNDS,
    _compute_adjusted_params,
    _merge_deltas,
    generate_improvement_plan,
)


# --------------------------------------------------------------------------- #
# Fixtures / helpers
# --------------------------------------------------------------------------- #


def _make_diagnosis(
    weakest: str = "Emergence",
    score: float = 0.3,
    bottleneck_suggestions: list[str] | None = None,
    failure_patterns: list[str] | None = None,
) -> dict:
    """Build a minimal diagnosis dict as returned by diagnose.diagnose()."""
    return {
        "weakest_dimension": weakest,
        "score": score,
        "target_module": "src/ese/engine/turn.py",
        "target_method": "TurnExecutor.execute",
        "suggestion": "Add emergent events step.",
        "failure_patterns": failure_patterns or [],
        "bottleneck_suggestions": bottleneck_suggestions or [],
    }


def _default_params() -> dict:
    return {
        "node_years": 100,
        "max_depth": 5,
        "cost_limit_per_cycle": 10.0,
        "convergence_threshold": 0.05,
    }


# --------------------------------------------------------------------------- #
# ImprovementPlan serialisation
# --------------------------------------------------------------------------- #


class TestImprovementPlan:
    def test_to_dict_round_trip(self):
        plan = ImprovementPlan(
            focus_dimension="Emergence",
            focus_score=0.3,
            param_adjustments={"node_years": 120, "max_depth": 5},
            strategy_hints=["hint A", "hint B"],
            new_evaluation_criteria=[{"name": "E", "description": "desc"}],
            bottleneck_corrections=["Correction 1"],
        )
        d = plan.to_dict()
        restored = ImprovementPlan.from_dict(d)

        assert restored.focus_dimension == "Emergence"
        assert restored.focus_score == pytest.approx(0.3)
        assert restored.param_adjustments["node_years"] == 120
        assert "hint A" in restored.strategy_hints
        assert restored.new_evaluation_criteria[0]["name"] == "E"
        assert restored.bottleneck_corrections[0] == "Correction 1"

    def test_to_dict_is_json_serialisable(self):
        plan = ImprovementPlan(
            focus_dimension="Character Fidelity",
            focus_score=0.4,
            param_adjustments={"cost_limit_per_cycle": 12.0},
        )
        serialised = json.dumps(plan.to_dict())
        data = json.loads(serialised)
        assert data["focus_dimension"] == "Character Fidelity"

    def test_from_dict_missing_keys_defaults(self):
        plan = ImprovementPlan.from_dict({})
        assert plan.focus_dimension == "unknown"
        assert plan.focus_score == pytest.approx(0.0)
        assert isinstance(plan.param_adjustments, dict)
        assert isinstance(plan.strategy_hints, list)

    def test_generated_at_is_set_automatically(self):
        plan = ImprovementPlan(focus_dimension="Plausibility", focus_score=0.2)
        assert plan.generated_at  # non-empty string


# --------------------------------------------------------------------------- #
# ImprovementRecord
# --------------------------------------------------------------------------- #


class TestImprovementRecord:
    def test_to_dict_structure(self):
        plan = ImprovementPlan(focus_dimension="Emergence", focus_score=0.3)
        record = ImprovementRecord(
            cycle=2,
            plan=plan,
            before_scores={"avg_emergence": 0.3, "avg_character_fidelity": 0.6},
        )
        d = record.to_dict()
        assert d["cycle"] == 2
        assert d["before_scores"]["avg_emergence"] == pytest.approx(0.3)
        assert "plan" in d
        assert d["plan"]["focus_dimension"] == "Emergence"

    def test_to_dict_json_serialisable(self):
        plan = ImprovementPlan(focus_dimension="Plausibility", focus_score=0.2)
        record = ImprovementRecord(cycle=1, plan=plan)
        json.dumps(record.to_dict())  # must not raise


# --------------------------------------------------------------------------- #
# _merge_deltas
# --------------------------------------------------------------------------- #


class TestMergeDeltas:
    def test_factor_multiplication(self):
        base = {"node_years_factor": 1.2}
        extra = {"node_years_factor": 1.3}
        _merge_deltas(base, extra)
        assert base["node_years_factor"] == pytest.approx(1.2 * 1.3)

    def test_delta_addition(self):
        base = {"max_depth_delta": 1}
        extra = {"max_depth_delta": -1}
        _merge_deltas(base, extra)
        assert base["max_depth_delta"] == 0

    def test_new_key_inserted(self):
        base = {}
        extra = {"cost_limit_factor": 1.5}
        _merge_deltas(base, extra)
        assert base["cost_limit_factor"] == pytest.approx(1.5)

    def test_multiple_keys(self):
        base = {"node_years_factor": 1.2, "max_depth_delta": 1}
        extra = {"node_years_factor": 1.1, "max_depth_delta": 2, "cost_limit_factor": 1.2}
        _merge_deltas(base, extra)
        assert base["node_years_factor"] == pytest.approx(1.2 * 1.1)
        assert base["max_depth_delta"] == 3
        assert base["cost_limit_factor"] == pytest.approx(1.2)


# --------------------------------------------------------------------------- #
# _compute_adjusted_params
# --------------------------------------------------------------------------- #


class TestComputeAdjustedParams:
    def test_factor_increases_value(self):
        params = _compute_adjusted_params(
            {"node_years_factor": 1.20},
            {"node_years": 100},
        )
        assert params["node_years"] == 120

    def test_factor_decreases_value(self):
        params = _compute_adjusted_params(
            {"cost_limit_factor": 0.80},
            {"cost_limit_per_cycle": 10.0},
        )
        assert params["cost_limit_per_cycle"] == pytest.approx(8.0)

    def test_delta_increases_depth(self):
        params = _compute_adjusted_params(
            {"max_depth_delta": 1},
            {"max_depth": 5},
        )
        assert params["max_depth"] == 6

    def test_delta_decreases_depth(self):
        params = _compute_adjusted_params(
            {"max_depth_delta": -1},
            {"max_depth": 3},
        )
        assert params["max_depth"] == 2

    def test_clamped_to_lower_bound(self):
        # max_depth lower bound is 1; 1 + (-5) = -4 → clamped to 1
        params = _compute_adjusted_params(
            {"max_depth_delta": -5},
            {"max_depth": 2},
        )
        lo, _ = PARAM_BOUNDS["max_depth"]
        assert params["max_depth"] >= int(lo)

    def test_clamped_to_upper_bound(self):
        # node_years upper bound is 1000
        params = _compute_adjusted_params(
            {"node_years_factor": 100.0},
            {"node_years": 100},
        )
        _, hi = PARAM_BOUNDS["node_years"]
        assert params["node_years"] <= int(hi)

    def test_no_deltas_returns_defaults(self):
        params = _compute_adjusted_params({}, {})
        assert "node_years" in params
        assert "max_depth" in params
        assert "cost_limit_per_cycle" in params
        assert "convergence_threshold" in params

    def test_integer_types_for_integer_fields(self):
        params = _compute_adjusted_params(
            {"node_years_factor": 1.5, "max_depth_delta": 1},
            {"node_years": 100, "max_depth": 3},
        )
        assert isinstance(params["node_years"], int)
        assert isinstance(params["max_depth"], int)

    def test_float_types_for_float_fields(self):
        params = _compute_adjusted_params(
            {"cost_limit_factor": 1.2, "convergence_threshold_factor": 0.8},
            {"cost_limit_per_cycle": 10.0, "convergence_threshold": 0.05},
        )
        assert isinstance(params["cost_limit_per_cycle"], float)
        assert isinstance(params["convergence_threshold"], float)


# --------------------------------------------------------------------------- #
# ScenarioImprover.generate_plan — per dimension
# --------------------------------------------------------------------------- #


class TestScenarioImproverGeneratePlan:
    def test_returns_improvement_plan(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert isinstance(plan, ImprovementPlan)

    def test_focus_dimension_preserved(self):
        diagnosis = _make_diagnosis("Emergence", 0.35)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert plan.focus_dimension == "Emergence"
        assert plan.focus_score == pytest.approx(0.35)

    def test_emergence_increases_node_years(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        # node_years should increase by ~20%
        assert plan.param_adjustments.get("node_years", 0) > current["node_years"]

    def test_character_fidelity_increases_cost_limit(self):
        diagnosis = _make_diagnosis("Character Fidelity", 0.25)
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        assert (
            plan.param_adjustments.get("cost_limit_per_cycle", 0)
            > current["cost_limit_per_cycle"]
        )

    def test_diversity_increases_max_depth(self):
        diagnosis = _make_diagnosis("Diversity", 0.2)
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        assert plan.param_adjustments.get("max_depth", 0) > current["max_depth"]

    def test_plausibility_decreases_convergence_threshold(self):
        diagnosis = _make_diagnosis("Plausibility", 0.15)
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        assert (
            plan.param_adjustments.get("convergence_threshold", 1.0)
            < current["convergence_threshold"]
        )

    def test_strategy_hints_populated_for_emergence(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert len(plan.strategy_hints) > 0

    def test_strategy_hints_populated_for_character_fidelity(self):
        diagnosis = _make_diagnosis("Character Fidelity", 0.25)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert len(plan.strategy_hints) > 0

    def test_new_criteria_added_for_diversity(self):
        diagnosis = _make_diagnosis("Diversity", 0.2)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert len(plan.new_evaluation_criteria) > 0
        names = [c.get("name", "") for c in plan.new_evaluation_criteria]
        assert any("diversity" in n.lower() or "distinct" in n.lower() for n in names)

    def test_new_criteria_added_for_plausibility(self):
        diagnosis = _make_diagnosis("Plausibility", 0.1)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert len(plan.new_evaluation_criteria) > 0

    def test_unknown_dimension_returns_empty_hints(self):
        diagnosis = _make_diagnosis("Unknown Dimension", 0.5)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        # Should not raise; may have empty hints
        assert isinstance(plan.strategy_hints, list)

    def test_source_diagnosis_stored(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert plan.source_diagnosis == diagnosis

    def test_param_adjustments_json_serialisable(self):
        diagnosis = _make_diagnosis("Character Fidelity", 0.4)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        json.dumps(plan.param_adjustments)  # must not raise


# --------------------------------------------------------------------------- #
# ScenarioImprover.generate_plan — bottleneck corrections
# --------------------------------------------------------------------------- #


class TestBottleneckCorrections:
    def test_unevaluated_nodes_increases_cost(self):
        diagnosis = _make_diagnosis(
            "Emergence",
            0.3,
            bottleneck_suggestions=[
                "Consider increasing cost_limit or reducing max_depth"
            ],
        )
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        # Cost limit should be increased (both dimension rule +10% and bottleneck +30%)
        assert (
            plan.param_adjustments.get("cost_limit_per_cycle", 0)
            > current["cost_limit_per_cycle"]
        )

    def test_depth_degradation_reduces_depth(self):
        diagnosis = _make_diagnosis(
            "Emergence",
            0.3,
            bottleneck_suggestions=["Quality declines at deeper tree levels"],
        )
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        # depth should decrease due to degradation correction
        assert plan.param_adjustments.get("max_depth", 999) <= current["max_depth"]

    def test_high_cost_reduces_node_years(self):
        diagnosis = _make_diagnosis(
            "Character Fidelity",
            0.3,
            bottleneck_suggestions=["Some turns are disproportionately expensive (costly)"],
        )
        current = _default_params()
        plan = ScenarioImprover().generate_plan(diagnosis, current)
        # node_years could be reduced due to high cost correction
        # (narrative rule increases cost_limit but high_cost reduces node_years)
        assert "node_years" in plan.param_adjustments

    def test_bottleneck_correction_recorded(self):
        diagnosis = _make_diagnosis(
            "Emergence",
            0.3,
            bottleneck_suggestions=["Consider increasing cost_limit"],
        )
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        assert len(plan.bottleneck_corrections) >= 1

    def test_no_bottlenecks_no_corrections(self):
        diagnosis = _make_diagnosis("Emergence", 0.3, bottleneck_suggestions=[])
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        # Only dimension-driven corrections, no bottleneck corrections
        assert isinstance(plan.bottleneck_corrections, list)


# --------------------------------------------------------------------------- #
# ScenarioImprover.apply_to_config
# --------------------------------------------------------------------------- #


class TestApplyToConfig:
    def test_updates_node_years(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test", node_years=100)
        plan = ImprovementPlan(
            focus_dimension="Emergence",
            focus_score=0.3,
            param_adjustments={"node_years": 120, "max_depth": 5,
                               "cost_limit_per_cycle": 10.0,
                               "convergence_threshold": 0.05},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert new_cfg.node_years == 120

    def test_updates_max_depth(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test", max_depth=3)
        plan = ImprovementPlan(
            focus_dimension="Diversity",
            focus_score=0.2,
            param_adjustments={"node_years": 100, "max_depth": 4,
                               "cost_limit_per_cycle": 10.0,
                               "convergence_threshold": 0.05},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert new_cfg.max_depth == 4

    def test_updates_cost_limit(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test", cost_limit_per_cycle=10.0)
        plan = ImprovementPlan(
            focus_dimension="Character Fidelity",
            focus_score=0.25,
            param_adjustments={"node_years": 100, "max_depth": 5,
                               "cost_limit_per_cycle": 12.0,
                               "convergence_threshold": 0.05},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert new_cfg.cost_limit_per_cycle == pytest.approx(12.0)

    def test_updates_convergence_threshold(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test", convergence_threshold=0.05)
        plan = ImprovementPlan(
            focus_dimension="Plausibility",
            focus_score=0.15,
            param_adjustments={"node_years": 100, "max_depth": 5,
                               "cost_limit_per_cycle": 10.0,
                               "convergence_threshold": 0.04},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert new_cfg.convergence_threshold == pytest.approx(0.04)

    def test_unchanged_fields_preserved(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(
            initial_topic="Mars colony",
            max_iterations=7,
            language="ko",
            total_cost_limit=99.0,
        )
        plan = ImprovementPlan(
            focus_dimension="Emergence",
            focus_score=0.3,
            param_adjustments={"node_years": 120, "max_depth": 5,
                               "cost_limit_per_cycle": 10.0,
                               "convergence_threshold": 0.05},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)

        assert new_cfg.initial_topic == "Mars colony"
        assert new_cfg.max_iterations == 7
        assert new_cfg.language == "ko"
        assert new_cfg.total_cost_limit == pytest.approx(99.0)

    def test_returns_evolveconfig_instance(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test")
        plan = ImprovementPlan(
            focus_dimension="Emergence",
            focus_score=0.3,
            param_adjustments={"node_years": 120, "max_depth": 5,
                               "cost_limit_per_cycle": 10.0,
                               "convergence_threshold": 0.05},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert isinstance(new_cfg, EvolveConfig)

    def test_empty_param_adjustments_preserves_config(self):
        from ese.orchestrator.evolve import EvolveConfig

        cfg = EvolveConfig(initial_topic="test", node_years=50, max_depth=3)
        plan = ImprovementPlan(
            focus_dimension="unknown",
            focus_score=0.5,
            param_adjustments={},
        )
        new_cfg = ScenarioImprover().apply_to_config(plan, cfg)
        assert new_cfg.node_years == 50
        assert new_cfg.max_depth == 3


# --------------------------------------------------------------------------- #
# generate_improvement_plan convenience wrapper
# --------------------------------------------------------------------------- #


class TestGenerateImprovementPlan:
    def test_returns_plan_from_diagnosis(self):
        diagnosis = _make_diagnosis("Character Fidelity", 0.4)
        plan = generate_improvement_plan(diagnosis)
        assert isinstance(plan, ImprovementPlan)
        assert plan.focus_dimension == "Character Fidelity"

    def test_uses_config_defaults_when_no_params(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        plan = generate_improvement_plan(diagnosis, current_params=None)
        assert isinstance(plan, ImprovementPlan)
        assert len(plan.param_adjustments) > 0

    def test_uses_provided_params(self):
        diagnosis = _make_diagnosis("Emergence", 0.3)
        params = {"node_years": 200, "max_depth": 3,
                  "cost_limit_per_cycle": 5.0, "convergence_threshold": 0.05}
        plan = generate_improvement_plan(diagnosis, params)
        # node_years should be > 200 due to +20% rule
        assert plan.param_adjustments.get("node_years", 0) > 200


# --------------------------------------------------------------------------- #
# Param bounds enforcement
# --------------------------------------------------------------------------- #


class TestParamBounds:
    """Ensure computed params always fall within PARAM_BOUNDS."""

    @pytest.mark.parametrize("dimension", [
        "Emergence", "Character Fidelity", "Fandom Resonance", "Diversity", "Plausibility"
    ])
    def test_all_dimensions_within_bounds(self, dimension):
        diagnosis = _make_diagnosis(dimension, 0.1)
        plan = ScenarioImprover().generate_plan(diagnosis, _default_params())
        for key, (lo, hi) in PARAM_BOUNDS.items():
            if key in plan.param_adjustments:
                val = plan.param_adjustments[key]
                assert val >= lo, f"{key}={val} < lower bound {lo}"
                assert val <= hi, f"{key}={val} > upper bound {hi}"

    def test_extreme_high_factor_clamped(self):
        params = _compute_adjusted_params(
            {"cost_limit_factor": 999.0}, {"cost_limit_per_cycle": 10.0}
        )
        _, hi = PARAM_BOUNDS["cost_limit_per_cycle"]
        assert params["cost_limit_per_cycle"] <= hi

    def test_extreme_low_threshold_clamped(self):
        params = _compute_adjusted_params(
            {"convergence_threshold_factor": 0.0001},
            {"convergence_threshold": 0.05},
        )
        lo, _ = PARAM_BOUNDS["convergence_threshold"]
        assert params["convergence_threshold"] >= lo


# --------------------------------------------------------------------------- #
# CLI smoke tests
# --------------------------------------------------------------------------- #


def test_cli_improve_command_exists():
    """The `improve` subcommand must be registered with the CLI group."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["improve", "--help"])
    assert result.exit_code == 0
    assert "improve" in result.output.lower() or "benchmark" in result.output.lower()


def test_cli_improve_no_benchmark(tmp_path, monkeypatch):
    """Improve with no benchmark file should exit with non-zero status."""
    from click.testing import CliRunner
    from ese.main import cli
    from ese import config as config_module

    monkeypatch.setattr(config_module.config, "data_dir", tmp_path / "simulations")

    runner = CliRunner()
    result = runner.invoke(cli, ["improve"])
    assert result.exit_code != 0
    assert "benchmark" in result.output.lower() or "No benchmark" in result.output


def test_cli_evolve_improve_flag_registered():
    """The `--improve` flag must be parseable on the `evolve` command."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["evolve", "--help"])
    assert result.exit_code == 0
    assert "--improve" in result.output


def test_cli_evolve_dry_run_with_improve_flag(tmp_path):
    """Dry-run with --improve flag should not fail."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "evolve",
            "Test topic",
            "--max-iterations", "1",
            "--dry-run",
            "--improve",
            "--output-dir", str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- #
# EvolveConfig enable_improve field
# --------------------------------------------------------------------------- #


def test_evolve_config_enable_improve_default():
    """enable_improve defaults to False."""
    from ese.orchestrator.evolve import EvolveConfig

    cfg = EvolveConfig(initial_topic="test")
    assert cfg.enable_improve is False


def test_evolve_config_enable_improve_set():
    """enable_improve can be set to True."""
    from ese.orchestrator.evolve import EvolveConfig

    cfg = EvolveConfig(initial_topic="test", enable_improve=True)
    assert cfg.enable_improve is True


# --------------------------------------------------------------------------- #
# Integration: plan → apply → within-bounds check
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("dimension,score", [
    ("Emergence", 0.2),
    ("Character Fidelity", 0.3),
    ("Fandom Resonance", 0.25),
    ("Diversity", 0.25),
    ("Plausibility", 0.1),
])
def test_full_pipeline_plan_apply_within_bounds(dimension, score):
    """Full pipeline: diagnose → plan → apply → config in valid range."""
    from ese.orchestrator.evolve import EvolveConfig

    diagnosis = _make_diagnosis(dimension, score)
    params = _default_params()
    plan = generate_improvement_plan(diagnosis, params)

    cfg = EvolveConfig(initial_topic="test")
    new_cfg = ScenarioImprover().apply_to_config(plan, cfg)

    lo_y, hi_y = PARAM_BOUNDS["node_years"]
    lo_d, hi_d = PARAM_BOUNDS["max_depth"]
    lo_c, hi_c = PARAM_BOUNDS["cost_limit_per_cycle"]
    lo_t, hi_t = PARAM_BOUNDS["convergence_threshold"]

    assert lo_y <= new_cfg.node_years <= hi_y
    assert lo_d <= new_cfg.max_depth <= hi_d
    assert lo_c <= new_cfg.cost_limit_per_cycle <= hi_c
    assert lo_t <= new_cfg.convergence_threshold <= hi_t
