---
name: evolve
description: "Continuous autonomous improvement loop — runs benchmark/diagnose/improve cycles until convergence"
---

# /dormammu:evolve

Autonomous improvement loop. Repeatedly benchmarks, diagnoses, and improves the
simulation until all scores exceed 0.8 or the time/cycle limit is reached.

## Usage

```
/dormammu:evolve
/dormammu:evolve --hours 2
/dormammu:evolve --cycles 5
```

**Trigger keywords:** "evolve", "keep improving", "autonomous loop", "don't stop improving",
"run until good", "improve until 0.8"

## Instructions

### Step 0: Parse Parameters

- `--hours N`: run for approximately N hours (estimate ~20 min per cycle)
- `--cycles N`: run exactly N cycles
- No argument: run until convergence (all scores > 0.8) or 10 cycles max

Set `max_cycles` accordingly.

### Step 1: Announce Start

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dormammu Evolution Loop Starting
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Goal:      <topic from .ese/goal.json or "default">
Strategy:  <cycles or hours>
Target:    All dimensions > 0.8

Starting cycle 1...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 2: Evolution Loop

For each cycle (1 to max_cycles):

#### 2a. Benchmark
Run `/dormammu:benchmark` logic:
```bash
ese benchmark 2>&1
```
Read scores from latest `data/benchmarks/` file.

#### 2b. Check Convergence
If ALL dimensions score > 0.8:
```
[✓] Converged! All dimensions above 0.8 threshold.
Stopping evolution loop.
```
Break out of loop.

#### 2c. Diagnose
Run `/dormammu:diagnose` logic to find the weakest dimension and target feature.

#### 2d. Improve
Run `/dormammu:improve` logic:
- Implement the chosen feature
- Run tests
- Re-benchmark
- Commit if improved, revert if regressed

#### 2e. Log to Evolution Journal

Append to `.ese/evolution.jsonl`:
```json
{"cycle": 1, "timestamp": "<ISO>", "scores": {"narrative_coherence": 0.72, ...}, "overall": 0.64, "feature_attempted": "F002", "result": "improved", "delta": 0.05}
```

#### 2f. Cycle Summary

```
Cycle <N> complete:
  Feature: [<F-ID>] <name>
  Result:  IMPROVED / REVERTED
  Overall: <before> → <after>
  Weakest: <dimension> (<score>)

Continuing to cycle <N+1>...
```

### Step 3: Final Report

After loop ends (convergence, cycle limit, or hour limit):

Generate `.ese/reports/evolution_<timestamp>.md`:

```markdown
# Dormammu Evolution Report
Generated: <timestamp>
Goal: <topic>

## Summary
- Cycles completed: <N>
- Starting score: <score>
- Final score: <score>
- Improvement: +<delta>

## Cycle History
| Cycle | Feature | Result | Overall Score |
|-------|---------|--------|---------------|
| 1     | F002    | +0.05  | 0.69          |
| 2     | F001    | +0.08  | 0.77          |
...

## Features Completed
- [F002] Persona-driven action divergence
- [F001] Agent-to-agent dialogue

## Remaining Weaknesses
- <dimension>: <score> (below 0.8 threshold)

## Next Steps
- Run /dormammu:diagnose for the next weakness
- Or /dormammu:simulate to see the improved simulation in action
```

Display summary in conversation:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Evolution Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Cycles:          <N>
Starting Score:  <score>
Final Score:     <score>
Improvement:     +<delta>

Features Implemented: <list>

Status: <CONVERGED (all > 0.8) / LIMIT REACHED>

Full report: .ese/reports/evolution_<timestamp>.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: /dormammu:simulate to see results, or /dormammu:status for overview
```
