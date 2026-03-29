---
name: run
description: "시뮬레이션 실행 — 시나리오 + 리서치 데이터를 기반으로 24h 자동 DFS 탐색"
---

# /dormammu:run

시나리오와 리서치 데이터를 기반으로 시뮬레이션을 실행합니다.
기본적으로 24시간 자동 구동되며 사용자가 중단할 수 있습니다.

## Usage

```
/dormammu:run                  — 기본 실행
/dormammu:run --auto           — 24h 자동 구동 (기본값)
/dormammu:run --quick          — 빠른 테스트용 (depth 2, 짧은 시간)
```

**Trigger keywords:** "run", "돌려봐", "시뮬레이션", "시작", "go"

## Instructions

### Step 1: Load Scenario & Research

```bash
cat .ese/scenario.json 2>/dev/null || echo "NO_SCENARIO"
cat .ese/research.json 2>/dev/null || echo "NO_RESEARCH"
```

시나리오 없으면: "먼저 /dormammu:imagine으로 시나리오를 설정해주세요."
리서치 없으면: 경고 표시 후 리서치 없이도 진행 가능 (추천하지 않음).

### Step 2: Configure Simulation

scenario.json과 research.json에서 파라미터 추출:

- `topic`: scenario.topic
- `agents`: research.character_profiles + research.supporting_characters
- `world_rules`: research.world_rules
- `evaluation_weights`: scenario.evaluation_weights
- `exploration_style`: scenario.exploration_style → DFS 파라미터 조정
  - wide: max_depth=3, branches_per_node=5
  - deep: max_depth=6, branches_per_node=2
  - balance: max_depth=4, branches_per_node=3
- `time_range`: scenario.time_range → node_years 계산
- `tone`: scenario.tone → 내러티브 생성 프롬프트에 반영
- `constraints`: scenario.constraints → 시뮬레이션 가드레일
- `curiosity_points`: scenario.curiosity_points → 가지 생성 시 가중치

### Step 3: Run Simulation

```bash
cd <project-root> && source .venv/bin/activate && ese run --topic "<topic>" 2>&1
```

실행 중 표시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Simulation Running
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Topic:      <대주제>
Mode:       <auto/quick>
Tree:       <exploration_style> (depth: <N>, branches: <N>)

Progress will be streamed below...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 4: Monitor & Display Progress

시뮬레이션 진행 중 주요 이벤트 표시:
- 노드 시뮬레이션 시작/완료
- 평가 점수
- 분기 생성/프루닝
- 비용 누적

### Step 5: Show Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Simulation Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Topic:        <대주제>
Duration:     <시간>
Nodes:        <총 노드 수> (completed: <N>, pruned: <N>)
Total Cost:   $<비용>

Top Scenarios (by composite score):
  1. [0.82] <경로 요약> — "<핵심 장면>"
  2. [0.78] <경로 요약> — "<핵심 장면>"
  3. [0.71] <경로 요약> — "<핵심 장면>"

Average Scores:
  character_fidelity   <score>
  fandom_resonance     <score>
  emergence            <score>
  diversity            <score>
  plausibility         <score>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next:
  /dormammu:deepen               — 최고 점수 시나리오 심화
  /dormammu:deepen --node <id>   — 특정 시나리오 심화
  /dormammu:benchmark            — 품질 상세 분석
  /dormammu:evolve               — 자율 개선 루프
```
