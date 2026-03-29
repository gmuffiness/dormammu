"""API route handlers for the Dormammu visualization backend."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from ese.api.environment import generate_environment
from ese.api.models import (
    AgentMemory,
    AgentPosition,
    AgentState,
    EnvironmentResponse,
    Landmark,
    PathNarrative,
    PathNode,
    PathsResponse,
    ScenarioTreeResponse,
    SimulationDetail,
    SimulationExport,
    SimulationSummary,
    TreeNode,
    TurnDetail,
    TurnSummary,
    Zone,
)
from ese.storage.database import Database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


def _get_db() -> Database:
    return Database()


def _parse_json_field(value: Any, fallback: Any) -> Any:
    """Parse a JSON string field, returning fallback on failure."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return fallback
    return value if value is not None else fallback


def _parse_eval_criteria(value: Any) -> list[str]:
    parsed = _parse_json_field(value, [])
    if isinstance(parsed, list):
        return [str(x) for x in parsed]
    return []


# ------------------------------------------------------------------ #
# Simulations
# ------------------------------------------------------------------ #


@router.get("/simulations", response_model=list[SimulationSummary])
async def list_simulations(limit: int = 20) -> list[SimulationSummary]:
    """List all simulations ordered by created_at descending."""
    db = _get_db()
    rows = db.list_simulations(limit=limit)

    results = []
    for row in rows:
        # Count hypotheses/nodes for this simulation
        hyps = db.get_hypotheses(row["id"])
        results.append(
            SimulationSummary(
                id=row["id"],
                topic=row.get("topic", ""),
                status=row.get("status", ""),
                turns=row.get("turns", 0),
                nodes=len(hyps),
                cost=row.get("total_cost_usd", 0.0),
                max_depth=row.get("max_depth", 0),
                total_cost_usd=row.get("total_cost_usd", 0.0),
                created_at=row.get("created_at", ""),
            )
        )
    return results


@router.get("/simulations/{sim_id}", response_model=SimulationDetail)
async def get_simulation(sim_id: str) -> SimulationDetail:
    """Get simulation details."""
    db = _get_db()
    row = db.get_simulation(sim_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")

    return SimulationDetail(
        id=row["id"],
        topic=row.get("topic", ""),
        status=row.get("status", ""),
        turns=row.get("turns", 0),
        max_depth=row.get("max_depth", 0),
        node_years=row.get("node_years", 0),
        cost_limit=row.get("cost_limit", 0.0),
        total_cost_usd=row.get("total_cost_usd", 0.0),
        openai_model=row.get("openai_model", ""),
        current_node_id=row.get("current_node_id", ""),
        evaluation_criteria=_parse_eval_criteria(row.get("evaluation_criteria")),
        created_at=row.get("created_at", ""),
        updated_at=row.get("updated_at", ""),
    )


# ------------------------------------------------------------------ #
# Turns
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/turns", response_model=list[TurnSummary])
async def get_turns(sim_id: str) -> list[TurnSummary]:
    """Get all turns for a simulation."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)
    rows = db.get_turns(sim_id)

    return [
        TurnSummary(
            turn_number=row["turn_number"],
            year=row.get("year", 0),
            narrative=row.get("narrative", ""),
            events=_parse_json_field(row.get("events_json"), []),
            agent_actions=_parse_json_field(row.get("agent_actions_json"), {}),
            cost=row.get("cost_usd", 0.0),
        )
        for row in rows
    ]


@router.get("/simulations/{sim_id}/turns/{turn_number}", response_model=TurnDetail)
async def get_turn(sim_id: str, turn_number: int) -> TurnDetail:
    """Get a single turn with full detail including world state snapshot."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    all_turns = db.get_turns(sim_id)
    turn_row = next((r for r in all_turns if r["turn_number"] == turn_number), None)
    if turn_row is None:
        raise HTTPException(status_code=404, detail=f"Turn {turn_number} not found")

    world_state = db.get_world_state_by_turn(sim_id, turn_number)

    return TurnDetail(
        turn_number=turn_row["turn_number"],
        year=turn_row.get("year", 0),
        narrative=turn_row.get("narrative", ""),
        events=_parse_json_field(turn_row.get("events_json"), []),
        agent_actions=_parse_json_field(turn_row.get("agent_actions_json"), {}),
        cost=turn_row.get("cost_usd", 0.0),
        world_state=world_state,
    )


# ------------------------------------------------------------------ #
# Agents
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/agents", response_model=list[AgentState])
async def get_agents(sim_id: str) -> list[AgentState]:
    """Get all agents with their personas, current state, and memories."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    # Agents are stored inside the latest world state
    turns = db.get_turns(sim_id)
    if not turns:
        return []

    latest_turn = turns[-1]["turn_number"]
    world_state = db.get_world_state_by_turn(sim_id, latest_turn)
    if world_state is None:
        return []

    agents_map: dict[str, Any] = world_state.get("agents", {})

    result = []
    for agent_id, agent_data in agents_map.items():
        persona = agent_data.get("persona", {})
        memories_raw = agent_data.get("memories", [])
        memories = [
            AgentMemory(
                turn=m.get("turn", 0),
                year=m.get("year", 0),
                description=m.get("description", ""),
                emotional_weight=m.get("emotional_weight", 0.5),
                tags=m.get("tags", []),
            )
            for m in memories_raw
            if isinstance(m, dict)
        ]
        result.append(
            AgentState(
                agent_id=agent_id,
                name=persona.get("name", agent_id),
                persona=persona,
                mood=agent_data.get("mood", 0.5),
                energy=agent_data.get("energy", 1.0),
                alive=agent_data.get("alive", True),
                relationships=agent_data.get("relationships", {}),
                memories=memories,
            )
        )
    return result


# ------------------------------------------------------------------ #
# Scenario tree
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/tree", response_model=ScenarioTreeResponse)
async def get_tree(sim_id: str) -> ScenarioTreeResponse:
    """Get the DFS scenario tree with node statuses and hypotheses."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    sim = db.get_simulation(sim_id)
    hyps = db.get_hypotheses(sim_id)

    # Build node map from hypothesis records
    nodes: dict[str, TreeNode] = {}
    root_id: str | None = None

    for hyp in hyps:
        node_id = hyp["node_id"]
        depth = hyp.get("depth", 0)
        if depth == 0:
            root_id = node_id

        tags = _parse_json_field(hyp.get("tags_json"), [])

        # Parse outcome metadata from description if it's JSON
        description = hyp.get("description", hyp.get("title", ""))
        metadata: dict[str, Any] = {}
        hypothesis_text = description
        outcome_data = _parse_json_field(description, None)
        if isinstance(outcome_data, dict) and "outcome" in outcome_data:
            metadata = outcome_data
            hypothesis_text = hyp.get("title", description)

        nodes[node_id] = TreeNode(
            node_id=node_id,
            parent_id=hyp.get("parent_id") or None,
            depth=depth,
            hypothesis=hypothesis_text,
            status="pruned" if metadata.get("outcome") == "pruned" else "complete",
            children=[],
            turns_simulated=0,
            years_simulated=0,
            score=hyp.get("probability"),
            tags=tags if isinstance(tags, list) else [],
            metadata=metadata,
            character_fidelity_score=hyp.get("character_fidelity_score"),
            fandom_resonance_score=hyp.get("fandom_resonance_score"),
            emergence_score=hyp.get("emergence_score"),
            diversity_score=hyp.get("diversity_score"),
            plausibility_score=hyp.get("plausibility_score"),
            foreshadowing_score=hyp.get("foreshadowing_score"),
        )

    # Wire up children lists
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            parent = nodes[node.parent_id]
            if node.node_id not in parent.children:
                parent.children.append(node.node_id)

    return ScenarioTreeResponse(
        simulation_id=sim_id,
        max_depth=sim.get("max_depth", 0) if sim else 0,
        root_id=root_id,
        nodes=nodes,
    )


# ------------------------------------------------------------------ #
# Path replay
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/paths", response_model=PathsResponse)
async def get_paths(sim_id: str) -> PathsResponse:
    """Get all root-to-leaf paths as continuous narratives."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    # Get tree structure
    tree_response = await get_tree(sim_id)
    nodes = tree_response.nodes
    root_id = tree_response.root_id

    if not root_id or not nodes:
        return PathsResponse(simulation_id=sim_id, paths=[], total_paths=0)

    # Find all root-to-leaf paths using DFS
    all_paths: list[list[str]] = []

    def dfs_paths(node_id: str, current_path: list[str]) -> None:
        current_path = current_path + [node_id]
        node = nodes.get(node_id)
        if not node or not node.children:
            all_paths.append(current_path)
            return
        for child_id in node.children:
            dfs_paths(child_id, current_path)

    dfs_paths(root_id, [])

    # Get all turns
    all_turns = db.get_turns(sim_id)

    # Build path narratives
    path_narratives: list[PathNarrative] = []
    for idx, path_node_ids in enumerate(all_paths):
        path_nodes = []
        for nid in path_node_ids:
            node = nodes[nid]
            path_nodes.append(PathNode(
                node_id=nid,
                depth=node.depth,
                hypothesis=node.hypothesis,
                status=node.status,
            ))

        # Collect turns for nodes in this path
        # For now, all turns belong to the path (since turns don't have node_id yet)
        # TODO: filter turns by node_id when that field is added to turns table
        path_turns = [
            TurnSummary(
                turn_number=row["turn_number"],
                year=row.get("year", 0),
                narrative=row.get("narrative", ""),
                events=_parse_json_field(row.get("events_json"), []),
                agent_actions=_parse_json_field(row.get("agent_actions_json"), {}),
                cost=row.get("cost_usd", 0.0),
            )
            for row in all_turns
        ]

        total_years = max((t.year for t in path_turns), default=0)

        path_narratives.append(PathNarrative(
            path_id=f"path-{idx}",
            nodes=path_nodes,
            turns=path_turns,
            total_years=total_years,
            total_turns=len(path_turns),
        ))

    return PathsResponse(
        simulation_id=sim_id,
        paths=path_narratives,
        total_paths=len(path_narratives),
    )


# ------------------------------------------------------------------ #
# Export
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/export", response_model=SimulationExport)
async def export_simulation(sim_id: str) -> SimulationExport:
    """Export full simulation data as a single JSON package for sharing."""
    from datetime import datetime, timezone

    simulation = await get_simulation(sim_id)
    turns = await get_turns(sim_id)
    tree = await get_tree(sim_id)
    agents = await get_agents(sim_id)

    return SimulationExport(
        simulation=simulation,
        turns=turns,
        tree=tree,
        agents=agents,
        exported_at=datetime.now(timezone.utc).isoformat(),
    )


# ------------------------------------------------------------------ #
# World state replay
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/world-state/{turn_number}")
async def get_world_state(sim_id: str, turn_number: int) -> dict[str, Any]:
    """Get the world state at a specific turn (for replay scrubbing)."""
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    state = db.get_world_state_by_turn(sim_id, turn_number)
    if state is None:
        raise HTTPException(
            status_code=404, detail=f"World state for turn {turn_number} not found"
        )
    return state


# ------------------------------------------------------------------ #
# Environment
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/environment", response_model=EnvironmentResponse)
async def get_environment(sim_id: str) -> EnvironmentResponse:
    """Get the 2D environment layout for rendering."""
    db = _get_db()
    sim = db.get_simulation(sim_id)
    if sim is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")

    topic = sim.get("topic", "")

    # Load agents from turn-0 world state
    world_state_0 = db.get_world_state_by_turn(sim_id, 0)
    agents_map: dict[str, Any] = (world_state_0 or {}).get("agents", {})
    agents = [{"agent_id": aid, "persona": data.get("persona", {})} for aid, data in agents_map.items()]

    env = await generate_environment(
        simulation_id=sim_id,
        topic=topic,
        agents=agents,
        world_state=world_state_0,
    )

    return EnvironmentResponse(
        simulation_id=env["simulation_id"],
        map_type=env["map_type"],
        width=env["width"],
        height=env["height"],
        landmarks=[Landmark(**lm) for lm in env.get("landmarks", [])],
        zones=[Zone(**z) for z in env.get("zones", [])],
        initial_agent_positions=[AgentPosition(**p) for p in env.get("initial_agent_positions", [])],
    )


# ------------------------------------------------------------------ #
# Metrics
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/metrics")
async def get_metrics(sim_id: str) -> dict[str, Any]:
    """Return lightweight per-node quality metrics (5 dimensions + composite).

    Returns only nodes that have been evaluated (at least one score != None).
    Weights: character_fidelity 25%, fandom_resonance 20%, emergence 20%, diversity 15%, plausibility 20%.
    """
    db = _get_db()
    _assert_simulation_exists(db, sim_id)

    hyps = db.get_hypotheses(sim_id)

    WEIGHTS = {
        "character_fidelity": 0.25,
        "fandom_resonance": 0.20,
        "emergence": 0.20,
        "diversity": 0.15,
        "plausibility": 0.20,
    }

    nodes: list[dict[str, Any]] = []
    for hyp in hyps:
        character_fidelity = hyp.get("character_fidelity_score")
        fandom_resonance   = hyp.get("fandom_resonance_score")
        emergence          = hyp.get("emergence_score")
        diversity          = hyp.get("diversity_score")
        plausibility       = hyp.get("plausibility_score")

        # Skip nodes that have never been evaluated
        if all(v is None for v in [character_fidelity, fandom_resonance, emergence, diversity, plausibility]):
            continue

        cf = character_fidelity or 0.0
        fr = fandom_resonance   or 0.0
        e  = emergence          or 0.0
        d  = diversity          or 0.0
        pl = plausibility       or 0.0
        composite = (
            cf * WEIGHTS["character_fidelity"]
            + fr * WEIGHTS["fandom_resonance"]
            + e  * WEIGHTS["emergence"]
            + d  * WEIGHTS["diversity"]
            + pl * WEIGHTS["plausibility"]
        )

        nodes.append({
            "node_id":              hyp["node_id"],
            "node_title":           hyp.get("title") or hyp.get("description", "")[:60],
            "character_fidelity":   cf,
            "fandom_resonance":     fr,
            "emergence":            e,
            "diversity":            d,
            "plausibility":         pl,
            "composite":            round(composite, 4),
        })

    # Sort by composite descending
    nodes.sort(key=lambda x: x["composite"], reverse=True)

    return {
        "simulation_id": sim_id,
        "evaluated_count": len(nodes),
        "nodes": nodes,
    }


# ------------------------------------------------------------------ #
# Research
# ------------------------------------------------------------------ #


@router.get("/simulations/{sim_id}/research")
async def get_research(sim_id: str) -> dict[str, Any]:
    """Get the research document for a simulation."""
    _assert_simulation_exists(_get_db(), sim_id)

    from ese.research.phase import ResearchPhase

    doc = ResearchPhase.load(sim_id)
    if doc is None:
        return {"topic": "", "summary": "No research data available"}
    return doc.to_dict()


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #


def _assert_simulation_exists(db: Database, sim_id: str) -> None:
    if db.get_simulation(sim_id) is None:
        raise HTTPException(status_code=404, detail=f"Simulation '{sim_id}' not found")
