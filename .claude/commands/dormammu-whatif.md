---
name: whatif
description: "What-if scenario explorer — auto-generates agents and world rules for a counterfactual, then simulates it"
---

# /dormammu:whatif

Explores a counterfactual scenario. Analyzes the 'what if' premise, auto-generates
world rules and an agent cast, runs the simulation, and shows the most interesting timeline.

## Usage

```
/dormammu:whatif "에렌이 땅울림을 하지 않았다면 100년 후"
/dormammu:whatif "what if Rome never fell"
/dormammu:whatif "what if the village elder refused the trade deal"
```

**Trigger keywords:** "what if", "what would happen if", "alternate timeline", "counterfactual"

## Instructions

### Step 1: Parse Scenario

Extract the what-if question from the user's argument.
If no argument, ask: "What's the 'what if' scenario you want to explore?"

### Step 2: Analyze the Scenario

Use LLM reasoning to break down the scenario:

**Premise Deconstruction:**
- What is the key divergence point? (the thing that "didn't happen" or "changed")
- What world does this occur in? (known fiction, history, or invented)
- What is the implied timeframe? (immediately after, years later, generations later)

**World Rules:**
Generate 3-5 concrete rules the simulation must respect:
- Example: "No Rumbling occurred → Eldian power is weakened, Marley dominates"
- Example: "Trade deal rejected → village faces resource scarcity by turn 3"

**Agent Cast:**
Generate 4-8 agents appropriate to this scenario:
```json
[
  {"name": "...", "role": "...", "motivation": "...", "key_trait": "..."},
  ...
]
```

Show the analysis to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Scenario: <question>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Divergence Point:
  <what changed>

World Rules:
  1. <rule>
  2. <rule>
  3. <rule>

Agent Cast (<N> characters):
  <name> — <role>, motivated by <motivation>
  <name> — <role>, motivated by <motivation>
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Running simulation...
```

### Step 3: Save Temporary Goal

Write a temporary `.ese/whatif_goal.json` for this run:
```json
{
  "topic": "<scenario>",
  "world_rules": ["rule1", "rule2"],
  "agents": [...],
  "is_whatif": true
}
```

### Step 4: Run Simulation

```bash
cd <project-root> && ese run --topic "<scenario>" 2>&1
```

Or if `--topic` is not supported, run `dormammu run` and note the scenario was pre-configured.

### Step 5: Show Narrative

After completion, read the results and render the most interesting timeline:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  What-If Timeline: "<scenario>"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Year 1]  <key event — consequence of the divergence>
[Year 10] <how factions/agents responded>
[Year 50] <a turning point>
[Year 100] <the eventual outcome>

Most Interesting Moment:
  "<direct quote or paraphrase of the most compelling agent action>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next:
  /dormammu:whatif "<different branch>"   — explore another timeline
  /dormammu:benchmark                      — score this simulation
  /dormammu:goal "<scenario>"              — set this as your main goal
```
