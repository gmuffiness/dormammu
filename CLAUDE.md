# CLAUDE.md — Dormammu Agent Harness

> **This file is the operating manual for an AI coding agent.** Read it completely before writing a single line of code. Every section exists to prevent wasted work.

---

## 1. Project Overview

**Dormammu** is a research prototype that simulates living worlds where AI agents with memory, personality, goals, and relationships interact autonomously over simulated time. The core mechanism is a **Depth-First Search (DFS) scenario tree**: starting from a free-form topic (e.g., "인류 최초의 화성 식민지 50년"), the engine generates branching hypotheses, simulates each branch via LLM-driven agents, scores each branch on emergence/narrative/diversity/novelty, and either expands (explores deeper) or prunes (abandons) each path. A 2D React canvas visualizer streams results in real time via FastAPI.

```
Topic
  └─ Genesis (root node)
       ├─ Hypothesis A  [DFS: simulate → score → expand/prune]
       │    ├─ Hypothesis A-1
       │    └─ Hypothesis A-2
       ├─ Hypothesis B
       └─ Hypothesis C

Dormammu Architecture
================
CLI (ese run / ese serve / ese auto)
  └─ OrchestratorLoop            # drives DFS lifecycle, async event loop
       ├─ HypothesisGenerator    # generates 3 child branches per node via LLM
       ├─ PersonaGenerator       # creates N agents with Big-5 traits via LLM
       ├─ Simulation             # owns ScenarioTree + WorldState + Agents
       │    ├─ ScenarioTree      # tree of ScenarioNodes, DFS traversal
       │    ├─ WorldState        # snapshot: agents, events, resources, metadata
       │    └─ TurnExecutor      # executes one turn: agents decide → narrative
       ├─ HypothesisEvaluator    # scores completed node, decide expand/prune
       ├─ InspirationSystem      # injects SF/literary seeds every 3 generations
       └─ TurnLogger / Database  # SQLite via sqlite-utils (WAL mode)

FastAPI Server (ese serve → localhost:8000)
  └─ /api/simulations/*          # REST endpoints for visualization

React Frontend (localhost:5173)
  └─ vite.config.ts proxies /api → localhost:8000
  └─ Canvas2D, SimulationViewer, ScenarioTree, Dashboard, EventLog
```

**Tech stack:** Python 3.10+, OpenAI API (gpt-4o), SQLite + sqlite-utils, FastAPI + uvicorn, Click CLI, Rich terminal UI, React 18 + Vite + TypeScript + Tailwind CSS, HTML5 Canvas.

---

## 2. Quick Start — Session Boot Protocol

**Run these steps in order at the start of every session, without skipping.**

```bash
# 1. Navigate to project root
cd /Users/daejeong/agent-workspace/personal-agent-workspace/apps/emergent-world

# 2. Check session state
cat claude-progress.txt 2>/dev/null || echo "(no prior progress file)"

# 3. Check the feature list
cat feature_list.json 2>/dev/null || echo "(no feature list yet)"

# 4. Verify Python environment is active
source .venv/bin/activate
python -c "import ese; print('Dormammu importable')"

# 5. Verify OPENAI_API_KEY is set (needed for LLM tests)
grep OPENAI_API_KEY .env 2>/dev/null || echo "WARNING: .env missing key"

# 6. Run baseline tests — all must pass before any change
pytest tests/ -v

# 7. Identify the highest-priority pending feature from feature_list.json
# 8. Begin implementation
```

**After boot, write your plan as a brief comment in claude-progress.txt before touching code.**

---

## 3. Architecture & Module Boundaries

### Module Map

| Module | Path | Responsibility |
|--------|------|---------------|
| `engine/world_state` | `src/ese/engine/world_state.py` | `WorldState` dataclass: agents dict, relationships, events list, resources, metadata. Serialization + `summary()` for LLM prompts. |
| `engine/scenario_tree` | `src/ese/engine/scenario_tree.py` | `ScenarioTree` + `ScenarioNode`: DFS tree, `next_pending()`, `add_child()`, `is_leaf()`, `dfs()`. |
| `engine/turn` | `src/ese/engine/turn.py` | `TurnExecutor.execute()`: runs one turn — collects agent actions, generates narrative, returns `TurnResult`. |
| `engine/simulation` | `src/ese/engine/simulation.py` | `Simulation` dataclass: owns tree + world state + agents. `run_turn_for_node()` for DFS-aware execution. Manages per-node world state snapshots. |
| `agents/persona` | `src/ese/agents/persona.py` | `Persona` dataclass + `PersonaGenerator`: Big-5 traits, backstory, goals. Generates personas via LLM or fallback. |
| `agents/agent` | `src/ese/agents/agent.py` | `Agent` + `Memory`: rolling memory (cap 20, pruned by emotional_weight), `decide_action()` via LLM, `update_relationship()`. |
| `agents/interaction` | `src/ese/agents/interaction.py` | `AgentInteraction`: thin wrapper around OpenAI client. `get_action()` with retry + cost tracking. |
| `hypothesis/generator` | `src/ese/hypothesis/generator.py` | `HypothesisGenerator.generate()`: produces 3 `Hypothesis` objects per node via LLM, sorted by probability descending. |
| `hypothesis/evaluator` | `src/ese/hypothesis/evaluator.py` | `HypothesisEvaluator.evaluate()`: scores completed node on 4 dimensions → `EvaluationResult`. Composite = 0.35*emergence + 0.30*narrative + 0.20*diversity + 0.15*novelty. Expand threshold: composite > 0.3. |
| `hypothesis/inspiration` | `src/ese/hypothesis/inspiration.py` | `InspirationSystem`: SF/literary seed bank, `pick()`, `build_injection()`. Injected every 3rd hypothesis generation at each depth. |
| `orchestrator/loop` | `src/ese/orchestrator/loop.py` | `OrchestratorLoop`: top-level async DFS driver. Detects macro/micro scale (keyword match). Generates criteria → agents → initial branches → DFS loop. |
| `orchestrator/autonomous` | `src/ese/orchestrator/autonomous.py` | `AutonomousRunner`: 24h continuous loop. Per-cycle: run sim → analyze → generate next topic via LLM → repeat. Stops on time/cost/3 consecutive failures. |
| `storage/database` | `src/ese/storage/database.py` | `Database`: sqlite-utils wrapper. Tables: `simulations`, `turns`, `world_states`, `hypotheses`. WAL mode + 30s busy timeout. Auto-recreates on corruption. |
| `storage/logger` | `src/ese/storage/logger.py` | `TurnLogger`: logs turn results and events to DB + JSONL files per simulation. |
| `storage/replay` | `src/ese/storage/replay.py` | `ReplaySystem`: replays a completed simulation at controllable speed. |
| `api/routes` | `src/ese/api/routes.py` | FastAPI route handlers. Endpoints: `GET /api/simulations`, `/api/simulations/{id}`, `/api/simulations/{id}/turns`, `/api/simulations/{id}/agents`, `/api/simulations/{id}/tree`, `/api/simulations/{id}/environment`, `/api/simulations/{id}/world-state/{turn}`. |
| `api/server` | `src/ese/api/server.py` | FastAPI app creation, CORS, router registration. |
| `api/environment` | `src/ese/api/environment.py` | `generate_environment()`: generates 2D map layout (zones, landmarks, agent positions) for the canvas renderer. |
| `api/models` | `src/ese/api/models.py` | Pydantic response models for all API endpoints. |
| `config` | `src/ese/config.py` | `Config(BaseSettings)`: singleton `config`. Reads `.env`. Keys: `OPENAI_API_KEY`, `OPENAI_MODEL`, `MAX_DEPTH`, `NODE_YEARS`, `COST_LIMIT`, `DATA_DIR`, `DB_PATH`. |
| `main` | `src/ese/main.py` | Click CLI: `dormammu run`, `ese resume`, `ese replay`, `ese list`, `ese status`, `dormammu auto`, `dormammu serve`. |
| `frontend/` | `frontend/src/` | React + Vite + TypeScript + Tailwind. Components: `Canvas2D`, `SimulationViewer`, `ScenarioTree`, `Dashboard`, `AgentDetail`, `EventLog`, `TimelineControls`. Hooks: `useSimulation`, `useReplay`. API client in `src/api/client.ts`. |

### Dependency Rules (strictly enforced)

```
engine/       MUST NOT import from orchestrator/ or api/
agents/       MUST NOT import from orchestrator/
storage/      MUST NOT import from engine/ or agents/ (except TYPE_CHECKING)
api/          imports from storage/ and engine/ only
orchestrator/ imports from everything except api/
frontend/     REST only — never imports Python
```

When in doubt, check: if adding an import would create a cycle, it's wrong.

### Key Data Flow

```
OrchestratorLoop._run_loop()
  → HypothesisGenerator → [ScenarioNode, ...]
  → PersonaGenerator    → [Agent, ...]
  → DFS while loop:
      ScenarioTree.next_pending() → node
      _simulate_node():
        for turn in range(node_years // years_per_turn):
          Simulation.run_turn_for_node()
            TurnExecutor.execute()
              Agent.decide_action() → action_dict, tokens
              [build narrative via LLM]
            → TurnResult(world_state, narrative, cost_usd)
          TurnLogger.log_turn(result)
      HypothesisEvaluator.evaluate() → EvaluationResult
      if should_expand: _expand_node() → add children
      else: node.status = PRUNED
```

### Scale Detection

`OrchestratorLoop._detect_scale(topic)` checks for macro keywords (civilization, 인류, empire, 세기, millennium, etc.). Macro → `years_per_turn=25, agents=3-5`. Micro → `years_per_turn=1, agents=default(5)`.

---

## 4. Development Commands

```bash
# --- Python ---

# Install (run once, or after pulling new dependencies)
pip install -e ".[dev]"

# Run all tests (MUST pass before and after every change)
pytest tests/ -v

# Run tests matching a pattern
pytest tests/ -v -k "scenario_tree"

# Benchmark simulation — fixed low-cost params for quick quality check
# No API key? It runs in fallback mode (no LLM, scores = 0.5)
ese run "인류 최초의 화성 식민지 50년" --max-depth 1 --cost-limit 0.5

# Full CLI reference
ese --help
ese run --help
ese auto --help

# Start API server (dev mode with auto-reload)
ese serve --reload

# List simulations in DB
ese list

# Type check (if mypy is available)
mypy src/ese/

# Lint (if ruff is available)
ruff check src/

# --- Frontend ---

# Install frontend deps (run once)
cd frontend && npm install

# Start frontend dev server (proxies /api → localhost:8000)
cd frontend && npm run dev

# TypeScript type check (MUST pass when frontend is changed)
cd frontend && npm run typecheck
# equivalent: cd frontend && npx tsc --noEmit

# Build for production
cd frontend && npm run build

# --- Environment ---

# .env file (project root) — required for LLM features
# Copy from .env.example and fill in your key:
cp .env.example .env
# Then edit: OPENAI_API_KEY=sk-...

# Config defaults (from config.py):
# OPENAI_MODEL=gpt-4o
# MAX_DEPTH=5
# NODE_YEARS=100
# COST_LIMIT=10.0
# DATA_DIR=data/simulations/
# DB_PATH=data/simulations/ese.db
```

---

## 5. Self-Verification Protocol

**Never mark a feature complete without running all steps below.**

```
Step 1: pytest tests/ -v
        → All tests must pass. Zero failures, zero errors.
        → If new code was added, at minimum one test covers it.

Step 2: ese run "인류 최초의 화성 식민지 50년" --max-depth 1 --cost-limit 0.5
        → Must complete without exception.
        → If OPENAI_API_KEY is set: check that scores are not all 0.5.
        → If no API key: verify fallback mode still produces turn output.

Step 3 (frontend changes only):
        cd frontend && npm run typecheck
        → Zero TypeScript errors.

Step 4: git commit -m "feat: <description>"
        → Commit only when tests pass.

Step 5: Update claude-progress.txt with what was done and any blockers.

Step 6: Update feature_list.json — set completed feature's status to "completed".
```

---

## 6. Benchmark & Quality Feedback Loop

The benchmark command is the quality signal. Run it before and after every substantive change.

**Benchmark command:**
```bash
ese run "인류 최초의 화성 식민지 50년" --max-depth 1 --cost-limit 0.5
```

**What to measure** (from `EvaluationResult`):

| Score | Weight | Meaning |
|-------|--------|---------|
| `emergence_score` | 35% | Unexpected, unscripted events arose |
| `narrative_score` | 30% | Story is interesting to observe |
| `agent_diversity_score` | 20% | Agents behaved distinctly |
| `novelty_score` | 15% | Branch is different from siblings |
| `composite_score` | 100% | Weighted sum; >0.3 → expand, ≤0.3 → prune |

**Decision rule:**
- Composite score improved or unchanged → commit and continue.
- Composite score dropped → revert with `git checkout -- .` and try a different approach.
- No API key → scores default to 0.5 (fallback). Only commit if tests pass.

**Where scores appear:** In the Rich terminal output during `dormammu run`, printed per node as `Score: X.XX | <rationale>`.

---

## 7. How to Pick the Next Task

```
1. cat feature_list.json
2. Find the first item with "status": "pending" and the highest "priority" value.
3. Edit feature_list.json — set that item's "status" to "in_progress".
4. Work on it.
5. When done, set "status" to "completed" in feature_list.json.
6. Update claude-progress.txt with a summary.
7. Go back to step 1.
```

**If feature_list.json does not exist yet**, create it with this structure:
```json
[
  {
    "id": "F001",
    "title": "Example feature",
    "description": "What it does and why",
    "priority": 1,
    "status": "pending",
    "module": "engine/",
    "acceptance": "Tests pass + benchmark score >= baseline"
  }
]
```

**If claude-progress.txt does not exist yet**, create it and write:
- Date/time session started
- What you plan to work on this session
- Any relevant context from previous sessions

---

## 8. Error Recovery

| Problem | Action |
|---------|--------|
| Tests fail after a change | `git checkout -- .` to revert. Re-read the failing test to understand intent. Try a different approach. |
| Benchmark score drops | `git checkout -- .`. Do not merge the change. |
| `OPENAI_API_KEY` missing | All LLM calls silently fall back (agents return `observe`, evaluator returns 0.5 scores). Work on non-LLM features: engine logic, tree traversal, API endpoints, frontend, storage. |
| OpenAI rate limit / timeout | The code has retry logic in `AgentInteraction`. If rate limits are persistent, use `--cost-limit 0.1 --max-depth 1` for local testing only. |
| Frontend build fails | Fix TypeScript errors shown by `npm run typecheck` before proceeding. Never skip this step. |
| SQLite write conflict | Handled — WAL mode + 30s busy timeout + auto-recreate on corruption in `Database.__init__`. |
| Import cycle detected | Consult the dependency rules in Section 3. Never import `orchestrator/` from `engine/` or `agents/`. |
| Same test fails 3+ times | Stop. Re-read the test and the relevant source file completely. Do not guess — understand the interface. |

**Hard rules:**
- NEVER delete existing tests.
- NEVER mark a feature complete without running `pytest tests/ -v`.
- NEVER force-push to main.
- NEVER modify test assertions to make tests pass — fix the production code.

---

## 9. Git Conventions

```bash
# One feature = one commit. Message format:
git commit -m "feat: <what changed>"     # new capability
git commit -m "fix: <what was wrong>"    # bug fix
git commit -m "refactor: <what moved>"  # no behavior change
git commit -m "test: <what tested>"     # tests only
git commit -m "docs: <what documented>" # docs/comments only

# Always verify before committing:
pytest tests/ -v               # must pass
# (frontend changed?) cd frontend && npm run typecheck  # must pass

# Check for leftover debug code before committing:
grep -r "print\|breakpoint\|pdb\|TODO\|HACK\|console\.log" src/ frontend/src/ --include="*.py" --include="*.ts" --include="*.tsx"
```

---

## 10. Known Issues & Gotchas

### Python

- **Python 3.10+ required.** The codebase uses `match` statements and `X | Y` union types. Do not downgrade syntax.
- **`asyncio.run()` inside `asyncio.run()`** — `OrchestratorLoop.start()` calls `asyncio.run()`. Use `start_async()` if you are already inside an async context (e.g., `AutonomousRunner`). Never nest `asyncio.run()`.
- **`WorldState` is treated as immutable per turn** — each `TurnResult` contains a new `WorldState`. Do not mutate the previous turn's state; produce a new one.
- **Memory pruning** — `Agent.remember()` keeps memories sorted by `(-emotional_weight, -turn)`. Cap is `MAX_MEMORY_CONTEXT * 2 = 40`; prunes to 20. High-weight memories survive longer.
- **Scale detection is keyword-based** — `OrchestratorLoop._detect_scale()` does a case-insensitive substring match. Adding new macro keywords requires updating `MACRO_KEYWORDS` in `loop.py`.
- **SF injection frequency** — `InspirationSystem` is injected every `SF_INJECTION_EVERY_N = 3` hypothesis generations at the same depth level. This is tracked in `_gen_count_per_depth`.
- **Database singleton per process** — `Database()` is instantiated fresh on each API request in `routes.py`. This is intentional (WAL mode handles concurrent reads). Do not cache it across requests.

### Frontend

- **Vite proxy** — `vite.config.ts` proxies all `/api` requests to `http://localhost:8000`. The API server must be running (`dormammu serve`) before the frontend works.
- **TypeScript strict mode** — `tsconfig.json` has strict checks. Always run `npm run typecheck` after any `.ts` / `.tsx` change.
- **Canvas rendering** — `Canvas2D.tsx` and `SimulationRenderer.ts` use HTML5 Canvas directly. Avoid DOM-manipulation patterns; pass data through React props and re-render the canvas imperatively.
- **No external state library** — state is managed with `useState` + `useEffect` hooks in `useSimulation.ts` and `useReplay.ts`. Keep it that way unless the task explicitly requires a store.

### Cost

- **Default `cost_limit` is $10.00** (from config). Always use `--cost-limit 0.5` or lower during development/testing to avoid accidental high spend.
- **`AutonomousRunner` default total cost cap is $50.00** — only trigger `dormammu auto` intentionally.
- **Cost tracking** — `total_cost_usd` on `Simulation` accumulates per `TurnResult.cost_usd`. The DB stores it and the API exposes it. Never reset it mid-simulation.
