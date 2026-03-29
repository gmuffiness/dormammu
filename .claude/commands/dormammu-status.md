---
name: status
description: "Shows current goal, latest benchmark scores, feature progress, and evolution history"
---

# /dormammu:status

Displays the full harness status: current goal, benchmark trends, feature progress,
evolution history, and cost summary.

## Usage

```
/dormammu:status
ese status
```

**Trigger keywords:** "status", "how are we doing", "progress", "overview", "where are we"

## Instructions

### Step 1: Load All State

Read each state file, silently skip if missing:

```bash
cat .ese/scenario.json 2>/dev/null
ls -t data/benchmarks/ 2>/dev/null | head -3
cat .ese/evolution.jsonl 2>/dev/null | tail -10
cat feature_list.json 2>/dev/null
cat claude-progress.txt 2>/dev/null | tail -20
```

### Step 2: Parse Benchmark History

From the two most recent benchmark files in `data/benchmarks/`, extract scores
to show current values and trend direction (↑ ↓ →).

### Step 3: Count Features

From `feature_list.json`, count:
- Total features
- Complete (`"status": "complete"`)
- In-progress (`"status": "in_progress"`)
- Pending (`"status": "pending"`)

### Step 4: Display Status

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dormammu Harness Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Current Goal:
  "<topic>"  [macro/micro]
  Set: <timestamp>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Latest Benchmark:  <timestamp>
  character_fidelity     <score>  <trend>
  fandom_resonance       <score>  <trend>
  emergence              <score>  <trend>
  diversity              <score>  <trend>
  plausibility           <score>  <trend>

  Overall Score          <score>  <trend>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature Progress:  <complete>/<total> complete
  [✓] <N> complete
  [~] <N> in progress
  [ ] <N> pending

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Evolution History:  <N> cycles run
  Best score:   <score>   (cycle <N>)
  Last cycle:   <result>  at <timestamp>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recommended Next Action:
  <based on current state — e.g., "Run /dormammu:improve — agent_diversity at 0.45 is the weakest point">

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 5: Recommended Action Logic

Choose the recommendation based on state:

| Condition | Recommendation |
|-----------|---------------|
| No scenario set | `/dormammu:imagine "your what-if"` — no scenario configured yet |
| No research yet | `/dormammu:research` — run fandom research first |
| No benchmark yet | `/dormammu:benchmark` — establish a baseline first |
| Any dimension < 0.5 | `/dormammu:improve` — <weakest dimension> needs urgent work |
| All dimensions 0.5–0.8 | `/dormammu:evolve --hours 2` — ready for autonomous improvement |
| All dimensions > 0.8 | `/dormammu:deepen` — converged! Deepen the best scenario |
| Evolution in progress | `/dormammu:status` again after current cycle completes |
