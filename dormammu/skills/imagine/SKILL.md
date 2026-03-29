---
name: imagine
description: "What-If 소설 시나리오 설정 — 인터뷰로 입력을 수집하고 시뮬레이션 목표를 구성"
---

# /dormammu:imagine

What-If 소설 창작 시뮬레이터의 시나리오를 설정합니다. 사용자와의 인터뷰를 통해
입력을 수집하고, 시뮬레이션 목표를 구성합니다.

## Usage

```
/dormammu:imagine "진격의 거인에서 아르민 대신 엘빈을 살렸다면?"
/dormammu:imagine "원피스에서 에이스가 죽지 않았다면 10년 뒤"
/dormammu:imagine "해리포터에서 네빌이 선택받은 아이였다면?"
/dormammu:imagine "스티브 잡스가 1985년에 애플에서 해고당하지 않았다면?"
/dormammu:imagine "AI 에이전트 기술이 지금 속도로 발전하면 100년 후 인류는?"
```

**Trigger keywords:** "imagine", "상상해봐", "what if", "만약에", "~했다면"

## Instructions

### Step 1: Interactive Interview

AskUserQuestion 도구를 사용해 순차적으로 입력을 수집합니다.
각 질문에는 대주제의 맥락에 맞는 구체적인 선택지를 제시합니다.

**Q1. 주제 (필수)**
"어떤 What-If 시나리오를 시뮬레이션할까요?"
- $ARGUMENTS가 있으면 자동으로 채우고 확인만 받음
- 없으면 예시와 함께 질문: "예: '진격의 거인에서 에렌이 땅울림을 하지 않았다면?'"

**주제 사전 조사 (Q1 직후, 자동 실행)**
Q1에서 주제를 받은 직후, Q2 선택지를 정확하게 제시하기 위해 가벼운 사전 조사를 수행합니다.
- WebSearch로 작품/세계관의 기본 정보 수집 (1~2회 검색)
- 파악 대상: 주요 캐릭터 목록, 핵심 설정/사건, 분기점 맥락
- 결과를 내부 컨텍스트에 보관 (파일 저장 없음, Q2~Q6 선택지 생성에만 활용)
- Claude가 이미 해당 작품을 잘 알고 있다고 판단되면 스킵 가능
- 사용자에게는 "주제를 파악하고 있습니다..." 정도로 간단히 안내

**Q2. 주인공 지정 (필수)**
"이 시나리오에서 누구의 시점을 중심으로 볼까요?"
- 주제에서 언급된 캐릭터들을 선택지로 제시
- 복수 선택 가능 (multiSelect: true)

**Q3. 톤/분위기 (선택)**
"어떤 분위기로 전개할까요?"
- 원작 톤 유지: 원작의 분위기를 최대한 재현
- 다크: 비극적, 암울한 전개 지향
- 라이트: 희망적, 해피엔딩 지향
- 리얼리스틱: 가장 현실적이고 개연성 있는 전개

**Q4. 시뮬레이션 범위 (선택)**
"어디까지 시뮬레이션할까요?"
- 직후 반응: 분기 직후 캐릭터와 세계의 즉각적 반응에 집중
- 중기 변화: 인물 관계와 세력 구도가 어떻게 변하는지
- 결말 변화: 원작 결말이 어떻게 달라지는지
- 전체 흐름: 분기점부터 결말까지 통째로 (기본값)
- 커스텀: 직접 입력

**Q5. 고정 조건/제약 (선택)**
"반드시 지켜야 할 조건이 있나요? (예: '특정 캐릭터는 반드시 생존', '세계관의 특정 규칙 유지')"
- 자유 텍스트 입력
- "없음" 옵션 포함

**Q6. 궁금한 포인트 (선택)**
"특히 궁금한 부분이 있나요? 이 질문에 우선적으로 가지를 뻗습니다."
- 주제에서 파생될 수 있는 흥미로운 질문을 2-3개 제시
- 자유 텍스트 입력 가능

**Q7. 탐색 전략 (선택)**
"시나리오를 어떻게 탐색할까요?"
- Wide (넓게, BFS): 같은 깊이의 모든 가능성을 먼저 탐색. 다양한 갈래를 비교하고 싶을 때.
- Deep (깊게, DFS): 하나의 줄기를 끝까지 파고든 뒤 다음 줄기로. 서사의 완결성이 중요할 때.
- Best-First (기본값): 점수가 높은 노드의 자식을 우선 탐색. 유망한 줄기를 깊이 파면서도 다양성 유지.

선택에 따라 `exploration_style` 필드를 설정:
- Wide → `"bfs"` (sort by depth ASC → 얕은 것 먼저)
- Deep → `"dfs"` (sort by depth DESC → 깊은 것 먼저)
- Best-First → `"best_first"` (sort by parent composite_score DESC → 유망한 것 먼저)

**Q8. DFS 엔진 (선택)**
"DFS 노드 처리 엔진을 선택해주세요:"
- Claude Code (claude -p): 기본값
- Codex (codex exec): OpenAI Codex CLI

선택에 따라 `dfs_engine` 필드를 설정:
- Claude → `"claude"`
- Codex → `"codex"` (codex 설치 여부와 API 키를 simulate Phase 0에서 확인)

**Q9. Heartbeat 설정 (선택)**
"시뮬레이션 중 멈춤 방지 heartbeat를 설정할까요?"
- 사용 (기본값): 10분 간격, 6시간 동안
- 커스텀: 간격(분)과 총 시간(시간)을 직접 입력
- 사용하지 않음

선택에 따라 `heartbeat` 필드를 설정:
- `{"enabled": true, "interval_min": 10, "total_hours": 6, "count": 36}` (기본값)
- `{"enabled": false}` (사용하지 않음)
- 커스텀: count = total_hours * 60 / interval_min

**Q10. 자동 심화 (선택)**
"시뮬레이션 완료 후 자동으로 최우수 경로를 소설화(Deepen)할까요?"
- 예 (기본값): DFS 완료 후 자동으로 /dormammu:deepen 실행
- 아니오: DFS까지만 실행, 이후 수동으로 deepen

**Q11. 이미지 생성 (Q10이 "예"일 때만)**
"Deepen 시 핵심 장면의 이미지를 AI로 생성할까요?"
- Gemini Flash (gemini-3.1-flash-image-preview): 빠르고 저렴 (~$0.045~0.151/장)
- Gemini Pro (gemini-3-pro-image-preview): 최고 품질 (~$0.134~0.24/장)
- OpenAI (gpt-image-1.5): OpenAI 키 사용 (~$0.04/장)
- 생성하지 않음 (기본값): 텍스트만 출력

선택에 따라 `image_generation` 필드를 설정:
- Gemini Flash → `{"enabled": true, "provider": "gemini", "model": "gemini-3.1-flash-image-preview", "quality": "standard"}`
- Gemini Pro → `{"enabled": true, "provider": "gemini", "model": "gemini-3-pro-image-preview", "quality": "high"}`
- OpenAI → `{"enabled": true, "provider": "openai", "model": "gpt-image-1.5", "quality": "standard"}`
- 생성하지 않음 → `{"enabled": false}`

### Step 2: Analyze Scenario

수집된 입력을 바탕으로 LLM 추론으로 분석:

**topic_type 자동 판별:**
- 실존 인물/사건이 중심이면 → `history`
- 원작 IP(만화, 소설, 게임 등)가 있으면 → `fiction`
- 순수 가설/미래 예측이면 → `speculative`

**세계관 감지 (topic_type별 분기):**
- `fiction`: 작품명, 원작 미디어 유형 (만화, 소설, 게임 등), 원작의 핵심 세계관 규칙 3-5개
- `history`: 관련 역사적 사실/인물 조사, 시대적 배경 및 실제 사건 흐름
- `speculative`: 관련 과학적 배경/기존 사고실험 조사, 현재 기술/사회 상태 파악

**스케일 감지:**
- `macro`: 국가/세계 단위 (decades/centuries)
- `micro`: 개인/소규모 집단 (days/years)

**평가 메트릭 가중치 조정:**
시나리오 특성에 따라 5개 메트릭 가중치를 미세 조정:
- character_fidelity (0.25): 캐릭터 충실도
- audience_resonance (0.20): 대상 독자 반응 예측
- emergence (0.20): 창발성
- narrative_flow (0.15): 서사 연결 매끄러움
- plausibility (0.20): 개연성

### Step 3: Show Analysis and Confirm

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  What-If Scenario
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Topic:        <주제>
Source:       <작품명> (<미디어 유형>)
Scale:        <macro/micro>
Protagonists: <주인공들>
Tone:         <톤>
Scope:        <시뮬레이션 범위>
Exploration:  <탐색 스타일>
DFS Engine:   <claude/codex>
Heartbeat:    <interval_min>분 간격, <total_hours>시간 (<count>회) 또는 "off"
Auto Deepen:  <yes/no>
Images:       <provider + model 또는 "off">

World Rules:
  1. <세계관 규칙>
  2. <세계관 규칙>
  ...

Constraints:
  - <고정 조건>

Focus Points:
  - <궁금한 포인트>

Evaluation Weights:
  character_fidelity  0.25
  audience_resonance  0.20
  emergence           0.20
  narrative_flow      0.15
  plausibility        0.20

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이대로 진행할까요? [Yes / Adjust]
```

### Step 4: Save Scenario

1. sim_id = UUID 8자리 생성 (Bash: `python3 -c "import uuid; print(uuid.uuid4().hex[:8])"`)
2. output_dir = `.dormammu/output/<sim-id>/`
3. `mkdir -p <output_dir>`
4. `<output_dir>/scenario.json`에 저장:

```json
{
  "sim_id": "<sim-id>",
  "topic": "<주제>",
  "source": {"title": "<작품명>", "media_type": "<유형>"},
  "protagonists": ["캐릭터1", "캐릭터2"],
  "tone": "original|dark|light|realistic",
  "scope": "immediate|midterm|ending|full|custom",
  "scope_detail": "<커스텀인 경우 상세 설명>",
  "constraints": ["조건1", "조건2"],
  "curiosity_points": ["궁금한 포인트1"],
  "exploration_style": "wide|deep|balance",
  "dfs_engine": "claude|codex",
  "scale": "macro|micro",
  "world_rules": ["규칙1", "규칙2"],
  "evaluation_weights": {
    "character_fidelity": 0.25,
    "audience_resonance": 0.20,
    "emergence": 0.20,
    "narrative_flow": 0.15,
    "plausibility": 0.20
  },
  "heartbeat": {
    "enabled": true,
    "interval_min": 10,
    "total_hours": 6,
    "count": 36
  },
  "auto_deepen": true,
  "image_generation": {
    "enabled": false
  },
  "created_at": "<ISO timestamp>"
}
```

5. 현재 활성 sim_id 기록: `.dormammu/active-sim-id` 파일에 sim_id 저장 (simulate가 찾을 수 있도록)

### Step 5: Confirm & Launch

```
[✓] Scenario saved to .dormammu/output/<sim-id>/scenario.json
```

AskUserQuestion으로 다음 단계를 물어봄:
"바로 시뮬레이션을 시작할까요?"
- 바로 시작: `/dormammu:simulate` 자동 실행
- 나중에: 안내만 표시

"나중에" 선택 시:
```
Ready to bring this story to life.

Next:
  /dormammu:simulate   — 시뮬레이션 시작
  /dormammu:status     — 현재 상태 확인
```
