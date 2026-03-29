---
name: diagnose
description: "Diagnoses simulation weaknesses and maps them to specific code locations"
---

# /dormammu:diagnose

Analyzes the latest benchmark, identifies the weakest dimension, maps it to
code, and recommends the next feature to implement.

## Usage

```
/dormammu:diagnose
ese diagnose
```

**Trigger keywords:** "diagnose", "what's wrong", "find weakness", "what should I fix"

## Instructions

### Step 1: Load Latest Benchmark

```bash
ls -t data/benchmarks/ | head -1
cat data/benchmarks/<latest-file>
```

If no benchmark exists: "No benchmark found. Run /dormammu:benchmark first."

### Step 2: Run CLI Diagnose

```bash
cd <project-root> && ese diagnose 2>&1
```

Read the CLI output for its weakness analysis.

### Step 3: Identify Weakest Dimension

Find the lowest-scoring evaluation dimension from the benchmark data.

### Step 4: Map to Code

Based on the weakest dimension, identify the relevant module:

| Weakness | Likely Module | Look For |
|----------|--------------|----------|
| `agent_diversity` | `src/ese/agents/` | `decide_action`, persona prompt construction |
| `narrative_coherence` | `src/ese/simulation/` | turn summarization, event chaining |
| `emergent_conflict` | `src/ese/agents/`, `src/ese/world/` | relationship tracking, tension logic |
| `world_consistency` | `src/ese/world/` | rule enforcement, state mutation |
| `causal_chain` | `src/ese/simulation/` | consequence propagation |

Read the relevant source file:
```bash
find src/ese/ -name "*.py" | head -20
cat src/ese/<relevant-module>.py
```

Identify the specific method or section that drives the weak metric.

### Step 5: Map to Feature List

Read `feature_list.json`:
```bash
cat feature_list.json
```

Find pending features that address the weakest dimension. Look for matching `module` field or description keywords.

### Step 6: Present Diagnosis

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Diagnosis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Weakest Dimension:  <name>  (<score>)

Root Cause:
  <specific method or logic gap identified in code>
  File: src/ese/<module>.py
  Method: <method_name>()

Recommended Feature:
  [<F-ID>] <feature name>
  "<feature description>"

Acceptance Criteria:
  - <criterion 1>
  - <criterion 2>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Should I fix this? Run /dormammu:improve to implement [<F-ID>].
```

### Step 7: Ask for Confirmation

End with: "Should I fix this? (/dormammu:improve)"

If the user says yes or "improve", trigger the improve skill logic.
