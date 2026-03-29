"""Basic smoke tests for Dormammu.

These tests verify that the core data structures and logic work correctly
without requiring OpenAI API access or a database.
"""

from __future__ import annotations

import asyncio
import pytest

# ------------------------------------------------------------------ #
# Engine
# ------------------------------------------------------------------ #


def test_world_state_initial():
    from ese.engine.world_state import WorldState

    ws = WorldState.initial(simulation_id="test-sim", topic="Test World")
    assert ws.simulation_id == "test-sim"
    assert ws.turn == 0
    assert ws.year == 0
    assert ws.metadata["topic"] == "Test World"


def test_world_state_add_event():
    from ese.engine.world_state import WorldState

    ws = WorldState.initial(simulation_id="test-sim", topic="Test World")
    ws.add_event("Something happened", type="test")
    assert len(ws.events) == 1
    assert ws.events[0]["description"] == "Something happened"


def test_world_state_serialization():
    from ese.engine.world_state import WorldState

    ws = WorldState.initial(simulation_id="test-sim", topic="Round-trip")
    ws.add_event("Event A")
    d = ws.to_dict()
    restored = WorldState.from_dict(d)
    assert restored.state_id == ws.state_id
    assert len(restored.events) == 1


def test_world_state_summary():
    from ese.engine.world_state import WorldState

    ws = WorldState.initial(simulation_id="s1", topic="Mars")
    summary = ws.summary()
    assert "Year" in summary
    assert "Turn" in summary


# ------------------------------------------------------------------ #
# Scenario tree
# ------------------------------------------------------------------ #


def test_scenario_tree_create_root():
    from ese.engine.scenario_tree import ScenarioTree, NodeStatus

    tree = ScenarioTree(simulation_id="sim-1", max_depth=3)
    root = tree.create_root(hypothesis="Genesis")
    assert root.depth == 0
    assert root.hypothesis == "Genesis"
    assert tree.node_count() == 1


def test_scenario_tree_add_child():
    from ese.engine.scenario_tree import ScenarioTree, NodeStatus

    tree = ScenarioTree(simulation_id="sim-1", max_depth=3)
    root = tree.create_root()
    child = tree.add_child(root.node_id, hypothesis="Branch A")
    assert child.depth == 1
    assert child.parent_id == root.node_id
    assert root.node_id in tree._nodes
    assert child.node_id in root.children


def test_scenario_tree_next_pending():
    from ese.engine.scenario_tree import ScenarioTree, NodeStatus

    tree = ScenarioTree(simulation_id="sim-1", max_depth=3)
    root = tree.create_root()
    pending = tree.next_pending()
    assert pending is not None
    assert pending.node_id == root.node_id


def test_scenario_tree_dfs_order():
    from ese.engine.scenario_tree import ScenarioTree

    tree = ScenarioTree(simulation_id="sim-1", max_depth=3)
    root = tree.create_root()
    child_a = tree.add_child(root.node_id, "A")
    child_b = tree.add_child(root.node_id, "B")
    grandchild = tree.add_child(child_a.node_id, "A1")

    nodes = list(tree.dfs())
    ids = [n.node_id for n in nodes]
    # DFS: root -> child_a -> grandchild -> child_b
    assert ids == [root.node_id, child_a.node_id, grandchild.node_id, child_b.node_id]


def test_scenario_tree_is_leaf():
    from ese.engine.scenario_tree import ScenarioTree

    tree = ScenarioTree(simulation_id="sim-1", max_depth=2)
    root = tree.create_root()
    child = tree.add_child(root.node_id, "A")
    grandchild = tree.add_child(child.node_id, "A1")

    assert not tree.is_leaf(root)
    assert not tree.is_leaf(child)
    assert tree.is_leaf(grandchild)


def test_scenario_tree_serialization():
    from ese.engine.scenario_tree import ScenarioTree

    tree = ScenarioTree(simulation_id="sim-1", max_depth=3)
    root = tree.create_root("Genesis")
    tree.add_child(root.node_id, "Branch A")

    d = tree.to_dict()
    restored = ScenarioTree.from_dict(d)
    assert restored.node_count() == 2
    assert restored._root_id == root.node_id


# ------------------------------------------------------------------ #
# Persona
# ------------------------------------------------------------------ #


def test_persona_default_traits():
    from ese.agents.persona import Persona, TRAIT_DIMENSIONS

    traits = Persona.default_traits()
    assert set(traits.keys()) == set(TRAIT_DIMENSIONS)
    assert all(v == 0.5 for v in traits.values())


def test_persona_trait_summary_balanced():
    from ese.agents.persona import Persona

    p = Persona(traits=Persona.default_traits())
    summary = p.trait_summary()
    assert summary == "balanced traits"


def test_persona_trait_summary_extremes():
    from ese.agents.persona import Persona

    p = Persona(
        traits={
            "openness": 0.9,
            "conscientiousness": 0.2,
            "extraversion": 0.5,
            "agreeableness": 0.5,
            "neuroticism": 0.5,
        }
    )
    summary = p.trait_summary()
    assert "openness" in summary
    assert "conscientiousness" in summary


def test_persona_to_prompt_block():
    from ese.agents.persona import Persona

    p = Persona(name="Alice", age=30, backstory="A wanderer.", goals=["explore"])
    block = p.to_prompt_block()
    assert "Alice" in block
    assert "30" in block
    assert "explore" in block


def test_persona_serialization():
    from ese.agents.persona import Persona

    p = Persona(name="Bob", traits=Persona.default_traits(), goals=["survive"])
    d = p.to_dict()
    restored = Persona.from_dict(d)
    assert restored.name == "Bob"
    assert restored.goals == ["survive"]


@pytest.mark.asyncio
async def test_persona_generator():
    from ese.agents.persona import PersonaGenerator

    gen = PersonaGenerator()
    persona = await gen.generate(topic="Mars colony", index=0)
    assert persona.name != ""
    assert len(persona.goals) > 0


@pytest.mark.asyncio
async def test_persona_generator_batch():
    from ese.agents.persona import PersonaGenerator

    gen = PersonaGenerator()
    personas = await gen.generate_batch(topic="Mars colony", count=3)
    assert len(personas) == 3
    names = [p.name for p in personas]
    assert len(set(names)) == 3  # All unique


# ------------------------------------------------------------------ #
# Agent
# ------------------------------------------------------------------ #


def test_agent_remember():
    from ese.agents.agent import Agent
    from ese.agents.persona import Persona

    agent = Agent(persona=Persona(name="Carol"))
    agent.remember("First memory", turn=1, year=1, emotional_weight=0.8)
    assert len(agent.memories) == 1
    assert agent.memories[0].description == "First memory"


def test_agent_update_relationship():
    from ese.agents.agent import Agent
    from ese.agents.persona import Persona

    agent = Agent(persona=Persona(name="Dave"))
    agent.update_relationship("other-id", delta=0.3)
    assert agent.relationships["other-id"] == pytest.approx(0.3)

    # Clamp at 1.0
    agent.update_relationship("other-id", delta=2.0)
    assert agent.relationships["other-id"] == pytest.approx(1.0)

    # Clamp at -1.0
    agent.update_relationship("other-id", delta=-5.0)
    assert agent.relationships["other-id"] == pytest.approx(-1.0)


@pytest.mark.asyncio
async def test_agent_decide_action():
    from ese.agents.agent import Agent
    from ese.agents.persona import Persona
    from ese.engine.world_state import WorldState

    agent = Agent(persona=Persona(name="Eve"))
    ws = WorldState.initial(simulation_id="s", topic="Test")
    action, tokens = await agent.decide_action(ws)
    assert "type" in action
    assert isinstance(tokens, int)


# ------------------------------------------------------------------ #
# Hypothesis
# ------------------------------------------------------------------ #


@pytest.mark.asyncio
async def test_hypothesis_generator():
    from ese.hypothesis.generator import HypothesisGenerator

    gen = HypothesisGenerator()
    hypotheses = await gen.generate(
        topic="Mars colony", world_summary="Year 0, no events.", depth=1, count=3
    )
    assert len(hypotheses) == 3
    # Ordered by probability descending
    probs = [h.probability for h in hypotheses]
    assert probs == sorted(probs, reverse=True)


def test_hypothesis_to_dict():
    from ese.hypothesis.generator import Hypothesis

    h = Hypothesis(title="Test", description="A branch", probability=0.7, tags=["a"])
    d = h.to_dict()
    assert d["title"] == "Test"
    assert d["probability"] == 0.7


# ------------------------------------------------------------------ #
# Inspiration
# ------------------------------------------------------------------ #


def test_inspiration_pick():
    from ese.hypothesis.inspiration import InspirationSystem

    sys = InspirationSystem()
    seeds = sys.pick(topic="Mars", count=2)
    assert len(seeds) == 2


def test_inspiration_build_injection():
    from ese.hypothesis.inspiration import InspirationSystem

    sys = InspirationSystem()
    seeds = sys.pick(topic="Mars", count=2)
    injection = sys.build_injection(seeds)
    assert "Inspiration sources" in injection


def test_inspiration_domains():
    from ese.hypothesis.inspiration import InspirationSystem

    sys = InspirationSystem()
    domains = sys.domains()
    assert "sci-fi" in domains


# ------------------------------------------------------------------ #
# Simulation
# ------------------------------------------------------------------ #


def test_simulation_initialize():
    from ese.engine.simulation import Simulation, SimulationConfig, SimulationStatus

    sim = Simulation(config=SimulationConfig(topic="Test"))
    sim.initialize()
    assert sim.scenario_tree is not None
    assert sim.current_world_state is not None
    assert sim.status == SimulationStatus.CREATED


@pytest.mark.asyncio
async def test_simulation_run_turn_no_agents():
    from ese.engine.simulation import Simulation, SimulationConfig

    sim = Simulation(config=SimulationConfig(topic="Test"))
    sim.initialize()
    # With no agents and a pending root node, run_turn should return a result
    result = await sim.run_turn()
    assert result is not None
    assert result.turn_number == 1
