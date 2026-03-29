---
name: improve
description: "One improvement cycle: diagnose → implement → test → benchmark → commit or revert"
---

# /dormammu:improve

Runs one complete improvement cycle: finds the weakest point, implements a fix,
verifies with tests, measures impact, and commits if improved.

## Usage

```
/dormammu:improve
/dormammu:improve --feature F003
```

**Trigger keywords:** "improve", "fix it", "implement fix", "one cycle", "make it better"

## Instructions

### Step 1: Diagnose

Follow the `/dormammu:diagnose` skill to identify the target. If `--feature <ID>` is given,
use that feature from `feature_list.json` directly instead.

Read the target feature from `feature_list.json`:
```bash
cat feature_list.json
```

Identify the `module`, `description`, and `acceptance_criteria` for the chosen feature.

### Step 2: Read Target Code

Read the relevant source file(s):
```bash
cat src/ese/<module>/<file>.py
```

Understand the current implementation before making changes.

### Step 3: Implement the Improvement

Edit the source file to implement the feature. Guidelines:
- Make the smallest change that satisfies the acceptance criteria
- Match existing code style (naming, error handling, docstrings)
- Do not refactor adjacent code unless required by the change
- Add a brief comment explaining the new logic

### Step 4: Run Tests

```bash
cd <project-root> && pytest tests/ -v --tb=short 2>&1 | tail -40
```

If tests fail:
- Read the failure carefully
- Fix the root cause in production code (not in the tests)
- Re-run tests
- If still failing after 2 attempts, revert the change and report

### Step 5: Run Benchmark

```bash
cd <project-root> && ese benchmark 2>&1
```

Read the new benchmark results from `data/benchmarks/`.

### Step 6: Compare Scores

Compare new scores against the pre-improvement baseline:

```
Impact Assessment:
  <dimension>    <before> → <after>   ↑/↓ <delta>
  Overall        <before> → <after>   ↑/↓ <delta>
```

**If improved (overall score up or target dimension up):**
- Commit with a descriptive message:
```bash
cd <project-root> && git add -p src/ese/
git commit -m "feat: <concise description of what was implemented>

Improves <dimension>: <before> → <after>
Feature: <F-ID> <feature name>"
```
- Update `feature_list.json`: set the feature's `"status"` to `"complete"`
- Append to `claude-progress.txt`

**If regressed (overall score down):**
- Revert the code change
- Note: "Reverted — this approach reduced overall score by <delta>. Will try a different method."
- Do NOT commit

### Step 7: Update Progress

Append to `claude-progress.txt`:

```
--- Improvement Cycle <timestamp> ---
Feature: <F-ID> <name>
Result: [IMPROVED / REVERTED]
Scores: <before> → <after>
Notes: <brief explanation of what was tried>
```

### Step 8: Report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Improvement Cycle Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature:   [<F-ID>] <name>
Result:    IMPROVED / REVERTED
Committed: yes / no

Score Delta:
  <dimension>   <before> → <after>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next: /dormammu:improve (next cycle) or /dormammu:evolve (autonomous loop)
```
