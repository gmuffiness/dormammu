# Dormammu Quickstart

> **Dormammu** — AI agents live in simulated worlds, branch into alternative timelines via DFS, and evolve autonomously through quality metrics.

## Prerequisites

- Python 3.10+
- Node.js 18+
- OpenAI API key (optional — fallback mode works without it)

## Install

```bash
# Clone and enter
cd apps/emergent-world

# Python deps
pip install -e ".[dev]"

# Frontend deps
cd frontend && npm install && cd ..

# Environment
cp .env.example .env
# Edit .env → set OPENAI_API_KEY=sk-...
```

## Run

### One-command start (backend + frontend)

```bash
# macOS/Linux
./scripts/dev.sh

# Windows
.\scripts\dev.ps1
```

Or manually:

```bash
# Terminal 1: Backend (localhost:8000)
ese serve --reload

# Terminal 2: Frontend (localhost:5173)
cd frontend && npm run dev
```

## Demo (5 minutes)

### 1. Simulate — watch agents live

```bash
ese run "가뭄이 닥친 작은 마을" --max-depth 2 --cost-limit 1.0
```

Open `http://localhost:5173` → click the simulation → watch Canvas + scenario tree.

### 2. Measure — see quality metrics

Click any scenario tree node → metrics dashboard shows emergence / narrative / diversity / novelty scores.

### 3. Evolve — AI improves the simulation

```bash
ese evolve --cycles 3 --seed 42
```

The engine automatically: benchmark → diagnose weakness → improve code → re-simulate → repeat.

### 4. Compare — before vs after

In the UI, open the Split Compare View to see side-by-side tree statistics and per-metric improvement deltas.

## CLI Reference

```bash
ese run <topic>          # Run a simulation
ese serve                # Start API server
ese evolve               # AI self-improvement loop
ese list                 # List all simulations
ese status <id>          # Check simulation status
ese replay <id>          # Replay a simulation
ese auto                 # Autonomous 24h mode
```

## Architecture

```
/ese:simulate → DFS scenario tree → quality metrics → /ese:evolve
     D1              D1                   D2              D3
  (agents)     (branch & prune)    (measure quality)  (AI improves)
```

The **Harness Triangle**: D1 (tree visualization) + D2 (metrics) + D3 (evolve loop) work as an inseparable unit.

## Key Files

| Path | What |
|------|------|
| `src/ese/main.py` | CLI entry point |
| `src/ese/orchestrator/loop.py` | DFS orchestrator |
| `src/ese/orchestrator/evolve.py` | Evolve E2E loop |
| `src/ese/hypothesis/evaluator.py` | 4-dim quality scorer |
| `frontend/src/components/Canvas2D.tsx` | 2D world renderer |
| `frontend/src/components/ScenarioTree.tsx` | Tree browser |
| `frontend/src/components/MetricsDashboard.tsx` | Metrics overlay |
