"""CLI entrypoint for the Dormammu.

Commands
--------
ese run <topic>              Start a new simulation
ese resume <simulation_id>   Resume a paused simulation
ese replay <simulation_id>   Replay a completed simulation
ese list                     List all simulations
ese status <simulation_id>   Check simulation status
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(package_name="emergent-simulation-engine")
def cli() -> None:
    """Dormammu — agentic world simulation via DFS scenario trees."""


@cli.command()
@click.argument("topic")
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Override DFS tree depth (default from config).",
)
@click.option(
    "--node-years",
    default=None,
    type=int,
    help="Override simulated years per node (default from config).",
)
@click.option(
    "--cost-limit",
    default=None,
    type=float,
    help="Override USD cost limit (default from config).",
)
@click.option(
    "--agent-model",
    default=None,
    type=str,
    help="Model for agent interactions (default: gpt-4o-mini). Use cheaper models for agents.",
)
@click.option(
    "--lang",
    default=None,
    type=str,
    help="Output language (default: en). Examples: ko, ja, zh.",
)
def run(topic: str, max_depth: int | None, node_years: int | None, cost_limit: float | None, agent_model: str | None, lang: str | None) -> None:
    """Start a new simulation for TOPIC.

    TOPIC is a free-form description of the scenario to simulate,
    e.g. "인류 최초의 화성 식민지 100년".
    """
    from ese.config import config
    from ese.orchestrator.loop import OrchestratorLoop

    effective_depth = max_depth or config.max_depth
    effective_years = node_years or config.node_years
    effective_cost = cost_limit or config.cost_limit

    effective_agent_model = agent_model or config.agent_model
    effective_lang = lang or config.language

    console.print(f"[bold green]Starting simulation:[/] {topic}")
    console.print(
        f"  max_depth={effective_depth}, node_years={effective_years}, "
        f"cost_limit=${effective_cost:.2f}, agent_model={effective_agent_model}, lang={effective_lang}"
    )

    loop = OrchestratorLoop(
        max_depth=effective_depth,
        node_years=effective_years,
        cost_limit=effective_cost,
        agent_model=effective_agent_model,
        language=effective_lang,
    )
    simulation_id = loop.start(topic=topic)
    console.print(f"[bold]Simulation ID:[/] {simulation_id}")


@cli.command()
@click.argument("simulation_id")
def resume(simulation_id: str) -> None:
    """Resume a paused simulation by SIMULATION_ID."""
    from ese.orchestrator.loop import OrchestratorLoop

    console.print(f"[bold yellow]Resuming simulation:[/] {simulation_id}")
    loop = OrchestratorLoop()
    loop.resume(simulation_id=simulation_id)


@cli.command()
@click.argument("simulation_id")
@click.option(
    "--speed",
    default=1.0,
    type=float,
    help="Replay speed multiplier (default 1.0 = real-time).",
)
def replay(simulation_id: str, speed: float) -> None:
    """Replay a simulation by SIMULATION_ID."""
    from ese.storage.replay import ReplaySystem

    console.print(f"[bold cyan]Replaying simulation:[/] {simulation_id} (speed={speed}x)")
    replayer = ReplaySystem()
    replayer.replay(simulation_id=simulation_id, speed=speed)


@cli.command("list")
@click.option("--limit", default=20, type=int, help="Maximum number of rows to show.")
def list_simulations(limit: int) -> None:
    """List all simulations."""
    from ese.storage.database import Database

    db = Database()
    simulations = db.list_simulations(limit=limit)

    if not simulations:
        console.print("[dim]No simulations found.[/]")
        return

    table = Table(title="Simulations", show_lines=True)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Topic", style="white")
    table.add_column("Status", style="green")
    table.add_column("Turns", justify="right")
    table.add_column("Created", style="dim")

    for sim in simulations:
        table.add_row(
            sim.get("id", ""),
            sim.get("topic", ""),
            sim.get("status", ""),
            str(sim.get("turns", 0)),
            sim.get("created_at", ""),
        )

    console.print(table)


@cli.command()
@click.argument("simulation_id")
def status(simulation_id: str) -> None:
    """Check the status of a simulation by SIMULATION_ID."""
    from ese.storage.database import Database

    db = Database()
    sim = db.get_simulation(simulation_id)

    if sim is None:
        console.print(f"[red]Simulation not found:[/] {simulation_id}")
        raise SystemExit(1)

    console.print(f"[bold]Simulation:[/] {simulation_id}")
    for key, value in sim.items():
        console.print(f"  [dim]{key}:[/] {value}")


@cli.command()
@click.argument("topic")
@click.option(
    "--duration",
    default=24.0,
    type=float,
    help="Duration in hours (default 24).",
)
@click.option(
    "--cost-per-sim",
    default=5.0,
    type=float,
    help="USD cost limit per simulation (default $5).",
)
@click.option(
    "--total-cost",
    default=50.0,
    type=float,
    help="Total USD cost limit across all simulations (default $50).",
)
@click.option(
    "--max-depth",
    default=3,
    type=int,
    help="DFS tree depth per simulation (default 3).",
)
def auto(
    topic: str,
    duration: float,
    cost_per_sim: float,
    total_cost: float,
    max_depth: int,
) -> None:
    """Run autonomous 24h simulation loop for TOPIC.

    Continuously generates and explores scenarios, evolving the topic
    based on findings from each simulation cycle.

    The loop runs until the time limit, cost limit, or 3 consecutive
    failures are reached. Press Ctrl+C to stop early and save a report.
    """
    from ese.orchestrator.autonomous import AutonomousRunner

    runner = AutonomousRunner(
        initial_topic=topic,
        duration_hours=duration,
        cost_limit_per_sim=cost_per_sim,
        total_cost_limit=total_cost,
        max_depth=max_depth,
    )
    runner.run()


@cli.command()
@click.argument("topic")
@click.option(
    "--max-iterations",
    default=10,
    type=int,
    show_default=True,
    help="Maximum number of evolve cycles to run.",
)
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Override DFS tree depth per cycle (default from config).",
)
@click.option(
    "--node-years",
    default=None,
    type=int,
    help="Override simulated years per node (default from config).",
)
@click.option(
    "--cost-per-cycle",
    default=None,
    type=float,
    help="USD cost limit per simulation cycle (default from config).",
)
@click.option(
    "--total-cost",
    default=50.0,
    type=float,
    show_default=True,
    help="Total USD budget across all cycles.",
)
@click.option(
    "--convergence-threshold",
    default=0.05,
    type=float,
    show_default=True,
    help="Stop when best-score improvement is below this for --convergence-patience cycles.",
)
@click.option(
    "--convergence-patience",
    default=3,
    type=int,
    show_default=True,
    help="Number of non-improving cycles before declaring convergence.",
)
@click.option(
    "--lang",
    default=None,
    type=str,
    help="Output language (default from config). Examples: ko, ja, zh.",
)
@click.option(
    "--output-dir",
    default=None,
    type=click.Path(path_type=str),
    help="Directory for reports and logs (default: data/simulations).",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Validate config and print plan without running any simulation.",
)
@click.option(
    "--improve",
    "enable_improve",
    is_flag=True,
    default=False,
    help="Enable the improve step: auto-tune parameters between cycles based on diagnosis.",
)
@click.option(
    "--re-simulate",
    "enable_re_simulate",
    is_flag=True,
    default=False,
    help=(
        "Re-simulate the best scenario after each cycle with improved parameters "
        "to validate score improvement (uses ½ node_years, ½ cost budget)."
    ),
)
def evolve(
    topic: str,
    max_iterations: int,
    max_depth: int | None,
    node_years: int | None,
    cost_per_cycle: float | None,
    total_cost: float,
    convergence_threshold: float,
    convergence_patience: int,
    lang: str | None,
    output_dir: str | None,
    dry_run: bool,
    enable_improve: bool,
    enable_re_simulate: bool,
) -> None:
    """Run the /dormammu:evolve E2E improvement loop for TOPIC.

    Executes up to --max-iterations simulation cycles, each time evolving
    the topic based on the best-scoring hypothesis from the previous cycle.

    The loop terminates when any of these conditions are met:

    \b
    - --max-iterations cycles complete
    - --total-cost budget is exhausted
    - Convergence: best score improves by less than --convergence-threshold
      for --convergence-patience consecutive cycles
    - 3 consecutive cycle failures
    - Ctrl+C (graceful shutdown with report)

    Reports are written to --output-dir (default: data/simulations/).
    """
    from pathlib import Path as _Path
    from ese.config import config as _config
    from ese.orchestrator.evolve import EvolveConfig, EvolveOrchestrator

    effective_depth = max_depth or _config.max_depth
    effective_years = node_years or _config.node_years
    effective_cost = cost_per_cycle or _config.cost_limit
    effective_lang = lang or _config.language
    effective_output = _Path(output_dir) if output_dir else _config.data_dir

    cfg = EvolveConfig(
        initial_topic=topic,
        max_iterations=max_iterations,
        max_depth=effective_depth,
        node_years=effective_years,
        cost_limit_per_cycle=effective_cost,
        total_cost_limit=total_cost,
        convergence_threshold=convergence_threshold,
        convergence_patience=convergence_patience,
        language=effective_lang,
        output_dir=effective_output,
        dry_run=dry_run,
        enable_improve=enable_improve,
        enable_re_simulate=enable_re_simulate,
    )

    console.print(f"[bold green]Starting /dormammu:evolve:[/] {topic}")
    console.print(
        f"  iterations={max_iterations}, depth={effective_depth}, "
        f"node_years={effective_years}, cost/cycle=${effective_cost:.2f}, "
        f"budget=${total_cost:.2f}, lang={effective_lang}"
    )

    orchestrator = EvolveOrchestrator(cfg)
    state = orchestrator.run()

    if not dry_run:
        successful = len(state.successful_cycles)
        console.print(
            f"\n[bold]Evolve complete.[/] "
            f"{successful}/{len(state.history)} cycles succeeded | "
            f"Best score: {state.global_best_score:.3f} | "
            f"Total cost: ${state.total_cost:.4f}"
        )


@cli.command()
@click.option(
    "--node-years",
    default=None,
    type=int,
    help="Override current node_years value (for before/after comparison).",
)
@click.option(
    "--max-depth",
    default=None,
    type=int,
    help="Override current max_depth value (for before/after comparison).",
)
@click.option(
    "--cost-per-cycle",
    default=None,
    type=float,
    help="Override current cost_limit_per_cycle (for before/after comparison).",
)
@click.option(
    "--convergence-threshold",
    default=None,
    type=float,
    help="Override current convergence_threshold (for before/after comparison).",
)
def improve(
    node_years: int | None,
    max_depth: int | None,
    cost_per_cycle: float | None,
    convergence_threshold: float | None,
) -> None:
    """Generate an improvement plan from the latest benchmark diagnosis.

    Reads the latest benchmark report (from data/benchmarks/), runs diagnose
    to identify the weakest dimension, then computes concrete parameter
    adjustments and strategy hints for the next simulation cycle.

    Run `ese benchmark` first to generate a benchmark report.
    """
    from ese.config import config as _config
    from ese.diagnose import load_latest_benchmark, diagnose as run_diagnose
    from ese.improve import generate_improvement_plan, print_improvement_plan

    report = load_latest_benchmark()
    if report is None:
        console.print(
            "[red]No benchmark found.[/] Run [bold]ese benchmark[/] first."
        )
        raise SystemExit(1)

    diagnosis = run_diagnose(report)

    current_params = {
        "node_years": node_years or _config.node_years,
        "max_depth": max_depth or _config.max_depth,
        "cost_limit_per_cycle": cost_per_cycle or _config.cost_limit,
        "convergence_threshold": convergence_threshold or 0.05,
    }

    plan = generate_improvement_plan(diagnosis, current_params)
    print_improvement_plan(plan, current_params)

    console.print(
        f"\n[dim]Generated at: {plan.generated_at}[/]\n"
        f"[dim]Run [bold]ese evolve --improve <topic>[/] to apply these "
        "improvements automatically in the evolve loop.[/]"
    )


@cli.command()
def benchmark() -> None:
    """Run a fixed benchmark simulation and print score report.

    Uses a deterministic topic and parameters so results are comparable
    across code changes. Saves report to data/benchmarks/.
    """
    from ese.benchmark import run_benchmark, print_report

    report = run_benchmark()
    print_report(report)


@cli.command()
def diagnose() -> None:
    """Identify the weakest score dimension from the latest benchmark.

    Reads data/benchmarks/benchmark_*.json and maps the lowest-scoring
    dimension to a specific module, method, and actionable suggestion.

    Run `ese benchmark` first to generate a report.
    """
    from ese.diagnose import load_latest_benchmark, diagnose as run_diagnose, print_diagnosis

    report = load_latest_benchmark()
    if report is None:
        console.print(
            "[red]No benchmark found.[/] Run [bold]ese benchmark[/] first to generate one."
        )
        raise SystemExit(1)

    diagnosis = run_diagnose(report)
    print_diagnosis(diagnosis, report)


@cli.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind host.")
@click.option("--port", default=8000, show_default=True, type=int, help="Bind port.")
@click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode).")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the Dormammu API server for 2D visualization."""
    import uvicorn

    console.print(f"[bold green]Starting Dormammu API server[/] on http://{host}:{port}")
    uvicorn.run(
        "ese.api.server:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    cli()
