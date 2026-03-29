<p align="right">
  <strong>English</strong> | <a href="./README.ko.md">한국어</a>
</p>

<p align="center">
  <br/>
  <strong>D O R M A M M U</strong>
  <br/><br/>
  <sub>I've come to bargain... with reality.</sub>
</p>

# Dormammu — What-If Fiction Simulation Harness

> **"What if...?"** — Starting from a single question, explore alternate timelines via DFS scenario trees and generate What-If fiction.

Dormammu is not a Python CLI tool. It is a **harness that runs inside agent sessions like Claude Code / Codex**.

## How It Works

```
"What if Erwin was saved instead of Armin in Attack on Titan?"
  ↓
Phase 1: Background Research   → 01-background-research.md
Phase 2: World Rules           → 02-world-rules.md
Phase 3: Character Generation  → characters/*.md (with OOC detection rules)
Phase 4: Scenario Tree Init
Phase 5: DFS Exploration       → N001/N002/node.md ... (expand/prune)
Phase 6: Best Path Novelization → 05-deepen-best-path.md
Phase 7: Metadata Report       → 07-best-path-metadata.md
```

## Quick Start

In a Claude Code session:

```
/dormammu:imagine                    # Set up scenario (interactive)
/dormammu:simulate "topic"           # Run simulation
/dormammu:status                     # Check progress
/dormammu:deepen                     # Novelization of best path
/dormammu:help                       # Full guide
```

Result viewer:
```bash
python viewer/serve.py .dormammu/output/<sim-id>
# → http://localhost:3000
```

## Design Principles

1. **Agent Native** — No API keys needed; runs entirely with skills + sub-agents inside an agent session
2. **Prompts Are Code** — Simulation logic lives in markdown prompt files, not Python classes
3. **State Is Files** — tree-index.json + node.md + run-state.json instead of databases
4. **Output Is Documents** — Human-readable markdown tree as simulation output

## Installation

Dormammu is a Claude Code plugin. Install it from any directory:

```bash
# Register as local marketplace
claude plugin marketplace add /path/to/dormammu

# Install
claude plugin install dormammu@dormammu

# Restart Claude Code session
```

Or from GitHub:

```bash
# Add marketplace
claude plugin marketplace add --source github --repo gmuffiness/dormammu

# Install
claude plugin install dormammu@dormammu
```

After installation, `/dormammu:*` commands are available globally.

## License

MIT
