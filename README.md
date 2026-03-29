# Dormammu — Dormammu

**English** | [한국어](README.ko.md)

**A simulation-specific harness for autonomous AI development**

Dormammu lets AI agents autonomously build, run, and improve world simulations. Unlike generic coding harnesses that measure code volume, Dormammu uses simulation output quality as the feedback signal — the product tells the AI what to improve next.

---

## What Makes This Different

Generic harnesses ask: *"Did the code compile?"*
Dormammu asks: *"Is the simulation interesting?"*

| | Generic Harness | Dormammu |
|---|---|---|
| **Feedback signal** | Tests pass / fail | Simulation quality scores |
| **What gets measured** | Lines of code, coverage | Emergence, narrative, diversity, novelty |
| **Spec** | Static, written upfront | Product output drives development |
| **Output** | Code diff | Generation-over-generation simulation improvement |

The key insight: simulation output is *quantitatively measurable*. A score moving from `0.31 → 0.58` tells the AI exactly what changed and whether it helped. No human judgment required in the loop.

---

## Quick Start

```bash
# Install
git clone https://github.com/gmuffiness/dormammu.git
cd emergent-world
pip install -e ".[dev]"
cp .env.example .env  # Add your OPENAI_API_KEY

# Set a simulation goal
dormammu run "What future awaits humanity over the next 100 years?"

# Run a quick benchmark (fixed params, ~$0.30)
dormammu run "50 years of humanity's first Mars colony" --max-depth 1 --cost-limit 0.5

# Autonomous improvement loop (5 hours)
dormammu evolve --hours 5
```

---

## The Feedback Loop

```
┌─ Build ──────────────────────────────────┐
│ AI modifies simulation engine code       │
└──────────────┬───────────────────────────┘
               ↓
┌─ Run ────────────────────────────────────┐
│ dormammu benchmark (fixed-condition sim)      │
└──────────────┬───────────────────────────┘
               ↓
┌─ Measure ────────────────────────────────┐
│ emergence: 0.45  narrative: 0.62         │
│ diversity: 0.31  novelty: 0.50           │
│ composite: 0.48                          │
└──────────────┬───────────────────────────┘
               ↓
┌─ Diagnose ───────────────────────────────┐
│ "diversity is lowest → agents/agent.py   │
│  decide_action() needs persona-aware     │
│  prompt differentiation"                 │
└──────────────┬───────────────────────────┘
               ↓
           (repeat)
```

Each generation, the AI identifies the weakest score, traces it to the responsible module, makes a targeted code change, and verifies improvement before committing. Score drops trigger automatic rollback.

---

## Commands

| Command | Description |
|---------|-------------|
| `dormammu run <topic>` | Start a new simulation with DFS scenario exploration |
| `dormammu resume <id>` | Resume a paused simulation |
| `dormammu replay <id>` | Replay a completed simulation at controllable speed |
| `dormammu list` | List all simulations with scores and status |
| `dormammu status <id>` | Show simulation state, scores, and cost |
| `dormammu auto` | 24-hour autonomous simulation loop (generates topics, runs, repeats) |
| `dormammu serve` | Start the FastAPI server for the 2D visualization frontend |
| `dormammu diagnose` | Identify the weakest quality dimension and map it to source code |
| `dormammu evolve --hours N` | Autonomous improvement loop: benchmark → diagnose → improve → repeat |

---

## Simulation Examples

The engine handles free-form topics across four categories:

**Future prediction**
- "What future awaits humanity over the next 100 years?"
- "50 years in a world where AI has fully replaced human jobs"
- "100 years of a city after sea levels rise by 5 meters due to climate change"

**Alternate history (what-if)**
- "Attack on Titan — what if Eren never activated the Rumbling? 100 years later"
- "What if the Cold War turned hot? The next 50 years"
- "What if the internet was never invented? Up to the present day"

**Fictional universe simulation**
- "The Three-Body Problem — 50 years after the Trisolarans arrive on Earth"
- "Lord of the Rings — what if Sauron reclaimed the One Ring?"
- "Star Wars — 100 years of a galaxy where the Empire won"

**Social experiment**
- "30 years of a nation with universal basic income"
- "100 years in a world with no borders"
- "A society that abolished currency and switched to a credit-based economy"

---

## Architecture

```
Dormammu
├── Engine          DFS scenario tree, agent turns, world state
│   ├── ScenarioTree    Branching hypothesis tree (DFS traversal)
│   ├── WorldState      Agents, relationships, events, resources
│   └── TurnExecutor    One turn: agents decide → narrative generated
│
├── Agents          LLM-driven personas with memory and personality
│   ├── Persona         Big-5 traits, backstory, goals (per agent)
│   ├── Agent           Memory (rolling, pruned by emotional weight)
│   └── Interaction     OpenAI calls with retry and cost tracking
│
├── Hypothesis      Branch generation, scoring, and SF inspiration
│   ├── Generator       3 child branches per node via LLM
│   ├── Evaluator       Scores: emergence (35%), narrative (30%),
│   │                   diversity (20%), novelty (15%)
│   └── Inspiration     SF/literary seed injection every 3 generations
│
├── Harness         The autonomous improvement layer
│   ├── Benchmark       Fixed-parameter simulation for consistent scoring
│   ├── Diagnose        Maps weak scores to responsible source modules
│   └── Evolve          Outer loop: benchmark → diagnose → improve → commit
│
├── Orchestrator    Async DFS driver, scale detection, cost management
│
├── Storage         SQLite (WAL mode), JSONL turn logs, replay
│
└── Frontend        FastAPI + React 2D canvas visualization
```

**Dependency rules:** `engine/` never imports from `orchestrator/` or `api/`. `agents/` never imports from `orchestrator/`. The harness sits outside the simulation — it reads scores and modifies source, never touching simulation internals directly.

---

## 2D Visualization

`dormammu serve` starts a FastAPI backend (port 8000). The React frontend (port 5173, `cd frontend && npm run dev`) renders:

- **Canvas2D** — real-time agent positions and interactions on a 2D map
- **ScenarioTree** — live DFS branch exploration with scores per node
- **EventLog** — turn-by-turn narrative stream
- **Dashboard** — composite score trends across generations
- **TimelineControls** — scrub through any completed simulation

---

## Quality Scores

| Score | Weight | What it measures |
|-------|--------|-----------------|
| `emergence` | 35% | Unexpected, unscripted events arose from agent interactions |
| `narrative` | 30% | The story is interesting and worth observing |
| `diversity` | 20% | Agents behaved distinctly from one another |
| `novelty` | 15% | This branch differs meaningfully from sibling branches |
| `composite` | — | Weighted sum; >0.3 expands the branch, ≤0.3 prunes it |

---

## Inspired By

- **[Karpathy's autoresearch](https://github.com/karpathy/autoresearch)** — the experiment → measure → iterate pattern. Fixed-duration runs, single scalar metric, automatic discard on regression.
- **[Ouroboros](https://github.com/Q00/ouroboros)** — specification-first harness. Immutable seed (CLAUDE.md + feature_list.json), multi-stage evaluation, drift detection.
- **[Anthropic autonomous-coding quickstart](https://github.com/anthropics/claude-quickstarts/tree/main/autonomous-coding)** — feature_list.json as progress tracker, claude-progress.txt for session continuity, git commits as rollback points.
- **[Stanford Generative Agents](https://arxiv.org/abs/2304.03442)** — agent memory streams, reflection, and planning. Dormammu extends this with an outer harness that measures and improves agent quality automatically.

---

## Tech Stack

Python 3.10+, OpenAI API (gpt-4o), SQLite + sqlite-utils, FastAPI + uvicorn, Click, Rich — React 18 + Vite + TypeScript + Tailwind CSS + HTML5 Canvas

---

## License

MIT
