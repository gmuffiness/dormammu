# CLAUDE.md — Dormammu

## Design Philosophy

> **Dormammu는 Python CLI 도구가 아니다. Claude Code/Codex 같은 에이전트 세션 안에서 동작하는 하네스(harness)다.**

이 프로젝트의 핵심 설계 원칙:

1. **에이전트 네이티브** — 별도 API 키나 Python 런타임 없이, 에이전트 세션 안에서 스킬과 서브에이전트만으로 시뮬레이션이 완결됨
2. **프롬프트가 코드** — 시뮬레이션 로직이 Python 클래스가 아니라 마크다운 프롬프트 파일(agents/*.md, .claude/commands/*.md)에 정의됨
3. **상태는 파일** — DB 대신 파일 시스템(tree-index.json, node.md, run-state.json)이 상태 저장소
4. **산출물은 문서** — 시뮬레이션 결과가 마크다운 문서 트리로 생성되어 사람이 직접 읽을 수 있음

**앞으로 기능을 추가할 때 이 원칙을 지켜야 한다:**
- Python 코드를 추가하기보다 에이전트 프롬프트를 개선할 것
- API 서버를 만들기보다 파일 기반 뷰어를 개선할 것
- DB를 도입하기보다 JSON/마크다운 파일 구조를 개선할 것

---

## Project Overview

**Dormammu**는 What-If 소설 시뮬레이션 하네스입니다. DFS 시나리오 트리를 탐색하며 분기 가설을 생성하고, 각 분기를 시뮬레이션하여 점수를 매기고, 확장(expand)하거나 가지치기(prune)합니다.

```
Topic: "진격의 거인에서 아르민 대신 엘빈을 살렸다면?"
  └─ N001 (root)
       ├─ N002: 지하실의 진실  [0.81] ■ EXPANDED
       │    ├─ N005: 마레 접촉  [0.91] ★ BEST
       │    └─ N006: 권력 투쟁  [0.25] ✕ PRUNED
       ├─ N003: 104기의 균열  [0.72] ■
       └─ N004: 마레의 그림자  [0.68] ■
```

---

## 사용 방법

Claude Code 세션에서:

```
/dormammu:imagine                    ← 시나리오 설정 (대화형)
/dormammu:simulate "주제"            ← 전체 시뮬레이션 실행
/dormammu:research                   ← 리서치만 단독 실행
/dormammu:deepen                     ← 최우수 경로 소설화
/dormammu:status                     ← 진행 상황 확인
/dormammu:help                       ← 가이드
```

결과 뷰어:
```bash
python viewer/serve.py .dormammu/output/<sim-id>
# → http://localhost:3000
```

---

## 프로젝트 구조

```
apps/dormammu/
├── .claude/commands/           # 스킬 6개
│   ├── dormammu-imagine.md     #   시나리오 설정
│   ├── dormammu-simulate.md    #   전체 시뮬레이션 (7-Phase)
│   ├── dormammu-research.md    #   리서치 단독
│   ├── dormammu-deepen.md      #   소설화 단독
│   ├── dormammu-status.md      #   진행 상황
│   └── dormammu-help.md        #   가이드
│
├── agents/                     # 서브에이전트 프롬프트 10개
│   ├── researcher.md           #   배경 리서치 (fiction/history/speculative)
│   ├── world-builder.md        #   세계관 규칙
│   ├── character-designer.md   #   캐릭터 프로필 (Big-5, OOC)
│   ├── hypothesis-generator.md #   분기 가설 생성
│   ├── agent-decision.md       #   캐릭터 행동 결정
│   ├── interaction-resolver.md #   상호작용 해결
│   ├── narrator.md             #   턴 내러티브
│   ├── character-validator.md  #   OOC 검증 + 페널티
│   ├── node-evaluator.md       #   6차원 노드 평가
│   ├── novelist.md             #   경로 소설화
│   └── scene-illustrator.md    #   장면 삽화 생성 (Gemini/OpenAI)
│
├── scripts/                    # DFS 오케스트레이터 (Ralph 패턴)
│   ├── dormammu-dfs.sh         #   Bash 메인 루프 + context 조립
│   ├── process-one-node.md     #   단일 노드 처리 프롬프트
│   └── deepen-best-path.md     #   Deepen + Report 프롬프트
│
├── viewer/                     # 심플 웹 뷰어
│   ├── index.html              #   단일 HTML (Tailwind + Marked.js CDN)
│   └── serve.py                #   파일 서버
│
├── src/dormammu/               # Python 유틸리티 (스키마 + 데이터만)
│   ├── config.py               #   WhatIfScenario, EvaluationWeights
│   ├── agents/persona.py       #   Persona 스키마 (Big-5, OOC 필드)
│   └── hypothesis/inspiration.py  # SF/문학 영감 시드 뱅크 (25+)
│
├── docs/mockup/                # 산출물 품질 기준 (참조용)
├── seeds/                      # 비전 문서
└── .dormammu/                  # 시뮬레이션 산출물 (실행 시 생성)
```

---

## 시뮬레이션 Phase

| Phase | 주체 | 산출물 |
|-------|------|--------|
| 1. Research | Agent(researcher) | 01-background-research.md |
| 2. World Rules | Agent(world-builder) | 02-world-rules.md |
| 3. Characters | Agent(character-designer) × N | characters/*.md + 03-character-profiles.md |
| 4. Init Tree | Claude 직접 | tree-index.json + N001/node.md |
| 5. DFS Loop | **scripts/dormammu-dfs.sh** (매 노드 새 claude -p) | N001/N002/node.md ... |
| 6. Deepen | scripts/dormammu-dfs.sh → claude -p | 05-deepen-best-path.md |
| 7. Report | scripts/dormammu-dfs.sh → claude -p | 07-best-path-metadata.md |

---

## 산출물 구조

시뮬레이션 결과는 파일 시스템 트리로 DFS 구조를 그대로 반영합니다:

```
.dormammu/output/<sim-id>/
├── 01-background-research.md
├── 02-world-rules.md
├── 03-character-profiles.md
├── characters/
│   ├── erwin-smith.md          # 심리 프로필 + OOC 탐지 규칙
│   └── levi-ackerman.md
├── tree-index.json             # 노드 메타데이터 (빠른 조회)
├── N001/                       # 루트 노드
│   ├── node.md                 # 가설, 내러티브, 점수, 이벤트
│   ├── N002/
│   │   ├── node.md
│   │   └── N005/
│   │       └── node.md
│   └── N003/
│       └── node.md             # (PRUNED)
├── 05-deepen-best-path.md
└── 07-best-path-metadata.md
```

---

## 평가 메트릭 (6차원)

| 메트릭 | 가중치 | 설명 |
|--------|--------|------|
| Character Fidelity | 20% | 캐릭터/인물 성격·동기 재현도 (OOC 페널티 반영) |
| Audience Resonance | 15% | 대상 독자가 흥미로워할 전개 |
| Emergence | 15% | 예상치 못한 창발적 사건 |
| Narrative Flow (NF) | 15% | 조상 내러티브와의 서사 연결 매끄러움 — 부모 Key Events에서 자연스럽게 이어지는지, 캐릭터 감정/동기 흐름이 끊기지 않는지, 시공간 전환이 자연스러운지 |
| Plausibility | 15% | 세계관 규칙 내 논리적 타당성 |
| Foreshadowing | 20% | 복선 품질 (자연스러움, 회수율) |

Composite > 0.3 → Expand, ≤ 0.3 → Prune

---

## 데이터 모델 (참조)

스킬에서 참조하는 Python 스키마:

- **WhatIfScenario** (`src/dormammu/config.py`) — 시나리오 설정 (주제, 톤, 시간범위, 평가가중치)
- **Persona** (`src/dormammu/agents/persona.py`) — 캐릭터 스키마 (Big-5, 목표, 두려움, OOC)
- **InspirationSystem** (`src/dormammu/hypothesis/inspiration.py`) — SF/문학 시드 뱅크

---

## Git Conventions

```bash
git commit -m "feat: <what changed>"     # 새 기능
git commit -m "fix: <what was wrong>"    # 버그 수정
git commit -m "refactor: <what moved>"   # 행동 변경 없음
git commit -m "docs: <what documented>"  # 문서만
```
