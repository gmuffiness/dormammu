# Dormammu — 서비스 기획서

> 버전: 1.0 | 작성일: 2026-03-18 | 상태: 초안

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [핵심 컨셉](#2-핵심-컨셉)
3. [시스템 아키텍처](#3-시스템-아키텍처)
4. [데이터 모델](#4-데이터-모델)
5. [시뮬레이션 엔진 상세](#5-시뮬레이션-엔진-상세)
6. [DFS 시나리오 트리](#6-dfs-시나리오-트리)
7. [가설 생성 시스템](#7-가설-생성-시스템)
8. [로깅 & 리플레이 시스템](#8-로깅--리플레이-시스템)
9. [자율 실행 루프](#9-자율-실행-루프)
10. [평가 시스템](#10-평가-시스템)
11. [Phase B 시각화 로드맵](#11-phase-b-시각화-로드맵)
12. [API 비용 최적화 전략](#12-api-비용-최적화-전략)
13. [기술 스택 & 의존성](#13-기술-스택--의존성)
14. [구현 우선순위](#14-구현-우선순위)

---

## 1. 프로젝트 개요

### 1.1 한 줄 정의

> **"Doctor Strange처럼 미래를 탐색하는 AI 시뮬레이션 엔진"**
> — 하나의 질문에서 출발해 수천 개의 가능한 미래를 자동 탐색하고, 최선/최악의 시나리오 트리를 구축한다.

### 1.2 배경 및 동기

현재 AI 시스템은 주어진 질문에 단일 답변을 제공한다. 하지만 복잡한 현실 세계의 문제(기후변화, 기술 발전, 사회 변화)는 단선적 예측으로는 이해할 수 없다. Dormammu는 다음 물음에 답하기 위해 설계되었다:

- "인류의 다음 100년에 어떤 일이 일어날까?"
- "AGI가 등장하면 사회는 어떻게 변할까?"
- "핵전쟁이 발생했을 때 살아남는 시나리오는?"

Dormammu는 이 질문들을 입력받아 **수천 개의 시나리오를 자율적으로 생성·실행·평가**하고, DFS(깊이 우선 탐색)로 가장 의미 있는 미래 경로를 탐색한다.

### 1.3 목표

| 목표 | 설명 |
|------|------|
| **자율 탐색** | 사람 개입 없이 24시간 시뮬레이션 루프 실행 |
| **다중 스케일** | 문명 단위(매크로) ↔ 개인 단위(마이크로) 전환 |
| **재현 가능성** | 모든 시뮬레이션 상태 저장 → 임의 시점 재진입 |
| **SF 영감** | 아이디어 고갈 시 SF 문학/영화 지식 자동 주입 |
| **확장성** | Phase A(텍스트) → Phase B(2D 픽셀 시각화) |

### 1.4 프로젝트 범위

| 구분 | 포함 | 제외 |
|------|------|------|
| Phase A | 텍스트 기반 시뮬레이션 엔진, DFS 트리, 자율 루프, 리플레이 | 시각화 |
| Phase B | 2D 픽셀 맵, 줌 레벨(세계↔도시↔개인) | 3D, 멀티유저 |

---

## 2. 핵심 컨셉

### 2.1 Doctor Strange 프레임

마블의 Doctor Strange는 *Avengers: Infinity War*에서 14,000,605개의 미래를 동시에 탐색해 유일한 승리 경로를 찾는다. Dormammu는 이 컨셉을 현실화한다:

```
사용자 입력: "인류의 다음 100년은?"
         │
         ▼
┌─────────────────────────────────────────────────────┐
│           Dormammu: 가능한 미래 탐색                   │
│                                                     │
│  현재 ──► [가설 A: AGI 공존]──► [AI 황금기]──► 번영  │
│         │                   └──► [AI 전쟁]──► ✗ 가지치기
│         │                                          │
│         ├──► [가설 B: 기후위기]──► [적응]──► 新문명  │
│         │                     └──► [붕괴]──► ✗ 가지치기
│         │                                          │
│         └──► [가설 C: 핵전쟁]──► [소수 생존]──► ...  │
│                              └──► [전멸]──► ✗ 가지치기
│                                                     │
│  결과: 긍정 경로 심화 탐색 / 부정 경로 즉시 가지치기    │
└─────────────────────────────────────────────────────┘
```

### 2.2 핵심 철학

1. **가설 주도**: 모든 시뮬레이션은 구체적 가설에서 시작
2. **에이전트 자율성**: AI 에이전트들이 스스로 상호작용하며 역사를 만들어냄
3. **평가 기반 탐색**: 주관적 판단이 아닌 자동 평가 기준으로 분기 결정
4. **스케일 적응**: 필요에 따라 문명 스케일과 개인 스케일을 전환
5. **SF 지식 활용**: 수십 년간 인류가 상상한 SF 시나리오를 영감으로 활용

### 2.3 전체 흐름 다이어그램

```
┌──────────────────────────────────────────────────────────────────┐
│                        사용자 인터페이스                           │
│  입력: 토픽/질문  │  평가 기준 선택  │  리플레이 진입               │
└──────────────┬───────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                    Claude Code 오케스트레이터                      │
│                                                                  │
│  ① 토픽 분석     → 평가 기준 후보 생성                            │
│  ② 가설 생성     → 시뮬레이션 환경 설정                            │
│  ③ 결과 분석     → 긍정/부정 판정                                  │
│  ④ DFS 결정     → 다음 분기 선택                                  │
│  ⑤ SF 주입      → 아이디어 고갈 시 SF 지식 투입                    │
└──────────────┬───────────────────────────────────────────────────┘
               │ 환경 설정 전달
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      시뮬레이션 엔진                               │
│                                                                  │
│  에이전트 생성 → 자율 상호작용 → 턴 처리 → 노드 종료               │
│                                                                  │
│  [매크로 모드] 국가/문명 단위 LLM 서술 (수십 년 단위)               │
│  [마이크로 모드] 개인 에이전트 상호작용 (일/주 단위)                 │
└──────────────┬───────────────────────────────────────────────────┘
               │ 결과 + 전체 로그
               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      로깅 & 저장소                                │
│  SQLite DB  │  JSON 스냅샷  │  대화 로그  │  상태 히스토리          │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 시스템 아키텍처

### 3.1 컴포넌트 맵

```
ese/
├── orchestrator/              # Claude Code 오케스트레이터
│   ├── topic_analyzer.py      # 토픽 분석 및 평가 기준 생성
│   ├── hypothesis_generator.py # 가설 생성 (+ SF 주입)
│   ├── environment_builder.py  # 시뮬레이션 환경 설정
│   ├── result_analyzer.py      # 결과 분석 및 판정
│   └── dfs_controller.py       # DFS 트리 탐색 제어
│
├── simulation/                # 시뮬레이션 엔진
│   ├── engine.py              # 메인 시뮬레이션 루프
│   ├── agent.py               # 에이전트 클래스
│   ├── agent_factory.py       # 에이전트 생성 (페르소나 할당)
│   ├── interaction_manager.py  # 에이전트 간 상호작용
│   ├── turn_manager.py        # 턴 처리
│   ├── macro_simulator.py     # 매크로 스케일 시뮬레이터
│   └── micro_simulator.py     # 마이크로 스케일 시뮬레이터
│
├── evaluation/                # 평가 시스템
│   ├── criteria_generator.py  # 평가 기준 자동 생성
│   ├── scorer.py              # 점수 계산
│   └── judge.py               # 긍정/부정 판정
│
├── sf_inspiration/            # SF 영감 시스템
│   ├── detector.py            # 아이디어 고갈 감지
│   ├── sf_knowledge.py        # SF 지식 베이스 (LLM 활용)
│   └── web_searcher.py        # 웹 검색 (최후 수단)
│
├── logging/                   # 로깅 시스템
│   ├── logger.py              # 메인 로거
│   ├── replay.py              # 리플레이 시스템
│   └── exporter.py            # 데이터 내보내기
│
├── storage/                   # 저장소
│   ├── database.py            # SQLite 인터페이스
│   ├── snapshot.py            # JSON 스냅샷 관리
│   └── migrations/            # DB 스키마 마이그레이션
│
├── api/                       # 외부 API 인터페이스
│   ├── openai_client.py       # OpenAI API 래퍼
│   └── rate_limiter.py        # API 사용량 제어
│
├── cli/                       # 커맨드라인 인터페이스
│   ├── main.py                # 메인 진입점
│   ├── interactive.py         # 대화형 모드
│   └── replay_cli.py          # 리플레이 모드
│
└── config/
    ├── settings.py            # 전역 설정
    └── prompts/               # 프롬프트 템플릿
        ├── topic_analysis.txt
        ├── hypothesis_gen.txt
        ├── agent_persona.txt
        ├── macro_narration.txt
        └── evaluation.txt
```

### 3.2 컴포넌트 책임 정의

| 컴포넌트 | 책임 | 핵심 출력 |
|---------|------|----------|
| `topic_analyzer` | 토픽 → 맥락 + 평가 기준 후보 | `TopicContext`, `CriteriaList` |
| `hypothesis_generator` | 맥락 + 역사 → 신규 가설 | `Hypothesis` |
| `environment_builder` | 가설 → 초기 세계 상태 | `WorldState` |
| `engine` | 에이전트 루프 실행 | `SimulationResult` |
| `result_analyzer` | 결과 → 평가 점수 + 판정 | `EvaluationResult` |
| `dfs_controller` | 트리 상태 관리 + 다음 노드 선택 | `NextAction` |
| `sf_inspiration` | 고갈 감지 → SF 영감 주입 | `InspirationHints` |
| `logger` | 모든 이벤트 영구 저장 | SQLite + JSON |
| `replay` | 임의 시점 상태 복원 | `RestoredState` |

### 3.3 실행 모드

| 모드 | 설명 | 용도 |
|------|------|------|
| `autonomous` | 24시간 자율 실행 루프 | 대규모 탐색 |
| `interactive` | 사용자가 단계별 승인 | 디버깅, 탐색 |
| `replay` | 저장된 시뮬레이션 재생 | 분석, NPC 대화 |
| `single` | 단일 시뮬레이션 실행 | 테스트 |

---

## 4. 데이터 모델

### 4.1 엔티티 관계도

```
Session (세션)
  │
  ├──► TopicContext (토픽 컨텍스트)
  │      ├── topic_text
  │      ├── background_analysis
  │      └── selected_criteria[] ──► EvaluationCriteria
  │
  ├──► ScenarioTree (시나리오 트리)
  │      └── nodes[] ──► TreeNode
  │                          ├── hypothesis ──► Hypothesis
  │                          ├── simulation ──► Simulation
  │                          ├── evaluation ──► EvaluationResult
  │                          ├── parent_node_id
  │                          ├── child_node_ids[]
  │                          └── status: [pending/running/positive/negative/pruned]
  │
  └──► RunLog (실행 로그)
         └── entries[] ──► LogEntry

Simulation (시뮬레이션)
  ├── scale: [macro/micro]
  ├── world_state ──► WorldState
  ├── agents[] ──► Agent
  ├── turns[] ──► Turn
  └── final_state ──► WorldState

Agent (에이전트)
  ├── persona ──► Persona
  ├── memory[]
  ├── relationships{} ──► Agent
  └── state_history[]

Turn (턴)
  ├── turn_number
  ├── simulated_time_delta
  ├── events[]
  ├── agent_actions[] ──► AgentAction
  ├── conversations[] ──► Conversation
  └── world_state_snapshot ──► WorldState
```

### 4.2 핵심 스키마 정의

#### Session

```python
@dataclass
class Session:
    id: str                          # UUID
    created_at: datetime
    topic: str                       # 사용자 입력 토픽
    topic_context: TopicContext
    scenario_tree: ScenarioTree
    status: Literal['active', 'paused', 'complete', 'failed']
    total_api_cost_usd: float
    config: SessionConfig
```

#### TreeNode

```python
@dataclass
class TreeNode:
    id: str                          # UUID
    session_id: str
    parent_id: Optional[str]         # 루트는 None
    depth: int                       # 트리 깊이 (0 = 루트)
    hypothesis: Hypothesis
    simulation_id: Optional[str]     # 실행 전에는 None
    evaluation: Optional[EvaluationResult]
    status: NodeStatus               # pending/running/positive/negative/pruned
    children: List[str]              # 자식 노드 ID 목록
    sf_inspiration_used: bool        # SF 영감 사용 여부
    created_at: datetime
    completed_at: Optional[datetime]
```

#### Hypothesis

```python
@dataclass
class Hypothesis:
    id: str
    title: str                       # 한 줄 제목
    description: str                 # 상세 설명
    key_assumptions: List[str]       # 핵심 가정 목록
    initial_conditions: Dict         # 초기 세계 조건
    expected_timespan_years: int     # 시뮬레이션 기간 (년)
    scale: SimulationScale           # macro / micro / adaptive
    inspiration_source: Optional[str] # SF 작품명 (영감 받은 경우)
```

#### WorldState

```python
@dataclass
class WorldState:
    year: int                        # 현재 연도
    technology_level: float          # 0.0 ~ 1.0
    population: int                  # 세계 인구
    resources: Dict[str, float]      # 자원 현황
    geopolitical: Dict               # 지정학적 상태
    cultural: Dict                   # 문화/사회 상태
    major_events: List[str]          # 이 시점까지의 주요 사건
    custom_fields: Dict              # 가설별 커스텀 필드
```

#### Agent

```python
@dataclass
class Agent:
    id: str
    name: str
    persona: Persona
    role: str                        # 역할 (지도자, 과학자, 시민 등)
    memory: List[MemoryEntry]        # 에이전트 기억
    relationships: Dict[str, Relationship]  # 다른 에이전트와의 관계
    current_state: AgentState        # 현재 심리/물리 상태
    decision_history: List[Decision]
```

#### Persona

```python
@dataclass
class Persona:
    background: str                  # 출신/역사
    personality_traits: List[str]    # 성격 특성 (MBTI 등)
    values: List[str]                # 핵심 가치관
    goals: List[str]                 # 목표
    fears: List[str]                 # 두려움
    skills: List[str]                # 능력/전문성
    worldview: str                   # 세계관
```

#### EvaluationCriteria

```python
@dataclass
class EvaluationCriteria:
    id: str
    name: str                        # "인류 생존률"
    description: str
    measurement_method: str          # 어떻게 측정할지
    weight: float                    # 0.0 ~ 1.0 (가중치)
    positive_threshold: float        # 이 이상이면 긍정
    is_selected: bool                # 사용자 선택 여부
```

#### EvaluationResult

```python
@dataclass
class EvaluationResult:
    node_id: str
    scores: Dict[str, float]         # criteria_id -> score
    weighted_total: float            # 가중 합산 점수
    judgment: Literal['positive', 'negative', 'neutral']
    reasoning: str                   # 판정 근거 설명
    key_outcomes: List[str]          # 핵심 결과 목록
    surprising_elements: List[str]   # 예상치 못한 요소
```

### 4.3 SQLite 테이블 구조

```sql
-- 세션
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at TIMESTAMP,
    topic TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    total_cost_usd REAL DEFAULT 0.0,
    config_json TEXT
);

-- 트리 노드
CREATE TABLE tree_nodes (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    parent_id TEXT REFERENCES tree_nodes(id),
    depth INTEGER NOT NULL,
    hypothesis_json TEXT,
    simulation_id TEXT,
    evaluation_json TEXT,
    status TEXT DEFAULT 'pending',
    sf_inspiration_used BOOLEAN DEFAULT 0,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 시뮬레이션
CREATE TABLE simulations (
    id TEXT PRIMARY KEY,
    node_id TEXT REFERENCES tree_nodes(id),
    scale TEXT NOT NULL,
    start_world_state_json TEXT,
    end_world_state_json TEXT,
    total_turns INTEGER,
    simulated_years INTEGER,
    api_cost_usd REAL
);

-- 턴
CREATE TABLE turns (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulations(id),
    turn_number INTEGER,
    simulated_year INTEGER,
    world_state_json TEXT,
    events_json TEXT,
    created_at TIMESTAMP
);

-- 에이전트
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    simulation_id TEXT REFERENCES simulations(id),
    name TEXT,
    persona_json TEXT,
    role TEXT
);

-- 대화 로그
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    turn_id TEXT REFERENCES turns(id),
    agent_id TEXT REFERENCES agents(id),
    target_agent_id TEXT,
    message TEXT,
    message_type TEXT,  -- dialogue/thought/decision/action
    timestamp TIMESTAMP
);

-- 에이전트 상태 히스토리
CREATE TABLE agent_states (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    turn_id TEXT REFERENCES turns(id),
    state_json TEXT,
    memory_json TEXT
);

-- API 비용 추적
CREATE TABLE api_calls (
    id TEXT PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id),
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL,
    purpose TEXT,  -- 어떤 작업에 사용됐는지
    created_at TIMESTAMP
);
```

---

## 5. 시뮬레이션 엔진 상세

### 5.1 스케일 적응 시뮬레이션

시뮬레이션 스케일은 가설의 성격에 따라 자동 결정되거나, 탐색 중 동적으로 전환된다.

```
스케일 결정 트리:
                    ┌─────────────────┐
                    │  가설 분석       │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    지배적 주체: 국가/문명            지배적 주체: 개인/집단
              │                             │
              ▼                             ▼
    ┌─────────────────┐         ┌──────────────────┐
    │  MACRO 모드      │         │  MICRO 모드       │
    │  단위: 수십 년   │         │  단위: 일/주/월    │
    │  주체: 국가, 세력 │         │  주체: 개인 에이전트│
    │  서술: LLM 내러티브│        │  서술: 에이전트 대화│
    └─────────────────┘         └──────────────────┘

    ADAPTIVE 모드: 거시→미시 줌인/아웃 가능
    예: 핵전쟁(매크로) → 생존자 캠프(마이크로)
```

#### 매크로 모드 (Macro Simulator)

**목적**: 국가, 문명, 거대 세력 단위의 역사를 빠르게 서술

**동작 방식**:
- LLM이 시대적 내러티브를 생성 (소설처럼)
- 각 "턴" = 5~20년
- 주요 사건(전쟁, 발명, 붕괴 등)을 중심으로 서술
- 세계 상태(World State) 자동 업데이트

**프롬프트 구조**:
```
현재 세계 상태:
- 연도: {year}
- 주요 세력: {factions}
- 기술 수준: {tech_level}
- 자원 현황: {resources}
- 직전 주요 사건: {last_events}

가설: {hypothesis}

다음 {timespan}년 동안 일어날 수 있는 주요 사건 3~5가지를 서술하고,
각 사건이 세계 상태에 미치는 영향을 수치로 표현하세요.
예상치 못한 반전 요소를 최소 1개 포함하세요.
```

#### 마이크로 모드 (Micro Simulator)

**목적**: 개인 에이전트들의 상호작용으로 역사를 하층부에서 구축

**동작 방식**:
- 5~20명의 다양한 페르소나 에이전트 생성
- 각 에이전트가 독립적 기억, 목표, 감정 보유
- 턴마다 에이전트들이 서로 대화/행동
- 에이전트 상호작용의 집합이 세계 이벤트를 만들어냄

**에이전트 수 결정**:
```python
def determine_agent_count(hypothesis: Hypothesis, budget: float) -> int:
    # 예산과 복잡도를 고려한 에이전트 수 결정
    base = 8
    complexity_bonus = len(hypothesis.key_assumptions) * 2
    budget_cap = int(budget / COST_PER_AGENT_PER_TURN)
    return min(base + complexity_bonus, budget_cap, 20)
```

### 5.2 에이전트 시스템

#### 페르소나 생성

에이전트 페르소나는 가설의 세계관에 맞게 자동 생성된다:

```
페르소나 생성 원칙:
1. 다양성: 성별, 나이, 문화권, 직업, 가치관 다양화
2. 갈등 씨앗: 서로 충돌할 수 있는 목표/가치관 부여
3. 역할 커버리지: 권력자, 혁신가, 저항세력, 일반인 모두 포함
4. 심리적 현실성: 두려움과 욕망이 명확한 입체적 캐릭터

예시 페르소나 (AGI 공존 가설):
- Elena Vasquez, 45세, AI 윤리학자, 인본주의자
  → "AI는 도구여야 한다" 신념, AGI에 공포와 매혹 동시 보유

- Kai Zhang, 28세, AI 개발자, 가속주의자
  → "AGI는 필연이며 좋은 것" 신념, 규제에 저항

- Maria Santos, 62세, 노동운동가
  → AI 실업에 분노, 구체제 수호 의지
```

#### 에이전트 메모리 시스템

```python
@dataclass
class MemoryEntry:
    turn: int
    year: int
    event: str                    # 무슨 일이 있었나
    emotional_impact: float       # -1.0 ~ 1.0 (트라우마 ~ 희열)
    relationship_changes: Dict    # 관계 변화
    decision_made: Optional[str]  # 내린 결정
    belief_update: Optional[str]  # 신념 변화

class AgentMemory:
    def __init__(self, capacity: int = 50):
        self.entries: List[MemoryEntry] = []
        self.capacity = capacity

    def add(self, entry: MemoryEntry):
        self.entries.append(entry)
        if len(self.entries) > self.capacity:
            # 오래된 기억 중 감정 강도 낮은 것 삭제 (망각)
            self._forget_weak_memories()

    def get_relevant(self, context: str) -> List[MemoryEntry]:
        # 현재 상황과 관련 있는 기억 필터링
        ...

    def summarize(self) -> str:
        # LLM으로 기억 요약 생성
        ...
```

#### 에이전트 상호작용 흐름

```
턴 N 시작
    │
    ▼
모든 에이전트에게 현재 상황 브리핑
    │
    ▼
각 에이전트: 내부 독백 생성 (생각/감정/의도)
    │         → "Elena는 Kai의 발표를 듣고 위협을 느낀다..."
    ▼
상호작용 매칭: 누가 누구와 대화/충돌/협력할지 결정
    │         → 관계 강도 + 목표 충돌 기반
    ▼
대화 시뮬레이션: 각 페어가 대화 교환
    │         → 각 발언이 API 호출
    ▼
행동 결정: 대화 결과로 에이전트가 행동 선택
    │         → 공개 연설, 정책 발의, 이주, 저항 등
    ▼
세계 상태 업데이트: 행동들의 집합 효과 계산
    │
    ▼
기억 업데이트: 각 에이전트 메모리에 이번 턴 기록
    │
    ▼
턴 N 종료, 로그 저장
```

### 5.3 턴 시스템

#### 턴 시간 단위 (스케일별)

| 스케일 | 1턴 = 실제 시간 | 노드 총 기간 | 턴 수 |
|--------|---------------|-------------|------|
| MACRO | 10년 | 100년 | 10턴 |
| MICRO | 1개월 | 1년 | 12턴 |
| ADAPTIVE | 가변 | 목표 기간까지 | 가변 |

#### 턴 종료 조건

```python
class TurnTerminator:
    def should_terminate(self, simulation: Simulation) -> Tuple[bool, str]:
        # 1. 목표 기간 달성
        if simulation.elapsed_years >= simulation.target_years:
            return True, "target_years_reached"

        # 2. 인류 멸종
        if simulation.world_state.population == 0:
            return True, "extinction"

        # 3. 안정 상태 수렴
        if self._is_stable(simulation):
            return True, "stable_state"

        # 4. 비용 한도 초과
        if simulation.api_cost > simulation.budget_limit:
            return True, "budget_exceeded"

        # 5. 최대 턴 수 초과 (안전장치)
        if simulation.turn_count > MAX_TURNS:
            return True, "max_turns_reached"

        return False, ""
```

---

## 6. DFS 시나리오 트리

### 6.1 트리 구조

```
루트 (토픽)
├── [가설 A: AGI 공존]          → 점수: 0.85 → 긍정 → 심화 탐색
│   ├── [A-1: 협력적 AGI]       → 점수: 0.92 → 긍정 → 심화
│   │   ├── [A-1-a: 유토피아]   → 점수: 0.95 → 긍정 → 최대 깊이
│   │   └── [A-1-b: 의존성 위기]→ 점수: 0.41 → 부정 → 가지치기 ✗
│   └── [A-2: 경쟁적 AGI]       → 점수: 0.60 → 중립 → 탐색 보류
│
├── [가설 B: 기후 붕괴]          → 점수: 0.35 → 부정 → 가지치기 ✗
│
└── [가설 C: 느린 적응]          → 점수: 0.71 → 긍정 → 심화 탐색
    ├── [C-1: 신재생 에너지 전환] → 점수: 0.88 → 긍정 → 심화
    └── [C-2: 인구 감소 적응]    → 점수: 0.65 → 중립 → 나중에
```

### 6.2 노드 상태 머신

```
         ┌──────────────────────────────────────────┐
         │                PENDING                   │
         │    (가설 생성됨, 아직 실행 안 됨)           │
         └──────────────────┬───────────────────────┘
                            │ DFS 선택
                            ▼
         ┌──────────────────────────────────────────┐
         │                RUNNING                   │
         │    (시뮬레이션 실행 중)                    │
         └──────────────────┬───────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
     ┌──────────┐   ┌──────────┐   ┌──────────────┐
     │ POSITIVE │   │ NEGATIVE │   │   NEUTRAL    │
     │ 심화 탐색  │   │ 가지치기  │   │ 보류/재검토   │
     └──────────┘   └────┬─────┘   └──────────────┘
                         │
                         ▼
                    ┌─────────┐
                    │ PRUNED  │
                    │(영구 제거)│
                    └─────────┘
```

### 6.3 평가 및 가지치기 로직

```python
class DFSController:
    def __init__(self, config: DFSConfig):
        self.positive_threshold = config.positive_threshold  # default: 0.6
        self.max_depth = config.max_depth  # default: 5
        self.max_breadth = config.max_breadth  # default: 3 (각 노드당 자식 수)

    def decide_next_action(self, node: TreeNode, result: EvaluationResult) -> DFSAction:
        # 판정 기반 액션 결정
        if result.judgment == 'negative':
            return DFSAction.PRUNE

        if node.depth >= self.max_depth:
            return DFSAction.MARK_COMPLETE  # 최대 깊이 도달

        if result.judgment == 'positive':
            # 현재 노드 심화 탐색 (자식 생성)
            return DFSAction.EXPLORE_DEEPER

        # neutral: 백트래킹 후 다른 경로 탐색
        return DFSAction.BACKTRACK

    def select_next_node(self, tree: ScenarioTree) -> Optional[TreeNode]:
        # 우선순위: 1) 가장 깊은 긍정 노드의 자식
        #           2) 미탐색 형제 노드
        #           3) 상위 레벨 미탐색 노드
        pending_nodes = tree.get_pending_nodes()
        if not pending_nodes:
            return None

        return max(pending_nodes, key=lambda n: (
            n.depth * 3 +                          # 깊이 우선
            n.parent_score * 2 +                   # 부모 점수 높은 것 우선
            (1 if n.sf_inspiration_pending else 0)  # SF 영감 대기 중인 것 우선
        ))
```

### 6.4 트리 탐색 전략

#### DFS vs BFS 선택 기준

Dormammu는 **DFS를 기본**으로 사용하되, 상황에 따라 전략을 조정한다:

| 상황 | 전략 | 이유 |
|------|------|------|
| 긍정 노드 발견 | DFS 심화 | 좋은 경로를 끝까지 탐색 |
| 연속 부정 (3회) | 레벨업 후 형제 탐색 | 막힌 경로에서 벗어나기 |
| 예산 50% 소진 | BFS 전환 (너비 탐색) | 다양한 경로 커버리지 확보 |
| 예산 80% 소진 | 상위 긍정 노드만 | 핵심 결과 보존 |

#### 트리 균형 알고리즘

```python
def rebalance_exploration(tree: ScenarioTree, budget_remaining: float) -> ExplorationStrategy:
    total_positive = len(tree.positive_nodes)
    total_unexplored = len(tree.pending_nodes)
    budget_ratio = budget_remaining / tree.initial_budget

    if budget_ratio > 0.5:
        return ExplorationStrategy.DEEP_FIRST      # 충분한 예산: 깊게
    elif budget_ratio > 0.2:
        return ExplorationStrategy.BALANCED        # 중간: 균형
    else:
        return ExplorationStrategy.HARVEST         # 부족: 최상위 긍정만 완결
```

---

## 7. 가설 생성 시스템

### 7.1 초기 가설 생성

사용자 토픽으로부터 최초 가설 집합을 생성하는 단계:

```python
class HypothesisGenerator:
    def generate_initial(self, topic_context: TopicContext, count: int = 5) -> List[Hypothesis]:
        """
        토픽 분석 결과로부터 다양한 첫 번째 가설 생성
        다양성 원칙: 낙관/비관/중립, 단기/장기, 기술/사회/자연 변수
        """
        prompt = HYPOTHESIS_GEN_PROMPT.format(
            topic=topic_context.topic,
            background=topic_context.background_analysis,
            existing_hypotheses=[],  # 초기에는 없음
            diversity_requirements=DIVERSITY_MATRIX,
            count=count
        )
        return self._parse_hypotheses(llm.complete(prompt))

    def generate_child(self, parent: TreeNode, branch_direction: str) -> List[Hypothesis]:
        """
        부모 노드 결과를 기반으로 자식 가설 생성
        branch_direction: 'continuation' | 'contrast' | 'zoom_in'
        """
        ...
```

#### 가설 다양성 매트릭스

초기 가설 생성 시 다음 축들을 커버하도록 강제:

```
              낙관적 ◄────────────────► 비관적
                │                        │
기술 주도 ───────┼────────────────────────┼──── 사회 주도
                │                        │
         단기(~10년)              장기(100년~)

목표: 각 사분면에 최소 1개 가설 배치
```

### 7.2 SF 영감 시스템

#### 아이디어 고갈 감지

```python
class ExhaustionDetector:
    def is_exhausted(self, tree: ScenarioTree, recent_hypotheses: List[Hypothesis]) -> bool:
        # 신호 1: 최근 N개 가설이 기존 것과 너무 유사
        similarity_score = self._calc_semantic_similarity(
            recent_hypotheses,
            tree.all_past_hypotheses
        )
        if similarity_score > 0.85:
            return True

        # 신호 2: LLM이 "새 가설 없음"을 반환하는 패턴 반복
        if self.consecutive_empty_responses >= 3:
            return True

        # 신호 3: 탐색 깊이 대비 가설 다양성 저하
        diversity_ratio = len(set(tree.hypothesis_themes)) / tree.total_nodes
        if diversity_ratio < 0.3:
            return True

        return False
```

#### SF 영감 주입 파이프라인

```
고갈 감지
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  레벨 1: LLM SF 지식 베이스 (비용 낮음)               │
│  프롬프트: "이 토픽과 관련된 SF 작품의 시나리오를      │
│           현실 가능성 높은 순으로 5개 제안해주세요"    │
│                                                     │
│  커버리지: 아이작 아시모프, 필립 K. 딕, 류츠신,        │
│           킴 스탠리 로빈슨, 어슐러 K. 르 귄 등        │
└────────────────────┬────────────────────────────────┘
                     │ 여전히 고갈
                     ▼
┌─────────────────────────────────────────────────────┐
│  레벨 2: 웹 검색 (비용 높음, 최후 수단)                │
│  검색어: "{토픽} 시나리오 예측 SF 소설"                │
│  검색어: "{토픽} futurism scenario"                  │
│  결과를 LLM으로 요약 및 가설화                        │
└─────────────────────────────────────────────────────┘
                     │
                     ▼
        SF 영감 → 새 가설로 변환 (현실화)
```

#### SF 지식 베이스 프롬프트 예시

```
당신은 SF 문학과 미래학의 전문가입니다.
주제: "{topic}"
현재까지 탐색된 가설들: {explored_hypotheses}

다음 SF 작품들의 핵심 시나리오를 참고하여, 아직 탐색되지 않은
새로운 가설을 3개 제안해주세요. 각 가설은 현실에서 실제로 일어날 수 있는
구체적인 메커니즘을 포함해야 합니다.

참고 SF 분야:
- 하드 SF (실현 가능한 기술 기반): 킴 스탠리 로빈슨, 그레그 베어
- 사회 SF (사회 변화 초점): 어슐러 K. 르 귄, 옥타비아 버틀러
- 디스토피아 SF: 조지 오웰, 올더스 헉슬리, 마거릿 애트우드
- 중국 SF: 류츠신 (삼체, 어두운 숲)
- 트랜스휴머니즘 SF: 피터 와츠, 찰스 스트로스

각 가설에 대해 영감을 받은 SF 작품명을 명시하세요.
```

### 7.3 가설 변환 (SF → 현실 가설)

SF 영감을 구체적 시뮬레이션 가설로 변환하는 과정:

```python
def convert_sf_to_hypothesis(sf_concept: SFConcept, topic_context: TopicContext) -> Hypothesis:
    """
    SF 개념을 현실 시뮬레이션 가설로 변환

    예: 류츠신의 '어두운 숲' →
        가설: "우주적 위협의 발견이 인류를 통일시키다"
        초기 조건: 2040년, 외계 신호 수신, 글로벌 패닉
        핵심 가정: 위협의 현실성 70%, 각국 협력 가능성 40%
    """
    ...
```

---

## 8. 로깅 & 리플레이 시스템

### 8.1 로깅 원칙

**"모든 것을 기록한다"**: 시뮬레이션의 모든 이벤트, 모든 에이전트의 모든 발언과 생각, 모든 세계 상태 변화를 영구 저장한다.

```
로그 레벨:
├── WORLD: 세계 상태 변화 (턴마다)
├── EVENT: 주요 사건 발생
├── AGENT_ACTION: 에이전트 행동
├── AGENT_DIALOGUE: 에이전트 대화
├── AGENT_THOUGHT: 에이전트 내부 독백
├── AGENT_STATE: 에이전트 상태 변화
├── EVALUATION: 평가 결과
├── DFS: DFS 결정 (심화/가지치기)
├── HYPOTHESIS: 가설 생성
├── SF_INSPIRATION: SF 영감 주입
└── API: API 호출 (토큰, 비용)
```

### 8.2 스냅샷 시스템

매 턴마다 전체 시뮬레이션 상태를 JSON으로 스냅샷 저장:

```python
@dataclass
class SimulationSnapshot:
    turn: int
    year: int
    timestamp: datetime
    world_state: WorldState
    all_agent_states: Dict[str, AgentState]  # agent_id -> state
    all_agent_memories: Dict[str, List[MemoryEntry]]
    recent_events: List[str]

class SnapshotManager:
    def save(self, snapshot: SimulationSnapshot, simulation_id: str):
        # SQLite에 메타데이터 저장
        # JSON 파일로 전체 상태 저장
        path = f"data/snapshots/{simulation_id}/turn_{snapshot.turn:04d}.json"
        ...

    def load(self, simulation_id: str, turn: int) -> SimulationSnapshot:
        ...
```

### 8.3 리플레이 시스템

#### 기본 리플레이

```bash
# 시뮬레이션 목록 확인
ese replay list

# 특정 시뮬레이션 재생 (처음부터)
ese replay show --simulation-id {sim_id}

# 특정 턴부터 재생
ese replay show --simulation-id {sim_id} --from-turn 5

# 특정 에이전트 관점으로 재생
ese replay show --simulation-id {sim_id} --agent "Elena Vasquez"
```

#### 리플레이 진입 (대화 인터랙션)

사용자가 저장된 시뮬레이션의 임의 시점에 진입해 AI NPC와 대화할 수 있다:

```bash
# 리플레이 진입: 특정 시뮬레이션, 특정 턴, 특정 에이전트와 대화
ese replay enter --simulation-id {sim_id} --turn 7 --agent "Elena Vasquez"

# 진입 후:
> 당신(사용자): "Elena, 당신은 AGI에 대해 어떻게 생각하시나요?"
> Elena Vasquez (AI NPC): "솔직히 말씀드리면, 두렵습니다. 하지만 동시에..."
  [Elena의 현재 상태, 기억, 관계를 컨텍스트로 활용]
```

#### NPC 대화 컨텍스트

리플레이 진입 시 NPC에게 제공되는 컨텍스트:

```python
def build_npc_context(agent: Agent, snapshot: SimulationSnapshot) -> str:
    return f"""
    당신은 {agent.name}입니다. 현재 {snapshot.year}년입니다.

    당신의 성격: {agent.persona.personality_traits}
    당신의 가치관: {agent.persona.values}
    당신의 목표: {agent.persona.goals}

    최근 기억 (중요도 높은 순):
    {agent.memory.get_top_memories(10)}

    현재 세계 상황:
    {snapshot.world_state.summary()}

    당신이 아는 사람들:
    {agent.relationships.summary()}

    지금 이 순간, 당신의 감정과 생각을 솔직하게 반영하여 대화하세요.
    당신은 자신이 시뮬레이션 캐릭터임을 모릅니다.
    """
```

### 8.4 데이터 내보내기

```bash
# 전체 트리를 Markdown 리포트로 내보내기
ese export report --session-id {session_id} --format markdown

# 시나리오 트리를 JSON으로 내보내기
ese export tree --session-id {session_id}

# 특정 에이전트의 전체 일지 내보내기
ese export agent-diary --simulation-id {sim_id} --agent "Elena Vasquez"
```

---

## 9. 자율 실행 루프

### 9.1 루프 아키텍처

Dormammu의 자율 실행 루프는 Claude Code 오케스트레이터와 시뮬레이션 엔진이 교대로 실행되는 구조다:

```
┌─────────────────────────────────────────────────────────────────┐
│                      자율 실행 루프 (24시간)                      │
│                                                                 │
│  ┌─────────────────┐                   ┌────────────────────┐   │
│  │ Claude Code     │                   │  Simulation Engine │   │
│  │ 오케스트레이터    │                   │  (Python 독립 실행) │   │
│  │                 │ ① 환경 설정 전달   │                    │   │
│  │  - 가설 생성    │──────────────────►│  - 에이전트 생성   │   │
│  │  - 환경 구성    │                   │  - 자율 상호작용   │   │
│  │  - DFS 결정    │◄──────────────────│  - 턴 처리         │   │
│  │  - SF 주입      │ ② 결과 + 로그 반환│  - 상태 저장       │   │
│  │  - 비용 관리    │                   │                    │   │
│  └────────┬────────┘                   └────────────────────┘   │
│           │                                                     │
│           │ ③ 평가 & DFS 결정                                    │
│           │                                                     │
│           └──────────────────────────────────────────────────►  │
│                        (다음 가설 생성 → 반복)                    │
└─────────────────────────────────────────────────────────────────┘
```

### 9.2 Claude Code 오케스트레이터 상세

Claude Code는 시뮬레이션 루프의 "두뇌" 역할을 한다:

```python
class Orchestrator:
    def run_autonomous(self, session: Session, max_hours: float = 24.0):
        start_time = time.time()

        while not self._should_stop(session, start_time, max_hours):
            # 1. 다음 실행할 노드 선택
            next_node = self.dfs_controller.select_next_node(session.tree)

            if next_node is None:
                # 탐색 완료 또는 가설 고갈
                if self.exhaustion_detector.is_exhausted(session.tree):
                    hints = self.sf_inspiration.get_hints(session.topic_context)
                    new_hypotheses = self.hypothesis_generator.generate_with_sf(hints)
                    self._add_to_tree(new_hypotheses, session.tree)
                    continue
                else:
                    break  # 진짜 완료

            # 2. 시뮬레이션 환경 설정
            env_config = self.env_builder.build(next_node.hypothesis)

            # 3. 시뮬레이션 실행 (별도 프로세스)
            sim_result = self.run_simulation(env_config)

            # 4. 결과 분석
            evaluation = self.result_analyzer.analyze(sim_result, session.criteria)

            # 5. DFS 결정
            action = self.dfs_controller.decide(next_node, evaluation)
            self._apply_action(action, next_node, session.tree)

            # 6. 자식 가설 생성 (긍정인 경우)
            if action == DFSAction.EXPLORE_DEEPER:
                child_hypotheses = self.hypothesis_generator.generate_child(next_node)
                self._add_children(child_hypotheses, next_node)

            # 7. 상태 저장 및 로그
            self.storage.save_session_state(session)
            self.logger.log_orchestrator_step(session, next_node, evaluation, action)
```

### 9.3 시뮬레이션 엔진 핸드오프

오케스트레이터와 시뮬레이션 엔진 간의 인터페이스:

```python
@dataclass
class SimulationConfig:
    """오케스트레이터 → 엔진으로 전달되는 설정"""
    hypothesis: Hypothesis
    initial_world_state: WorldState
    agent_personas: List[Persona]
    scale: SimulationScale
    target_years: int
    budget_limit_usd: float
    evaluation_criteria: List[EvaluationCriteria]

@dataclass
class SimulationResult:
    """엔진 → 오케스트레이터로 반환되는 결과"""
    simulation_id: str
    final_world_state: WorldState
    all_turns: List[Turn]  # 전체 턴 데이터
    all_agents: List[Agent]  # 최종 에이전트 상태
    key_events: List[str]  # 주요 사건 요약
    termination_reason: str
    api_cost_usd: float
    snapshot_paths: List[str]  # 저장된 스냅샷 경로
```

### 9.4 일시정지 & 재개

자율 루프는 언제든지 일시정지하고 재개할 수 있다:

```bash
# 현재 세션 상태 확인
ese status --session-id {session_id}

# 일시정지 (현재 시뮬레이션 완료 후)
ese pause --session-id {session_id}

# 재개
ese resume --session-id {session_id}

# 즉시 중단 (진행 중 시뮬레이션 종료)
ese stop --session-id {session_id} --force
```

### 9.5 24시간 운영 모니터링

```python
class SessionMonitor:
    def generate_progress_report(self, session: Session) -> str:
        tree = session.scenario_tree
        return f"""
        === Dormammu 진행 상황 보고서 ===
        시작 시간: {session.created_at}
        경과 시간: {session.elapsed_hours:.1f}시간

        [트리 현황]
        총 노드: {tree.total_nodes}
        긍정 노드: {len(tree.positive_nodes)} ({tree.positive_ratio:.1%})
        부정/가지치기: {len(tree.pruned_nodes)}
        대기 중: {len(tree.pending_nodes)}
        최대 깊이 도달: {tree.max_reached_depth}

        [SF 영감]
        SF 주입 횟수: {session.sf_injection_count}
        활용된 SF 작품: {session.sf_sources_used}

        [비용]
        소비: ${session.total_api_cost_usd:.2f}
        예산: ${session.budget_usd:.2f}
        잔여: ${session.budget_remaining:.2f} ({session.budget_ratio:.1%})

        [최상위 긍정 시나리오]
        {self._format_top_scenarios(tree)}
        """
```

---

## 10. 평가 시스템

### 10.1 평가 기준 자동 생성

토픽 입력 시 LLM이 평가 기준 후보를 자동 생성하고, 사용자가 선택한다:

```python
def generate_evaluation_criteria(topic: str, background: str) -> List[EvaluationCriteria]:
    prompt = f"""
    주제: "{topic}"
    배경 분석: {background}

    이 시뮬레이션을 평가할 수 있는 다양한 기준을 10개 제안해주세요.

    기준 유형을 다양하게 포함하세요:
    - 정량적 기준: 인구, GDP, 기술 지수 등
    - 정성적 기준: 자유도, 행복지수, 문화 다양성 등
    - 도덕적 기준: 인권 보장, 공정성 등
    - 목적론적 기준: 인류의 장기 생존 가능성 등

    각 기준에 대해:
    - 이름 (한 단어 ~ 5단어)
    - 측정 방법 (시뮬레이션 내 어떻게 측정하는지)
    - 기본 가중치 (0.0 ~ 1.0)
    - 긍정 임계값 (이 점수 이상이면 긍정)
    """
    return parse_criteria(llm.complete(prompt))
```

**예시 (토픽: "인류의 다음 100년"):**

| # | 기준 | 측정 방법 | 가중치 |
|---|------|----------|-------|
| 1 | 인류 생존률 | 최종 인구 / 초기 인구 | 0.30 |
| 2 | 기술 발전 지수 | 기술 수준 변화율 | 0.15 |
| 3 | 자유 지수 | 에이전트 자율 행동 비율 | 0.10 |
| 4 | 갈등 강도 | 전쟁/분쟁 이벤트 빈도 | 0.20 |
| 5 | 지속 가능성 | 자원 고갈 여부 | 0.15 |
| 6 | 문화 다양성 | 독립 문화권 수 | 0.10 |

### 10.2 점수 계산 메커니즘

```python
class Scorer:
    def score_simulation(
        self,
        result: SimulationResult,
        criteria: List[EvaluationCriteria]
    ) -> Dict[str, float]:
        scores = {}

        for criterion in criteria:
            if not criterion.is_selected:
                continue

            raw_score = self._measure(result, criterion)
            normalized = self._normalize(raw_score, criterion)
            scores[criterion.id] = normalized

        return scores

    def _measure(self, result: SimulationResult, criterion: EvaluationCriteria) -> float:
        match criterion.name:
            case "인류 생존률":
                return result.final_world_state.population / result.initial_population

            case "기술 발전 지수":
                return (result.final_world_state.technology_level -
                        result.initial_tech_level) / 100

            case "갈등 강도":
                conflict_events = [e for e in result.all_events if "전쟁" in e or "분쟁" in e]
                return 1.0 - (len(conflict_events) / result.total_events)

            case _:
                # 커스텀 기준: LLM으로 평가
                return self._llm_evaluate(result, criterion)
```

### 10.3 긍정/부정 판정

```python
class Judge:
    def judge(
        self,
        scores: Dict[str, float],
        criteria: List[EvaluationCriteria]
    ) -> EvaluationResult:
        # 가중 합산 점수 계산
        weighted_total = sum(
            scores[c.id] * c.weight
            for c in criteria if c.is_selected and c.id in scores
        )

        # 판정
        if weighted_total >= 0.6:
            judgment = 'positive'
        elif weighted_total <= 0.3:
            judgment = 'negative'
        else:
            judgment = 'neutral'

        # 판정 근거 생성 (LLM)
        reasoning = self._generate_reasoning(scores, criteria, weighted_total)

        return EvaluationResult(
            scores=scores,
            weighted_total=weighted_total,
            judgment=judgment,
            reasoning=reasoning,
            key_outcomes=self._extract_key_outcomes(scores),
            surprising_elements=self._identify_surprises(scores)
        )
```

### 10.4 평가 결과 해석

```
평가 점수 구간:

0.0 ──────── 0.3 ──────── 0.6 ──────────── 1.0
 │            │            │                │
부정적 결과   중립/혼합    긍정적 결과      이상적 결과
 → 가지치기   → 보류       → 심화 탐색      → 최우선 탐색

가지치기 조건:
  - 점수 0.3 미만 → 즉시 가지치기
  - 특정 기준 (인류 생존률) 0.1 미만 → 즉시 가지치기 (단일 거부권)
  - 부모 노드 점수보다 0.3 이상 하락 → 가지치기 (하향 추세)
```

---

## 11. Phase B 시각화 로드맵

### 11.1 개요

Phase A(텍스트 엔진) 완성 후 Phase B에서 2D 픽셀 시각화를 추가한다.

### 11.2 줌 레벨 아키텍처

```
줌 레벨 1: 세계 지도 (World View)
┌──────────────────────────────────────────┐
│  🌍 세계 지도                              │
│  • 국가/세력별 색상 구분                   │
│  • 인구 밀도 히트맵                        │
│  • 자원/기술 수준 오버레이                  │
│  • 전쟁/무역 루트 표시                     │
│  클릭 → 줌 레벨 2 (도시)                  │
└──────────────────────────────────────────┘
        ↕ 줌
줌 레벨 2: 도시 뷰 (City View)
┌──────────────────────────────────────────┐
│  🏙️ 도시 픽셀 맵                           │
│  • 건물, 광장, 공장, 주거지                │
│  • 에이전트들이 도시를 돌아다님             │
│  • 상호작용 시 말풍선 표시                 │
│  클릭 → 줌 레벨 3 (개인)                  │
└──────────────────────────────────────────┘
        ↕ 줌
줌 레벨 3: 개인 뷰 (Individual View)
┌──────────────────────────────────────────┐
│  👤 에이전트 상세                          │
│  • 현재 상태 (감정, 건강, 자원)            │
│  • 현재 하는 행동                         │
│  • 현재 대화 (실시간)                     │
│  • 기억 타임라인                          │
└──────────────────────────────────────────┘
```

### 11.3 기술 스택 (Phase B)

| 레이어 | 기술 | 이유 |
|--------|------|------|
| 렌더링 | Pygame / Arcade | Python 생태계 일관성 |
| 맵 에디터 | Tiled Map Editor | 픽셀 맵 제작 도구 |
| 에셋 | 픽셀 아트 (직접 제작) | 라이선스 자유도 |
| UI | Dear PyGui | Python 네이티브 GUI |
| 애니메이션 | 스프라이트 시트 | 에이전트 이동/동작 |

### 11.4 Phase B 구현 마일스톤

```
M1: 세계 지도 정적 렌더링 (2주)
  - 세계 상태 데이터 → 픽셀 지도 변환
  - 색상 오버레이 시스템

M2: 도시 뷰 (3주)
  - 픽셀 아트 도시 맵
  - 에이전트 스프라이트 이동

M3: 에이전트 실시간 렌더링 (2주)
  - 에이전트 행동 → 애니메이션 매핑
  - 대화 말풍선

M4: 줌 전환 (1주)
  - 부드러운 레벨 전환
  - 데이터 LOD(Level of Detail)

M5: 리플레이 모드 연동 (1주)
  - 저장된 데이터로 과거 재생
  - 재생 속도 조절
```

---

## 12. API 비용 최적화 전략

### 12.1 비용 구조 분석

초기 예산: **$1,000 (OpenAI API 크레딧)**

| 작업 | 모델 추천 | 평균 비용/호출 | 빈도 |
|------|----------|--------------|------|
| 가설 생성 | GPT-4o | $0.05 | 노드당 1회 |
| 환경 설정 | GPT-4o-mini | $0.005 | 노드당 1회 |
| 에이전트 대화 | GPT-4o-mini | $0.002 | 턴당 N×M회 |
| 매크로 내러티브 | GPT-4o | $0.03 | 턴당 1회 |
| 결과 분석 | GPT-4o | $0.04 | 노드당 1회 |
| SF 영감 | GPT-4o | $0.03 | 고갈 시 |

**예상 노드당 총 비용: ~$0.5 ~ $2.0**
**$1,000 예산으로 탐색 가능한 노드: 500 ~ 2,000개**

### 12.2 최적화 전략

#### 전략 1: 모델 티어링

```python
MODEL_ROUTING = {
    # 고품질 필요 작업
    'hypothesis_generation': 'gpt-4o',
    'result_analysis': 'gpt-4o',
    'sf_inspiration': 'gpt-4o',

    # 비용 민감 작업 (많이 발생)
    'agent_dialogue': 'gpt-4o-mini',
    'agent_thought': 'gpt-4o-mini',
    'world_state_update': 'gpt-4o-mini',
    'environment_setup': 'gpt-4o-mini',

    # 캐싱 우선
    'criteria_generation': 'gpt-4o',  # 세션당 1회
    'topic_analysis': 'gpt-4o',        # 세션당 1회
}
```

#### 전략 2: 응답 캐싱

```python
class CachedLLMClient:
    def __init__(self):
        self.cache = {}  # prompt_hash -> response

    def complete(self, prompt: str, model: str, cache_ttl: int = 3600) -> str:
        cache_key = hashlib.md5(f"{model}:{prompt}".encode()).hexdigest()

        if cache_key in self.cache:
            self.cache_hits += 1
            return self.cache[cache_key]

        response = openai.chat.complete(prompt, model=model)
        self.cache[cache_key] = response
        return response
```

#### 전략 3: 에이전트 수 동적 조정

```python
def calc_agents_for_budget(remaining_budget: float, remaining_turns: int) -> int:
    budget_per_turn = remaining_budget / remaining_turns
    # 턴당 예산 기반 에이전트 수 결정
    if budget_per_turn > 0.5:
        return 15  # 풍부: 많은 에이전트
    elif budget_per_turn > 0.2:
        return 8   # 중간
    else:
        return 4   # 절약 모드
```

#### 전략 4: 매크로 우선, 마이크로는 선택적

```
비용 절약 원칙:
1. 기본값: MACRO 모드 (빠르고 저렴)
2. MICRO는 특별한 경우에만:
   - 사용자가 명시적 요청
   - 매크로로 충분히 탐색한 경로의 마지막 단계
   - 예산이 충분할 때 (50% 이상 잔여)
```

#### 전략 5: 비용 알림 & 자동 throttle

```python
class BudgetManager:
    ALERT_THRESHOLDS = [0.5, 0.75, 0.9]  # 50%, 75%, 90% 소진 시 알림

    def check_and_throttle(self, session: Session):
        ratio = session.total_cost / session.budget

        if ratio >= 0.9:
            # 90%: 핵심 노드만 완결 모드
            session.config.max_agents = 4
            session.config.max_depth = session.current_max_depth  # 더 이상 깊어지지 않음

        elif ratio >= 0.75:
            # 75%: 검소 모드
            session.config.max_agents = 6
            session.config.prefer_macro = True

        elif ratio >= 0.5:
            # 50%: 일반 알림
            logger.warning(f"예산 50% 소진: ${session.total_cost:.2f} / ${session.budget:.2f}")
```

### 12.3 비용 추적 대시보드

```bash
# 실시간 비용 확인
ese cost --session-id {session_id}

출력:
=== 비용 현황 ===
총 소비: $234.50 / $1,000.00 (23.5%)
노드당 평균: $1.23
탐색 노드: 191개

모델별 분류:
  GPT-4o:       $189.20 (80.7%)
  GPT-4o-mini:   $45.30 (19.3%)

작업별 분류:
  가설 생성:    $38.10
  에이전트 대화: $102.30
  결과 분석:    $67.80
  기타:         $26.30

예상 잔여 용량:
  현재 속도 기준: 619개 추가 노드 탐색 가능
  예상 완료 시간: 약 32시간 후
```

---

## 13. 기술 스택 & 의존성

### 13.1 핵심 기술 스택

| 레이어 | 기술 | 버전 | 용도 |
|--------|------|------|------|
| **언어** | Python | 3.11+ | 전체 백엔드 |
| **LLM API** | OpenAI Python SDK | latest | GPT-4o, GPT-4o-mini |
| **데이터베이스** | SQLite | 3.x | 영구 저장소 |
| **ORM** | SQLAlchemy | 2.x | DB 추상화 |
| **직렬화** | Pydantic | 2.x | 데이터 모델 검증 |
| **CLI** | Click | 8.x | 커맨드라인 인터페이스 |
| **비동기** | asyncio | 내장 | 병렬 에이전트 실행 |
| **로깅** | Loguru | latest | 구조화 로깅 |
| **설정** | python-dotenv | latest | 환경 변수 관리 |
| **테스트** | pytest | latest | 단위/통합 테스트 |

### 13.2 선택적 의존성

| 패키지 | 용도 | 필수 여부 |
|--------|------|---------|
| `tenacity` | API 재시도 로직 | 권장 |
| `rich` | 터미널 렌더링 | 권장 |
| `tiktoken` | 토큰 수 예측 | 권장 |
| `httpx` | HTTP 클라이언트 (웹 검색) | SF 레벨 2만 |
| `pygame` | Phase B 시각화 | Phase B |

### 13.3 프로젝트 설정

```toml
# pyproject.toml
[tool.poetry]
name = "emergent-simulation-engine"
version = "0.1.0"
description = "Multi-scenario AI simulation engine with DFS tree exploration"
python = "^3.11"

[tool.poetry.dependencies]
openai = "^1.0"
sqlalchemy = "^2.0"
pydantic = "^2.0"
click = "^8.0"
loguru = "^0.7"
python-dotenv = "^1.0"
tenacity = "^8.0"
rich = "^13.0"
tiktoken = "^0.5"

[tool.poetry.scripts]
ese = "ese.cli.main:cli"
```

### 13.4 환경 변수

```bash
# .env
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...

# 예산 한도
ESE_BUDGET_USD=1000.0
ESE_ALERT_AT_PERCENT=75

# 기본 모델
ESE_DEFAULT_MODEL=gpt-4o
ESE_CHEAP_MODEL=gpt-4o-mini

# 저장 경로
ESE_DATA_DIR=./data
ESE_SNAPSHOTS_DIR=./data/snapshots
ESE_DB_PATH=./data/ese.db

# 시뮬레이션 기본값
ESE_DEFAULT_SCALE=macro
ESE_MAX_AGENTS=15
ESE_DEFAULT_TARGET_YEARS=100
ESE_MAX_TREE_DEPTH=5
ESE_MAX_CHILDREN_PER_NODE=3
```

---

## 14. 구현 우선순위

### 14.1 Phase A 로드맵

```
Week 1-2: 기반 인프라
├── [ ] 프로젝트 구조 설정 (pyproject.toml, 디렉토리)
├── [ ] SQLite 스키마 + SQLAlchemy 모델
├── [ ] OpenAI API 클라이언트 + 비용 추적
├── [ ] 기본 로깅 시스템 (Loguru)
└── [ ] 환경 설정 (.env, config)

Week 3-4: 오케스트레이터 핵심
├── [ ] TopicAnalyzer (토픽 → 컨텍스트 + 평가 기준)
├── [ ] HypothesisGenerator (초기 가설 생성)
├── [ ] EnvironmentBuilder (가설 → 세계 초기 상태)
├── [ ] EvaluationCriteria 선택 UI (CLI)
└── [ ] 단일 가설 end-to-end 테스트

Week 5-6: 시뮬레이션 엔진 (매크로)
├── [ ] MacroSimulator (LLM 내러티브 기반)
├── [ ] WorldState 관리 + 업데이트
├── [ ] TurnManager + 종료 조건
├── [ ] 결과 저장 + 스냅샷
└── [ ] 매크로 시뮬레이션 단독 실행 테스트

Week 7-8: DFS 트리 + 평가
├── [ ] ScenarioTree 자료구조
├── [ ] DFSController (노드 선택, 판정, 가지치기)
├── [ ] ResultAnalyzer + Scorer + Judge
├── [ ] 자식 가설 생성 (부모 결과 기반)
└── [ ] DFS 루프 단독 테스트

Week 9-10: 마이크로 시뮬레이터
├── [ ] AgentFactory + Persona 생성
├── [ ] AgentMemory 시스템
├── [ ] InteractionManager (에이전트 간 대화)
├── [ ] MicroSimulator 완성
└── [ ] 마이크로 시뮬레이션 단독 테스트

Week 11-12: 자율 루프 + SF 영감
├── [ ] Orchestrator 자율 루프
├── [ ] ExhaustionDetector
├── [ ] SFInspiration 시스템 (레벨 1, 2)
├── [ ] BudgetManager + throttle
└── [ ] 24시간 자율 실행 테스트

Week 13-14: 리플레이 + CLI 완성
├── [ ] SnapshotManager 완성
├── [ ] ReplaySystem (재생 + NPC 대화)
├── [ ] CLI 전체 명령어
├── [ ] 리포트 내보내기
└── [ ] 통합 테스트 + 버그 수정
```

### 14.2 MVP 정의

**MVP (4주 내)**: 단일 가설 → 매크로 시뮬레이션 → 평가 → 결과 저장

```bash
# MVP 실행 예시
ese run --topic "AGI가 등장하면 인류는 어떻게 될까?" --mode single

# 출력:
평가 기준을 선택하세요:
  [1] 인류 생존률 (가중치: 0.30)
  [2] 기술 발전 지수 (가중치: 0.15)
  [3] 자유 지수 (가중치: 0.10)
  ... (기준 선택 후)

가설 생성 중...
  가설: "AGI와 인류의 협력적 공존 — 2035년 AGI 등장, 인류와 공생"

시뮬레이션 실행 중... (매크로, 100년)
  [2035] AGI 첫 등장, 글로벌 패닉 시작...
  [2040] UN AGI 협약 체결...
  [2060] AGI 지원 하에 기후위기 해결...
  [2100] 인류-AGI 공생 문명 완성

평가 결과:
  인류 생존률: 0.95
  기술 발전: 0.90
  자유 지수: 0.75
  최종 점수: 0.88 → 긍정

결과 저장: data/simulations/sim_20260318_001/
```

### 14.3 구현 위험 요소 및 대응

| 위험 | 가능성 | 대응 |
|------|--------|------|
| API 비용 폭발 | 높음 | BudgetManager 먼저 구현, 모든 호출에 비용 추적 |
| 에이전트 대화 루프 | 중간 | 최대 발언 수 하드 제한, 타임아웃 |
| 가설 중복 수렴 | 중간 | 유사도 필터 + SF 영감 조기 발동 |
| LLM 응답 파싱 실패 | 높음 | Pydantic 검증 + fallback 파서 |
| SQLite 병목 | 낮음 | WAL 모드, 비동기 커밋 |
| 24시간 루프 크래시 | 중간 | 체크포인트 저장, 자동 재개 로직 |

---

## 부록

### A. 용어 사전

| 용어 | 정의 |
|------|------|
| **노드** | DFS 트리의 단위. 하나의 가설 + 시뮬레이션 + 평가 결과 |
| **가설** | 시뮬레이션의 전제 조건과 초기 상태를 정의한 명제 |
| **가지치기** | 부정적 평가를 받은 노드와 그 하위 트리를 탐색 대상에서 제외 |
| **매크로 모드** | 국가/문명 단위, 수십 년 단위 서술형 시뮬레이션 |
| **마이크로 모드** | 개인 에이전트 단위, 일/주 단위 상호작용 시뮬레이션 |
| **SF 영감** | 가설 아이디어 고갈 시 SF 문학/영화 지식에서 새 가설을 도출하는 시스템 |
| **리플레이 진입** | 저장된 시뮬레이션의 임의 시점에 진입해 AI NPC와 대화하는 기능 |
| **오케스트레이터** | Claude Code 기반의 시뮬레이션 루프 제어 시스템 |

### B. 참고 자료

- OpenAI API Reference: https://platform.openai.com/docs
- SQLAlchemy 2.0 Docs: https://docs.sqlalchemy.org/en/20/
- Pydantic v2 Docs: https://docs.pydantic.dev/latest/
- 웨스트월드 레퍼런스: `docs/westworld-reference.md`
- inZOI 레퍼런스: `docs/inzoi-reference.md`
- 플레이어 동기 리서치: `docs/player-motivation-research.md`

---

*이 문서는 Dormammu 시스템 구축을 위한 단일 레퍼런스입니다. 구현 과정에서 발생하는 변경사항은 이 문서에 반영되어야 합니다.*
