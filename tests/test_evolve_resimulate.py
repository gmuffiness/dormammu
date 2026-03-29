"""Tests for Sub-AC 3d: re-simulate step and loop termination conditions.

Covers:
- ReSimulateResult construction, score_delta, improved, serialization
- EvolveCycleResult.to_dict() includes re_simulate_result field
- EvolveState.re_simulate_history population via record()
- EvolveState.score_deltas property
- EvolveState.re_simulate_score_deltas property
- Convergence via re-simulate delta stagnation
- EvolveConfig.enable_re_simulate flag
- _write_final_report() includes re-simulate comparison and convergence analysis
- CLI --re-simulate flag registration and dry-run with flag
- EvolveOrchestrator._run_re_simulate_step (mocked simulation)
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ese.orchestrator.evolve import (
    EvolveConfig,
    EvolveCycleResult,
    EvolveOrchestrator,
    EvolveState,
    ReSimulateResult,
    _composite_score,
    _mean,
)


# --------------------------------------------------------------------------- #
# ReSimulateResult — basic construction
# --------------------------------------------------------------------------- #


class TestReSimulateResult:
    def test_default_scores_are_zero(self):
        rs = ReSimulateResult(cycle=1, topic="Mars", simulation_id="sim-1")
        assert rs.original_score == pytest.approx(0.0)
        assert rs.re_simulate_score == pytest.approx(0.0)

    def test_score_delta_positive(self):
        rs = ReSimulateResult(
            cycle=1, topic="Mars", simulation_id="sim-1",
            original_score=0.4, re_simulate_score=0.6,
        )
        assert rs.score_delta == pytest.approx(0.2)
        assert rs.improved is True

    def test_score_delta_negative(self):
        rs = ReSimulateResult(
            cycle=1, topic="Mars", simulation_id="sim-1",
            original_score=0.7, re_simulate_score=0.5,
        )
        assert rs.score_delta == pytest.approx(-0.2)
        assert rs.improved is False

    def test_score_delta_zero(self):
        rs = ReSimulateResult(
            cycle=1, topic="Mars", simulation_id="sim-1",
            original_score=0.5, re_simulate_score=0.5,
        )
        assert rs.score_delta == pytest.approx(0.0)
        assert rs.improved is False  # strictly greater required

    def test_failed_result(self):
        rs = ReSimulateResult(
            cycle=2, topic="Colony", simulation_id="",
            failed=True, error_message="timeout",
        )
        assert rs.failed is True
        assert rs.error_message == "timeout"


# --------------------------------------------------------------------------- #
# ReSimulateResult — serialization
# --------------------------------------------------------------------------- #


class TestReSimulateResultSerialization:
    def test_to_dict_keys_present(self):
        rs = ReSimulateResult(
            cycle=3,
            topic="Test topic",
            simulation_id="abc-123",
            original_score=0.45,
            re_simulate_score=0.62,
            cost_usd=0.50,
            nodes_explored=4,
        )
        d = rs.to_dict()

        required_keys = {
            "cycle", "topic", "simulation_id",
            "original_score", "re_simulate_score",
            "score_delta", "improved",
            "cost_usd", "nodes_explored",
            "failed", "error_message",
        }
        assert required_keys.issubset(d.keys())

    def test_to_dict_values_correct(self):
        rs = ReSimulateResult(
            cycle=2,
            topic="Moon base",
            simulation_id="xyz",
            original_score=0.4,
            re_simulate_score=0.55,
        )
        d = rs.to_dict()
        assert d["cycle"] == 2
        assert d["topic"] == "Moon base"
        assert d["simulation_id"] == "xyz"
        assert d["original_score"] == pytest.approx(0.4)
        assert d["re_simulate_score"] == pytest.approx(0.55)
        assert d["score_delta"] == pytest.approx(0.15)
        assert d["improved"] is True

    def test_to_dict_is_json_serializable(self):
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=0.3, re_simulate_score=0.4,
        )
        serialized = json.dumps(rs.to_dict())
        restored = json.loads(serialized)
        assert restored["cycle"] == 1
        assert restored["improved"] is True

    def test_to_dict_failed_result(self):
        rs = ReSimulateResult(
            cycle=5, topic="fail-topic", simulation_id="",
            failed=True, error_message="network error",
        )
        d = rs.to_dict()
        assert d["failed"] is True
        assert d["error_message"] == "network error"

    def test_score_delta_rounded_in_dict(self):
        """score_delta in to_dict() is rounded to 6 decimal places."""
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=1 / 3, re_simulate_score=2 / 3,
        )
        d = rs.to_dict()
        # Should be finite and reasonable
        assert abs(d["score_delta"] - (1 / 3)) < 1e-5


# --------------------------------------------------------------------------- #
# EvolveCycleResult — re_simulate_result field
# --------------------------------------------------------------------------- #


class TestEvolveCycleResultReSimulate:
    def test_re_simulate_result_defaults_to_none(self):
        r = EvolveCycleResult(cycle=1, topic="t", simulation_id="s")
        assert r.re_simulate_result is None

    def test_to_dict_includes_re_simulate_result_as_none(self):
        r = EvolveCycleResult(cycle=1, topic="t", simulation_id="s")
        d = r.to_dict()
        assert "re_simulate_result" in d
        assert d["re_simulate_result"] is None

    def test_to_dict_includes_re_simulate_result_as_dict(self):
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="rs-sim",
            original_score=0.5, re_simulate_score=0.65,
        )
        r = EvolveCycleResult(
            cycle=1, topic="t", simulation_id="orig-sim",
            re_simulate_result=rs,
        )
        d = r.to_dict()
        assert isinstance(d["re_simulate_result"], dict)
        assert d["re_simulate_result"]["re_simulate_score"] == pytest.approx(0.65)

    def test_to_dict_json_serializable_with_re_simulate(self):
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=0.3, re_simulate_score=0.4,
        )
        r = EvolveCycleResult(
            cycle=1, topic="t", simulation_id="o",
            re_simulate_result=rs,
        )
        # Must not raise
        json.dumps(r.to_dict())


# --------------------------------------------------------------------------- #
# EvolveState — re_simulate_history and score_deltas
# --------------------------------------------------------------------------- #


def _make_config(**kwargs) -> EvolveConfig:
    defaults = dict(
        initial_topic="test",
        max_iterations=10,
        total_cost_limit=100.0,
        convergence_patience=3,
        convergence_threshold=0.05,
    )
    defaults.update(kwargs)
    return EvolveConfig(**defaults)


def _make_result(
    cycle: int,
    score: float = 0.5,
    cost: float = 0.5,
    re_sim: ReSimulateResult | None = None,
) -> EvolveCycleResult:
    r = EvolveCycleResult(
        cycle=cycle,
        topic=f"topic-{cycle}",
        simulation_id=f"sim-{cycle}",
        best_composite_score=score,
        cost_usd=cost,
        re_simulate_result=re_sim,
    )
    return r


def _make_state(**kwargs) -> EvolveState:
    return EvolveState(config=_make_config(**kwargs))


class TestEvolveStateReSimulateHistory:
    def test_re_simulate_history_starts_empty(self):
        state = _make_state()
        assert state.re_simulate_history == []

    def test_record_populates_re_simulate_history(self):
        state = _make_state()
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=0.5, re_simulate_score=0.6,
        )
        r = _make_result(1, score=0.5, re_sim=rs)
        state.record(r)
        assert len(state.re_simulate_history) == 1
        assert state.re_simulate_history[0].re_simulate_score == pytest.approx(0.6)

    def test_record_skips_none_re_simulate(self):
        state = _make_state()
        r = _make_result(1, score=0.5, re_sim=None)
        state.record(r)
        assert state.re_simulate_history == []

    def test_record_multiple_re_simulate_results(self):
        state = _make_state()
        for i in range(1, 4):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.4 + i * 0.05,
                re_simulate_score=0.5 + i * 0.05,
            )
            r = _make_result(i, score=0.4 + i * 0.05, re_sim=rs)
            state.record(r)
        assert len(state.re_simulate_history) == 3

    def test_re_simulate_score_deltas_property(self):
        state = _make_state()
        for i in range(1, 4):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.5,
                re_simulate_score=0.5 + i * 0.02,
            )
            r = _make_result(i, score=0.5, re_sim=rs)
            state.record(r)

        deltas = state.re_simulate_score_deltas
        assert len(deltas) == 3
        assert all(d > 0 for d in deltas)

    def test_re_simulate_score_deltas_excludes_failures(self):
        state = _make_state()
        rs_ok = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=0.4, re_simulate_score=0.6,
        )
        rs_fail = ReSimulateResult(
            cycle=2, topic="t", simulation_id="",
            failed=True,
        )
        state.record(_make_result(1, score=0.4, re_sim=rs_ok))
        state.record(_make_result(2, score=0.5, re_sim=rs_fail))

        deltas = state.re_simulate_score_deltas
        assert len(deltas) == 1
        assert deltas[0] == pytest.approx(0.2)


# --------------------------------------------------------------------------- #
# EvolveState — score_deltas property
# --------------------------------------------------------------------------- #


class TestEvolveStateScoreDeltas:
    def test_empty_with_no_cycles(self):
        state = _make_state()
        assert state.score_deltas == []

    def test_empty_with_one_cycle(self):
        state = _make_state()
        state.record(_make_result(1, score=0.5))
        assert state.score_deltas == []

    def test_two_cycles_gives_one_delta(self):
        state = _make_state()
        state.record(_make_result(1, score=0.4))
        state.record(_make_result(2, score=0.6))
        deltas = state.score_deltas
        assert len(deltas) == 1
        assert deltas[0] == pytest.approx(0.2)

    def test_three_cycles_gives_two_deltas(self):
        state = _make_state()
        state.record(_make_result(1, score=0.3))
        state.record(_make_result(2, score=0.5))
        state.record(_make_result(3, score=0.6))
        deltas = state.score_deltas
        assert len(deltas) == 2
        assert deltas[0] == pytest.approx(0.2)
        assert deltas[1] == pytest.approx(0.1)

    def test_score_deltas_exclude_failures(self):
        """Failed cycles should not appear in score_deltas."""
        state = _make_state()
        state.record(_make_result(1, score=0.4))
        failed = EvolveCycleResult(cycle=2, topic="t2", simulation_id="s2", failed=True)
        state.record(failed)
        state.record(_make_result(3, score=0.7))
        deltas = state.score_deltas
        # Only cycles 1 and 3 are successful; delta = 0.7 - 0.4 = 0.3
        assert len(deltas) == 1
        assert deltas[0] == pytest.approx(0.3)


# --------------------------------------------------------------------------- #
# EvolveState — convergence using re-simulate deltas
# --------------------------------------------------------------------------- #


class TestReSimulateConvergence:
    def test_no_termination_without_enough_re_sim_cycles(self):
        state = _make_state(
            convergence_patience=3,
            convergence_threshold=0.05,
        )
        # Only 2 re-simulate cycles → not enough for convergence
        for i in range(1, 3):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.5, re_simulate_score=0.51,  # tiny delta < 0.05
            )
            r = _make_result(i, score=0.5, re_sim=rs)
            state.record(r)

        assert state.termination_check() is None

    def test_terminates_when_re_sim_deltas_stagnate(self):
        state = _make_state(
            convergence_patience=3,
            convergence_threshold=0.05,
            max_iterations=20,  # won't hit iteration limit
        )
        # 3 consecutive tiny re-simulate deltas (< 0.05)
        for i in range(1, 4):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.5,
                re_simulate_score=0.51,  # delta = 0.01 < 0.05
            )
            r = _make_result(i, score=0.5 + i * 0.001, re_sim=rs)
            state.record(r)

        reason = state.termination_check()
        assert reason is not None
        assert "re-simulate" in reason.lower() or "converged" in reason.lower()

    def test_no_termination_when_re_sim_deltas_improving(self):
        state = _make_state(
            convergence_patience=3,
            convergence_threshold=0.05,
            max_iterations=20,
        )
        # 3 cycles with large positive re-simulate deltas
        for i in range(1, 4):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.3 + i * 0.1,
                re_simulate_score=0.3 + i * 0.1 + 0.10,  # delta = 0.10 >= 0.05
            )
            r = _make_result(i, score=0.3 + i * 0.1, re_sim=rs)
            state.record(r)

        assert state.termination_check() is None

    def test_re_sim_convergence_message_contains_patience_info(self):
        state = _make_state(
            convergence_patience=3,
            convergence_threshold=0.05,
            max_iterations=20,
        )
        for i in range(1, 4):
            rs = ReSimulateResult(
                cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
                original_score=0.5, re_simulate_score=0.51,
            )
            r = _make_result(i, score=0.5 + i * 0.001, re_sim=rs)
            state.record(r)

        reason = state.termination_check()
        assert reason is not None
        # Should mention the threshold
        assert "0.05" in reason or "0.050" in reason

    def test_standard_convergence_still_works_without_re_sim(self):
        """Original convergence logic must work even when no re-simulates run."""
        state = _make_state(
            convergence_patience=3,
            convergence_threshold=0.05,
            max_iterations=20,
        )
        # First cycle sets best to 0.8
        state.record(_make_result(1, score=0.8))
        # 3 non-improving cycles
        for i in range(2, 5):
            state.record(_make_result(i, score=0.80 + i * 0.005))

        reason = state.termination_check()
        assert reason is not None
        assert "converged" in reason


# --------------------------------------------------------------------------- #
# EvolveState — effective_score with re-simulate
# --------------------------------------------------------------------------- #


class TestEvolveStateEffectiveScore:
    """When re_simulate_result is present, global_best_score uses re-sim score."""

    def test_global_best_uses_re_sim_score_when_available(self):
        state = _make_state(convergence_threshold=0.05)
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="s",
            original_score=0.5, re_simulate_score=0.75,
        )
        r = _make_result(1, score=0.5, re_sim=rs)
        state.record(r)
        # global_best should be 0.75 (re-sim score), not 0.5
        assert state.global_best_score == pytest.approx(0.75)

    def test_global_best_falls_back_to_original_when_no_re_sim(self):
        state = _make_state(convergence_threshold=0.05)
        r = _make_result(1, score=0.65, re_sim=None)
        state.record(r)
        assert state.global_best_score == pytest.approx(0.65)

    def test_global_best_falls_back_when_re_sim_failed(self):
        state = _make_state(convergence_threshold=0.05)
        rs = ReSimulateResult(
            cycle=1, topic="t", simulation_id="",
            original_score=0.5, failed=True,
        )
        r = _make_result(1, score=0.65, re_sim=rs)
        state.record(r)
        # Failed re-sim → use original score
        assert state.global_best_score == pytest.approx(0.65)


# --------------------------------------------------------------------------- #
# EvolveConfig — enable_re_simulate flag
# --------------------------------------------------------------------------- #


class TestEvolveConfigReSimulate:
    def test_enable_re_simulate_defaults_to_false(self):
        cfg = EvolveConfig(initial_topic="test")
        assert cfg.enable_re_simulate is False

    def test_enable_re_simulate_can_be_set_true(self):
        cfg = EvolveConfig(initial_topic="test", enable_re_simulate=True)
        assert cfg.enable_re_simulate is True

    def test_enable_re_simulate_independent_of_enable_improve(self):
        cfg = EvolveConfig(
            initial_topic="test",
            enable_improve=True,
            enable_re_simulate=False,
        )
        assert cfg.enable_improve is True
        assert cfg.enable_re_simulate is False

    def test_both_flags_can_be_true(self):
        cfg = EvolveConfig(
            initial_topic="test",
            enable_improve=True,
            enable_re_simulate=True,
        )
        assert cfg.enable_improve is True
        assert cfg.enable_re_simulate is True


# --------------------------------------------------------------------------- #
# EvolveOrchestrator._run_re_simulate_step (with mocked OrchestratorLoop)
# --------------------------------------------------------------------------- #


class TestRunReSimulateStep:
    """Test the _run_re_simulate_step method with a mocked DB and loop."""

    def _make_orch(self, tmp_path: Path) -> EvolveOrchestrator:
        cfg = EvolveConfig(
            initial_topic="test topic",
            max_iterations=3,
            node_years=100,
            cost_limit_per_cycle=5.0,
            output_dir=tmp_path,
        )
        return EvolveOrchestrator(cfg)

    @pytest.mark.asyncio
    async def test_re_simulate_returns_result(self, tmp_path):
        orch = self._make_orch(tmp_path)

        # Mock OrchestratorLoop.start_async to return a sim_id immediately
        with patch("ese.orchestrator.evolve.OrchestratorLoop") as MockLoop:
            mock_loop_instance = MockLoop.return_value
            mock_loop_instance.start_async = AsyncMock(return_value="re-sim-123")

            # Mock DB queries
            orch.db.get_hypotheses = MagicMock(return_value=[
                {
                    "character_fidelity_score": 0.7,
                    "fandom_resonance_score": 0.6,
                    "emergence_score": 0.5,
                    "diversity_score": 0.4,
                    "plausibility_score": 0.6,
                }
            ])
            orch.db.get_simulation = MagicMock(return_value={
                "total_cost_usd": 0.25,
                "turns": 5,
            })

            result = await orch._run_re_simulate_step(
                cycle=1,
                topic="test topic",
                original_score=0.50,
            )

        assert isinstance(result, ReSimulateResult)
        assert result.cycle == 1
        assert result.topic == "test topic"
        assert result.simulation_id == "re-sim-123"
        assert result.original_score == pytest.approx(0.50)
        assert result.re_simulate_score > 0  # computed from mocked hypotheses
        assert result.failed is False

    @pytest.mark.asyncio
    async def test_re_simulate_uses_half_budget(self, tmp_path):
        """OrchestratorLoop must be constructed with ½ node_years and ½ cost."""
        orch = self._make_orch(tmp_path)

        captured_kwargs: dict = {}

        def capture_loop(*args, **kwargs):
            captured_kwargs.update(kwargs)
            mock = MagicMock()
            mock.start_async = AsyncMock(return_value="sim-abc")
            return mock

        with patch("ese.orchestrator.evolve.OrchestratorLoop", side_effect=capture_loop):
            orch.db.get_hypotheses = MagicMock(return_value=[])
            orch.db.get_simulation = MagicMock(return_value={"total_cost_usd": 0.1})

            await orch._run_re_simulate_step(
                cycle=1,
                topic="test",
                original_score=0.5,
                updated_cfg=orch.cfg,
            )

        expected_node_years = max(10, orch.cfg.node_years // 2)
        expected_cost = max(0.1, orch.cfg.cost_limit_per_cycle * 0.5)

        assert captured_kwargs.get("node_years") == expected_node_years
        assert captured_kwargs.get("cost_limit") == pytest.approx(expected_cost)

    @pytest.mark.asyncio
    async def test_re_simulate_handles_exception(self, tmp_path):
        """If the simulation raises, re_simulate_result.failed is True."""
        orch = self._make_orch(tmp_path)

        with patch("ese.orchestrator.evolve.OrchestratorLoop") as MockLoop:
            mock_loop_instance = MockLoop.return_value
            mock_loop_instance.start_async = AsyncMock(
                side_effect=RuntimeError("sim crashed")
            )

            result = await orch._run_re_simulate_step(
                cycle=2,
                topic="crash topic",
                original_score=0.6,
            )

        assert result.failed is True
        assert "sim crashed" in result.error_message
        assert result.re_simulate_score == pytest.approx(0.0)

    @pytest.mark.asyncio
    async def test_re_simulate_no_evaluated_nodes(self, tmp_path):
        """When no hypotheses are evaluated, re_simulate_score stays 0."""
        orch = self._make_orch(tmp_path)

        with patch("ese.orchestrator.evolve.OrchestratorLoop") as MockLoop:
            mock_loop_instance = MockLoop.return_value
            mock_loop_instance.start_async = AsyncMock(return_value="sim-empty")
            orch.db.get_hypotheses = MagicMock(return_value=[])
            orch.db.get_simulation = MagicMock(return_value={"total_cost_usd": 0.05})

            result = await orch._run_re_simulate_step(
                cycle=1, topic="empty", original_score=0.5,
            )

        assert result.re_simulate_score == pytest.approx(0.0)
        assert result.nodes_explored == 0
        assert result.failed is False

    @pytest.mark.asyncio
    async def test_re_simulate_uses_updated_cfg_params(self, tmp_path):
        """updated_cfg overrides self.cfg for the re-simulation."""
        orch = self._make_orch(tmp_path)

        updated_cfg = EvolveConfig(
            initial_topic="test",
            node_years=200,
            max_depth=4,
            cost_limit_per_cycle=8.0,
            output_dir=tmp_path,
        )

        captured_kwargs: dict = {}

        def capture_loop(*args, **kwargs):
            captured_kwargs.update(kwargs)
            mock = MagicMock()
            mock.start_async = AsyncMock(return_value="sim-upd")
            return mock

        with patch("ese.orchestrator.evolve.OrchestratorLoop", side_effect=capture_loop):
            orch.db.get_hypotheses = MagicMock(return_value=[])
            orch.db.get_simulation = MagicMock(return_value={"total_cost_usd": 0.1})

            await orch._run_re_simulate_step(
                cycle=1,
                topic="test",
                original_score=0.5,
                updated_cfg=updated_cfg,
            )

        # Should use ½ of updated_cfg.node_years (200 // 2 = 100)
        assert captured_kwargs.get("node_years") == max(10, 200 // 2)
        assert captured_kwargs.get("max_depth") == 4


# --------------------------------------------------------------------------- #
# EvolveOrchestrator — _write_final_report content
# --------------------------------------------------------------------------- #


class TestFinalReport:
    def _make_state_with_history(
        self,
        tmp_path: Path,
        include_re_sim: bool = False,
    ) -> tuple[EvolveOrchestrator, EvolveState]:
        cfg = EvolveConfig(
            initial_topic="Test topic",
            max_iterations=3,
            convergence_patience=3,
            convergence_threshold=0.05,
            output_dir=tmp_path,
            enable_re_simulate=include_re_sim,
        )
        orch = EvolveOrchestrator(cfg)
        state = EvolveState(config=cfg)
        state.termination_reason = "max_iterations=3 reached"

        for i in range(1, 4):
            rs = None
            if include_re_sim:
                rs = ReSimulateResult(
                    cycle=i,
                    topic=f"topic-{i}",
                    simulation_id=f"re-sim-{i}",
                    original_score=0.4 + i * 0.1,
                    re_simulate_score=0.4 + i * 0.1 + 0.05,
                    cost_usd=0.1,
                    nodes_explored=2,
                )
            r = EvolveCycleResult(
                cycle=i,
                topic=f"topic-{i}",
                simulation_id=f"sim-{i}",
                best_hypothesis_title=f"Hypothesis {i}",
                best_composite_score=0.4 + i * 0.1,
                avg_character_fidelity_score=0.5,
                avg_fandom_resonance_score=0.4,
                avg_emergence_score=0.5,
                avg_diversity_score=0.3,
                avg_plausibility_score=0.6,
                cost_usd=0.5,
                nodes_explored=3,
                turns_simulated=10,
                re_simulate_result=rs,
            )
            state.record(r)
            if rs is not None:
                # Direct append (mirrors what run_async does)
                pass  # already appended via record()

        return orch, state

    @pytest.mark.asyncio
    async def test_report_file_created(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        await orch._write_final_report(state)

        reports = list(tmp_path.glob("evolve_report_*.md"))
        assert len(reports) == 1

    @pytest.mark.asyncio
    async def test_report_contains_cycle_history(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Cycle History" in report_text
        assert "topic-1" in report_text
        assert "topic-2" in report_text
        assert "topic-3" in report_text

    @pytest.mark.asyncio
    async def test_report_contains_convergence_analysis(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Convergence Analysis" in report_text
        assert "Termination reason" in report_text

    @pytest.mark.asyncio
    async def test_report_contains_score_delta_trend(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Score Delta Trend" in report_text

    @pytest.mark.asyncio
    async def test_report_contains_re_simulate_section_when_present(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path, include_re_sim=True)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Re-Simulate Comparison" in report_text
        assert "Re-Sim" in report_text

    @pytest.mark.asyncio
    async def test_report_no_re_simulate_section_when_absent(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path, include_re_sim=False)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        # Re-simulate section should not appear
        assert "Re-Simulate Comparison" not in report_text

    @pytest.mark.asyncio
    async def test_report_contains_best_cycle(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Best Cycle" in report_text

    @pytest.mark.asyncio
    async def test_report_skipped_with_no_successful_cycles(self, tmp_path):
        cfg = EvolveConfig(initial_topic="t", output_dir=tmp_path)
        orch = EvolveOrchestrator(cfg)
        state = EvolveState(config=cfg)
        state.termination_reason = "consecutive_failures"

        await orch._write_final_report(state)
        # No report file should be created
        assert not list(tmp_path.glob("evolve_report_*.md"))

    @pytest.mark.asyncio
    async def test_report_convergence_analysis_marks_converged_correctly(self, tmp_path):
        orch, state = self._make_state_with_history(tmp_path)
        state.termination_reason = "converged: no improvement > 0.050 for 3 consecutive cycles"
        await orch._write_final_report(state)

        report_text = next(tmp_path.glob("evolve_report_*.md")).read_text(encoding="utf-8")
        assert "Yes" in report_text  # Converged = Yes


# --------------------------------------------------------------------------- #
# CLI -- --re-simulate flag
# --------------------------------------------------------------------------- #


class TestCLIReSimulateFlag:
    def test_re_simulate_flag_in_evolve_help(self):
        from click.testing import CliRunner
        from ese.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["evolve", "--help"])
        assert result.exit_code == 0
        assert "--re-simulate" in result.output

    def test_evolve_dry_run_with_re_simulate_flag(self, tmp_path):
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
                "--re-simulate",
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output

    def test_evolve_dry_run_with_both_improve_and_re_simulate(self, tmp_path):
        from click.testing import CliRunner
        from ese.main import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "evolve",
                "Combined flags test",
                "--dry-run",
                "--improve",
                "--re-simulate",
                "--output-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 0, result.output


# --------------------------------------------------------------------------- #
# Integration: dry-run loop with enable_re_simulate
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_dry_run_with_re_simulate_flag(tmp_path):
    """enable_re_simulate=True in dry-run should have zero history."""
    cfg = EvolveConfig(
        initial_topic="Dry run re-simulate",
        max_iterations=3,
        dry_run=True,
        enable_re_simulate=True,
        output_dir=tmp_path,
    )
    orch = EvolveOrchestrator(cfg)
    state = await orch.run_async()

    assert state.termination_reason == "dry_run"
    assert len(state.history) == 0
    assert len(state.re_simulate_history) == 0


@pytest.mark.asyncio
async def test_state_re_simulate_history_json_serializable(tmp_path):
    """All re_simulate_history entries must be JSON-serializable."""
    state = EvolveState(config=_make_config())

    for i in range(1, 4):
        rs = ReSimulateResult(
            cycle=i, topic=f"t{i}", simulation_id=f"s{i}",
            original_score=0.5, re_simulate_score=0.55,
        )
        r = _make_result(i, score=0.5, re_sim=rs)
        state.record(r)

    for rs in state.re_simulate_history:
        json.dumps(rs.to_dict())  # must not raise
