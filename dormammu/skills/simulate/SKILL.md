---
name: simulate
description: "What-If 소설 시뮬레이션 — DFS 시나리오 트리 탐색"
---

# /dormammu:simulate

What-If 소설 시뮬레이션을 실행합니다.
Phase 0~4는 Claude Code 세션에서, Phase 5~7은 bash 오케스트레이터가 처리합니다.

**사용법:** `/dormammu:simulate "진격의 거인에서 아르민 대신 엘빈을 살렸다면?"`

**인자:**
- `$ARGUMENTS` — What-If 시나리오 주제 (필수)
- `--max-depth N` — DFS 최대 깊이 (기본 10)
- `--max-nodes N` — 최대 노드 수 (기본 100)
- `--resume` — 중단된 시뮬레이션 재개

---

## Phase 0: 초기화

```
1. sim_id 결정:
   - .dormammu/active-sim-id 파일이 있으면 sim_id를 읽음
   - 없으면 새로 생성: python3 -c "import uuid; print(uuid.uuid4().hex[:8])"
2. output_dir = .dormammu/output/<sim-id>/
3. Read <output_dir>/scenario.json — /dormammu:imagine으로 생성된 시나리오 확인
   - 있으면: topic, dfs_engine, heartbeat, auto_deepen, image_generation 등 모든 설정을 로드
   - 없으면: $ARGUMENTS에서 topic 추출, 나머지는 기본값 사용
4. DFS 엔진 결정:
   - scenario.json에 dfs_engine이 있으면 그대로 사용
   - 없으면 사용자에게 질문 (claude/codex)
   - codex 선택 시: 설치 여부(which codex)와 API 키(~/.codex/auth.json > OPENAI_API_KEY) 확인, 미설정이면 claude로 폴백
5. mkdir -p <output_dir>/characters <output_dir>/artifacts
6. Write <output_dir>/run-state.json:
   {"sim_id": "<sim-id>", "phase": "research", "topic": "<topic>",
    "dfs_engine": "claude|codex",
    "max_depth": 10, "max_nodes": 100, "nodes_completed": 0,
    "started_at": "<현재 실제 KST 타임스탬프 — Bash: TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00>",
    "updated_at": "<현재 실제 KST 타임스탬프 — 동일>",
    "phase_timings": {},
    "current_activity": {"phase": "init", "detail": "시나리오 로드 중", "node_id": null, "progress": "0/0"}}
8. 뷰어 대시보드 실행 (백그라운드):
   - 포트 3000이 이미 사용 중인지 확인
   - 사용 중이 아니면 `python viewer/serve.py .dormammu/output &` 로 백그라운드 서버 시작
   - `open "http://localhost:3000/sim/<sim-id>"` 로 브라우저에서 대시보드 열기
   - 이미 사용 중이면 브라우저만 열기
9. Heartbeat 백그라운드 프로세스 실행:
   - scenario.json의 `heartbeat` 설정을 읽음 (없으면 기본값: interval_min=10, total_hours=6, count=36)
   - `heartbeat.enabled`가 false이면 스킵
   - count 횟수만큼 각각 **별도의 Bash(run_in_background=true)** 호출:
     ```
     N번째: sleep (N * interval_min * 60) && echo "🔔 HEARTBEAT #N: 시뮬레이션이 멈춰있다면 run-state.json을 확인하고 다음 Phase를 계속 진행하세요."
     ```
   - 예: count=6, interval_min=10 → 6개 호출 (sleep 600, 1200, 1800, 2400, 3000, 3600)
   - 예: count=36, interval_min=10 → 36개 호출 (sleep 600 ~ 21600)
   - 각 프로세스는 완료 시 자동으로 알림 주입
   - Claude가 idle 상태이면 즉시 반응, thinking 중이면 턴 종료 후 주입
```

**재개 모드 (`--resume`):**
```
1. Read <output_dir>/run-state.json
2. sim_id, phase 복원
3. phase가 "dfs"이면 바로 Phase 5(bash 오케스트레이터) 실행
4. 그 외 해당 phase부터 계속 진행
```

---

## Phase 타이밍 & 실시간 상태 규칙

**매 Phase 시작/종료 시 `run-state.json`을 업데이트합니다:**

### phase_timings (소요 시간 기록)

**중요: 반드시 단일 Bash 명령으로 타임스탬프 취득과 JSON 업데이트를 한 번에 수행합니다.**
Python subprocess로 date를 호출하지 마세요. jq 또는 bash 변수 치환을 사용합니다.

Phase 시작 시:
```bash
ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00) && \
jq --arg ts "$ts" --arg phase "<phase_name>" \
  '.phase_timings[$phase].started_at = $ts | .current_activity = {"phase":$phase,"detail":"...","node_id":null,"progress":"N/7"} | .updated_at = $ts' \
  <output_dir>/run-state.json > <output_dir>/run-state.tmp && mv <output_dir>/run-state.tmp <output_dir>/run-state.json
```

Phase 종료 시:
```bash
ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00) && \
jq --arg ts "$ts" --arg phase "<phase_name>" \
  '.phase_timings[$phase].ended_at = $ts | .updated_at = $ts' \
  <output_dir>/run-state.json > <output_dir>/run-state.tmp && mv <output_dir>/run-state.tmp <output_dir>/run-state.json
```

**phase_name:** `"init"`, `"research"`, `"world_rules"`, `"characters"`, `"init_tree"`, `"dfs"`, `"deepen"`, `"report"`

### current_activity (실시간 상태 — viewer 폴링용)

```json
{
  "phase": "research|world_rules|characters|init_tree|dfs|deepen|report|complete",
  "detail": "배경 리서치 중...",
  "node_id": null,          // DFS 시 현재 처리 중인 노드 ID (예: "N008")
  "progress": "5/100"       // DFS 시 "완료/목표" 형식
}
```

**각 Phase 시작 시 `current_activity`를 업데이트합니다:**
- Phase 1: `{"phase":"research", "detail":"배경 리서치 중...", "node_id":null, "progress":"1/7"}`
- Phase 2: `{"phase":"world_rules", "detail":"세계관 규칙 생성 중...", "node_id":null, "progress":"2/7"}`
- Phase 3: `{"phase":"characters", "detail":"캐릭터 프로필 생성 중...", "node_id":null, "progress":"3/7"}`
- Phase 4: `{"phase":"init_tree", "detail":"트리 초기화 + 가설 생성 중...", "node_id":null, "progress":"4/7"}`
- Phase 5 (DFS): bash 오케스트레이터가 노드별로 업데이트
- Phase 6: `{"phase":"deepen", "detail":"최우수 경로 소설화 중...", "node_id":null, "progress":"6/7"}`
- Phase 7: `{"phase":"report", "detail":"메타데이터 리포트 생성 중...", "node_id":null, "progress":"7/7"}`
- 완료: `{"phase":"complete", "detail":"시뮬레이션 완료", "node_id":null, "progress":"7/7"}`

---

## Phase 1: Research (Claude)

```
1. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json:
     phase_timings.research.started_at = ts
     current_activity = {"phase":"research", "detail":"배경 리서치 중...", "node_id":null, "progress":"1/7"}
2. Read ${CLAUDE_PLUGIN_ROOT}/agents/researcher.md
3. Agent(prompt=researcher_prompt + topic + "한국어로 작성") 실행
4. Write <output_dir>/01-background-research.md — JSON을 풍부한 마크다운으로 변환:
   - # 제목, ## 개요 (summary 전문)
   - ## 주요 캐릭터: 각 캐릭터별 ### 소제목, 역할/설명/동기를 상세히
   - ## 세력 구도: 각 세력별 입장/목표/보유 자원, 세력 간 관계
   - ## 갈등 구조: conflict_structure 전문 + 갈등 간 인과관계
   - ## 역사적 맥락: historical_context 전문
   - ## 팬 이론: 각 이론을 번호 목록으로, 근거와 함께 상세히
   - ## 주제적 요소: thematic_elements 목록
   - ## 출처: 각 출처를 `[제목](URL) — 유형` 형식의 링크로. URL 없는 출처도 제목+설명으로 기재
   ★ 모든 섹션에서 JSON 원문 내용을 축약하지 말고 전부 포함할 것
5. Write <output_dir>/artifacts/research.json
6. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json: phase = "world-rules", phase_timings.research.ended_at = ts
7. 콘솔 출력: "✓ Phase 1 Research complete ({소요시간})"
```

---

## Phase 2: World Rules (Claude)

```
1. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json:
     phase_timings.world_rules.started_at = ts
     current_activity = {"phase":"world_rules", "detail":"세계관 규칙 생성 중...", "node_id":null, "progress":"2/7"}
2. Read ${CLAUDE_PLUGIN_ROOT}/agents/world-builder.md
3. Read <output_dir>/artifacts/research.json
4. Agent(prompt=world_builder_prompt + research + topic) 실행
5. Write <output_dir>/02-world-rules.md
6. Write <output_dir>/artifacts/world-rules.json
7. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json: phase = "characters", phase_timings.world_rules.ended_at = ts
8. 콘솔 출력: "✓ Phase 2 World Rules complete ({소요시간})"
```

---

## Phase 3: Characters (Claude, 병렬)

```
1. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json:
     phase_timings.characters.started_at = ts
     current_activity = {"phase":"characters", "detail":"캐릭터 프로필 생성 중...", "node_id":null, "progress":"3/7"}
2. Read ${CLAUDE_PLUGIN_ROOT}/agents/character-designer.md
3. Read <output_dir>/artifacts/research.json (key_characters)
4. 각 캐릭터에 대해 Agent(run_in_background=true) 병렬 실행
5. Write <output_dir>/characters/<name-slug>.md — JSON을 풍부한 마크다운으로 변환:
   - # 캐릭터 이름
   - **나이/역할** 한 줄 요약
   - ## 배경: backstory 전문 (What-If 분기 영향 포함)
   - ## 원작 아크: arc_in_original (원작 캐릭터인 경우)
   - ## 분기 영향: divergence_impact (이 What-If가 캐릭터에 미치는 변화)
   - ## Big-5 성격 특성: 테이블 (특성|점수|해석)
   - ## 목표 (Goals): 우선순위 순 번호 목록
   - ## 두려움 (Fears): 목록
   - ## 가치관 (Values): 목록
   - ## 말투: speech_style 상세 설명 + catchphrases 인용
   - ## 관계: relationships를 "캐릭터 → 관계강도(0-1) + 관계 설명" 형태로
   - ## OOC 탐지 기준: ooc_triggers 목록 (이 캐릭터가 절대 하지 않을 행동)
   ★ JSON의 모든 필드를 빠짐없이 마크다운에 포함할 것. 축약 금지.
6. Write <output_dir>/03-character-profiles.md — 전체 캐릭터 요약 테이블 + 각 캐릭터 간 관계 매트릭스
7. Write <output_dir>/artifacts/characters.json
8. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json: phase = "init-tree", phase_timings.characters.ended_at = ts
9. 콘솔 출력: "✓ Phase 3 Characters complete ({소요시간})"
```

---

## Phase 4: Initialize Tree + Initial Hypotheses (Claude)

Python CLI 없이 Claude가 직접 tree-index.json과 노드 폴더를 생성합니다.

```
0. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json:
     phase_timings.init_tree.started_at = ts
     current_activity = {"phase":"init_tree", "detail":"트리 초기화 + 가설 생성 중...", "node_id":null, "progress":"4/7"}

1. Write <output_dir>/tree-index.json:
   {
     "sim_id": "<sim-id>",
     "topic": "<topic>",
     "max_depth": 10,
     "nodes": {
       "N001": {
         "path": "N001",
         "depth": 0,
         "parent": null,
         "status": "expanded",
         "composite_score": null,
         "title": "<topic 요약>"
       }
     },
     "best_path": [],
     "node_counter": 1
   }

2. Write <output_dir>/N001/node.md:
   # N001: <topic 요약>
   ## Hypothesis
   <시나리오의 핵심 분기점 설명>
   ## Status: ROOT | Depth: 0

3. Read ${CLAUDE_PLUGIN_ROOT}/agents/hypothesis-generator.md
4. Agent(prompt=hypothesis_generator_prompt + topic + world_rules + "depth 0에서 3개 가설") 실행
5. 결과에서 3개 가설 파싱

6. tree-index.json 업데이트:
   - N002, N003, N004 노드 추가 (status: "pending", parent: "N001")
   - node_counter = 4

7. 자식 폴더 생성:
   mkdir -p <output_dir>/N001/N002 N001/N003 N001/N004

8. Bash: ts=$(TZ=Asia/Seoul date +%Y-%m-%dT%H:%M:%S+09:00)
   Edit run-state.json: phase = "dfs", phase_timings.init_tree.ended_at = ts
9. 콘솔 출력: "✓ Phase 4 Init Tree complete ({소요시간})"
```

---

## Phase 5+6+7: DFS Loop → Deepen → Report (Bash Orchestrator)

**핵심 변경: DFS 루프가 bash 스크립트로 이동했습니다.**

단일 세션에서 WHILE 루프를 돌리면 컨텍스트가 포화되어 조기 종료됩니다.
대신 Ralph 패턴을 적용: **매 노드마다 새 claude 프로세스 = 새 컨텍스트**.

```
Phase 4 완료 후, bash 오케스트레이터를 실행:

Bash: cd apps/dormammu && ./scripts/dormammu-dfs.sh \
  --min-nodes <max_nodes> \
  --max-depth <max_depth>
```

### 오케스트레이터 동작

1. **매 반복 새 `claude -p` 프로세스** 생성 (컨텍스트 격리)
2. **Ancestor chain + sibling summaries**만 컨텍스트에 로드
3. **MIN_NODES 미달 시 절대 Deepen으로 안 넘어감** (bash 게이트키퍼)
4. 노드 실패 시 자동 재시도 (연속 5회 실패까지)
5. Phase 6 (Deepen) + Phase 7 (Report)도 자동 실행
6. 중단 후 재개: 동일 명령 다시 실행 (tree-index.json의 pending 노드부터)

### 컨텍스트 관리 전략

각 노드 처리 시 bash가 `.node-context.md`를 자동 조립합니다:

```
✅ 로드됨:
  - World Rules 요약 (불변 규칙)
  - Ancestor Chain: Root → Parent의 Hypothesis + Key Events + Narrative
  - Sibling Summaries: 같은 부모의 이미 처리된 형제 노드 (다양성 보장)
  - Characters JSON
  - 현재 노드 가설 + 메타데이터

❌ 제외됨:
  - 다른 브랜치의 노드들 (사촌, 삼촌 등)
  - Phase 1-3의 원본 마크다운 (요약만 사용)
  - 이전 노드 처리의 Agent 호출 결과
```

**컨텍스트 크기:** depth와 무관하게 최대 ~25K tokens (200K 윈도우의 12.5%)

### 보장 메커니즘

| 보장 | 구현 | LLM 우회 |
|------|------|:---:|
| MIN_NODES 도달 필수 | bash if 조건 | **불가능** |
| Deepen은 MIN_NODES 후에만 | bash 루프 밖에서 실행 | **불가능** |
| 컨텍스트 격리 | claude -p = 새 프로세스 | **불가능** |
| Ancestor only context | bash가 컨텍스트 파일 조립 | **불가능** |
| 형제 다양성 | sibling summaries 주입 | **불가능** |

### 파일 구조

```
apps/dormammu/scripts/
├── dormammu-dfs.sh          # Bash 오케스트레이터 (메인 루프 + context 조립)
├── process-one-node.md      # 단일 노드 처리 프롬프트
└── deepen-best-path.md      # Deepen + Report 프롬프트
```

---

## 산출물 폴더 구조

```
.dormammu/output/<sim-id>/
├── 01-background-research.md
├── 02-world-rules.md
├── 03-character-profiles.md
├── characters/
│   ├── <character-1>.md
│   └── <character-2>.md
├── tree-index.json
├── dfs-progress.txt            ← NEW: DFS 진행 로그
├── .node-context.md            ← NEW: 임시 컨텍스트 (매 노드마다 덮어씀)
├── N001/
│   ├── node.md
│   ├── N002/
│   │   ├── node.md
│   │   └── N005/
│   │       └── node.md
│   └── N003/
│       └── node.md          ← (PRUNED)
├── 05-deepen-best-path.md
└── 07-best-path-metadata.md
```

---

## 주의사항

- Phase 0~4: Claude Code 세션에서 Agent 서브에이전트로 실행
- Phase 5~7: `scripts/dormammu-dfs.sh` bash 오케스트레이터로 실행
- 매 노드마다 새 claude 프로세스 = 컨텍스트 포화 방지
- JSON 파싱 실패 시 자동 재시도
- 매 Phase 완료 시 run-state.json 업데이트 (중단/재개 지원)
- node.md의 Children 섹션에 상대 경로 링크 포함
- 한국어 기본 출력 (scenario.json에 language 설정 있으면 따름)
- 결과 확인: `python ${CLAUDE_PLUGIN_ROOT}/viewer/serve.py .dormammu/output/<sim-id>`

---

## Phase 8: Auto Deepen (조건부)

```
1. scenario.json의 auto_deepen 확인 (기본값: true)
2. auto_deepen이 true이면:
   - scenario.json의 image_generation 설정도 함께 전달
   - /dormammu:deepen 자동 실행 (최우수 경로 소설화)
3. auto_deepen이 false이면:
   - "시뮬레이션 완료! /dormammu:deepen으로 소설화할 수 있습니다." 안내 출력
```
