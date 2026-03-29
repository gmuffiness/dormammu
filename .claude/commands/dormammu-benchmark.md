---
name: benchmark
description: "Runs a benchmark simulation and displays scores with trend comparison"
---

# /dormammu:benchmark

Runs a benchmark simulation, displays scores, and compares with the previous run.

## Usage

```
/dormammu:benchmark
ese benchmark
```

**Trigger keywords:** "benchmark", "run benchmark", "measure quality", "score it"

## Instructions

### Step 1: Read Current Goal

Check `.ese/goal.json`:
```bash
cat .ese/goal.json 2>/dev/null || echo "NO_GOAL"
```

If no goal, note: "No goal set. Using default benchmark topic. Run /dormammu:goal to set a custom scenario."

### Step 2: Run Benchmark

```bash
cd <project-root> && ese benchmark 2>&1
```

Show: "Running benchmark simulation..." while it executes.

### Step 3: Find Latest Results

```bash
ls -t data/benchmarks/ | head -5
```

Read the most recent benchmark file:
```bash
cat data/benchmarks/<latest-file>
```

### Step 4: Display Scores

Parse and display with clean formatting:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Benchmark Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  narrative_coherence    0.72  ████████░░  [good]
  agent_diversity        0.58  ██████░░░░  [needs work]
  emergent_conflict      0.45  █████░░░░░  [weak]
  world_consistency      0.81  ████████░░  [good]

  Overall Score          0.64

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Bar fill: use 10 characters, filled proportionally to the score.

### Step 5: Compare with Previous

If a prior benchmark exists in `data/benchmarks/`, load the second-most-recent and diff:

```
Trend vs. Previous Run:
  narrative_coherence    0.65 → 0.72  ↑ +0.07
  agent_diversity        0.61 → 0.58  ↓ -0.03
  emergent_conflict      0.45 → 0.45  → unchanged
  world_consistency      0.78 → 0.81  ↑ +0.03
```

If no previous run: "First benchmark — no prior to compare."

### Step 6: Suggest Next Action

Based on the lowest-scoring dimension:

```
Weakest dimension: <name> (<score>)

Next:
  /dormammu:diagnose   — find the specific code causing this weakness
  /dormammu:improve    — run one targeted improvement cycle
  /dormammu:evolve     — start autonomous multi-cycle improvement
```
