"""24-hour autonomous simulation runner for Dormammu.

This module implements a continuous simulation loop that:
1. Runs a simulation for a given topic
2. Analyzes the results and extracts insights
3. Generates a new topic/angle based on previous results + SF inspiration
4. Repeats until time limit or cost limit is reached

Designed to run independently for extended periods (e.g., 24 hours)
with no human intervention.

Flow per cycle
--------------
1. Analyze topic → generate evaluation criteria
2. Generate 3 hypotheses (DFS branches)
3. Run simulation for each branch (agents interact via OpenAI)
4. Evaluate each branch → score
5. Best-scoring branch → extract key insights
6. Generate next topic based on insights + SF inspiration
→ repeat
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ese.config import config
from ese.orchestrator.loop import OrchestratorLoop
from ese.storage.database import Database
from ese.hypothesis.inspiration import InspirationSystem
from ese.agents.interaction import AgentInteraction

logger = logging.getLogger(__name__)
console = Console()

# Stop the loop after this many consecutive failures to avoid infinite error loops
MAX_CONSECUTIVE_FAILURES = 3

# Pause between cycles to avoid hammering the API
INTER_CYCLE_SLEEP_SECONDS = 2


class AutonomousRunner:
    """Runs continuous simulation cycles for extended autonomous operation.

    Each cycle:
    1. Pick or generate a topic
    2. Run a full DFS simulation
    3. Analyze results → extract the most interesting findings
    4. Generate next topic based on findings + SF inspiration
    5. Repeat
    """

    def __init__(
        self,
        initial_topic: str,
        duration_hours: float = 24.0,
        cost_limit_per_sim: float = 5.0,
        total_cost_limit: float = 50.0,
        max_depth: int = 3,
        node_years: int = 100,
    ) -> None:
        self.initial_topic = initial_topic
        self.duration_hours = duration_hours
        self.cost_limit_per_sim = cost_limit_per_sim
        self.total_cost_limit = total_cost_limit
        self.max_depth = max_depth
        self.node_years = node_years

        self.db = Database()
        self.inspiration = InspirationSystem()
        self.total_cost = 0.0
        self.simulations_completed: list[dict[str, Any]] = []
        self.start_time: float = 0.0

        # Track consecutive failures to stop infinite error loops
        self._consecutive_failures = 0
        # Track cycle costs separately (None means the cycle errored)
        self._cycle_costs: list[float | None] = []

        self._report_path = config.data_dir / "autonomous_report.jsonl"

    def run(self) -> None:
        """Start the autonomous runner (blocking call)."""
        asyncio.run(self._run())

    async def _run(self) -> None:
        """Main autonomous loop."""
        self.start_time = time.time()
        deadline = self.start_time + (self.duration_hours * 3600)

        console.print(
            Panel(
                f"[bold cyan]Dormammu Autonomous Simulation Runner[/]\n\n"
                f"[bold]Initial topic:[/]   {self.initial_topic}\n"
                f"[bold]Duration:[/]        {self.duration_hours}h\n"
                f"[bold]Cost per sim:[/]    ${self.cost_limit_per_sim:.2f}\n"
                f"[bold]Total cost cap:[/]  ${self.total_cost_limit:.2f}\n"
                f"[bold]Max DFS depth:[/]   {self.max_depth}\n"
                f"[bold]Deadline:[/]        {datetime.fromtimestamp(deadline).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                "[dim]Press Ctrl+C at any time to stop gracefully and save a report.[/]",
                title="[bold green]Starting Autonomous Runner[/]",
                border_style="green",
            )
        )

        current_topic = self.initial_topic
        cycle = 0

        try:
            while True:
                cycle += 1
                elapsed = time.time() - self.start_time
                remaining = deadline - time.time()

                # Check termination conditions
                if remaining <= 0:
                    console.print("\n[yellow]Time limit reached. Stopping.[/]")
                    break

                if self.total_cost >= self.total_cost_limit:
                    console.print(
                        f"\n[yellow]Total cost limit ${self.total_cost_limit:.2f} reached "
                        f"(spent ${self.total_cost:.2f}). Stopping.[/]"
                    )
                    break

                if self._consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    console.print(
                        f"\n[red]Stopping: {MAX_CONSECUTIVE_FAILURES} consecutive failures. "
                        "Check logs for details.[/]"
                    )
                    break

                # Display cycle header
                console.print(
                    Panel(
                        f"[bold]Topic:[/]       {current_topic}\n"
                        f"[bold]Elapsed:[/]     {elapsed / 3600:.2f}h / {self.duration_hours}h\n"
                        f"[bold]Cost so far:[/] ${self.total_cost:.4f} / ${self.total_cost_limit:.2f}\n"
                        f"[bold]Completed:[/]   {len(self.simulations_completed)} simulation(s)",
                        title=f"[cyan]Cycle {cycle}[/]",
                        border_style="cyan",
                    )
                )

                # Run simulation
                try:
                    sim_result = await self._run_simulation(current_topic)
                    cycle_cost = sim_result.get("total_cost_usd", 0.0)
                    self.simulations_completed.append(sim_result)
                    self.total_cost += cycle_cost
                    self._cycle_costs.append(cycle_cost)
                    self._consecutive_failures = 0  # reset on success

                    # Log to report file
                    self._log_report(cycle, sim_result)

                    # Analyze results and generate next topic
                    next_topic = await self._generate_next_topic(sim_result)

                    console.print(
                        f"\n[green]Cycle {cycle} complete.[/] "
                        f"Cost: ${cycle_cost:.4f} | "
                        f"Nodes: {sim_result.get('nodes', 0)} | "
                        f"Turns: {sim_result.get('turns', 0)}\n"
                        f"  [dim]Next topic:[/] {next_topic}"
                    )

                    current_topic = next_topic

                except Exception as exc:
                    self._consecutive_failures += 1
                    self._cycle_costs.append(None)
                    logger.error("Cycle %d failed: %s", cycle, exc, exc_info=True)
                    console.print(
                        f"\n[red]Cycle {cycle} failed[/] "
                        f"(consecutive failures: {self._consecutive_failures}/{MAX_CONSECUTIVE_FAILURES}): "
                        f"{exc}"
                    )
                    if self._consecutive_failures < MAX_CONSECUTIVE_FAILURES:
                        current_topic = self._recover_topic()
                    continue

                # Brief pause between cycles to avoid hammering the API
                await asyncio.sleep(INTER_CYCLE_SLEEP_SECONDS)

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted by user (Ctrl+C). Saving report...[/]")

        # Final summary + report
        self._print_final_summary()
        await self._generate_final_report()

    async def _run_simulation(self, topic: str) -> dict[str, Any]:
        """Run a single simulation and return the result summary."""
        loop = OrchestratorLoop(
            max_depth=self.max_depth,
            node_years=self.node_years,
            cost_limit=self.cost_limit_per_sim,
            db=self.db,
        )

        sim_id = await loop.start_async(topic=topic)
        sim_data = self.db.get_simulation(sim_id) or {}
        turns = self.db.get_turns(sim_id)

        # Collect narratives for analysis
        narratives = [t.get("narrative", "") for t in turns if t.get("narrative")]

        return {
            "simulation_id": sim_id,
            "topic": topic,
            "total_cost_usd": sim_data.get("total_cost_usd", 0.0),
            "turns": len(turns),
            "nodes": sim_data.get("turns", 0),
            "status": sim_data.get("status", "unknown"),
            "narratives": narratives[-5:],  # Last 5 for analysis
            "completed_at": datetime.utcnow().isoformat(),
        }

    async def _generate_next_topic(self, sim_result: dict[str, Any]) -> str:
        """Generate the next simulation topic based on previous results.

        Uses LLM to analyze what was most interesting and propose a new angle.
        Injects SF inspiration to prevent convergence.
        """
        if not config.openai_api_key:
            return self._recover_topic()

        interaction = AgentInteraction(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )

        # Pick SF inspiration seeds
        seeds = self.inspiration.pick(topic=sim_result["topic"], count=2)
        inspiration_text = self.inspiration.build_injection(seeds)

        # Build analysis prompt
        narratives_text = "\n".join(
            f"- {n[:200]}" for n in sim_result.get("narratives", [])
        )

        previous_topics = [s["topic"] for s in self.simulations_completed[-5:]]
        previous_text = "\n".join(f"- {t}" for t in previous_topics)

        prompt = (
            f"Previous simulation topic: {sim_result['topic']}\n"
            f"Key narratives from the simulation:\n{narratives_text}\n\n"
            f"Previous topics explored (AVOID repeating):\n{previous_text}\n\n"
            f"{inspiration_text}\n\n"
            "Based on the most interesting findings from the previous simulation, "
            "propose a NEW simulation topic that:\n"
            "1. Explores a different angle or deeper aspect of what was discovered\n"
            "2. Is surprising and thought-provoking\n"
            "3. Is clearly different from all previous topics listed above\n"
            "4. Can be simulated as a scenario with agents and events\n"
            "5. Is stated as a concise, self-contained scenario description\n\n"
            'Respond with JSON: {"topic": "the new topic", "reasoning": "why this is interesting"}'
        )

        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are a creative scenario designer for a world simulation engine. "
                    "Your job is to propose fascinating 'what if' scenarios for simulation. "
                    "Always respond with valid JSON only."
                ),
                user_prompt=prompt,
                temperature=0.95,
            )

            data = json.loads(response.content)
            new_topic = data.get("topic", "").strip()
            reasoning = data.get("reasoning", "")

            if new_topic:
                console.print(f"  [dim]Next topic reasoning: {reasoning[:150]}[/]")
                return new_topic

        except Exception as exc:
            logger.warning("Failed to generate next topic via LLM: %s", exc)

        return self._recover_topic()

    def _recover_topic(self) -> str:
        """Generate a recovery topic from SF inspiration when LLM fails.

        Returns a clean, standalone topic string without awkward concatenation.
        """
        seeds = self.inspiration.pick(topic=self.initial_topic, count=1)
        if seeds:
            seed = seeds[0]
            # Build a standalone scenario description from the SF seed's prompt fragment
            # rather than awkwardly appending it to the initial topic
            fragment = seed.prompt_fragment
            # Strip the "Inspired by X: " prefix to get just the scenario idea
            if ": " in fragment:
                scenario = fragment.split(": ", 1)[1].strip()
            else:
                scenario = fragment.strip()
            # Capitalise and use as a standalone topic
            if scenario:
                return scenario[0].upper() + scenario[1:]
        return self.initial_topic

    def _log_report(self, cycle: int, sim_result: dict[str, Any]) -> None:
        """Append a cycle report to the JSONL log."""
        self._report_path.parent.mkdir(parents=True, exist_ok=True)
        record = {
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "elapsed_hours": (time.time() - self.start_time) / 3600,
            "simulation_id": sim_result.get("simulation_id"),
            "topic": sim_result.get("topic"),
            "total_cost_usd": sim_result.get("total_cost_usd"),
            "turns": sim_result.get("turns"),
            "nodes": sim_result.get("nodes"),
            "cumulative_cost": self.total_cost,
        }
        with self._report_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def _print_final_summary(self) -> None:
        """Print a Rich table summary of all simulations run."""
        elapsed = (time.time() - self.start_time) / 3600

        if not self.simulations_completed:
            console.print("\n[dim]No simulations completed.[/]")
            return

        table = Table(title="Autonomous Run Summary", show_lines=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Topic", style="white", max_width=50)
        table.add_column("Nodes", justify="right")
        table.add_column("Turns", justify="right")
        table.add_column("Cost", justify="right", style="green")

        for i, sim in enumerate(self.simulations_completed, 1):
            table.add_row(
                str(i),
                sim.get("topic", "")[:50],
                str(sim.get("nodes", 0)),
                str(sim.get("turns", 0)),
                f"${sim.get('total_cost_usd', 0):.4f}",
            )

        console.print()
        console.print(table)
        console.print(
            Panel(
                f"[bold]Duration:[/]    {elapsed:.2f} hours\n"
                f"[bold]Simulations:[/] {len(self.simulations_completed)}\n"
                f"[bold]Total cost:[/]  ${self.total_cost:.4f}\n"
                f"[bold]JSONL log:[/]   {self._report_path}",
                title="[green]Run Complete[/]",
                border_style="green",
            )
        )

    async def _generate_final_report(self) -> None:
        """Generate a comprehensive Markdown report after all cycles complete.

        Writes to data/simulations/report_{timestamp}.md and includes:
        - All cycles with topics and scores
        - The highest-scoring simulation (best timeline)
        - Key themes and patterns
        - Cost breakdown per cycle
        - LLM-generated narrative summary (if API key available)
        """
        if not self.simulations_completed:
            return

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        report_path = config.data_dir / f"report_{timestamp}.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        elapsed_hours = (time.time() - self.start_time) / 3600

        # Find best simulation by nodes explored (proxy for richness)
        best_sim = max(
            self.simulations_completed,
            key=lambda s: (s.get("nodes", 0), s.get("turns", 0)),
        )

        lines: list[str] = []
        lines.append(f"# Dormammu Autonomous Run Report")
        lines.append(f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n")

        lines.append("## Overview\n")
        lines.append(f"| Field | Value |")
        lines.append(f"|-------|-------|")
        lines.append(f"| Initial topic | {self.initial_topic} |")
        lines.append(f"| Duration | {elapsed_hours:.2f} hours |")
        lines.append(f"| Simulations completed | {len(self.simulations_completed)} |")
        lines.append(f"| Total cost | ${self.total_cost:.4f} |")
        lines.append(f"| Cost cap | ${self.total_cost_limit:.2f} |")

        lines.append("\n## All Simulation Cycles\n")
        lines.append("| # | Topic | Nodes | Turns | Cost (USD) |")
        lines.append("|---|-------|-------|-------|------------|")
        for i, sim in enumerate(self.simulations_completed, 1):
            topic = sim.get("topic", "")
            nodes = sim.get("nodes", 0)
            turns = sim.get("turns", 0)
            cost = sim.get("total_cost_usd", 0.0)
            lines.append(f"| {i} | {topic} | {nodes} | {turns} | ${cost:.4f} |")

        lines.append("\n## Best Timeline\n")
        lines.append(
            f"**Topic:** {best_sim.get('topic', '')}\n\n"
            f"**Simulation ID:** `{best_sim.get('simulation_id', '')}`\n\n"
            f"**Nodes explored:** {best_sim.get('nodes', 0)}\n\n"
            f"**Turns simulated:** {best_sim.get('turns', 0)}\n\n"
            f"**Cost:** ${best_sim.get('total_cost_usd', 0):.4f}\n"
        )

        if best_sim.get("narratives"):
            lines.append("### Key Narratives\n")
            for narrative in best_sim["narratives"]:
                lines.append(f"> {narrative[:400]}\n")

        lines.append("\n## Cost Breakdown per Cycle\n")
        lines.append("| Cycle | Cost (USD) | Cumulative |")
        lines.append("|-------|-----------|------------|")
        cumulative = 0.0
        for i, cost in enumerate(self._cycle_costs, 1):
            if cost is None:
                lines.append(f"| {i} | ERROR | ${cumulative:.4f} |")
            else:
                cumulative += cost
                lines.append(f"| {i} | ${cost:.4f} | ${cumulative:.4f} |")

        # LLM narrative summary
        narrative_summary = await self._llm_narrative_summary()
        if narrative_summary:
            lines.append("\n## AI-Generated Narrative Summary\n")
            lines.append(narrative_summary)

        lines.append(f"\n---\n*Report generated by Dormammu autonomous runner. "
                     f"Full cycle log: `{self._report_path}`*\n")

        report_content = "\n".join(lines)
        report_path.write_text(report_content, encoding="utf-8")

        console.print(f"\n[bold green]Final report saved:[/] {report_path}")

    async def _llm_narrative_summary(self) -> str:
        """Use LLM to generate a narrative summary of all simulation findings.

        Returns empty string if API key is not set or call fails.
        """
        if not config.openai_api_key or not self.simulations_completed:
            return ""

        interaction = AgentInteraction(
            api_key=config.openai_api_key,
            model=config.openai_model,
        )

        topics_text = "\n".join(
            f"{i}. {s.get('topic', '')}" for i, s in enumerate(self.simulations_completed, 1)
        )
        all_narratives = []
        for sim in self.simulations_completed:
            all_narratives.extend(sim.get("narratives", [])[:2])
        narratives_text = "\n".join(f"- {n[:300]}" for n in all_narratives[:10])

        prompt = (
            f"An autonomous simulation engine explored {len(self.simulations_completed)} "
            f"different scenarios over {(time.time() - self.start_time) / 3600:.1f} hours.\n\n"
            f"Topics explored:\n{topics_text}\n\n"
            f"Key narrative fragments:\n{narratives_text}\n\n"
            "Write a 3-5 paragraph narrative summary that:\n"
            "1. Identifies the common themes and patterns across all simulations\n"
            "2. Highlights the most surprising or interesting discoveries\n"
            "3. Draws connections between different scenarios explored\n"
            "4. Concludes with what these simulations suggest about the initial topic\n\n"
            'Respond with JSON: {"summary": "your narrative text here"}'
        )

        try:
            response = await interaction.get_action(
                system_prompt=(
                    "You are an analyst synthesizing findings from a world simulation engine. "
                    "Write in an engaging, analytical style. Respond with valid JSON only."
                ),
                user_prompt=prompt,
                temperature=0.7,
            )
            data = json.loads(response.content)
            return data.get("summary", "")
        except Exception as exc:
            logger.warning("Failed to generate LLM narrative summary: %s", exc)
            return ""
