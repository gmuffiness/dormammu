"""Autonomous execution loop orchestrator for Dormammu.

The OrchestratorLoop is the top-level driver. It:
1. Creates or loads a Simulation
2. Generates evaluation criteria from topic via LLM
3. Generates initial hypotheses for root node (3 branches)
4. Drives the DFS scenario tree node-by-node
5. Evaluates each completed node and expands or prunes
6. Persists everything to the database via TurnLogger
7. Respects cost limits and can pause/resume cleanly
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.tree import Tree as RichTree

from ese.config import config
from ese.engine.scenario_tree import NodeStatus, ScenarioNode, ScenarioTree
from ese.engine.simulation import Simulation, SimulationConfig, SimulationStatus
from ese.engine.world_state import WorldState
from ese.agents.agent import Agent
from ese.agents.persona import PersonaGenerator
from ese.hypothesis.evaluator import EvaluationResult, HypothesisEvaluator
from ese.hypothesis.generator import Hypothesis, HypothesisGenerator
from ese.hypothesis.inspiration import InspirationSystem
from ese.research.phase import ResearchDocument, ResearchPhase
from ese.storage.database import Database
from ese.storage.logger import TurnLogger

logger = logging.getLogger(__name__)
console = Console()

# Default number of agents per simulation
DEFAULT_AGENT_COUNT = 5

# Branching factor at each non-leaf node
BRANCHES_PER_NODE = 3

LANGUAGE_NAMES = {
    "en": "English", "ko": "Korean", "ja": "Japanese", "zh": "Chinese",
    "es": "Spanish", "fr": "French", "de": "German",
}

# Macro-scale keywords — topics containing these use fewer agents and more years/turn
MACRO_KEYWORDS = [
    "civilization", "humanity", "인류", "제국", "empire", "nation", "국가",
    "century", "세기", "millennia", "millennium", "world", "세계", "global",
    "species", "mankind", "history", "역사", "civilization", "문명",
]

# SF injection threshold: inject inspiration every N hypothesis generations at the same depth
SF_INJECTION_EVERY_N = 3


class OrchestratorLoop:
    """Drives the full autonomous simulation lifecycle.

    Designed to be called from the CLI (`ese run`) but is also importable
    for programmatic use or testing.
    """

    def __init__(
        self,
        max_depth: int | None = None,
        node_years: int | None = None,
        cost_limit: float | None = None,
        openai_model: str | None = None,
        agent_model: str | None = None,
        agent_count: int = DEFAULT_AGENT_COUNT,
        language: str | None = None,
        db: Database | None = None,
    ) -> None:
        self.max_depth = max_depth or config.max_depth
        self.node_years = node_years or config.node_years
        self.cost_limit = cost_limit or config.cost_limit
        self.openai_model = openai_model or config.openai_model
        self.agent_model = agent_model or config.agent_model
        self.agent_count = agent_count
        self.language = language or config.language

        self.db = db or Database()
        self.research_phase = ResearchPhase(openai_model=self.openai_model)
        self.persona_generator = PersonaGenerator(openai_model=self.openai_model)
        self.hypothesis_generator = HypothesisGenerator(openai_model=self.openai_model)
        self.hypothesis_evaluator = HypothesisEvaluator(openai_model=self.openai_model)
        self.inspiration = InspirationSystem()
        self._research_doc: ResearchDocument | None = None

        # Track hypothesis generation count per depth for SF injection
        self._gen_count_per_depth: dict[int, int] = {}

    # ------------------------------------------------------------------ #
    # Public interface
    # ------------------------------------------------------------------ #

    def start(self, topic: str) -> str:
        """Start a new simulation and run it to completion or cost limit.

        Args:
            topic: Free-form description of the scenario to simulate.

        Returns:
            The simulation_id of the newly created simulation.
        """
        sim_config = SimulationConfig(
            topic=topic,
            max_depth=self.max_depth,
            node_years=self.node_years,
            cost_limit=self.cost_limit,
            openai_model=self.openai_model,
            language=self.language,
        )
        simulation = Simulation(config=sim_config)
        simulation.initialize()

        self.db.upsert_simulation(simulation.to_dict())
        logger.info("Started simulation %s", simulation.simulation_id)

        asyncio.run(self._run_loop(simulation))
        return simulation.simulation_id

    async def start_async(self, topic: str) -> str:
        """Async version of start() for use within an existing event loop.

        Args:
            topic: Free-form description of the scenario to simulate.

        Returns:
            The simulation_id of the newly created simulation.
        """
        sim_config = SimulationConfig(
            topic=topic,
            max_depth=self.max_depth,
            node_years=self.node_years,
            cost_limit=self.cost_limit,
            openai_model=self.openai_model,
            language=self.language,
        )
        simulation = Simulation(config=sim_config)
        simulation.initialize()

        self.db.upsert_simulation(simulation.to_dict())
        logger.info("Started simulation %s", simulation.simulation_id)

        await self._run_loop(simulation)
        return simulation.simulation_id

    def resume(self, simulation_id: str) -> None:
        """Resume a paused simulation.

        Args:
            simulation_id: ID of the simulation to resume.
        """
        sim_data = self.db.get_simulation(simulation_id)
        if sim_data is None:
            console.print(f"[red]Simulation not found:[/] {simulation_id}")
            return

        if sim_data.get("status") == SimulationStatus.COMPLETE.value:
            console.print("[yellow]Simulation is already complete.[/]")
            return

        sim_config = SimulationConfig(
            topic=sim_data["topic"],
            max_depth=sim_data["max_depth"],
            node_years=sim_data["node_years"],
            cost_limit=sim_data["cost_limit"],
            openai_model=sim_data["openai_model"],
            language=self.language,
        )
        simulation = Simulation(
            simulation_id=simulation_id,
            config=sim_config,
            total_cost_usd=sim_data.get("total_cost_usd", 0.0),
            evaluation_criteria=sim_data.get("evaluation_criteria", []),
        )
        simulation.initialize()

        console.print(f"Resuming simulation [cyan]{simulation_id}[/]")
        asyncio.run(self._run_loop(simulation))

    # ------------------------------------------------------------------ #
    # Internal async loop
    # ------------------------------------------------------------------ #

    async def _run_loop(self, simulation: Simulation) -> None:
        """Core DFS loop driving the full simulation."""
        log_dir = config.data_dir / simulation.simulation_id
        turn_logger = TurnLogger(
            simulation_id=simulation.simulation_id,
            db=self.db,
            log_dir=log_dir,
        )

        topic = simulation.config.topic
        scale = self._detect_scale(topic)
        years_per_turn, effective_agent_count = self._scale_params(scale)

        # Build language instruction for LLM prompts
        lang_name = LANGUAGE_NAMES.get(self.language, self.language)
        lang_instruction = (
            f"\nIMPORTANT: All output (narratives, descriptions, character names, dialogue) "
            f"must be written in {lang_name}.\n"
            if self.language != "en"
            else ""
        )

        console.print(
            f"\n[bold cyan]Dormammu Simulation[/] | Topic: [yellow]{topic}[/]\n"
            f"  Scale: [green]{scale}[/] | "
            f"Years/turn: {years_per_turn} | "
            f"Agents: {effective_agent_count} | "
            f"Max depth: {self.max_depth}\n"
        )

        # Step 0: Research phase
        if self._research_doc is None:
            console.print("[dim]Researching topic...[/]")
            self._research_doc = await self.research_phase.research(topic)
            self.research_phase.save(self._research_doc, simulation.simulation_id)
            console.print(
                f"[green]Research complete:[/] "
                f"{len(self._research_doc.key_characters)} characters, "
                f"{len(self._research_doc.key_factions)} factions, "
                f"{len(self._research_doc.topic_specific_metrics)} domain metrics"
            )
            # Store research context in world state metadata
            if simulation.current_world_state is not None:
                simulation.current_world_state.metadata["research_context"] = (
                    self._research_doc.to_prompt_context()
                )

        research_context = self._research_doc.to_prompt_context() if self._research_doc else ""
        research_context = lang_instruction + research_context

        # Step 1: Generate evaluation criteria
        if not simulation.evaluation_criteria:
            console.print("[dim]Generating evaluation criteria...[/]")
            simulation.evaluation_criteria = await self._generate_evaluation_criteria(
                topic, research_context=research_context
            )
            console.print(
                "[green]Evaluation criteria:[/] "
                + ", ".join(c["name"] for c in simulation.evaluation_criteria)
            )

        # Step 2: Generate agents
        if not simulation.agents:
            console.print(f"[dim]Generating {effective_agent_count} agents...[/]")
            personas = await self.persona_generator.generate_batch(
                topic=topic, count=effective_agent_count, research_context=research_context
            )
            simulation.agents = [
                Agent(
                    persona=p,
                    simulation_id=simulation.simulation_id,
                    openai_model=self.agent_model,
                    language=self.language,
                )
                for p in personas
            ]
            logger.info("Created %d agents", len(simulation.agents))

            # Register agents in the initial world state so summaries are meaningful
            if simulation.current_world_state is not None:
                for agent in simulation.agents:
                    simulation.current_world_state.agents[agent.agent_id] = {
                        "name": agent.persona.name,
                        "age": agent.persona.age,
                        "goals": agent.persona.goals,
                        "traits": agent.persona.trait_summary(),
                    }

        turn_logger.log_event(
            {
                "type": "simulation_start",
                "topic": topic,
                "scale": scale,
                "years_per_turn": years_per_turn,
                "agent_count": len(simulation.agents),
                "evaluation_criteria": simulation.evaluation_criteria,
            }
        )

        # Step 3: Generate initial hypotheses for root node, then add as children
        root_node = simulation.scenario_tree.get_node(simulation.scenario_tree._root_id)
        if root_node and not root_node.children:
            console.print("[dim]Generating initial hypotheses...[/]")
            root_state = simulation.get_world_state_for_node(root_node)
            hypotheses = await self._generate_hypotheses_for_node(
                simulation=simulation,
                node=root_node,
                world_state=root_state,
            )
            for h in hypotheses:
                child = simulation.scenario_tree.add_child(
                    parent_id=root_node.node_id,
                    hypothesis=h.title,
                )
                child.metadata["hypothesis"] = h.to_dict()
                # Child inherits root's world state
                simulation._node_world_states[child.node_id] = root_state
                # Persist hypothesis to DB for tree visualization
                self.db.save_hypothesis(
                    node_id=child.node_id,
                    simulation_id=simulation.simulation_id,
                    hyp_data={
                        "parent_id": root_node.node_id,
                        "depth": child.depth,
                        **h.to_dict(),
                    },
                )

            # Save root node as genesis hypothesis
            self.db.save_hypothesis(
                node_id=root_node.node_id,
                simulation_id=simulation.simulation_id,
                hyp_data={
                    "parent_id": "",
                    "depth": 0,
                    "title": simulation.config.topic,
                    "description": simulation.config.topic,
                    "probability": 1.0,
                    "tags": [],
                },
            )

            # Mark root as complete (genesis node — no turns to simulate)
            root_node.status = NodeStatus.COMPLETE
            console.print(
                f"[green]Generated {len(hypotheses)} initial branches:[/] "
                + ", ".join(h.title for h in hypotheses)
            )

        self._print_tree(simulation)

        # Step 4: DFS loop
        global_turn_number = len(simulation.turn_results) + 1

        while True:
            if simulation.total_cost_usd >= self.cost_limit:
                console.print(
                    f"[yellow]Cost limit ${self.cost_limit:.2f} reached "
                    f"(spent ${simulation.total_cost_usd:.4f}). Pausing.[/]"
                )
                simulation.status = SimulationStatus.PAUSED
                break

            next_node = simulation.scenario_tree.next_pending()
            if next_node is None:
                simulation.status = SimulationStatus.COMPLETE
                break

            # Build DFS path label for display
            path_label = self._node_path_label(simulation, next_node)
            console.print(f"\n[bold]Exploring:[/] {path_label}")
            console.print(
                f"  Hypothesis: [italic]{next_node.hypothesis}[/] "
                f"| Depth {next_node.depth}"
            )

            # Simulate this node
            global_turn_number = await self._simulate_node(
                simulation=simulation,
                node=next_node,
                turn_logger=turn_logger,
                years_per_turn=years_per_turn,
                global_turn_number=global_turn_number,
            )

            # Evaluate the completed node
            if next_node.status == NodeStatus.COMPLETE:
                eval_result = await self._evaluate_node(simulation, next_node)

                # Save evaluation scores to DB for visualization
                self.db.save_hypothesis(
                    node_id=next_node.node_id,
                    simulation_id=simulation.simulation_id,
                    hyp_data={
                        "character_fidelity_score": eval_result.character_fidelity_score,
                        "fandom_resonance_score": eval_result.fandom_resonance_score,
                        "emergence_score": eval_result.emergence_score,
                        "diversity_score": eval_result.diversity_score,
                        "plausibility_score": eval_result.plausibility_score,
                        "foreshadowing_score": eval_result.foreshadowing_score,
                    },
                )

                turn_logger.log_event(
                    {
                        "type": "node_evaluated",
                        "node_id": next_node.node_id,
                        "hypothesis": next_node.hypothesis,
                        "composite_score": eval_result.composite_score,
                        "should_expand": eval_result.should_expand,
                        "rationale": eval_result.rationale,
                    }
                )

                score_color = "green" if eval_result.composite_score > 0.5 else "red"
                console.print(
                    f"  Score: [{score_color}]{eval_result.composite_score:.2f}[/] | "
                    f"{eval_result.rationale[:100]}..."
                    if len(eval_result.rationale) > 100
                    else f"  Score: [{score_color}]{eval_result.composite_score:.2f}[/] | "
                    f"{eval_result.rationale}"
                )

                # Expand or prune
                at_max_depth = simulation.scenario_tree.is_leaf(next_node)
                if eval_result.should_expand and not at_max_depth:
                    children = await self._expand_node(simulation, next_node, eval_result)
                    console.print(
                        f"  [green]Expanded[/] → {len(children)} child branches"
                    )
                    turn_logger.log_event(
                        {
                            "type": "node_expanded",
                            "node_id": next_node.node_id,
                            "child_ids": [c.node_id for c in children],
                        }
                    )
                else:
                    if not eval_result.should_expand:
                        next_node.status = NodeStatus.PRUNED
                        console.print("  [red]Pruned[/] (low score)")
                        turn_logger.log_event(
                            {
                                "type": "node_pruned",
                                "node_id": next_node.node_id,
                                "reason": "composite_score <= 0.5",
                            }
                        )
                    else:
                        console.print("  [dim]Leaf node — no further expansion[/]")

            self._print_tree(simulation)
            self.db.upsert_simulation(simulation.to_dict())
            await asyncio.sleep(0)  # yield control

        # Final persist
        self.db.upsert_simulation(simulation.to_dict())
        turn_logger.log_event(
            {
                "type": "simulation_end",
                "status": simulation.status.value,
                "total_turns": len(simulation.turn_results),
                "total_cost_usd": simulation.total_cost_usd,
                "nodes_explored": simulation.scenario_tree.complete_count(),
            }
        )

        status_color = "green" if simulation.status == SimulationStatus.COMPLETE else "yellow"
        console.print(
            f"\n[{status_color}]Simulation {simulation.status.value}.[/] "
            f"Nodes: {simulation.scenario_tree.complete_count()} | "
            f"Turns: {len(simulation.turn_results)} | "
            f"Cost: ${simulation.total_cost_usd:.4f}"
        )

    # ------------------------------------------------------------------ #
    # Node simulation
    # ------------------------------------------------------------------ #

    async def _simulate_node(
        self,
        simulation: Simulation,
        node: ScenarioNode,
        turn_logger: TurnLogger,
        years_per_turn: int,
        global_turn_number: int,
    ) -> int:
        """Run all turns for a single node.

        Args:
            simulation: The active simulation.
            node: The scenario node to simulate.
            turn_logger: Logger for persisting turn results.
            years_per_turn: Years advanced per turn.
            global_turn_number: Starting global turn counter.

        Returns:
            Updated global turn number after all turns in this node.
        """
        node.status = NodeStatus.IN_PROGRESS

        turns_needed = max(1, self.node_years // years_per_turn)
        world_state = simulation.get_world_state_for_node(node)

        logger.info(
            "Simulating node %s (%d turns, %d years/turn)",
            node.node_id[:8],
            turns_needed,
            years_per_turn,
        )

        for turn_idx in range(turns_needed):
            if simulation.total_cost_usd >= self.cost_limit:
                logger.warning("Cost limit hit mid-node at turn %d", global_turn_number)
                simulation.status = SimulationStatus.PAUSED
                # Snapshot partial exit state
                simulation.snapshot_node_exit_state(node.node_id, world_state)
                node.turns_simulated = turn_idx
                node.years_simulated = turn_idx * years_per_turn
                return global_turn_number

            result = await simulation.run_turn_for_node(
                node=node,
                world_state=world_state,
                turn_number=global_turn_number,
                years_per_turn=years_per_turn,
            )

            if result is None:
                # Cost limit hit inside run_turn_for_node
                simulation.snapshot_node_exit_state(node.node_id, world_state)
                node.turns_simulated = turn_idx
                node.years_simulated = turn_idx * years_per_turn
                return global_turn_number

            turn_logger.log_turn(result)
            world_state = result.world_state
            global_turn_number += 1
            node.turns_simulated = turn_idx + 1
            node.years_simulated = (turn_idx + 1) * years_per_turn

            console.print(
                f"    Turn {global_turn_number - 1} | "
                f"Year {world_state.year} | "
                f"Cost ${simulation.total_cost_usd:.4f}"
            )

            await asyncio.sleep(0)

        # Node complete — snapshot final world state
        simulation.snapshot_node_exit_state(node.node_id, world_state)
        node.exit_world_state_id = world_state.state_id
        node.status = NodeStatus.COMPLETE

        logger.info(
            "Node %s complete: %d turns, %d years simulated",
            node.node_id[:8],
            node.turns_simulated,
            node.years_simulated,
        )
        return global_turn_number

    # ------------------------------------------------------------------ #
    # Evaluation & expansion
    # ------------------------------------------------------------------ #

    async def _evaluate_node(
        self, simulation: Simulation, node: ScenarioNode
    ) -> EvaluationResult:
        """Evaluate a completed node and decide: expand or prune.

        Args:
            simulation: The active simulation.
            node: The completed node.

        Returns:
            EvaluationResult with scores and expand/prune recommendation.
        """
        hypothesis_data = node.metadata.get("hypothesis", {})
        from ese.hypothesis.generator import Hypothesis as HypothesisClass

        hypothesis = HypothesisClass(
            title=hypothesis_data.get("title", node.hypothesis),
            description=hypothesis_data.get("description", node.hypothesis),
            probability=hypothesis_data.get("probability", 0.5),
            tags=hypothesis_data.get("tags", []),
            sf_inspired=hypothesis_data.get("sf_inspired", False),
        )

        # Collect turn narratives for this node
        node_turns = simulation.turn_results[
            max(0, len(simulation.turn_results) - node.turns_simulated):
        ]
        turn_narratives = [r.narrative for r in node_turns if r.narrative]

        # Collect sibling summaries for novelty scoring
        sibling_summaries: list[str] = []
        if node.parent_id:
            parent = simulation.scenario_tree.get_node(node.parent_id)
            if parent:
                for sib_id in parent.children:
                    if sib_id != node.node_id:
                        sib = simulation.scenario_tree.get_node(sib_id)
                        if sib and sib.status == NodeStatus.COMPLETE:
                            sibling_summaries.append(sib.hypothesis)

        final_world_state = simulation._node_world_states.get(
            node.node_id, simulation.current_world_state
        )

        return await self.hypothesis_evaluator.evaluate(
            hypothesis=hypothesis,
            node_id=node.node_id,
            final_world_state=final_world_state,
            turn_narratives=turn_narratives,
            sibling_summaries=sibling_summaries,
            evaluation_criteria=simulation.evaluation_criteria,
        )

    async def _expand_node(
        self,
        simulation: Simulation,
        node: ScenarioNode,
        eval_result: EvaluationResult,
    ) -> list[ScenarioNode]:
        """Generate child hypotheses and add child nodes.

        Args:
            simulation: The active simulation.
            node: The node to expand.
            eval_result: Evaluation result guiding expansion.

        Returns:
            List of newly created child ScenarioNode objects.
        """
        exit_world_state = simulation._node_world_states.get(
            node.node_id, simulation.current_world_state
        )

        hypotheses = await self._generate_hypotheses_for_node(
            simulation=simulation,
            node=node,
            world_state=exit_world_state,
        )

        children: list[ScenarioNode] = []
        for h in hypotheses:
            child = simulation.scenario_tree.add_child(
                parent_id=node.node_id,
                hypothesis=h.title,
            )
            child.metadata["hypothesis"] = h.to_dict()
            # Child inherits parent's exit world state
            simulation._node_world_states[child.node_id] = exit_world_state
            children.append(child)
            # Persist hypothesis to DB for tree visualization
            self.db.save_hypothesis(
                node_id=child.node_id,
                simulation_id=simulation.simulation_id,
                hyp_data={
                    "parent_id": node.node_id,
                    "depth": child.depth,
                    **h.to_dict(),
                },
            )

        return children

    # ------------------------------------------------------------------ #
    # Hypothesis generation helpers
    # ------------------------------------------------------------------ #

    async def _generate_hypotheses_for_node(
        self,
        simulation: Simulation,
        node: ScenarioNode,
        world_state: WorldState,
    ) -> list[Hypothesis]:
        """Generate hypotheses appropriate for the given node and world state."""
        depth = node.depth + 1  # children will be at depth+1

        # Track generation count at this depth for SF injection
        self._gen_count_per_depth[depth] = self._gen_count_per_depth.get(depth, 0) + 1
        gen_count = self._gen_count_per_depth[depth]
        use_sf = (gen_count % SF_INJECTION_EVERY_N == 0)

        inspiration_injection = ""
        if use_sf:
            seeds = self.inspiration.pick(topic=simulation.config.topic, count=2)
            inspiration_injection = self.inspiration.build_injection(seeds)
            logger.info("Injecting SF inspiration at depth %d (gen %d)", depth, gen_count)

        # Collect existing sibling hypotheses for diversity
        sibling_titles = [
            simulation.scenario_tree.get_node(cid).hypothesis
            for cid in node.children
            if simulation.scenario_tree.get_node(cid)
        ]

        research_context = ""
        if self._research_doc:
            research_context = self._research_doc.to_prompt_context()

        return await self.hypothesis_generator.generate(
            topic=simulation.config.topic,
            world_summary=world_state.summary(),
            depth=depth,
            count=BRANCHES_PER_NODE,
            sibling_hypotheses=sibling_titles,
            sf_inspired=use_sf,
            inspiration_injection=inspiration_injection,
            research_context=research_context,
        )

    # ------------------------------------------------------------------ #
    # Scale detection
    # ------------------------------------------------------------------ #

    def _detect_scale(self, topic: str) -> str:
        """Detect 'macro' or 'micro' scale from topic.

        Macro: civilizations, nations, centuries — fewer agents, more years/turn.
        Micro: village, family, years — more agents, 1 year/turn.

        Args:
            topic: The simulation topic string.

        Returns:
            'macro' or 'micro'
        """
        topic_lower = topic.lower()
        for keyword in MACRO_KEYWORDS:
            if keyword in topic_lower:
                return "macro"
        return "micro"

    def _scale_params(self, scale: str) -> tuple[int, int]:
        """Return (years_per_turn, agent_count) for the given scale.

        Args:
            scale: 'macro' or 'micro'

        Returns:
            Tuple of (years_per_turn, agent_count)
        """
        if scale == "macro":
            return 25, max(3, min(5, self.agent_count))
        else:
            return 1, self.agent_count

    # ------------------------------------------------------------------ #
    # Evaluation criteria generation
    # ------------------------------------------------------------------ #

    async def _generate_evaluation_criteria(
        self, topic: str, research_context: str = ""
    ) -> list[dict[str, str]]:
        """Generate evaluation criteria from topic via LLM.

        Args:
            topic: The simulation topic.

        Returns:
            List of {'name': str, 'description': str} dicts.
        """
        from ese.agents.interaction import AgentInteraction
        import json

        if not config.openai_api_key:
            logger.debug("No API key; returning default evaluation criteria.")
            return self._default_criteria(topic)

        interaction = AgentInteraction(api_key=config.openai_api_key, model=self.openai_model)
        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are a simulation designer. Generate clear, measurable evaluation "
                    "criteria for assessing simulation branches. Always respond with valid JSON."
                ),
                user_prompt=(
                    f"Topic: {topic}\n\n"
                    + (f"Research context:\n{research_context}\n\n" if research_context else "")
                    + "Generate 3-5 evaluation criteria for assessing how well a simulated "
                    "scenario branch performs. Each criterion should be specific to this topic. "
                    "Use the research context to create domain-appropriate metrics.\n\n"
                    "Respond with a JSON array:\n"
                    '[{"name": "short name", "description": "what this measures"}]'
                ),
                temperature=0.5,
            )
            data = json.loads(response.content)
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # Try common wrapper keys
                for key in ("criteria", "evaluation_criteria", "items"):
                    if key in data and isinstance(data[key], list):
                        items = data[key]
                        break
                else:
                    items = list(data.values())[0] if data else []
            else:
                items = []

            criteria = [
                {"name": str(c.get("name", "")), "description": str(c.get("description", ""))}
                for c in items
                if isinstance(c, dict) and c.get("name")
            ]
            return criteria if criteria else self._default_criteria(topic)

        except Exception as exc:
            logger.error("Failed to generate evaluation criteria: %s", exc)
            return self._default_criteria(topic)

    def _default_criteria(self, topic: str) -> list[dict[str, str]]:
        """Return generic fallback criteria."""
        return [
            {"name": "Survival", "description": "Whether key entities/groups survive"},
            {"name": "Progress", "description": "Technological or social advancement"},
            {"name": "Stability", "description": "Social and political stability"},
            {"name": "Novelty", "description": "Surprising or unexpected developments"},
        ]

    # ------------------------------------------------------------------ #
    # Display helpers
    # ------------------------------------------------------------------ #

    def _node_path_label(self, simulation: Simulation, node: ScenarioNode) -> str:
        """Build a human-readable DFS path label for a node.

        Args:
            simulation: The active simulation.
            node: Target node.

        Returns:
            E.g. 'Root → Branch A → Sub-branch A-1'
        """
        path: list[str] = []
        current: ScenarioNode | None = node
        while current is not None:
            label = current.hypothesis[:40] + ("..." if len(current.hypothesis) > 40 else "")
            path.append(label)
            current = (
                simulation.scenario_tree.get_node(current.parent_id)
                if current.parent_id
                else None
            )
        path.reverse()
        return " → ".join(path)

    def _print_tree(self, simulation: Simulation) -> None:
        """Print ASCII tree of current exploration state."""
        tree = simulation.scenario_tree
        if tree._root_id is None:
            return

        root_node = tree.get_node(tree._root_id)
        if root_node is None:
            return

        STATUS_ICONS = {
            NodeStatus.PENDING: "[dim]○[/]",
            NodeStatus.IN_PROGRESS: "[yellow]◎[/]",
            NodeStatus.COMPLETE: "[green]●[/]",
            NodeStatus.PRUNED: "[red]✗[/]",
        }

        def _build_rich_tree(node: ScenarioNode, rich_parent: RichTree) -> None:
            icon = STATUS_ICONS.get(node.status, "?")
            label = node.hypothesis[:50] + ("..." if len(node.hypothesis) > 50 else "")
            branch = rich_parent.add(f"{icon} {label}")
            for child_id in node.children:
                child = tree.get_node(child_id)
                if child and child.status != NodeStatus.PRUNED:
                    _build_rich_tree(child, branch)

        root_label = root_node.hypothesis[:50]
        rich_tree = RichTree(
            f"[bold]{root_label}[/] "
            f"[dim]({tree.complete_count()}/{tree.node_count()} complete)[/]"
        )
        for child_id in root_node.children:
            child = tree.get_node(child_id)
            if child:
                _build_rich_tree(child, rich_tree)

        console.print(rich_tree)
        console.print(
            f"  [dim]Cost: ${simulation.total_cost_usd:.4f} / "
            f"${self.cost_limit:.2f}[/]\n"
        )
