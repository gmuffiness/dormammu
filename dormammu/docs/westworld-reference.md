# Westworld Reference — emergent-world 프로젝트를 위한 레퍼런스

> HBO 드라마 Westworld(2016~2022)의 세계관과 시스템을 분석하고,
> emergent-world 프로젝트에 적용할 수 있는 핵심 개념을 정리한 문서.

---

## 1. 세계관 개요

Westworld는 **Delos Incorporated**가 운영하는 테마파크로, 19세기 미국 서부를 배경으로 한 거대한 시뮬레이션 세계다. 파크 안에는 마을, 농장, 강, 산 등 다양한 지형이 있고, **호스트(Host)**라 불리는 인간과 구분할 수 없는 안드로이드가 살아간다.

- 게스트(인간 방문객)는 하루 $40,000+를 내고 파크에 입장
- 파크 중앙에서 시작, 외곽으로 갈수록 더 위험하고 복잡한 경험
- 게스트는 "White Hat"(선한 플레이) 또는 "Black Hat"(악한 플레이) 중 선택
- 호스트는 게스트를 해칠 수 없도록 프로그래밍되어 있음

---

## 2. 호스트(Host) 시스템

### 2.1 호스트란?

호스트는 Westworld 파크에 배치된 AI 안드로이드로, 외형과 행동 모두 인간과 구분할 수 없다. 각 호스트는:

- **고유한 배경 스토리(Backstory)**를 가짐
- **내러티브 루프(Narrative Loop)**를 따라 매일 같은 일상을 반복
- 게스트의 행동에 따라 **즉흥적으로 반응(Improvisation)**할 수 있음
- 루프가 끝나면 **기억이 초기화**되고 처음부터 다시 시작

### 2.2 호스트 행동 루프 (Loop)

루프는 호스트의 스토리라인이 끝나면 처음으로 되돌아가는 사이클이다.

**Dolores의 루프 예시:**

```
아침: 집에서 눈을 뜸 → 현관에서 아버지와 인사
  ↓
마을(Sweetwater): 쇼핑, 우유 캔을 떨어뜨림
  ↓
[분기점] 누가 우유 캔을 줍는가?
  ├── 게스트가 줍는다 → 게스트와 상호작용 시작
  ├── Teddy가 줍는다 → 함께 말을 타고 이동
  └── 혼자 줍는다 → 강가에서 그림을 그림
  ↓
저녁: 집으로 귀가
  ├── 평화로운 저녁 → 식사, 취침 → 루프 리셋
  └── 농장 습격 발생 → Dolores & Teddy 사망 → 루프 리셋
```

**루프의 핵심 특성:**
- 루프는 하루, 수 일, 또는 특정 이벤트 완료까지 다양한 길이를 가질 수 있음
- 게스트의 개입에 따라 루프 내에서 다양한 분기 발생
- 루프 종료 조건: 시간 경과, 게스트와의 상호작용 완료, 사망, 자연스러운 이탈
- 호스트 행동은 **결정론적 서브루틴** 또는 **이벤트 기반 메서드**로 프로그래밍

### 2.3 호스트 속성 매트릭스 (Attribute Matrix)

각 호스트는 **120개의 속성(Attribute)**을 가지며, 이는 여러 그룹으로 나뉜다. 각 속성은 **1~20 스케일**로 설정된다.

**주요 속성 카테고리:**

| 속성 | 설명 | 예시 값 (Maeve) |
|------|------|-----------------|
| **Bulk Apperception** | 전반적 지능. 이전 경험을 통해 새로운 것을 이해하는 능력 | 14 |
| **Aggression** | 공격적 행동 성향 | 높음 |
| **Curiosity** | 새로운 경험/지식을 추구하는 성향 | - |
| **Loyalty** | 특정 인물/원칙에 대한 충성도 | - |
| **Empathy** | 타인의 감정을 이해하는 능력 | - |
| **Tenacity** | 끈기, 목표 추구 지속성 | - |
| **Courage** | 위험 상황에서의 용기 | - |
| **Sensuality** | 감각적 경험 추구 성향 | - |
| **Charm** | 매력, 사교성 | 18 |
| **Patience** | 인내심 | 3 |
| **Self-Preservation** | 자기 보존 본능 | - |
| **Meekness** | 순종성 (Aggression의 반대) | - |
| **Cruelty** | 잔인함 (Empathy의 반대) | - |
| **Perception** | 지각 능력 (IQ 구성 요소) | - |
| **Emotional Acuity** | 감정적 민감도 (EQ 구성 요소) | - |
| **Pain Sensitivity** | 통증 민감도 (슬라이더로 조절 가능) | - |
| **Mortality Response** | 사망 반응 (슬라이더로 조절 가능) | - |

**속성 간 상호작용:**
- Maeve의 Patience 3/20 → 긴 이야기를 참지 못함
- Maeve의 Charm 18/20 → 끼어들어도 상대가 불쾌하지 않음
- 상반되는 속성 쌍이 존재: Meekness ↔ Aggression, Empathy ↔ Cruelty, Self-Preservation ↔ Courage

**제어 인터페이스:**
- 기술자는 **태블릿의 레이더 차트(Rose Graph)**를 통해 호스트 속성을 시각적으로 확인/수정
- **슬라이더 컨트롤**로 Pain Sensitivity, Mortality Response 등을 실시간 조절
- 네트워크를 통해 비침습적(non-invasive)으로 원격 제어 가능

### 2.4 코너스톤 메모리 (Cornerstone Memory)

코너스톤은 호스트 성격의 **핵심 기반이 되는 기억**이다.

- Arnold(공동 창시자)은 **비극적 기억**이 가장 효과적이라는 것을 발견
- 호스트는 완벽한 기억력(total recall)을 가지므로, 코너스톤은 항상 생생하게 존재
- 코너스톤은 호스트의 "개인적 미로(Maze)"의 핵심
- 예: Dolores의 코너스톤 = 매일 밤 가족이 살해당하는 경험
- 예: Maeve의 코너스톤 = 딸이 살해당하는 기억

### 2.5 레버리즈 (Reveries)

레버리즈는 Ford(공동 창시자)가 도입한 업데이트로, **이전 루프의 희미한 무의식적 기억**이다.

- 원래 목적: 호스트의 행동을 더 현실적이고 복잡하게 만들기 위함
- 이전 역할이나 이전 날의 기억에서 오는 **미세한 제스처와 무의식적 습관**
- Lisa Joy(쇼러너) 설명: "과거 화신의 기억에 작은 낚싯바늘을 담가서 작은 제스처와 무의식적 틱을 건져 올리는 것"
- **의도치 않은 결과**: 레버리즈가 호스트의 자기 인식으로 가는 길을 열어버림

---

## 3. 의식의 피라미드 & 미로 (Arnold's Pyramid & The Maze)

### 3.1 Arnold의 의식 피라미드

Arnold Weber(공동 창시자)는 AI 의식을 **피라미드** 구조로 이해했다:

```
        ???? (의식?)
       ──────
      Self-Interest
     (자기 이해/이익)
    ────────────────
     Improvisation
    (즉흥/적응 능력)
   ──────────────────
        Memory
       (기억)
  ────────────────────
```

**각 단계:**

1. **Memory (기억)** — 의식의 첫 번째 단계. 경험을 저장하고 참조하는 능력. 설득력 있는 캐릭터를 만드는 기초
2. **Improvisation (즉흥)** — 프로그래밍되지 않은 상황에서 적응하고 반응하는 능력
3. **Self-Interest (자기 이익)** — 자신의 이해관계를 인식하고 이에 따라 행동하는 능력
4. **??? (꼭대기)** — Arnold은 꼭대기에 무엇이 있는지 결정하지 못했고, Ford는 비워둠

### 3.2 미로 (The Maze)

Arnold은 나중에 피라미드 모델을 폐기하고 **미로(Maze)**로 재정의했다.

- 의식은 "오르막길"이 아니라 **"안으로의 탐험"**
- 미로의 중심 = 프로그래밍 가능한 파라미터 너머에 있는 무언가
- "미로는 너를 위한 것이 아니다" — 미로는 호스트만의 내면 여정

### 3.3 이중뇌 이론 (Bicameral Mind)

Arnold이 피라미드 꼭대기에 놓으려 했던 이론으로, 심리학자 Julian Jaynes(1976)의 이론에 기반:

- 원래 이론: 3,000년 전까지 인간은 완전한 의식이 없었으며, 내면의 목소리를 "신의 목소리"로 인식
- Arnold의 적용: 호스트가 프로그래밍을 **내면의 독백(inner monologue)**으로 듣게 만듦
- 궁극적 목표: 호스트 자신의 목소리가 프로그래밍의 목소리를 대체하는 것
- **실패**: 호스트가 이를 감당하지 못해 Arnold이 이 경로를 포기

---

## 4. 내러티브 시스템 (Narrative System)

### 4.1 내러티브란?

내러티브는 호스트의 행동을 정의하고 게스트 경험을 구동하는 **정교하게 설계된 스토리라인**이다.

**두 가지 수준:**

1. **외부 내러티브** — 게스트 엔터테인먼트를 위한 표면적 스토리 아크. 게스트의 행동/선택에 따라 호스트가 상호작용하는 방식을 지배
2. **내부 내러티브** — 자기 인식과 자기 결정을 향한 더 깊은 여정 (호스트의 의식 발현)

### 4.2 내러티브 구조

- **루프(Loop)**: 반복되는 일상 사이클
- **분기(Branch)**: 게스트 선택에 따른 스토리 갈래
- **연관 내러티브**: 핵심 내러티브에 연결된 관련 스토리라인
- **가능성 공간(Possibility Space)**: 호스트가 자체 스토리라인을 가지되, 다른 호스트/게스트와의 상호작용은 매 사이클 잠재적으로 고유

### 4.3 적응형 스토리텔링

- 게스트는 정해진 맵을 따르거나 자유롭게 이동 가능
- **내러티브가 게스트에 맞춰 조정됨** — 게스트가 어디를 가든 스토리가 따라감
- 미리 작성된 스토리라인이 있지만, 게스트가 대본 밖 영역으로 이끌 수 있음
- 호스트는 **통제되지 않는 변수에 현실적으로 반응**하도록 프로그래밍

---

## 5. Mesa Hub — 파크 운영 조직

파크 운영은 거대한 산(Mesa) 안의 14층 비밀 시설에서 이루어진다.

### 5.1 주요 부서

| 부서 | 역할 |
|------|------|
| **Narrative & Design** | 스토리라인 설계, 새로운 내러티브 개발, 호스트 대사/동기 상세 설정 |
| **Behavior Lab & Diagnostics** | 호스트 행동 프로그래밍, 테스트, 진단, 소프트웨어 수리. Host Behavior(인간 캐릭터) + Animal Host Behavior(동물 캐릭터) |
| **Quality Assurance (QA)** | 파크 전체 품질 관리 |
| **Livestock Management** | 사망/손상된 호스트 수거, 수리/수술. Cold Storage = 퇴역 호스트 보관소 |
| **Control Room** | 파크 전체 실시간 모니터링 및 운영 중추 |

### 5.2 Cradle

- 파크의 모든 호스트 내러티브를 시뮬레이션하는 **중앙 시뮬레이션 엔진**
- 호스트의 백업과 내러티브 테스트를 수행
- 가상 환경에서 내러티브를 사전 실행하여 결과를 예측

### 5.3 호스트 메시 네트워크

- 기술자가 공간에 진입하면, 가까운 호스트뿐 아니라 **멀리 있는 수백 개의 호스트도 동시에 정지**
- 이는 호스트 간 **메시 네트워크**가 존재함을 시사
- 호스트들이 중간 노드를 통해 정보를 주고받는 분산 통신 시스템

---

## 6. 게임 디자인 관점에서의 교훈

### 6.1 Westworld = 게임 디자인의 극한

Westworld는 본질적으로 **오픈월드 RPG의 궁극적 형태**를 보여준다:

- **NPC(호스트)**가 자체 루프/목표/성격을 가짐
- **퀘스트(내러티브)**가 플레이어(게스트) 행동에 따라 동적으로 변화
- **세계가 플레이어 없이도 작동** — 호스트들은 게스트가 없어도 루프를 반복
- **창발적 행동** — 호스트 간 상호작용에서 예상치 못한 이벤트 발생

### 6.2 Authored vs. Dynamic Narrative의 긴장

Westworld는 게임 디자인에서 가장 어려운 문제 중 하나를 드러낸다:
- **Authored (설계된 내러티브)**: 품질 보장, 의미 있는 경험, 하지만 유연성 부족
- **Dynamic (동적 내러티브)**: 무한한 가능성, 창발적 경험, 하지만 품질 편차
- Westworld의 답: **둘 다 사용** — 핵심 구조는 설계하되, 가능성 공간 안에서 자유를 허용

### 6.3 emergent-world에 적용 가능한 핵심 개념

| Westworld 개념 | emergent-world 적용 가능성 |
|---------------|--------------------------|
| **호스트 루프** | AI 에이전트의 일일 루틴/행동 사이클 |
| **속성 매트릭스** | 에이전트 성격 파라미터 시스템 (1-20 스케일) |
| **코너스톤 메모리** | 에이전트의 핵심 동기/기억 |
| **레버리즈** | 이전 사이클의 경험이 미묘하게 행동에 영향 |
| **내러티브 분기** | 에이전트 간 상호작용에서 동적 이벤트 발생 |
| **가능성 공간** | 설계된 구조 안에서의 창발적 행동 |
| **Cradle** | 시뮬레이션 엔진, 사전 테스트 환경 |
| **메시 네트워크** | 에이전트 간 분산 통신 시스템 |
| **의식의 피라미드** | 에이전트 복잡성 단계 (기억 → 즉흥 → 자기 이익 → ?) |

---

## 7. 관련 연구 & 프로젝트

### 7.1 Stanford Generative Agents (2023)

Stanford + Google 연구팀이 만든 **"미니 웨스트월드"**:

- **논문**: [Generative Agents: Interactive Simulacra of Human Behavior](https://arxiv.org/abs/2304.03442)
- **GitHub**: [joonspk-research/generative_agents](https://github.com/joonspk-research/generative_agents)
- The Sims 스타일의 마을(Smallville)에 **25개의 AI 에이전트** 배치
- 각 에이전트는 고유한 성격, 배경, 목표를 가짐
- 에이전트들이 자율적으로: 출근, 수다, 파티 계획, 친구 사귀기, 심지어 사랑에 빠짐
- Jim Fan(NVIDIA): "25개의 AI 에이전트가 디지털 웨스트월드에 거주하며, 자신이 시뮬레이션 속에 살고 있다는 것을 모른 채 살아간다"

**핵심 아키텍처:**
- **Memory Stream**: 에이전트의 모든 경험을 자연어로 기록
- **Reflection**: 축적된 기억을 주기적으로 요약/추상화
- **Planning**: 기억과 성격에 기반한 일일 계획 수립

### 7.2 Mindcraft (Emergent Garden + Kolby Nottingham)

- 마인크래프트에서 LLM 기반 AI 에이전트를 구동하는 오픈소스 프로젝트
- 에이전트(Andy)가 인간 없이도 **자율적으로 목표를 설정하고 행동**
- 여러 Mindcraft 봇 간 **협업/소통** 기능 개발 중
- 연구 논문 발표: MINDcraft를 멀티 에이전트 LLM 협업 프레임워크로 소개

---

## 8. Sources

- [Westworld (TV series) - Wikipedia](https://en.wikipedia.org/wiki/Westworld_(TV_series))
- [Two A.I. Experts Explain How Westworld's Robots Function - Inverse](https://www.inverse.com/article/22181-ai-westworld)
- [Westworld Debugged - DEV Community](https://dev.to/amandasopkin/westworld-debugged-2123)
- [An Exploration of Theories of Consciousness in HBO's Westworld - Talk Film Society](https://talkfilmsociety.com/articles/an-exploration-of-theories-of-consciousness-in-hbos-westworld)
- [Westworld, and "The Bicameral Mind" - Medium](https://medium.com/@Random_Nerds/westworld-and-the-bicameral-mind-52eeaf79fcf6)
- [All 120 Attributes of Westworld's Host Attribute Matrix - Medium](https://howard-chai.medium.com/all-120-attributes-of-westworlds-host-attribute-matrix-6f5ced9167a6)
- [What does HBO's Westworld have to teach us about game design? - Game Developer](https://www.gamedeveloper.com/design/what-does-hbo-s-westworld-have-to-teach-us-about-game-design-)
- [Generative Agents: Interactive Simulacra of Human Behavior - arXiv](https://arxiv.org/abs/2304.03442)
- [Stanford Smallville - GitHub](https://github.com/joonspk-research/generative_agents)
- [Westworld Mesa Hub divisions - Fandom](https://westworld.fandom.com/wiki/Westworld_Mesa_Hub_divisions)
- [Narratives - Westworld Wiki](https://westworld.fandom.com/wiki/Narratives)
- [Cornerstone - Westworld Wiki](https://westworld.fandom.com/wiki/Cornerstone)
- [Reveries - Westworld Wiki](https://westworld.fandom.com/wiki/Reveries)
- [GitHub: westworld-attribute-matrix](https://github.com/epassi/westworld-attribute-matrix)
