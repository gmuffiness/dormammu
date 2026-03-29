"""Tests for benchmark and diagnose stages (Sub-AC 3b).

Covers:
- _aggregate_scores: with evaluated hypotheses, unevaluated, and mixed
- _collect_per_node_metrics: ordering, field presence
- _detect_bottlenecks: low-score nodes, unevaluated, depth trend, high-cost turns
- _collect_turn_stats: totals, averages, edge cases (empty, single turn)
- diagnose: weakest dimension detection, returns structured dict
- detect_failure_patterns: placeholder detection, unevaluated nodes, low coverage
- detect_bottleneck_suggestions: depth degradation, high cost, low score nodes
- CLI smoke tests: benchmark and diagnose commands exist
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


# --------------------------------------------------------------------------- #
# Helpers to build fixture data
# --------------------------------------------------------------------------- #


def _make_hyp(
    node_id: str = "n1",
    title: str = "Test Hypothesis",
    depth: int = 1,
    character_fidelity: float | None = 0.6,
    fandom_resonance: float | None = 0.5,
    emergence: float | None = 0.6,
    diversity: float | None = 0.5,
    plausibility: float | None = 0.7,
    probability: float = 0.8,
    sf_inspired: bool = False,
) -> dict:
    """Build a minimal hypothesis row as returned by Database.get_hypotheses()."""
    return {
        "node_id": node_id,
        "simulation_id": "sim-test",
        "parent_id": "",
        "depth": depth,
        "title": title,
        "description": "A test branch.",
        "probability": probability,
        "tags_json": "[]",
        "sf_inspired": int(sf_inspired),
        "character_fidelity_score": character_fidelity,
        "fandom_resonance_score": fandom_resonance,
        "emergence_score": emergence,
        "diversity_score": diversity,
        "plausibility_score": plausibility,
        "created_at": "2026-01-01T00:00:00",
    }


def _make_turn(
    turn_number: int = 1,
    year: int = 1,
    cost_usd: float = 0.01,
    tokens_used: int = 500,
) -> dict:
    """Build a minimal turn row as returned by Database.get_turns()."""
    return {
        "id": turn_number,
        "simulation_id": "sim-test",
        "turn_number": turn_number,
        "year": year,
        "narrative": "Something happened.",
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "events_json": "[]",
        "agent_actions_json": "{}",
        "created_at": "2026-01-01T00:00:00",
    }


def _make_report(
    scores: dict | None = None,
    per_node: list | None = None,
    bottlenecks: dict | None = None,
    turn_stats: dict | None = None,
    metadata: dict | None = None,
    placeholder: bool = False,
) -> dict:
    """Build a benchmark report dict for diagnose tests."""
    default_scores = {
        "avg_character_fidelity": 0.6,
        "avg_fandom_resonance": 0.5,
        "avg_emergence": 0.6,
        "avg_diversity": 0.4,
        "avg_plausibility": 0.7,
        "avg_composite": 0.55,
    }
    return {
        "timestamp": "2026-01-01T00:00:00+00:00",
        "git_hash": "abc1234",
        "scores": scores if scores is not None else default_scores,
        "per_node_metrics": per_node if per_node is not None else [],
        "bottlenecks": bottlenecks
        if bottlenecks is not None
        else {
            "low_score_nodes": [],
            "unevaluated_nodes": [],
            "high_cost_turns": [],
            "depth_score_trend": {},
            "summary": "No bottlenecks detected.",
        },
        "turn_stats": turn_stats
        if turn_stats is not None
        else {
            "total_turns": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "avg_cost_per_turn": 0.0,
            "avg_tokens_per_turn": 0.0,
            "max_cost_turn": None,
            "min_cost_turn": None,
        },
        "metadata": metadata
        if metadata is not None
        else {
            "topic": "Test",
            "simulation_id": "sim-1",
            "placeholder": placeholder,
        },
    }


# --------------------------------------------------------------------------- #
# _aggregate_scores
# --------------------------------------------------------------------------- #


class TestAggregateScores:
    """Tests for benchmark._aggregate_scores."""

    def test_all_evaluated(self):
        from ese.benchmark import _aggregate_scores

        hyps = [
            _make_hyp("n1", character_fidelity=0.8, fandom_resonance=0.6, emergence=0.4, diversity=0.4, plausibility=0.2),
            _make_hyp("n2", character_fidelity=0.4, fandom_resonance=0.2, emergence=0.6, diversity=0.6, plausibility=0.8),
        ]
        scores = _aggregate_scores(hyps)

        assert scores["avg_character_fidelity"] == pytest.approx(0.6, abs=1e-4)
        assert scores["avg_fandom_resonance"] == pytest.approx(0.4, abs=1e-4)
        assert scores["avg_emergence"] == pytest.approx(0.5, abs=1e-4)
        assert scores["avg_diversity"] == pytest.approx(0.5, abs=1e-4)
        assert scores["avg_plausibility"] == pytest.approx(0.5, abs=1e-4)
        # composite must be in [0, 1]
        assert 0.0 <= scores["avg_composite"] <= 1.0

    def test_no_evaluated_returns_placeholder(self):
        from ese.benchmark import _aggregate_scores

        hyps = [
            _make_hyp("n1", character_fidelity=None, fandom_resonance=None, emergence=None, diversity=None, plausibility=None),
        ]
        scores = _aggregate_scores(hyps)

        for key in ("avg_character_fidelity", "avg_fandom_resonance", "avg_emergence", "avg_diversity", "avg_plausibility", "avg_composite"):
            assert scores[key] == pytest.approx(0.5, abs=1e-4)

    def test_empty_returns_placeholder(self):
        from ese.benchmark import _aggregate_scores

        scores = _aggregate_scores([])
        for key in ("avg_character_fidelity", "avg_fandom_resonance", "avg_emergence", "avg_diversity", "avg_plausibility", "avg_composite"):
            assert scores[key] == pytest.approx(0.5, abs=1e-4)

    def test_mixed_evaluated_and_unevaluated(self):
        """Only evaluated nodes (emergence_score not None) contribute to averages."""
        from ese.benchmark import _aggregate_scores

        hyps = [
            _make_hyp("n1", character_fidelity=1.0, fandom_resonance=1.0, emergence=1.0, diversity=1.0, plausibility=1.0),
            _make_hyp("n2", character_fidelity=None, fandom_resonance=None, emergence=None, diversity=None, plausibility=None),
        ]
        scores = _aggregate_scores(hyps)

        assert scores["avg_character_fidelity"] == pytest.approx(1.0, abs=1e-4)
        assert scores["avg_emergence"] == pytest.approx(1.0, abs=1e-4)

    def test_composite_weights(self):
        """avg_composite follows 0.25/0.20/0.20/0.15/0.20 weighting."""
        from ese.benchmark import _aggregate_scores

        # Single node with all 1s → composite = 1.0
        hyps = [_make_hyp("n1", character_fidelity=1.0, fandom_resonance=1.0, emergence=1.0, diversity=1.0, plausibility=1.0)]
        scores = _aggregate_scores(hyps)
        assert scores["avg_composite"] == pytest.approx(1.0, abs=1e-4)

        # Single node with all 0s → composite = 0.0
        hyps = [_make_hyp("n1", character_fidelity=0.0, fandom_resonance=0.0, emergence=0.0, diversity=0.0, plausibility=0.0)]
        scores = _aggregate_scores(hyps)
        assert scores["avg_composite"] == pytest.approx(0.0, abs=1e-4)

    def test_single_node_exact_values(self):
        """Exact weights: character_fidelity=0.25, fandom_resonance=0.20, emergence=0.20, diversity=0.15, plausibility=0.20."""
        from ese.benchmark import _aggregate_scores

        hyps = [_make_hyp("n1", character_fidelity=1.0, fandom_resonance=0.0, emergence=0.0, diversity=0.0, plausibility=0.0)]
        scores = _aggregate_scores(hyps)
        assert scores["avg_composite"] == pytest.approx(0.25, abs=1e-4)


# --------------------------------------------------------------------------- #
# _collect_per_node_metrics
# --------------------------------------------------------------------------- #


class TestCollectPerNodeMetrics:
    """Tests for benchmark._collect_per_node_metrics."""

    def test_returns_all_nodes(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [_make_hyp("n1"), _make_hyp("n2")]
        nodes = _collect_per_node_metrics(hyps)
        assert len(nodes) == 2

    def test_evaluated_flag(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [
            _make_hyp("n1", emergence=0.7),
            _make_hyp("n2", emergence=None),
        ]
        nodes = _collect_per_node_metrics(hyps)
        evaluated = [n for n in nodes if n["evaluated"]]
        unevaluated = [n for n in nodes if not n["evaluated"]]
        assert len(evaluated) == 1
        assert len(unevaluated) == 1

    def test_sorted_best_first(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [
            _make_hyp("n1", emergence=0.1, narrative=0.1, diversity=0.1, novelty=0.1),
            _make_hyp("n2", emergence=0.9, narrative=0.9, diversity=0.9, novelty=0.9),
        ]
        nodes = _collect_per_node_metrics(hyps)
        assert nodes[0]["node_id"] == "n2"
        assert nodes[1]["node_id"] == "n1"

    def test_unevaluated_nodes_sorted_after_evaluated(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [
            _make_hyp("n1", emergence=None),
            _make_hyp("n2", emergence=0.8),
        ]
        nodes = _collect_per_node_metrics(hyps)
        assert nodes[0]["evaluated"] is True
        assert nodes[1]["evaluated"] is False

    def test_composite_score_none_for_unevaluated(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [_make_hyp("n1", emergence=None)]
        nodes = _collect_per_node_metrics(hyps)
        assert nodes[0]["composite_score"] is None

    def test_field_presence(self):
        from ese.benchmark import _collect_per_node_metrics

        hyps = [_make_hyp("n1")]
        nodes = _collect_per_node_metrics(hyps)
        required_fields = {
            "node_id", "title", "depth", "evaluated",
            "character_fidelity_score", "fandom_resonance_score",
            "emergence_score", "diversity_score", "plausibility_score",
            "composite_score", "probability", "sf_inspired",
        }
        assert required_fields.issubset(set(nodes[0].keys()))

    def test_empty_input(self):
        from ese.benchmark import _collect_per_node_metrics

        assert _collect_per_node_metrics([]) == []


# --------------------------------------------------------------------------- #
# _detect_bottlenecks
# --------------------------------------------------------------------------- #


class TestDetectBottlenecks:
    """Tests for benchmark._detect_bottlenecks."""

    def test_no_bottlenecks(self):
        from ese.benchmark import _detect_bottlenecks

        hyps = [_make_hyp("n1", character_fidelity=0.8, fandom_resonance=0.8, emergence=0.8, diversity=0.8, plausibility=0.8)]
        turns = [_make_turn(1, cost_usd=0.005)]
        result = _detect_bottlenecks(hyps, turns)

        assert result["low_score_nodes"] == []
        assert result["unevaluated_nodes"] == []
        assert result["summary"] == "No bottlenecks detected."

    def test_detects_low_score_nodes(self):
        from ese.benchmark import _detect_bottlenecks

        hyps = [
            _make_hyp("n1", character_fidelity=0.1, fandom_resonance=0.1, emergence=0.1, diversity=0.1, plausibility=0.1),
        ]
        result = _detect_bottlenecks(hyps, [])
        assert len(result["low_score_nodes"]) == 1
        assert result["low_score_nodes"][0]["node_id"] == "n1"
        assert "low_score_nodes" in result["summary"] or "0.4" in result["summary"]

    def test_detects_unevaluated_nodes(self):
        from ese.benchmark import _detect_bottlenecks

        hyps = [_make_hyp("n1", emergence=None, character_fidelity=None, fandom_resonance=None, diversity=None, plausibility=None)]
        result = _detect_bottlenecks(hyps, [])
        assert len(result["unevaluated_nodes"]) == 1
        assert result["unevaluated_nodes"][0]["node_id"] == "n1"

    def test_high_cost_turns_top_3(self):
        from ese.benchmark import _detect_bottlenecks

        turns = [
            _make_turn(1, cost_usd=0.01),
            _make_turn(2, cost_usd=0.10),
            _make_turn(3, cost_usd=0.05),
            _make_turn(4, cost_usd=0.03),
            _make_turn(5, cost_usd=0.02),
        ]
        result = _detect_bottlenecks([], turns)
        # Top 3 by cost
        assert len(result["high_cost_turns"]) == 3
        assert result["high_cost_turns"][0]["turn_number"] == 2

    def test_depth_score_trend(self):
        from ese.benchmark import _detect_bottlenecks

        hyps = [
            _make_hyp("n1", depth=0, character_fidelity=0.9, fandom_resonance=0.9, emergence=0.9, diversity=0.9, plausibility=0.9),
            _make_hyp("n2", depth=1, character_fidelity=0.1, fandom_resonance=0.1, emergence=0.1, diversity=0.1, plausibility=0.1),
        ]
        result = _detect_bottlenecks(hyps, [])
        trend = result["depth_score_trend"]
        assert 0 in trend and 1 in trend
        assert trend[0] > trend[1]
        # Degradation should be mentioned in summary
        assert "depth" in result["summary"].lower() or len(result["summary"]) > 0

    def test_depth_trend_single_depth(self):
        from ese.benchmark import _detect_bottlenecks

        hyps = [_make_hyp("n1", depth=1, character_fidelity=0.5, fandom_resonance=0.5, emergence=0.5, diversity=0.5, plausibility=0.5)]
        result = _detect_bottlenecks(hyps, [])
        assert 1 in result["depth_score_trend"]

    def test_empty_inputs(self):
        from ese.benchmark import _detect_bottlenecks

        result = _detect_bottlenecks([], [])
        assert result["low_score_nodes"] == []
        assert result["unevaluated_nodes"] == []
        assert result["high_cost_turns"] == []
        assert result["depth_score_trend"] == {}


# --------------------------------------------------------------------------- #
# _collect_turn_stats
# --------------------------------------------------------------------------- #


class TestCollectTurnStats:
    """Tests for benchmark._collect_turn_stats."""

    def test_empty_turns(self):
        from ese.benchmark import _collect_turn_stats

        stats = _collect_turn_stats([])
        assert stats["total_turns"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["total_tokens"] == 0

    def test_single_turn(self):
        from ese.benchmark import _collect_turn_stats

        turns = [_make_turn(1, cost_usd=0.05, tokens_used=1000)]
        stats = _collect_turn_stats(turns)

        assert stats["total_turns"] == 1
        assert stats["total_cost_usd"] == pytest.approx(0.05)
        assert stats["total_tokens"] == 1000
        assert stats["avg_cost_per_turn"] == pytest.approx(0.05)
        assert stats["avg_tokens_per_turn"] == pytest.approx(1000.0)

    def test_multiple_turns(self):
        from ese.benchmark import _collect_turn_stats

        turns = [
            _make_turn(1, cost_usd=0.01, tokens_used=200),
            _make_turn(2, cost_usd=0.03, tokens_used=600),
            _make_turn(3, cost_usd=0.02, tokens_used=400),
        ]
        stats = _collect_turn_stats(turns)

        assert stats["total_turns"] == 3
        assert stats["total_cost_usd"] == pytest.approx(0.06)
        assert stats["total_tokens"] == 1200
        assert stats["avg_cost_per_turn"] == pytest.approx(0.02)
        assert stats["avg_tokens_per_turn"] == pytest.approx(400.0)

    def test_max_cost_turn_identified(self):
        from ese.benchmark import _collect_turn_stats

        turns = [
            _make_turn(1, cost_usd=0.01),
            _make_turn(2, cost_usd=0.09),
            _make_turn(3, cost_usd=0.03),
        ]
        stats = _collect_turn_stats(turns)
        assert stats["max_cost_turn"]["turn_number"] == 2
        assert stats["max_cost_turn"]["cost_usd"] == pytest.approx(0.09)

    def test_none_cost_treated_as_zero(self):
        from ese.benchmark import _collect_turn_stats

        turns = [
            {"turn_number": 1, "year": 1, "cost_usd": None, "tokens_used": 300},
        ]
        stats = _collect_turn_stats(turns)
        assert stats["total_cost_usd"] == pytest.approx(0.0)

    def test_stats_are_json_serializable(self):
        from ese.benchmark import _collect_turn_stats

        turns = [_make_turn(1), _make_turn(2)]
        stats = _collect_turn_stats(turns)
        serialized = json.dumps(stats)
        restored = json.loads(serialized)
        assert restored["total_turns"] == 2


# --------------------------------------------------------------------------- #
# detect_failure_patterns
# --------------------------------------------------------------------------- #


class TestDetectFailurePatterns:
    """Tests for diagnose.detect_failure_patterns."""

    def test_no_failures(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.7,
                "avg_fandom_resonance": 0.6,
                "avg_emergence": 0.7,
                "avg_diversity": 0.65,
                "avg_plausibility": 0.55,
                "avg_composite": 0.64,
            },
            per_node=[{"evaluated": True}, {"evaluated": True}],
        )
        patterns = detect_failure_patterns(report)
        assert patterns == []

    def test_detects_placeholder_scores(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.5,
                "avg_fandom_resonance": 0.5,
                "avg_emergence": 0.5,
                "avg_diversity": 0.5,
                "avg_plausibility": 0.5,
                "avg_composite": 0.5,
            }
        )
        patterns = detect_failure_patterns(report)
        assert any("0.5" in p or "placeholder" in p.lower() for p in patterns)

    def test_detects_unevaluated_nodes(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report(
            bottlenecks={
                "unevaluated_nodes": [{"node_id": "n1", "title": "Test", "depth": 1}],
                "low_score_nodes": [],
                "high_cost_turns": [],
                "depth_score_trend": {},
                "summary": "",
            }
        )
        patterns = detect_failure_patterns(report)
        assert any("not evaluated" in p or "unevaluated" in p.lower() for p in patterns)

    def test_detects_zero_evaluation_coverage(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report(
            per_node=[
                {"evaluated": False},
                {"evaluated": False},
                {"evaluated": False},
            ]
        )
        patterns = detect_failure_patterns(report)
        assert any("none" in p.lower() or "0/" in p or "evaluated" in p.lower() for p in patterns)

    def test_detects_low_coverage(self):
        from ese.diagnose import detect_failure_patterns

        # 1 evaluated out of 4 = 25% coverage
        report = _make_report(
            per_node=[
                {"evaluated": True},
                {"evaluated": False},
                {"evaluated": False},
                {"evaluated": False},
            ]
        )
        patterns = detect_failure_patterns(report)
        assert any("coverage" in p.lower() or "only" in p.lower() for p in patterns)

    def test_detects_placeholder_metadata_flag(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report(placeholder=True)
        patterns = detect_failure_patterns(report)
        assert any("placeholder" in p.lower() for p in patterns)

    def test_returns_list(self):
        from ese.diagnose import detect_failure_patterns

        report = _make_report()
        result = detect_failure_patterns(report)
        assert isinstance(result, list)


# --------------------------------------------------------------------------- #
# detect_bottleneck_suggestions
# --------------------------------------------------------------------------- #


class TestDetectBottleneckSuggestions:
    """Tests for diagnose.detect_bottleneck_suggestions."""

    def test_no_bottlenecks(self):
        from ese.diagnose import detect_bottleneck_suggestions

        report = _make_report()
        suggestions = detect_bottleneck_suggestions(report)
        assert suggestions == []

    def test_unevaluated_nodes_suggestion(self):
        from ese.diagnose import detect_bottleneck_suggestions

        report = _make_report(
            bottlenecks={
                "unevaluated_nodes": [{"node_id": "n1", "title": "T", "depth": 1}],
                "low_score_nodes": [],
                "high_cost_turns": [],
                "depth_score_trend": {},
                "summary": "",
            }
        )
        suggestions = detect_bottleneck_suggestions(report)
        assert len(suggestions) >= 1
        assert any("cost" in s.lower() or "limit" in s.lower() for s in suggestions)

    def test_low_score_nodes_suggestion(self):
        from ese.diagnose import detect_bottleneck_suggestions

        report = _make_report(
            bottlenecks={
                "unevaluated_nodes": [],
                "low_score_nodes": [{"node_id": "n1", "composite_score": 0.2}],
                "high_cost_turns": [],
                "depth_score_trend": {},
                "summary": "",
            }
        )
        suggestions = detect_bottleneck_suggestions(report)
        assert len(suggestions) >= 1

    def test_depth_degradation_suggestion(self):
        from ese.diagnose import detect_bottleneck_suggestions

        # Depth 0 → 0.9, depth 1 → 0.7 (< 0.1 drop, no suggestion)
        report_no_degrade = _make_report(
            bottlenecks={
                "unevaluated_nodes": [],
                "low_score_nodes": [],
                "high_cost_turns": [],
                "depth_score_trend": {0: 0.9, 1: 0.85},
                "summary": "",
            }
        )
        # Depth 0 → 0.9, depth 1 → 0.7 (0.2 drop → degradation)
        report_degrade = _make_report(
            bottlenecks={
                "unevaluated_nodes": [],
                "low_score_nodes": [],
                "high_cost_turns": [],
                "depth_score_trend": {0: 0.9, 1: 0.7},
                "summary": "",
            }
        )
        s_no = detect_bottleneck_suggestions(report_no_degrade)
        s_yes = detect_bottleneck_suggestions(report_degrade)
        assert not any("deeper" in s.lower() or "depth" in s.lower() for s in s_no)
        assert any("deeper" in s.lower() or "depth" in s.lower() for s in s_yes)

    def test_high_cost_turn_suggestion(self):
        from ese.diagnose import detect_bottleneck_suggestions

        report = _make_report(
            bottlenecks={
                "unevaluated_nodes": [],
                "low_score_nodes": [],
                "high_cost_turns": [{"turn_number": 2, "cost_usd": 0.12, "tokens_used": 8000}],
                "depth_score_trend": {},
                "summary": "",
            }
        )
        suggestions = detect_bottleneck_suggestions(report)
        assert any("cost" in s.lower() or "prompt" in s.lower() for s in suggestions)

    def test_returns_list(self):
        from ese.diagnose import detect_bottleneck_suggestions

        assert isinstance(detect_bottleneck_suggestions(_make_report()), list)


# --------------------------------------------------------------------------- #
# diagnose (end-to-end)
# --------------------------------------------------------------------------- #


class TestDiagnose:
    """Tests for diagnose.diagnose()."""

    def test_identifies_weakest_dimension(self):
        from ese.diagnose import diagnose

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.8,
                "avg_fandom_resonance": 0.7,
                "avg_emergence": 0.8,
                "avg_diversity": 0.3,  # lowest
                "avg_plausibility": 0.6,
                "avg_composite": 0.65,
            }
        )
        result = diagnose(report)
        assert result["weakest_dimension"] == "Diversity"
        assert result["score"] == pytest.approx(0.3, abs=1e-4)

    def test_emergence_weakest(self):
        from ese.diagnose import diagnose

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.8,
                "avg_fandom_resonance": 0.8,
                "avg_emergence": 0.2,
                "avg_diversity": 0.7,
                "avg_plausibility": 0.6,
                "avg_composite": 0.6,
            }
        )
        result = diagnose(report)
        assert result["weakest_dimension"] == "Emergence"
        assert "turn.py" in result["target_module"]

    def test_plausibility_weakest(self):
        from ese.diagnose import diagnose

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.7,
                "avg_fandom_resonance": 0.7,
                "avg_emergence": 0.7,
                "avg_diversity": 0.7,
                "avg_plausibility": 0.1,
                "avg_composite": 0.6,
            }
        )
        result = diagnose(report)
        assert result["weakest_dimension"] == "Plausibility"
        assert "evaluator.py" in result["target_module"]

    def test_character_fidelity_weakest(self):
        from ese.diagnose import diagnose

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.2,
                "avg_fandom_resonance": 0.8,
                "avg_emergence": 0.8,
                "avg_diversity": 0.8,
                "avg_plausibility": 0.8,
                "avg_composite": 0.7,
            }
        )
        result = diagnose(report)
        assert result["weakest_dimension"] == "Character Fidelity"

    def test_composite_excluded_from_weakest(self):
        """avg_composite must not be chosen as weakest_dimension."""
        from ese.diagnose import diagnose

        report = _make_report(
            scores={
                "avg_character_fidelity": 0.5,
                "avg_fandom_resonance": 0.5,
                "avg_emergence": 0.5,
                "avg_diversity": 0.5,
                "avg_plausibility": 0.5,
                "avg_composite": 0.1,  # lowest but should be excluded
            }
        )
        result = diagnose(report)
        assert result["weakest_dimension"] != "Composite Score"

    def test_returns_required_keys(self):
        from ese.diagnose import diagnose

        result = diagnose(_make_report())
        required = {
            "weakest_dimension",
            "score",
            "target_module",
            "target_method",
            "suggestion",
            "failure_patterns",
            "bottleneck_suggestions",
        }
        assert required.issubset(set(result.keys()))

    def test_no_scores_returns_unknown(self):
        from ese.diagnose import diagnose

        report = _make_report(scores={})
        result = diagnose(report)
        assert result["weakest_dimension"] == "unknown"
        assert "benchmark" in result["suggestion"].lower()

    def test_failure_patterns_included(self):
        from ese.diagnose import diagnose

        # Placeholder scores → failure pattern expected
        report = _make_report(
            scores={
                "avg_character_fidelity": 0.5,
                "avg_fandom_resonance": 0.5,
                "avg_emergence": 0.5,
                "avg_diversity": 0.5,
                "avg_plausibility": 0.5,
                "avg_composite": 0.5,
            }
        )
        result = diagnose(report)
        assert isinstance(result["failure_patterns"], list)
        assert len(result["failure_patterns"]) >= 1

    def test_bottleneck_suggestions_included(self):
        from ese.diagnose import diagnose

        report = _make_report(
            bottlenecks={
                "unevaluated_nodes": [{"node_id": "n1", "title": "T", "depth": 1}],
                "low_score_nodes": [],
                "high_cost_turns": [],
                "depth_score_trend": {},
                "summary": "",
            }
        )
        result = diagnose(report)
        assert isinstance(result["bottleneck_suggestions"], list)
        assert len(result["bottleneck_suggestions"]) >= 1

    def test_result_is_json_serializable(self):
        from ese.diagnose import diagnose

        result = diagnose(_make_report())
        serialized = json.dumps(result)
        restored = json.loads(serialized)
        assert restored["weakest_dimension"] == result["weakest_dimension"]


# --------------------------------------------------------------------------- #
# load_latest_benchmark
# --------------------------------------------------------------------------- #


class TestLoadLatestBenchmark:
    """Tests for diagnose.load_latest_benchmark."""

    def test_returns_none_when_no_benchmarks(self, tmp_path, monkeypatch):
        from ese.diagnose import load_latest_benchmark
        from ese import config as config_module

        # Point config.data_dir to tmp_path so benchmarks dir doesn't exist
        monkeypatch.setattr(
            config_module.config, "data_dir", tmp_path / "simulations"
        )
        result = load_latest_benchmark()
        assert result is None

    def test_loads_latest_file(self, tmp_path, monkeypatch):
        from ese.diagnose import load_latest_benchmark
        from ese import config as config_module

        # _benchmarks_dir() = config.data_dir.parent / "data" / "benchmarks"
        # So set data_dir = tmp_path / "simulations", then benchmarks_dir =
        # tmp_path / "data" / "benchmarks"
        simulations_dir = tmp_path / "simulations"
        simulations_dir.mkdir(parents=True)
        benchmarks_dir = tmp_path / "data" / "benchmarks"
        benchmarks_dir.mkdir(parents=True)

        # Create two fake benchmark files
        report_old = {"timestamp": "2026-01-01", "git_hash": "aaa", "scores": {}}
        report_new = {"timestamp": "2026-06-01", "git_hash": "bbb", "scores": {}}
        (benchmarks_dir / "benchmark_2026-01-01T00-00-00.json").write_text(
            json.dumps(report_old)
        )
        (benchmarks_dir / "benchmark_2026-06-01T00-00-00.json").write_text(
            json.dumps(report_new)
        )

        # Monkeypatch config.data_dir so _benchmarks_dir() resolves correctly:
        # data_dir.parent = tmp_path → tmp_path / "data" / "benchmarks"
        monkeypatch.setattr(config_module.config, "data_dir", simulations_dir)

        result = load_latest_benchmark()
        # Should load the newest (alphabetically last) file
        assert result is not None
        assert result["git_hash"] == "bbb"


# --------------------------------------------------------------------------- #
# _placeholder_report
# --------------------------------------------------------------------------- #


class TestPlaceholderReport:
    """Tests for benchmark._placeholder_report."""

    def test_structure(self):
        from ese.benchmark import _placeholder_report

        report = _placeholder_report("2026-01-01T00:00:00+00:00", "abc1234")
        assert report["git_hash"] == "abc1234"
        assert report["metadata"]["placeholder"] is True
        assert "scores" in report
        assert "per_node_metrics" in report
        assert "bottlenecks" in report
        assert "turn_stats" in report

    def test_error_included(self):
        from ese.benchmark import _placeholder_report

        report = _placeholder_report("2026-01-01T00:00:00+00:00", "abc", error="timeout")
        assert report["metadata"]["error"] == "timeout"

    def test_scores_are_placeholder(self):
        from ese.benchmark import _placeholder_report

        report = _placeholder_report("2026-01-01T00:00:00+00:00", "abc")
        for k in ("avg_character_fidelity", "avg_fandom_resonance", "avg_emergence", "avg_diversity", "avg_plausibility"):
            assert report["scores"][k] == pytest.approx(0.5)

    def test_is_json_serializable(self):
        from ese.benchmark import _placeholder_report

        report = _placeholder_report("2026-01-01T00:00:00+00:00", "abc")
        serialized = json.dumps(report)
        restored = json.loads(serialized)
        assert restored["git_hash"] == "abc"


# --------------------------------------------------------------------------- #
# CLI smoke tests
# --------------------------------------------------------------------------- #


def test_cli_benchmark_command_exists():
    """The `benchmark` subcommand must be registered with the CLI group."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["benchmark", "--help"])
    assert result.exit_code == 0
    assert "benchmark" in result.output.lower()


def test_cli_diagnose_command_exists():
    """The `diagnose` subcommand must be registered with the CLI group."""
    from click.testing import CliRunner
    from ese.main import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["diagnose", "--help"])
    assert result.exit_code == 0
    assert "diagnose" in result.output.lower()


def test_cli_diagnose_no_benchmark(tmp_path, monkeypatch):
    """Diagnose with no benchmark file should exit with non-zero status."""
    from click.testing import CliRunner
    from ese.main import cli
    from ese import config as config_module

    monkeypatch.setattr(config_module.config, "data_dir", tmp_path / "simulations")

    runner = CliRunner()
    result = runner.invoke(cli, ["diagnose"])
    assert result.exit_code != 0
    assert "benchmark" in result.output.lower() or "No benchmark" in result.output
