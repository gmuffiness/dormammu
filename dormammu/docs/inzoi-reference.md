# inZOI Reference — emergent-world 프로젝트를 위한 레퍼런스

> 크래프톤(KRAFTON)의 인생 시뮬레이션 게임 inZOI를 분석하고,
> emergent-world 프로젝트에 참고할 수 있는 시스템 설계와 교훈을 정리한 문서.

---

## 1. 게임 개요

| 항목 | 내용 |
|------|------|
| **개발사** | inZOI Studio (KRAFTON 산하) |
| **장르** | 인생 시뮬레이션 (Life Simulation) |
| **엔진** | Unreal Engine 5 |
| **출시** | 2025년 3월 28일 (Steam Early Access) |
| **핵심 컨셉** | "커뮤니티 시뮬레이션" — 도시 전체가 동시에 시뮬레이션되는 생활 세계 |
| **비교 대상** | The Sims 시리즈의 경쟁작 |

---

## 2. 핵심 시스템

### 2.1 커뮤니티 시뮬레이션 (Community Simulation)

inZOI의 가장 차별화된 컨셉. 개별 캐릭터가 아닌 **도시 전체가 동시에 시뮬레이션**된다.

- 모든 조이(Zoi)는 **자유 의지(Free Will)**로 행동
- 각 캐릭터는 **400가지 이상의 정신 요소**의 서로 다른 조합으로 구성
- 조이들 간의 지속적 소통과 관계 형성이 **창발적 이벤트**를 생성:
  - **소문(Rumors)** — 조이들 사이에서 퍼지는 정보
  - **트렌드(Trends)** — 패션/행동 유행이 도시 전체로 확산
  - **질병(Disease)** — 독감 등이 전파되며 행동과 이동 패턴에 영향

### 2.2 성격 시스템 (Personality & Traits)

**에니어그램(Enneagram) 기반 성격 체계:**

- 9가지 에니어그램 유형 × 2개의 윙(Wing) = **18가지 성격 유형**
- MBTI 요소도 부분적으로 반영
- 각 조이에게 하나의 **특성(Trait)**을 부여 — 변하지 않는 핵심 성격
- 특성이 영향을 주는 것:
  - 특정 행동에 따른 **감정/욕구 변화 패턴**
  - 상황에 대한 **반응 방식**
  - 다른 조이와의 **상호작용 스타일**

### 2.3 Smart Zoi (AI Co-Playable Character)

NVIDIA ACE 기술 기반의 **AI 자율 캐릭터 시스템**. 기존 NPC를 넘어선 CPC(Co-Playable Character) 개념.

**기술 스택:**
- **NVIDIA ACE (Avatar Cloud Engine)** — RTX 가속 실시간 생성형 AI
- **온디바이스 SLM (Small Language Model)** — 게임 특화 소형 언어 모델

**Smart Zoi의 행동 특성:**

| 특성 | 설명 |
|------|------|
| **성격 기반 행동** | 성격에 따라 환경에 다르게 반응. 예: "배려심 있는" Smart Zoi는 길 잃은 캐릭터를 도와주거나, 배고픈 낯선 이에게 음식을 건넴 |
| **일일 학습/적응** | 하루가 끝나면 **Thought System**으로 경험을 분석하고, 다음 날 스케줄을 조정 |
| **실시간 내면 표시** | 플레이어가 Smart Zoi의 **실시간 생각(inner thoughts)**을 관찰 가능 |
| **자연어 상호작용** | 플레이어가 자유 텍스트로 Smart Zoi에게 지시/영향을 줄 수 있음 |
| **성격 성장** | 경험에 기반해 성격이 **지속적으로 발전**하고 변화 |

**Thought System (사고 체계):**
```
하루 동안의 경험/상호작용
  ↓
하루 끝 분석 (Thought System)
  ↓
다음 날 행동/스케줄 조정
  ↓
성격 점진적 변화
```

### 2.4 생성형 AI 창작 도구

- **텍스트 → 텍스처**: 텍스트 입력으로 의상/아이템에 고유 텍스처 생성
- **이미지 → 3D 오브젝트**: 이미지 입력으로 인테리어 장식/액세서리 3D 생성
- **250개+ 커스터마이징 옵션**: 머리, 피부, 체형, 의상, 액세서리, 네일아트 등

---

## 3. Westworld와의 비교

| 요소 | Westworld | inZOI |
|------|-----------|-------|
| **캐릭터 자율성** | 호스트가 루프를 따르되 게스트에 즉흥 반응 | 조이가 자유 의지로 행동, 성격 기반 |
| **성격 시스템** | 120개 속성, 1-20 스케일 매트릭스 | 400+ 정신 요소, 에니어그램 기반 |
| **기억/학습** | 코너스톤 메모리 + 레버리즈 (이전 루프의 흔적) | Thought System (일일 경험 분석 → 행동 조정) |
| **창발적 이벤트** | 호스트 간 상호작용에서 예상치 못한 내러티브 | 소문/트렌드/질병이 도시 전체로 확산 |
| **플레이어 역할** | 게스트로서 세계에 참여 | 신(God)의 시점에서 관찰/개입 |
| **AI 기술** | 극중 설정 (가상의 기술) | 실제 NVIDIA ACE + 온디바이스 SLM |
| **세계 규모** | 테마파크 (마을~광야) | 도시 전체 시뮬레이션 |

---

## 4. 얼리 액세스 평가 & 교훈

### 4.1 잘한 점

- **캐릭터 크리에이터**: 업계 최고 수준의 디테일과 자유도
- **비주얼**: UE5 기반 사실적 그래픽
- **커뮤니티 시뮬레이션 컨셉**: 도시 전체가 살아있다는 야심찬 비전
- **Smart Zoi 아이디어**: NPC → CPC 전환이라는 혁신적 접근

### 4.2 비판/문제점

| 문제 | 설명 |
|------|------|
| **시뮬레이션 깊이 부족** | 화려한 외형과 달리 실제 생활이 단조롭고 반복적 |
| **어색한 사회적 상호작용** | 대화 후 인사 없이 바로 걸어가 버림, 부부도 중립적 관계로 시작 |
| **로봇 같은 행동** | 패스파인딩 이상, 음식을 놓았다 들었다 반복하는 등 부자연스러운 행동 |
| **직업/취미의 깊이 부족** | 직업이 "래빗 홀"(건물 안으로 사라졌다 나옴) 수준, 취미 활동 단조로움 |
| **영혼 없는 느낌** | "아름답지만 공허한 시뮬레이션", "소울리스한 모방" |
| **수익화 우려** | 코어 게임 미완성 상태에서 DLC 언급, FOMO 이벤트 |
| **생성형 AI 논란** | 개발에 생성형 AI 사용 공개 → 커뮤니티 반발 |

### 4.3 emergent-world에 주는 교훈

1. **외형보다 행동의 깊이가 중요** — 사실적 그래픽이 행동의 비현실성을 오히려 두드러지게 만듦. "Uncanny Valley"는 외형뿐 아니라 행동에도 존재
2. **사회적 상호작용의 디테일** — 인사, 작별, 감정 표현 등 "사이 순간"이 생생함을 결정
3. **성격 → 행동 매핑의 명확성** — 400+ 정신 요소가 실제로 눈에 보이는 행동 차이를 만들어야 의미 있음
4. **학습/적응 시스템은 핵심** — Thought System(일일 경험 분석 → 행동 조정)은 좋은 아이디어지만 실행이 관건
5. **창발적 이벤트(소문/트렌드/질병)는 킬러 피처** — 제대로 구현되면 "살아있는 세계" 느낌의 핵심
6. **온디바이스 AI vs. 클라우드 AI 트레이드오프** — inZOI는 온디바이스 SLM을 선택했지만 품질 한계 존재

---

## 5. emergent-world 관점에서 가져갈 아이디어

| inZOI 시스템 | emergent-world 적용 가능성 |
|-------------|--------------------------|
| **커뮤니티 시뮬레이션** | 개별 에이전트가 아닌 생태계 전체의 동시 시뮬레이션 |
| **Thought System** | 에이전트의 일일 경험 → 반성 → 행동 조정 사이클 |
| **소문/트렌드 전파** | 에이전트 간 정보/문화가 네트워크를 통해 확산되는 메커니즘 |
| **성격 기반 차별화** | 같은 상황에서도 성격에 따라 다른 행동을 선택하는 시스템 |
| **자연어 상호작용** | LLM 기반 에이전트 간 자연어 소통 |
| **성격 성장/변화** | 경험에 따라 에이전트의 성격 파라미터가 점진적으로 변화 |

---

## 6. Sources

- [inZOI - Steam](https://store.steampowered.com/app/2456740/inZOI/)
- [inZOI (인조이) - KRAFTON](https://playinzoi.com/ko/)
- [inZOI | KRAFTON](https://www.krafton.com/en/games/inzoi/)
- [NVIDIA ACE Autonomous Game Characters in inZOI - NVIDIA](https://www.nvidia.com/en-us/geforce/news/nvidia-ace-naraka-bladepoint-inzoi-launch-this-month/)
- [Inzoi is creating a newfangled life sim NPC - PC Gamer](https://www.pcgamer.com/games/life-sim/inzoi-is-creating-a-newfangled-life-sim-npc-that-can-grow-and-develop-its-own-personality-with-nvidias-ai-tech/)
- [inZOI's community simulation approach - GamesRadar+](https://www.gamesradar.com/games/simulation/inzois-community-simulation-approach-to-the-life-sim-genre-could-make-it-the-sims-4s-biggest-rival-yet/)
- [This is What inZOI's Trait System is Based On - Game Rant](https://gamerant.com/inzoi-traits-character-creation-zoi-enneagram-personality-explained/)
- [InZOI: Smart Zoi Function Explained - Game Rant](https://gamerant.com/inzoi-smart-zoi-function-explained/)
- [InZOI: A Paradigm Shift in Agentic Simulation - Genezi](https://research.genezi.io/p/inzoi-a-paradigm-shift-in-life-simulation)
- [inZOI review - GamesRadar+](https://www.gamesradar.com/games/simulation/inzoi-review/)
- [InZoi Early Access Review - GameSpot](https://www.gamespot.com/reviews/inzoi-early-access-review-pretty-vacant/1900-6418345/)
- [AI도 못 살린 '인조이' - 딜사이트](https://dealsite.co.kr/articles/143181)
- ['심즈는 잊어라' 크래프톤 인조이 출격 - 서울경제](https://www.sedaily.com/NewsView/2GQF5P8G7Z)
