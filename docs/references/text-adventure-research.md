# 텍스트 어드벤처 & 인터랙티브 픽션 엔진 연구

> **목적:** Dormammu 개발에 적용 가능한 인사이트 추출을 위한 텍스트 어드벤처 / AI 내러티브 시스템 종합 레퍼런스
>
> **작성일:** 2026-03-22
> **분류:** `docs/references/`

---

## 목차

1. [클래식 텍스트 어드벤처 — 기초 구조](#1-클래식-텍스트-어드벤처--기초-구조)
2. [현대 AI 인터랙티브 픽션](#2-현대-ai-인터랙티브-픽션)
3. [시뮬레이션 기반 내러티브](#3-시뮬레이션-기반-내러티브)
4. [결정 트리 / 브랜칭 내러티브](#4-결정-트리--브랜칭-내러티브)
5. [핵심 교훈 — Dormammu 적용 인사이트](#5-핵심-교훈--ese-적용-인사이트)

---

## 1. 클래식 텍스트 어드벤처 — 기초 구조

### 1.1 역사적 계보

```
1976  Colossal Cave Adventure (Crowther & Woods)
        │  최초의 텍스트 어드벤처. 2-단어 파서(NORTH, GET LAMP)
        │  동굴 탐험 = room graph의 원형
        ↓
1977  Zork I (MIT: Anderson, Blank, Daniels, Lebling)
        │  MDL(LISP 방언)로 작성. 완전 문장 파서 구현
        │  "kill troll with sword" 같은 복잡 명령 처리
        ↓
1980  Zork → Infocom 상업화 → ZIL + Z-machine
        │  이식성을 위한 가상머신(Z-machine) 설계
        │  게임 로직(ZIL) / 인터프리터 분리 = 현대 VM의 선조
        ↓
1987  Inform 1~6 (Graham Nelson)
        │  Z-machine 타깃 도메인 언어
        ↓
2006  Inform 7
           자연어 기반 프로그래밍("A sword is in the dungeon.")
```

### 1.2 Parser-Based vs Choice-Based — 핵심 차이

| 구분 | Parser-Based | Choice-Based |
|------|-------------|--------------|
| **입력 방식** | 자유 텍스트 입력 (`GO NORTH`, `PICK UP KEY`) | 제시된 선택지 클릭 |
| **대표작** | Zork, Infocom 시리즈, Inform 7 작품 | Choose Your Own Adventure, Twine 작품 |
| **플레이어 경험** | "무엇이든 가능하다"는 개방감, 퍼즐 지향 | 스토리 모멘텀 유지, 소설 읽기에 가까운 몰입 |
| **세계 모델** | 명시적 오브젝트 상태 필수 (`door.is_locked = true`) | 변수/플래그 추적으로 분기 처리 |
| **진입 장벽** | 파서 문법 학습 필요, "뭘 해야 할지 모름" 좌절감 | 즉시 참여 가능 |
| **서사 밀도** | 제작자가 예상치 못한 상호작용 가능 → emergent | 제작자가 설계한 분기 범위 안에서만 가능 |
| **Dormammu 연관성** | **WorldState의 명시적 상태 관리** 패턴이 직접 적용됨 | 분기 설계 없이 LLM이 생성 → Dormammu와 유사 |

> **핵심 통찰:** Parser IF의 자유도는 세계 모델이 탄탄할수록 신뢰감 있게 작동한다. "뭐든 할 수 있는 느낌"은 실제로는 수천 개의 명시적 상태 체크에서 온다.

### 1.3 Room/Location Graph

클래식 텍스트 어드벤처의 공간 구조:

```
[West of House] ──── [North of House] ──── [Behind House]
       │                                          │
  [Forest]                                   [Kitchen]
                                                  │
                              [Living Room] ──── [Cellar]
                                    │
                             [Underground]
```

**핵심 구성 요소:**

```python
# Zork/Inform 7 세계 모델 개념 (의사코드)
class Room:
    name: str
    description: str
    exits: dict[Direction, Room]   # NORTH, SOUTH, EAST, WEST, UP, DOWN
    objects: list[GameObject]
    is_lit: bool                   # 어두우면 동작 제한

class GameObject:
    name: str
    description: str
    location: Room | Player | Container
    properties: set[str]           # "takeable", "wearable", "openable"
    state: dict[str, Any]          # {"is_open": False, "is_locked": True}

class Player:
    location: Room
    inventory: list[GameObject]
    score: int
```

**Inform 7 자연어 예시:**

```inform7
The Dungeon is a room. "You are in a dark dungeon."
A rusty sword is in the Dungeon.
The rusty sword is a weapon.
The wooden door is a door. It is closed and locked.
The iron key unlocks the wooden door.
```

### 1.4 World Model과 Narrative Engine의 분리

Infocom이 설계한 핵심 아키텍처 원칙:

```
┌─────────────────────────────────────────┐
│           World Model (ZIL)             │
│  - 오브젝트 트리                          │
│  - 룸 그래프                             │
│  - 상태 변수 (locked, open, held...)     │
│  - 게임 규칙 (액션 핸들러)                │
└────────────────┬────────────────────────┘
                 │ 상태 조회 / 변경
┌────────────────▼────────────────────────┐
│          Narrative Engine               │
│  - 파서 (입력 → 정규화된 액션)            │
│  - 응답 생성 (상태 → 텍스트 출력)         │
│  - 스코어 계산                           │
└────────────────┬────────────────────────┘
                 │ 텍스트 I/O
┌────────────────▼────────────────────────┐
│     Z-machine Interpreter (이식 레이어)  │
│  - CP/M, DOS, Apple II, TRS-80...       │
└─────────────────────────────────────────┘
```

**왜 이 분리가 중요한가:**
- World Model은 **진실의 원천(source of truth)**. 내러티브가 틀려도 상태는 정확해야 한다.
- 같은 상태 변화가 다른 맥락에서 다른 텍스트를 생성할 수 있다.
- Dormammu에서 `WorldState`가 진실의 원천이고 LLM이 텍스트를 생성하는 구조가 정확히 이 패턴이다.

### 1.5 State Machine으로서의 텍스트 어드벤처

전통 텍스트 어드벤처는 사실상 **유한 상태 머신(FSM)**:

```
초기 상태
    │
    ├─ "TAKE KEY" → key.location = Player.inventory
    │                door.unlock_condition = satisfied
    │
    ├─ "OPEN DOOR" [if key in inventory] → door.is_open = True
    │               [if key not in inventory] → "The door is locked."
    │
    └─ "GO NORTH" [if door.is_open] → player.location = Next Room
                  [if door.is_closed] → "You can't go that way."
```

각 액션은:
1. **전제 조건 체크** (precondition): 현재 상태가 허용하는가?
2. **상태 변경** (state transition): WorldState 업데이트
3. **응답 생성** (output): 변경 결과를 텍스트로 출력

---

## 2. 현대 AI 인터랙티브 픽션

### 2.1 AI Dungeon — GPT 기반 텍스트 어드벤처

**배경:**
- 2019년 Nick Walton이 GPT-2로 개발, 이후 GPT-3 → 자체 fine-tuned 모델로 발전
- Latitude가 상업화. 2020년 초 100만+ 유저 폭발적 성장

**아키텍처 핵심:**

```
사용자 입력 ("I attack the dragon")
    │
    ▼
Context Window 관리
    ├─ Recent History (최근 N턴)
    ├─ Memory Layer (중요 사건 압축 요약)
    ├─ World Info / Lorebook (등장인물, 설정, 규칙)
    └─ Author's Note (현재 분위기/방향 힌트)
    │
    ▼
LLM 생성 (narrative continuation)
    │
    ▼
출력 (다음 장면)
```

**World State 관리 방식 (Phoenix 시스템 이후):**

```
Memory System
├─ Short-term: 직전 몇 턴의 대화 컨텍스트
├─ World Info: 트리거 키워드 기반 자동 삽입
│   예) "Aria" 언급 시 → "Aria is a 25-year-old elf warrior..." 자동 주입
└─ Author's Note: 현재 어조/장르/설정 힌트
    예) "[Adventure, dark fantasy, tense atmosphere]"
```

**AI Dungeon의 한계 (실제 운영 교훈):**

| 문제 | 원인 | 대응 |
|------|------|------|
| Narrative drift | LLM이 초기 설정을 망각 | World Info로 핵심 사실 고정 |
| 무한 인플레이션 | LLM이 새 오브젝트를 지속 생성 | 엄격한 컨텍스트 윈도우 관리 |
| 일관성 붕괴 | 이전 결정이 반영 안 됨 | Memory Layer 요약 삽입 |
| 고비용 | 모든 텍스트가 LLM 호출 | 캐싱, 모델 다운그레이드 |

### 2.2 NovelAI — 작가 지향 시스템

NovelAI는 AI Dungeon과 달리 **창작 보조** 포지셔닝:

```
┌──────────────────────────────────────────┐
│              NovelAI 컨텍스트 구조          │
│                                          │
│  Memory (단기 기억)                        │
│  ├─ 최근 사건 수동 요약                    │
│  └─ 작가가 AI에게 "지금 기억해야 할 것" 명시 │
│                                          │
│  Lorebook (장기 설정 DB)                   │
│  ├─ 캐릭터 시트 (외모, 성격, 관계)          │
│  ├─ 세계관 설정 (지리, 역사, 규칙)          │
│  └─ 트리거 키워드 → 관련 정보 자동 주입     │
│                                          │
│  Author's Note                           │
│  └─ 현재 톤/장르/금지 사항 힌트             │
└──────────────────────────────────────────┘
```

**Lorebook 패턴 — Dormammu의 WorldState와 유사:**

```json
{
  "entry": "Aria",
  "keys": ["Aria", "the elf"],
  "content": "Aria is a 25-year-old moon elf warrior. She is cautious and values honor above all. She has a scar on her left cheek from a battle at Ashenvale.",
  "enabled": true,
  "placement": "before_AN"
}
```

키워드가 감지되면 해당 엔트리가 컨텍스트에 자동 삽입 → LLM이 설정 망각 방지.

**2026 업데이트:** 128k 토큰 컨텍스트 윈도우 → 장편 소설 전체를 메모리에 유지 가능.

### 2.3 Character.AI — 캐릭터 중심 접근

Character.AI는 **고정된 캐릭터 페르소나** 유지가 핵심:

```
캐릭터 정의 (system prompt)
├─ 이름, 성격, 말투
├─ 절대 어기면 안 되는 규칙
└─ 예시 대화 (few-shot)
    │
    ▼
대화마다 페르소나 재주입 → 일관성 유지

문제: 긴 대화에서 캐릭터 드리프트 발생
해결: 주기적 페르소나 리마인더 삽입
```

### 2.4 LLM 기반 텍스트 어드벤처의 장단점

**장점:**
- 작가가 예상 못한 입력에도 자연스러운 응답 생성
- 세계관 규모에 관계없이 즉흥 서사 가능
- 플레이어의 창의적 행동을 수용
- 전통 IF 대비 개발 비용 대폭 절감

**단점:**

```
1. 상태 일관성 문제
   "당신이 10턴 전에 잃어버린 검을 다시 들고 있습니다" — 오류 생성
   → 해결: 명시적 상태 DB + LLM은 텍스트 생성만 담당

2. Hallucination Loop
   AI가 잘못된 사실을 생성 → 그것이 컨텍스트에 포함
   → 다음 턴에 그 사실을 기반으로 더 잘못된 내용 생성
   → 해결: 핵심 사실은 구조화된 데이터로 분리 관리

3. 인플레이션 (Inflation)
   LLM이 매 턴 새로운 오브젝트, 캐릭터, 장소를 생성
   → "열쇠"의 가치가 희석됨
   → 해결: 오브젝트 생성을 엄격히 제한하거나 레지스트리 관리

4. 비용
   모든 상호작용 = API 호출 = 비용
   → 해결: 캐싱, 짧은 프롬프트, 저렴한 모델 선택적 사용

5. 지연 시간
   직렬 이벤트 생성으로 응답이 느림
   → 해결: 병렬 생성, 스트리밍
```

### 2.5 Ian Bicking의 "Intra" — LLM 텍스트 어드벤처 실전 교훈

2025년 개인 프로젝트에서 발견한 핵심 아키텍처 패턴:

**작동한 것:**

```python
# 1. 명시적 상태는 코드로, 텍스트는 LLM으로
class GameState:
    player_inventory: set[str]   # "is holding the key"는 DB에
    door_locked: bool             # LLM에게 물어보지 않음
    npc_locations: dict[str, str]

# 2. Intent Parsing — 입력 정규화 후 상태 체크
def handle_input(raw_input: str) -> Action:
    action = llm_parse_intent(raw_input)  # "make them fight" → Attack(target=...)
    if not preconditions_met(action, game_state):
        return failure_response(action)   # LLM 없이 즉시 반환
    return execute_and_narrate(action)    # 상태 변경 후 LLM으로 텍스트 생성

# 3. NPC는 자신이 있는 방의 이벤트만 앎
def get_npc_context(npc: NPC) -> str:
    return filter_events(
        all_events,
        lambda e: e.location == npc.location  # 정보 은폐 → 현실감
    )
```

**작동하지 않은 것:**
- 도구/함수 호출(function calling)로 내러티브 생성: 평문 마크업이 더 나음
- NPC 완전 자율성: 비용 대비 효과 미미
- 상태 없이 순수 LLM 신뢰: hallucination loop 불가피

---

## 3. 시뮬레이션 기반 내러티브

### 3.1 Dwarf Fortress — Emergent Narrative의 원형

**기본 철학:**
> "Dwarf Fortress는 게임이기 이전에 이야기 생성 엔진이다."
> — Aaron Reed, *50 Years of Text Games* (2022)

**핵심 메커니즘:**

```
Procedural World Generation (Legend 모드)
    │
    ├─ 수천 년의 역사 자동 생성
    │   (전쟁, 인물, 도시, 유물의 역사)
    │
    └─ Fortress 모드 진입 시
           │
           ├─ 드워프들: 욕구(needs), 감정, 기억, 관계
           │   → 굶주림 → 기분 저하 → 작업 거부 → 연쇄 효과
           │
           ├─ 외부 위협: 고블린 습격, 야생동물, 재앙
           │
           └─ 플레이어: 직접 지시 불가, 구역 배치와 우선순위 설정만 가능

결과: 예측 불가능한 이야기가 시스템 충돌에서 자연 발생
```

**Emergent Narrative 생성 루프:**

```
시스템 A (굶주림)
    │ 드워프 Urist 배고픔
    ↓
시스템 B (감정)
    │ 기분 저하, 작업 효율 감소
    ↓
시스템 C (사회)
    │ 동료들이 Urist의 게으름에 불평
    ↓
시스템 D (정치)
    │ 리더가 Urist를 처벌
    ↓
시스템 E (복수)
    │ Urist가 리더에게 앙심
    ↓
예측 불가능한 클라이맥스
```

**Tarn Adams의 설계 방법론:**
게임을 만들기 전, 그 세계를 배경으로 단편 소설을 쓴다. 그 이야기를 게임이 시뮬레이션할 수 없다면 → 새 시스템을 추가한다. **이야기가 시스템 설계를 이끈다.**

**DF가 Dormammu에 주는 교훈:**

| DF 메커니즘 | Dormammu 적용 방향 |
|-----------|-------------|
| 드워프의 감정/욕구 시스템 | Agent의 `emotional_weight` 메모리 + 관계 변화 |
| 시스템 간 연쇄 반응 | `WorldState`의 다중 차원 상호작용 |
| 플레이어는 관찰자 | Dormammu는 시뮬레이션 실행 후 이야기를 읽는 구조 |
| 역사 생성 | 시나리오 트리가 분기별 "역사" 생성 |

### 3.2 RimWorld — AI Storyteller 시스템

**3명의 스토리텔러:**

```
Cassandra Classic   Phoebe Chillax    Randy Random
      │                   │                │
 점진적 난이도 상승    느긋한 곡선     완전 랜덤 이벤트
 "극적인 아치" 설계   초보자 친화     카오스 이야기 생성
      │                   │                │
      └───────────────────┴────────────────┘
                          │
              공통: 이벤트 풀(event pool) 관리
              │   - 습격(raids)
              │   - 기상 재해
              │   - 질병
              │   - 불시착 생존자
              │   - 정신 이상
              └── 각 스토리텔러가 타이밍과 강도를 결정
```

**Randy Random의 역설적 가치:**
Randy는 규칙이 없다 → 플레이어가 이야기의 저자가 된다.
순수한 카오스가 플레이어를 **능동적 내러티브 생성자**로 만든다.

**Emergent Narrative 생성 공식 (RimWorld):**

```
고정 프레임워크 (매 플레이마다 다름)
├─ 고유한 배경 이야기
├─ 독특한 성격 특성 (덜렁대는, 완벽주의, 공격적...)
└─ 세계 역사 시드

+

반자율 NPC
├─ 플레이어가 우선순위 설정
└─ 성격/기분/부상이 실제 행동을 변형

+

이벤트 시스템 (스토리텔러)
└─ 플레이어 선택의 결과로 연쇄 발생

= 고유한 이야기 (재현 불가)
```

**"의미 있는 실패(Meaningful Failure)":**
RimWorld에서 콜로니 붕괴는 실패가 아니라 이야기의 클라이맥스다. 취약성이 결정을 중요하게 만든다. Dormammu에서 낮은 점수로 가지치기(pruning)되는 브랜치도 이야기의 일부다.

### 3.3 Crusader Kings III — Event Chain 시스템

**이벤트 구조:**

```
Event Namespace.ID (예: intrigue.1023)
├─ type: character_event
├─ title: "The Betrayal"
├─ desc: "Your trusted spymaster has been caught..."
├─ trigger:
│   ├─ is_at_war = yes
│   ├─ spymaster_opinion < -20
│   └─ NOT = { has_character_flag = already_betrayed }
├─ immediate:
│   └─ set_character_flag = already_betrayed
└─ option:
    ├─ A: "Execute him." → effect: execute_character
    ├─ B: "Imprison him." → effect: imprison_character
    └─ C: "Forgive him." → effect: add_opinion_modifier
```

**트리거 기반 이벤트 vs 타이머 기반 이벤트 — Paradox의 진화:**

> "이전에는 게임 상태 파라미터와 랜덤 타이머로 이벤트를 생성했다.
>  이제는 모든 이벤트가 플레이어의 액션이나 주변 AI 행위자의 직접적인 결과다."
> — Maximilian Olbers, CK3 콘텐츠 디자인 리드

**핵심 설계 원칙:**

```
나쁜 방식: 랜덤 타이머 → 이벤트 발생 (맥락 없음)
좋은 방식: 플레이어/AI 행동 → 트리거 조건 만족 → 이벤트 발생

Dormammu 적용: 에이전트 행동 → WorldState 변화 → 새 이벤트/브랜치 생성
```

**Event Chain 패턴:**

```
Event A (발단: 스파이가 발각됨)
    │ option_B 선택 (투옥)
    ▼
Event B (3개월 후 트리거: 투옥된 자의 동료들이 불만)
    │ opinion < -30 && imprisoned_count > 0
    ▼
Event C (반란 음모 발각)
    │ player 대응에 따라 분기
    ├─ 강경 진압 → Event D (공포 통치 루트)
    └─ 유화 협상 → Event E (외교 루트)
```

**Paradox 이벤트 시스템의 강점:**
- 조건 기반이라 "말이 되는" 이야기만 발생
- 플래그(flag)로 동일 이벤트 중복 방지
- 선택의 결과가 미래 이벤트의 트리거가 됨 → 인과 사슬

### 3.4 세 시스템 비교

| 시스템 | 내러티브 생성 방식 | 플레이어 역할 | 스크립트 비율 |
|--------|-----------------|------------|------------|
| Dwarf Fortress | 시스템 충돌 → 자연 발생 | 관찰자 + 환경 설계자 | 극히 낮음 |
| RimWorld | 이벤트 풀 + AI 스토리텔러 | 생존 의사결정 | 중간 |
| Crusader Kings III | 조건부 이벤트 체인 | 정치적 행위자 | 중간~높음 |

**Emergent Narrative의 공통 공식:**

```
탄탄한 시스템 규칙
    × 자율적인 행위자 (욕구/성격/기억)
    × 예측 불가능한 외부 사건
    ─────────────────────────────
    = 플레이어가 직접 쓰지 않은 이야기
```

---

## 4. 결정 트리 / 브랜칭 내러티브

### 4.1 Choice of Games — ChoiceScript

**설계 철학:**
> "ChoiceScript는 변수를 기록함으로써 낭비되는 설계 노력을 최소화한다."

분기를 만드는 대신, **변수로 상태를 추적**하고 동일한 텍스트가 변수에 따라 다르게 표현된다.

**구조:**

```
startup.txt
├─ *create strength 50      # 변수 선언
├─ *create is_warrior false
└─ *goto_scene chapter1

chapter1.txt
├─ *if strength > 70
│   You tower over the guards.
├─ *else
│   The guards don't look impressed.
│
└─ *choice
    #Attack the guards.
        *set strength -10
        *goto fight_scene
    #Negotiate.
        *if is_warrior
            As a warrior, your reputation precedes you.
        *goto talk_scene
    *selectable_if (has_key) #Use the secret door.
        *goto escape_scene
```

**핵심 패턴 — Forking vs Filtering:**

```
Forking Choice (완전 분기)
    │
    ├─ 선택 A → 완전히 다른 경로
    └─ 선택 B → 완전히 다른 경로
    (제작 비용 O(2^n), 관리 어려움)

Filtering Choice (변수 기반 필터링)
    │
    ├─ 선택 A → courage +1
    ├─ 선택 B → charm +1
    └─ 이후 동일 씬에서 변수에 따라 다른 텍스트 표시
    (제작 비용 O(n), 유지보수 용이)
```

**교훈:** ChoiceScript 게임들은 수백 개 선택지를 제공하면서도 관리 가능한 이유가 변수 기반 필터링 덕분이다.

### 4.2 Twine — 비주얼 노드 에디터

```
[시작] → [숲 입구] → [선택: 동굴 들어가기 | 돌아가기]
                              │                │
                         [동굴 내부]         [마을]
                              │
                    [선택: 보물 집다 | 무시]
```

**Twine의 상태 관리 (SugarCube 엔진):**

```javascript
// 변수 설정
<<set $playerName = "Arthur">>
<<set $sword = true>>
<<set $reputation = 0>>

// 조건 분기
<<if $sword is true>>
    You raise your sword against the troll.
<<else>>
    You face the troll unarmed.
<</if>>

// 매크로로 상태 추적
<<set $reputation += 10>>
```

**Twine vs Ink 비교:**

| 구분 | Twine | Ink (inkle) |
|------|-------|-------------|
| **접근성** | 비주얼 에디터, 초보자 친화 | 텍스트 스크립트, 개발자 친화 |
| **통합** | 독립 웹 게임 | Unity/Unreal 플러그인 가능 |
| **상태 관리** | JavaScript 변수 | 내장 변수 + knot/stitch 구조 |
| **대표작** | 독립 IF 다수 | 80 Days, Heaven's Vault |
| **Dormammu 연관** | 낮음 | Ink의 knot 구조 = Dormammu ScenarioNode와 유사 |

### 4.3 Ink — 전문 게임 개발용 내러티브 스크립트

inkle Studios(80 Days, Sorcery!)가 개발한 전문 도구:

```ink
=== forest_path ===
You walk through the forest.
* [Take the left path]
    -> dark_cave
* [Take the right path]
    -> sunny_clearing
* {visited_village} [Head back to the village]
    -> village

=== dark_cave ===
~ courage++
The cave is dark and damp.
-> END
```

**Ink의 고급 상태 관리:**

```ink
// 변수와 함수
VAR health = 100
VAR has_sword = false

=== function damage(amount) ===
~ health -= amount
~ return health > 0  // 생존 여부 반환

// Tunnel — 재사용 가능한 서브루틴
=== combat_sequence ===
You fight!
{ damage(20):
    - true: You survive, bloodied.
    - false: You fall.
}
->->  // 터널 탈출, 호출 지점으로 복귀
```

**Ink의 핵심 강점 — Thread와 Tunnel:**

```ink
// Thread: 병렬 스토리라인 합류
=== prologue ===
<- setup_world
<- introduce_hero
<- introduce_villain
-> main_story

// Tunnel: 재사용 서브루틴
-> check_inventory ->
// 인벤토리 확인 후 자동으로 원래 위치로 복귀
```

### 4.4 비주얼 노블 — Route 시스템

**일반적인 VN 구조:**

```
공통 루트 (Common Route)
    │ 여러 선택지 → 플래그 누적
    │
분기점 (Branch Point)
    ├─ 루트 A (히로인 1)
    │   ├─ A-1 씬
    │   ├─ A-2 씬
    │   └─ A 엔딩
    │
    ├─ 루트 B (히로인 2)
    │   └─ B 엔딩
    │
    └─ True Route (모든 루트 클리어 후 해금)
         └─ True Ending (전체 이야기의 진실)
```

**플래그 기반 State Management:**

```python
# VN 상태 관리 개념 (의사코드)
class GameFlags:
    # 불리언 플래그
    met_hero: bool = False
    saved_village: bool = False
    true_route_unlocked: bool = False

    # 수치 변수
    affection_A: int = 0
    affection_B: int = 0

    # 루트 클리어 기록
    completed_routes: set[str] = set()

def check_true_route_unlock(flags: GameFlags) -> bool:
    return (
        "route_A" in flags.completed_routes and
        "route_B" in flags.completed_routes and
        flags.affection_A >= 80
    )
```

**VN의 핵심 교훈:**
- **의존성 그래프**: 어떤 플래그가 어떤 씬을 해금하는지 명시적 관리 필수
- **True End 설계**: 모든 루트가 완성되어야만 드러나는 진실 → 재플레이 동기 부여
- **분기 폭발 방지**: 공통 루트에서 플래그만 설정 → 루트 진입 후 분기

### 4.5 브랜칭 패턴 분류 (공통 원칙)

```
1. 단순 분기 (Simple Branch)
   A → B 또는 C
   복잡도: 낮음, 제작 비용: 낮음, 유지보수: 쉬움

2. 분기 후 합류 (Split & Merge)
   A → (B → D) 또는 (C → D)
   공통 경험을 유지하면서 다양성 제공

3. 연쇄 분기 (Chain Branch)
   A → B → (B1 또는 B2) → C → (C1 또는 C2)...
   지수적 복잡도 증가 → 관리 위험

4. 플래그 기반 필터링 (Flag Filtering)
   단일 경로지만 변수에 따라 다른 텍스트
   ChoiceScript, Ink의 핵심 패턴

5. 수렴형 내러티브 (Funnel Narrative)
   여러 입구 → 공통 중요 장면으로 수렴
   제작 효율 최대화
```

---

## 5. 핵심 교훈 — Dormammu 적용 인사이트

### 5.1 좋은 텍스트 어드벤처/인터랙티브 픽션의 핵심 요소

연구한 모든 시스템에서 반복되는 공통 원칙:

**① 세계가 먼저, 이야기는 나중 (World First, Narrative Second)**
- Dwarf Fortress: 시스템을 먼저 만들고, 이야기는 시스템 충돌에서 자연 발생
- Zork: 오브젝트 트리와 상태를 먼저 설계, 텍스트는 상태의 반영
- Dormammu 적용: `WorldState` 시뮬레이션이 정직하게 실행되어야 한다. LLM 내러티브가 WorldState를 "고쳐서는" 안 된다.

**② 진실의 원천은 하나여야 한다 (Single Source of Truth)**
- Infocom Z-machine: 상태는 코드에, 텍스트는 상태의 함수
- Ian Bicking의 Intra: "열쇠를 들고 있는지 여부는 코드가 안다"
- Dormammu 적용: `WorldState.agents`, `WorldState.relationships` 등이 진실. LLM이 생성한 내러티브에 모순이 있어도 상태는 정확해야 한다.

**③ 제약이 창의성을 만든다 (Constraints Enable Creativity)**
- ChoiceScript: 변수 기반 필터링으로 무한 분기 대신 관리 가능한 구조
- RimWorld Randy: 완전 랜덤이지만 이벤트 풀 안에서만 작동
- Dormammu 적용: `InspirationSystem`의 22개 SF 씨앗이 열린 LLM보다 강한 이유. 제약이 일관된 "세계"를 만든다.

**④ 의미 있는 실패 (Meaningful Failure)**
- RimWorld: 콜로니 붕괴 = 이야기의 클라이맥스, 실패가 아님
- Dwarf Fortress: "Losing is Fun"
- Dormammu 적용: 낮은 점수로 pruning되는 브랜치도 탐색 결과다. `PRUNED` 상태가 "실패"가 아니라 DFS의 유의미한 정보다.

### 5.2 World State 관리 Best Practices

연구 결과를 종합한 WorldState 관리 원칙:

```python
# Dormammu WorldState 관리 원칙

# 원칙 1: 상태 변경은 항상 새 스냅샷으로 (불변성)
# Infocom, Dormammu 공통 원칙
class TurnExecutor:
    def execute(self, state: WorldState) -> TurnResult:
        new_state = state.copy()          # 원본 불변 유지
        new_state.apply_actions(actions)  # 새 스냅샷에만 변경
        return TurnResult(world_state=new_state, ...)

# 원칙 2: 핵심 사실은 구조화된 데이터로 (Lorebook 패턴)
# NovelAI Lorebook → Dormammu WorldState.agents
{
    "agent_id": "aria_001",
    "name": "Aria",
    "traits": {"openness": 0.8, "agreeableness": 0.3},
    "memories": [...],         # 감정적 가중치로 정렬된 기억
    "relationships": {...}     # 다른 에이전트와의 관계
}

# 원칙 3: LLM에게는 요약된 컨텍스트만 (컨텍스트 윈도우 효율)
# AI Dungeon Memory Layer 패턴
def build_llm_context(state: WorldState, turn: int) -> str:
    return state.summary()  # 전체 상태 덤프가 아닌 요약

# 원칙 4: 에이전트는 자신이 아는 것만 (정보 은폐)
# CK3의 개인별 정보 접근 + Intra의 NPC 관점
def get_agent_context(agent: Agent, state: WorldState) -> str:
    return "\n".join(
        m.content for m in agent.memories
        if m.turn >= (turn - RECENT_WINDOW)  # 최근 기억만
    )
```

**WorldState 계층화 아키텍처 (NovelAI 패턴 적용):**

```
Tier 1: 불변 설정 (Lorebook)
├─ 에이전트 성격 특성 (Big-5)
├─ 시나리오 배경 및 제약
└─ 물리적 세계 규칙

Tier 2: 장기 상태 (WorldState snapshot)
├─ 관계 매트릭스
├─ 리소스 현황
└─ 중요 사건 기록

Tier 3: 단기 컨텍스트 (최근 N턴)
├─ 직전 액션들
└─ 현재 내러티브 흐름

Tier 4: LLM 생성 텍스트 (덧없는 출력)
└─ 읽고 나면 상태만 추출, 원문은 보관
```

### 5.3 Player/Reader Engagement를 높이는 패턴

**① Apophenia 활용 (의미 투영)**
- Dwarf Fortress의 단순 ASCII 그래픽: 플레이어가 직접 의미를 부여
- RimWorld의 최소 묘사: "Urist is sad" → 플레이어가 이야기를 완성
- Dormammu 적용: LLM이 모든 것을 설명하지 않아도 된다. 관계 수치 변화(+0.2 → -0.4)가 스스로 이야기를 만든다.

**② 내러티브 엘립시스 (Narrative Ellipsis)**
- 화면 밖에서 일어나는 일, 직접 보여주지 않는 전개
- RimWorld의 원정대: 보내고 나면 어떻게 됐는지 모른다 → 긴장감
- Dormammu 적용: 모든 턴을 보여주지 않고, 중요한 순간만 하이라이트. `TurnLogger`의 EventLog 중 emotional_weight 높은 것만 전면에.

**③ 인과 사슬의 가시성 (Visible Causality)**
- CK3: "네가 스파이마스터를 투옥했기 때문에 반란이 일어났다"
- 원인-결과 연결이 보여야 몰입도 상승
- Dormammu 적용: 브랜치 평가 시 `rationale`에 인과 관계 명시. "A가 B를 배신했고, 그것이 C의 동기가 됨"

**④ 의미 있는 선택과 트레이드오프**
- ChoiceScript의 stat-based choices: 선택에 비용과 이득이 있어야 의미 있음
- VN의 True Route: 모든 루트를 경험해야 전체 진실 접근 가능
- Dormammu 적용: `HypothesisEvaluator`의 4차원 점수(emergence/narrative/diversity/novelty)가 서로 상충할 때 트레이드오프가 발생 → 이것이 "이야기"

### 5.4 AI 기반 Narrative의 일관성 유지 방법

연구한 시스템들의 일관성 유지 전략 종합:

**전략 1: 구조화된 상태 + LLM 텍스트 분리**

```
[나쁜 방식]
LLM: "이전에 잃어버린 검을 들고 있습니다"
     ← LLM이 상태와 내러티브를 동시에 생성

[좋은 방식]
Code: player.inventory.has("sword") == False
LLM: [sword not in inventory, player is unarmed] →
     "맨손으로 적과 마주선 당신은..."
     ← 상태는 코드, 텍스트만 LLM
```

**전략 2: 컨텍스트 계층화 (AI Dungeon + NovelAI 방식)**

```python
def build_simulation_prompt(
    agent: Agent,
    world: WorldState,
    turn: int,
    inspiration: str | None
) -> str:
    sections = []

    # Tier 1: 불변 설정 (항상 포함)
    sections.append(f"## World Rules\n{world.scenario_context}")

    # Tier 2: 에이전트 장기 기억 (중요도 상위 N개)
    top_memories = sorted(agent.memories, key=lambda m: -m.emotional_weight)[:5]
    sections.append(f"## {agent.name}'s Core Memories\n" + "\n".join(m.content for m in top_memories))

    # Tier 3: 최근 상태 (WorldState 요약)
    sections.append(f"## Current State\n{world.summary()}")

    # Tier 4: 영감 주입 (선택적)
    if inspiration:
        sections.append(f"## Narrative Inspiration\n{inspiration}")

    return "\n\n".join(sections)
```

**전략 3: Hallucination Loop 방지**

```
탐지: 생성된 텍스트가 WorldState와 모순되는지 체크
방지: 핵심 사실을 시스템 프롬프트에 명시적으로 고정
복구: 모순 감지 시 WorldState를 우선, 내러티브를 수정

예시 체크:
- 텍스트에 "sword"가 등장 → inventory에 없으면 경고
- 텍스트에 "alone"이 나옴 → 에이전트가 여럿이면 경고
```

**전략 4: 에이전트별 관점 제한 (CK3 + Intra 방식)**

```python
class Agent:
    def build_decision_context(self, world: WorldState, turn: int) -> str:
        # 에이전트는 자신의 기억만 접근
        my_memories = self.memories[-10:]

        # 에이전트는 같은 장소의 이벤트만 앎
        visible_events = [
            e for e in world.recent_events
            if e.location == self.current_location
               or self.name in e.participants
        ]

        # 에이전트는 자신의 관계 수치를 명시적으로 모름
        # (감정적 표현으로만 전달)
        return self._format_subjective_context(my_memories, visible_events)
```

### 5.5 Dormammu를 위한 종합 아키텍처 권고사항

연구 결과를 Dormammu의 현재 구조에 매핑:

```
현재 Dormammu 구조 → 연구 기반 강화 방향
──────────────────────────────────────

WorldState                    ← DF의 시스템, Infocom의 상태 모델
├─ agents (현재 구현됨)
│   └─ + 에이전트별 관점 제한 (Intra 패턴)
├─ relationships (현재 구현됨)
│   └─ + 관계 변화 인과 사슬 추적
├─ events (현재 구현됨)
│   └─ + emotional_weight 기반 하이라이트 선별
└─ resources (현재 구현됨)

TurnExecutor                  ← Infocom 액션 핸들러 패턴
└─ + 액션 전제 조건 체크 강화 (파서 IF 방식)

HypothesisEvaluator           ← RimWorld 스토리텔러 + CK3 트리거 시스템
└─ 4차원 점수가 트레이드오프를 만들 때 가장 흥미로운 브랜치

InspirationSystem             ← Dwarf Fortress "이야기 먼저 설계" 방법론
└─ 22개 SF 씨앗 = 작동 중. 씨앗별 예상 이야기 아크 정의 고려

ScenarioTree (DFS)            ← VN의 True Route 패턴
└─ 깊은 브랜치 = True Route. pruning은 "실패"가 아닌 내러티브 정보
```

**가장 중요한 단일 교훈:**

> **세계 모델이 진실이고, LLM은 번역기다.**
>
> Zork의 Z-machine이 상태를 보호하고 ZIL이 텍스트를 생성했듯,
> Dormammu의 `WorldState`는 절대적 진실이고 LLM은 그 상태를 아름다운 이야기로 번역하는 도구다.
> LLM이 상태를 바꾸게 하는 순간, 일관성이 붕괴된다.

---

## 참고 자료

### 공식 문서 / 위키

- [Inform 7 공식 사이트](https://ganelson.github.io/inform-website/) — 자연어 기반 IF 프로그래밍
- [inkle/ink GitHub](https://github.com/inkle/ink) — 브랜칭 내러티브 스크립트
- [ChoiceScript Introduction](https://www.choiceofgames.com/make-your-own-games/choicescript-intro/) — 변수 기반 IF
- [RimWorld AI Storytellers Wiki](https://rimworldwiki.com/wiki/AI_Storytellers) — 스토리텔러 메커니즘
- [CK3 Event Modding Wiki](https://ck3.paradoxwikis.com/Event_modding) — 이벤트 체인 구조

### 연구 / 분석

- [Characterization and Emergent Narrative in Dwarf Fortress](https://www.researchgate.net/publication/356686095_Characterization_and_Emergent_Narrative_in_Dwarf_Fortress) — 학술 논문
- [Intra: LLM-Driven Text Adventure 설계 노트](https://ianbicking.org/blog/2025/07/intra-llm-text-adventure) — Ian Bicking, 2025 (LLM IF 실전 교훈)
- [RimWorld, Dwarf Fortress, Procedurally Generated Storytelling](https://www.gamedeveloper.com/design/rimworld-dwarf-fortress-and-procedurally-generated-story-telling) — Game Developer 분석
- [50 Years of Text Games: Dwarf Fortress](https://if50.substack.com/p/2006-dwarf-fortress) — Aaron Reed
- [Standard Patterns in Choice-Based Games](https://heterogenoustasks.wordpress.com/2015/01/26/standard-patterns-in-choice-based-games/) — 브랜칭 패턴 분류
- [World Models vs Narrative Choices](https://maetl.net/notes/storyboard/choice-fiction) — parser vs choice 심층 분석

### AI Dungeon / NovelAI

- [AI Dungeon Wikipedia](https://en.wikipedia.org/wiki/AI_Dungeon) — 역사 및 아키텍처
- [How We Scaled AI Dungeon 2](https://aidungeon.medium.com/how-we-scaled-ai-dungeon-2-to-support-over-1-000-000-users-d207d5623de9) — 운영 교훈
- [NovelAI Memory and Lorebooks](https://www.toolify.ai/ai-news/unveiling-novelais-secret-sauce-memory-and-lorebooks-90326) — 컨텍스트 관리 시스템

### 게임 디자인

- [Twine vs Ink vs Yarn 비교](https://medium.com/@haikus_by_KN/authoring-interactive-narrative-in-twine-2-vs-ink-a-quick-and-dirty-comparison-using-examples-e695eb4dfc3e)
- [VN 브랜칭 구조](https://vndev.wiki/Branching) — 비주얼 노블 분기 패턴
- [Text-Based Game Design Principles](https://gamedesignskills.com/game-design/text-based/)
