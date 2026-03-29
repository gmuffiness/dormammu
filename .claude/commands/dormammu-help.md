---
name: help
description: "Full reference guide for all Dormammu commands and workflow"
---

# /dormammu:help

What-If 소설 창작 시뮬레이터 — 하네스 엔지니어링 레퍼런스 가이드.

## Usage

```
/dormammu:help
```

**Trigger keywords:** "help", "commands", "커맨드", "도움말", "ese help"

## Instructions

Display the following reference guide when invoked:

---

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Dormammu — What-If Fiction Simulator
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

특정 세계관의 What-If 시나리오를 자동으로 시뮬레이션하고,
소설급 내러티브를 생성하는 하네스 엔지니어링 시스템.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Commands
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Scenario Setup:
  /dormammu:imagine "<What-If>"   시나리오 설정 — 인터뷰로 7가지 입력 수집
  /dormammu:research              팬덤 리서치 — 웹검색, 캐릭터 분석, 세계관 추출

Simulation:
  /dormammu:run                   시뮬레이션 실행 (24h 자동)
  /dormammu:status                진행 상황 + 점수 + 트리 개요

Quality & Improvement:
  /dormammu:benchmark             품질 측정 — 5개 메트릭 점수화
  /dormammu:diagnose              약점 분석 — 가장 낮은 메트릭 → 코드 매핑
  /dormammu:improve               1회 개선 사이클 (진단 → 수정 → 검증 → 커밋)
  /dormammu:evolve                자율 개선 루프 (수렴까지 반복)

Output:
  /dormammu:deepen                시나리오 심화 — 선택 경로 → 상세 내러티브 + 이미지 + PDF
  /dormammu:deepen --autopilot    자동 심화 — 최고 점수 경로 자동 선택

Utilities:
  /dormammu:setup                 초기 설정 마법사
  /dormammu:help                  이 도움말

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Evaluation Metrics (5 Dimensions)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  character_fidelity   (0.25)  캐릭터 충실도 — 원작 성격/동기/말투 재현
  fandom_resonance     (0.20)  팬 반응 예측 — 팬덤이 흥미로워할 전개
  emergence            (0.20)  창발성 — 예상치 못한 사건 발생
  diversity            (0.15)  다양성 — 분기 간 차별화
  plausibility         (0.20)  개연성 — 세계관 내 논리적 타당성

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Quick Start:
    /dormammu:imagine "..." → /dormammu:research → /dormammu:run → /dormammu:deepen

  Full Autonomous:
    /dormammu:imagine "..." → /dormammu:research → /dormammu:run → /dormammu:evolve → /dormammu:deepen --autopilot

  Manual Improvement:
    /dormammu:benchmark → /dormammu:diagnose → /dormammu:improve → repeat

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Natural Language Triggers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  "상상해봐", "what if", "만약에"      → /dormammu:imagine
  "리서치", "팬덤 조사"                → /dormammu:research
  "시뮬레이션", "돌려봐", "run"        → /dormammu:run
  "심화", "더 보고싶어", "deepen"      → /dormammu:deepen
  "점수", "benchmark"                  → /dormammu:benchmark
  "약점", "diagnose"                   → /dormammu:diagnose
  "개선", "improve"                    → /dormammu:improve
  "자동 개선", "evolve"                → /dormammu:evolve
  "상태", "status"                     → /dormammu:status
  "도움말", "help"                     → /dormammu:help

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  State Files
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  .ese/scenario.json         시나리오 설정 (/dormammu:imagine)
  .ese/research.json         리서치 결과 (/dormammu:research)
  .ese/evolution.jsonl       개선 사이클 로그
  .ese/deepened/             심화 결과물 (내러티브, 이미지, PDF)
  data/benchmarks/           벤치마크 히스토리
  data/ese.db                시뮬레이션 데이터베이스

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
