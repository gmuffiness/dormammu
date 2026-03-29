"""Pydantic response models for the Dormammu API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


# ------------------------------------------------------------------ #
# Simulation
# ------------------------------------------------------------------ #


class SimulationSummary(BaseModel):
    id: str
    topic: str
    status: str
    turns: int
    nodes: int
    cost: float
    max_depth: int = 0
    total_cost_usd: float = 0.0
    created_at: str


class SimulationDetail(BaseModel):
    id: str
    topic: str
    status: str
    turns: int
    max_depth: int
    node_years: int
    cost_limit: float
    total_cost_usd: float
    openai_model: str
    current_node_id: str
    evaluation_criteria: list[str]
    created_at: str
    updated_at: str


# ------------------------------------------------------------------ #
# Turns
# ------------------------------------------------------------------ #


class TurnSummary(BaseModel):
    turn_number: int
    year: int
    narrative: str
    events: list[dict[str, Any]]
    agent_actions: dict[str, Any]
    cost: float


class TurnDetail(TurnSummary):
    world_state: dict[str, Any] | None = None


# ------------------------------------------------------------------ #
# Agents
# ------------------------------------------------------------------ #


class AgentMemory(BaseModel):
    turn: int
    year: int
    description: str
    emotional_weight: float
    tags: list[str]


class AgentState(BaseModel):
    agent_id: str
    name: str
    persona: dict[str, Any]
    mood: float
    energy: float
    alive: bool
    relationships: dict[str, float]
    memories: list[AgentMemory]


# ------------------------------------------------------------------ #
# Scenario tree
# ------------------------------------------------------------------ #


class TreeNode(BaseModel):
    node_id: str
    parent_id: str | None
    depth: int
    hypothesis: str
    status: str
    children: list[str]
    turns_simulated: int
    years_simulated: int
    score: float | None = None
    tags: list[str] = []
    metadata: dict[str, Any] = {}
    character_fidelity_score: float | None = None
    fandom_resonance_score: float | None = None
    emergence_score: float | None = None
    diversity_score: float | None = None
    plausibility_score: float | None = None
    foreshadowing_score: float | None = None


class ScenarioTreeResponse(BaseModel):
    simulation_id: str
    max_depth: int
    root_id: str | None
    nodes: dict[str, TreeNode]


# ------------------------------------------------------------------ #
# Path replay
# ------------------------------------------------------------------ #


class PathNode(BaseModel):
    """A node in a path."""

    node_id: str
    depth: int
    hypothesis: str
    status: str


class PathNarrative(BaseModel):
    """A continuous narrative for a root-to-leaf path."""

    path_id: str  # Generated: "path-0", "path-1", etc.
    nodes: list[PathNode]  # Ordered root → leaf
    turns: list[TurnSummary]  # All turns across all nodes in this path, chronologically
    total_years: int
    total_turns: int


class PathsResponse(BaseModel):
    """All root-to-leaf paths in the simulation."""

    simulation_id: str
    paths: list[PathNarrative]
    total_paths: int


# ------------------------------------------------------------------ #
# Environment
# ------------------------------------------------------------------ #


class Landmark(BaseModel):
    name: str
    x: int
    y: int
    type: str
    description: str


class Zone(BaseModel):
    name: str
    bounds: dict[str, int]
    """{"x": int, "y": int, "width": int, "height": int}"""
    type: str


class AgentPosition(BaseModel):
    agent_id: str
    x: int
    y: int


class EnvironmentResponse(BaseModel):
    simulation_id: str
    map_type: str
    width: int
    height: int
    landmarks: list[Landmark]
    zones: list[Zone]
    initial_agent_positions: list[AgentPosition]


# ------------------------------------------------------------------ #
# Export
# ------------------------------------------------------------------ #


class SimulationExport(BaseModel):
    """Full simulation data package for sharing/export."""

    simulation: SimulationDetail
    turns: list[TurnSummary]
    tree: ScenarioTreeResponse
    agents: list[AgentState]
    exported_at: str
