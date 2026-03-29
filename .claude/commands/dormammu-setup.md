---
name: setup
description: "Guided onboarding wizard for Dormammu — checks environment, installs deps, runs baseline benchmark"
---

# /dormammu:setup

Setup wizard that gets you from zero to a running simulation harness.

## Usage

```
/dormammu:setup
ese setup
```

**Trigger keywords:** "setup", "install", "onboarding", "initialize ese"

## Instructions

When the user invokes this skill, run each step sequentially and report results.

---

### Step 1: Environment Check

```bash
python3 --version
pip --version
echo $OPENAI_API_KEY | head -c 10
```

Report findings:

```
Environment Check:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Python                  [✓ / ✗]  <version>
pip                     [✓ / ✗]
OPENAI_API_KEY          [✓ set / ✗ missing]
```

If Python < 3.10, stop and tell the user: "Dormammu requires Python 3.10+. Install it first, then re-run /dormammu:setup."
If OPENAI_API_KEY is missing, note it — the user will need it before running simulations.

---

### Step 2: Install Dependencies

```bash
cd <project-root> && pip install -e ".[dev]"
```

Show: "Installing Dormammu and dev dependencies..."
On success: "[✓] Dependencies installed"
On failure: show pip error output and stop.

---

### Step 3: Environment File

Check if `.env` exists:
```bash
ls .env 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

If missing and `.env.example` exists:
```bash
cp .env.example .env
```
Tell the user: "Copied .env.example → .env. Open .env and add your OPENAI_API_KEY."

If `.env` already exists: "[✓] .env present"

---

### Step 4: Run Tests

```bash
cd <project-root> && pytest tests/ -v --tb=short 2>&1 | tail -30
```

Show a summary:
- "[✓] All tests passed" — if exit code 0
- "[!] X tests failed" — show the failures, but continue setup

---

### Step 5: Establish Baseline Benchmark

Run the first benchmark to create a starting point:

```bash
cd <project-root> && ese benchmark 2>&1
```

If this succeeds, note: "[✓] Baseline benchmark recorded in data/benchmarks/"
If it fails (e.g., no OPENAI_API_KEY), note: "[!] Skipped — add OPENAI_API_KEY to .env and run /dormammu:benchmark"

---

### Step 6: Initialize Progress File

Check if `claude-progress.txt` exists:
```bash
ls claude-progress.txt 2>/dev/null && echo "EXISTS" || echo "MISSING"
```

If missing, create it with initial content:
```
# Dormammu Claude Progress Log
# Created by /dormammu:setup

Session 1 — Initial Setup
- Environment: ready
- Baseline benchmark: pending
- Goal: not set

Next: Run /dormammu:goal "your scenario" to set a simulation goal.
```

---

### Step 7: Success Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dormammu Setup Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dependencies:     [✓] Installed
Tests:            [✓/!] <result>
Baseline:         [✓/!] <result>
Progress log:     [✓] claude-progress.txt ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Next Steps
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Set a goal:      /dormammu:goal "your scenario idea"
2. Run a sim:       /dormammu:simulate
3. Improve it:      /dormammu:evolve --hours 2
4. See all cmds:    /dormammu:help
```
