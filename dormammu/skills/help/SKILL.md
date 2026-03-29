---
name: help
description: "Dormammu 커맨드 가이드"
---

# /dormammu:help

Display the following reference guide:

---

## Dormammu — What-If 소설 시뮬레이션 하네스

Claude Code 세션 안에서 DFS 시나리오 트리를 탐색하여 What-If 소설을 생성합니다.

### 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/dormammu:imagine` | 시나리오 설정 — 대화형으로 7가지 입력 수집 |
| `/dormammu:simulate` | 전체 시뮬레이션 실행 (7-Phase) |
| `/dormammu:research` | Phase 1만 단독 실행 (배경 리서치) |
| `/dormammu:deepen` | Phase 6만 단독 실행 (경로 소설화) |
| `/dormammu:status` | 진행 상황 확인 |
| `/dormammu:help` | 이 가이드 표시 |

### 일반적인 워크플로우

```
1. /dormammu:imagine          ← 시나리오 설정
2. /dormammu:simulate         ← 시뮬레이션 실행
3. /dormammu:status           ← 진행 상황 확인
4. /dormammu:deepen           ← 최우수 경로 소설화
5. python viewer/serve.py .dormammu/output/<sim-id>  ← 웹 뷰어
```

### 시뮬레이션 Phase

| Phase | 주체 | 산출물 |
|-------|------|--------|
| 1. Research | Claude (researcher) | 01-background-research.md |
| 2. World Rules | Claude (world-builder) | 02-world-rules.md |
| 3. Characters | Claude (character-designer) | 03-character-profiles.md + characters/*.md |
| 4. Init Tree | Claude | tree-index.json + N001/ |
| 5. DFS Loop | Claude (agent-decision, narrator, evaluator, ...) | N001/N002/node.md ... |
| 6. Deepen | Claude (novelist) | 05-deepen-best-path.md |
| 7. Report | Claude | 07-best-path-metadata.md |

### 산출물 구조

```
.dormammu/output/<sim-id>/
├── 01-background-research.md
├── 02-world-rules.md
├── 03-character-profiles.md
├── characters/*.md
├── tree-index.json
├── N001/
│   ├── node.md
│   ├── N002/
│   │   └── node.md
│   └── N003/
│       └── node.md
├── 05-deepen-best-path.md
└── 07-best-path-metadata.md
```

### 서브에이전트

| 에이전트 | 역할 |
|----------|------|
| researcher | 배경 리서치 (fiction/history/speculative) |
| world-builder | 세계관 규칙 도출 |
| character-designer | 캐릭터 프로필 생성 |
| hypothesis-generator | 분기 가설 생성 |
| agent-decision | 캐릭터 행동 결정 |
| interaction-resolver | 상호작용 해결 |
| narrator | 턴 내러티브 생성 |
| character-validator | OOC 검증 + 페널티 |
| node-evaluator | 6차원 노드 평가 |
| novelist | 경로 소설화 |
