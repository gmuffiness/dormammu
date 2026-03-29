---
name: imagine
description: "What-If 소설 시나리오 설정 — 인터뷰로 7가지 입력을 수집하고 시뮬레이션 목표를 구성"
---

# /dormammu:imagine

What-If 소설 창작 시뮬레이터의 시나리오를 설정합니다. 사용자와의 인터뷰를 통해
7가지 입력을 수집하고, 시뮬레이션 목표를 구성합니다.

## Usage

```
/dormammu:imagine "진격의 거인에서 아르민 대신 엘빈을 살렸다면?"
/dormammu:imagine "원피스에서 에이스가 죽지 않았다면 10년 뒤"
/dormammu:imagine "해리포터에서 네빌이 선택받은 아이였다면?"
```

**Trigger keywords:** "imagine", "상상해봐", "what if", "만약에", "~했다면"

## Instructions

### Step 1: Parse Topic (대주제)

사용자 인자에서 What-If 질문을 추출합니다.
인자가 없으면: "어떤 세계관의 What-If 시나리오를 상상해볼까요? (예: '진격의 거인에서 에렌이 땅울림을 하지 않았다면?')"

### Step 2: Interactive Interview (6가지 추가 입력)

대주제를 받은 후, AskUserQuestion 도구를 사용해 순차적으로 추가 입력을 수집합니다.
각 질문에는 대주제의 맥락에 맞는 구체적인 선택지를 제시합니다.

**Q1. 주인공 지정 (필수)**
"이 시나리오에서 누구의 시점을 중심으로 볼까요?"
- 대주제에서 언급된 캐릭터들을 선택지로 제시
- 복수 선택 가능 (multiSelect: true)

**Q2. 톤/분위기 (선택)**
"어떤 분위기로 전개할까요?"
- 원작 톤 유지: 원작의 분위기를 최대한 재현
- 다크: 비극적, 암울한 전개 지향
- 라이트: 희망적, 해피엔딩 지향
- 리얼리스틱: 가장 현실적이고 개연성 있는 전개

**Q3. 시간 범위 (선택)**
"분기점 이후 얼마나 먼 미래까지 시뮬레이션할까요?"
- 단기 (1-5년): 분기 직후의 즉각적 파급효과
- 중기 (5-20년): 캐릭터 인생의 중요한 변화
- 장기 (20-100년): 세대를 아우르는 거시적 변화
- 커스텀: 직접 입력

**Q4. 고정 조건/제약 (선택)**
"반드시 지켜야 할 조건이 있나요? (예: '특정 캐릭터는 반드시 생존', '세계관의 특정 규칙 유지')"
- 자유 텍스트 입력
- "없음" 옵션 포함

**Q5. 궁금한 포인트 (선택)**
"특히 궁금한 부분이 있나요? 이 질문에 우선적으로 가지를 뻗습니다."
- 대주제에서 파생될 수 있는 흥미로운 질문을 2-3개 제시
- 자유 텍스트 입력 가능

**Q6. 탐색 스타일 (선택)**
"시나리오를 어떻게 탐색할까요?"
- Wide (넓게): 다양한 가능성을 폭넓게 탐색 (분기 많음)
- Deep (깊게): 하나의 줄기를 끝까지 완성도 높게
- Balance (밸런스): 기본값 — 적절한 폭과 깊이

### Step 3: Analyze Scenario

수집된 입력을 바탕으로 LLM 추론으로 분석:

**세계관 감지:**
- 작품명, 원작 미디어 유형 (만화, 소설, 게임 등)
- 원작의 핵심 세계관 규칙 3-5개

**스케일 감지:**
- `macro`: 국가/세계 단위 (decades/centuries)
- `micro`: 개인/소규모 집단 (days/years)

**평가 메트릭 가중치 조정:**
시나리오 특성에 따라 5개 메트릭 가중치를 미세 조정:
- character_fidelity (0.25): 캐릭터 충실도
- fandom_resonance (0.20): 팬 반응 예측
- emergence (0.20): 창발성
- diversity (0.15): 다양성
- plausibility (0.20): 개연성

### Step 4: Show Analysis and Confirm

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  What-If Scenario
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Topic:        <대주제>
Source:       <작품명> (<미디어 유형>)
Scale:        <macro/micro>
Protagonists: <주인공들>
Tone:         <톤>
Time Range:   <시간 범위>
Exploration:  <탐색 스타일>

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
  fandom_resonance    0.20
  emergence           0.20
  diversity           0.15
  plausibility        0.20

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

이대로 진행할까요? [Yes / Adjust]
```

### Step 5: Save Scenario

`.ese/scenario.json`에 저장:

```json
{
  "topic": "<대주제>",
  "source": {"title": "<작품명>", "media_type": "<유형>"},
  "protagonists": ["캐릭터1", "캐릭터2"],
  "tone": "original|dark|light|realistic",
  "time_range": {"value": 10, "unit": "years", "label": "중기"},
  "constraints": ["조건1", "조건2"],
  "curiosity_points": ["궁금한 포인트1"],
  "exploration_style": "wide|deep|balance",
  "scale": "macro|micro",
  "world_rules": ["규칙1", "규칙2"],
  "evaluation_weights": {
    "character_fidelity": 0.25,
    "fandom_resonance": 0.20,
    "emergence": 0.20,
    "diversity": 0.15,
    "plausibility": 0.20
  },
  "created_at": "<ISO timestamp>"
}
```

`.ese/` 디렉토리가 없으면 먼저 생성.

### Step 6: Confirm

```
[✓] Scenario saved to .ese/scenario.json

Ready to bring this story to life.

Next:
  /dormammu:research   — 팬덤 리서치 + 캐릭터/세계관 분석 (권장)
  /dormammu:run         — 바로 시뮬레이션 시작 (24h 자동)
  /dormammu:status      — 현재 상태 확인
```
