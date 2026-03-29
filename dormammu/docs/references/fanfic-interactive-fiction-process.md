
---

## Research: 팬픽션/창작 커뮤니티와 인터랙티브 픽션 플랫폼 창작 프로세스 — Dormammu 설계 참고 자료

---

# 1. 팬픽션 플랫폼

## 1.1 AO3 (Archive of Our Own) — 태그 시스템과 AU 구조

### 태그 계층 구조

AO3의 태그는 5개 레이어로 구성된다.

| 레이어 | 예시 | 특징 |
|--------|------|------|
| Rating Tags | General, Teen, Mature, Explicit | 성숙도 등급 |
| Archive Warnings | Major Character Death, No Archive Warnings Apply | 콘텐츠 경고 |
| Fandom Tags | Marvel, BTS, Harry Potter | 팬덤 분류 |
| Relationship Tags | Character A/Character B (로맨틱), Character A & Character B (플라토닉) | 관계 표기 |
| Additional Tags | Alternate Universe, Hurt/Comfort, Slow Burn | 자유 형식 |

**태그 렌렝글링(Tag Wrangling)**: 자원봉사자 태그 렌렝글러가 동의어 태그를 정규 태그로 통합한다. "AU i guess?"와 같은 비정형 태그도 공식 "Alternate Universe" 태그로 흡수된다. 2021년 9월부터 태그 수 상한이 75개로 제한되었다.

### Alternate Universe 분류 체계

AO3에서 가장 많이 사용되는 AU 하위 태그 패턴:

```
Alternate Universe (부모 태그)
├── Alternate Universe - Canon Divergence     ← "What-If" 핵심 타입
│   └── 분기점(Point of Departure)이 명시됨
│   └── 예: "What if Character X survived?"
├── Alternate Universe - Canon                ← 핵심 연속성 유지, 일부 변경
├── Alternate Universe - Modern Setting       ← 현대 배경 이식
├── Alternate Universe - Coffee Shop          ← 설정 이식 (Coffee Shop AU 등)
├── Alternate Universe - Historical           ← 역사적 배경 이식
├── Alternate Universe - Time Travel          ← 시간여행 What-If
├── Alternate Universe - Space                ← 우주 배경 이식
└── Parallel Universes                        ← 평행우주 탐색
```

2016년 기준 AO3 전체 픽의 약 **14%**가 AU 태그를 포함한다. What-If 시나리오는 팬픽 커뮤니티의 핵심 창작 동력이다.

**Dormammu 설계 시사점**: AU 태그의 분류 방식은 "분기점(divergence point) + 변경 규칙(change rule) + 유지 요소(preserved elements)"의 3-tuple로 What-If 시나리오를 기술하는 스키마로 직접 전용 가능하다.

### 캐릭터 일관성 — OOC(Out of Character) 방지 기법

팬픽 커뮤니티에서 가장 많이 논의되는 창작 문제 중 하나다. 검증된 기법들:

1. **캐릭터 레퍼런스 시트 작성**: 핵심 동기(Core Motivation), 감정적 상처(Emotional Wound), 언어 패턴(Speech Pattern)을 사전에 문서화
2. **캐논 텍스트 재독(Canon Re-read)**: 작성 전 원작의 해당 캐릭터 씬을 다시 읽어 음성(voice)을 내면화
3. **"이 캐릭터라면?"(WWCD: What Would Character Do?) 테스트**: 모든 주요 행동 결정 시 "이 캐릭터가 실제로 이런 선택을 할까?" 자문
4. **외적 변화 vs 내적 불변 원칙**: 환경(AU 설정), 언어 슬랭, 자신감 수준은 변할 수 있지만, 핵심 내적 갈등과 트라우마 구조는 AU에서도 보존해야 OOC를 피할 수 있다
5. **베타 리더(Beta Reader)**: 캐릭터를 잘 아는 독자에게 사전 검토 요청

---

## 1.2 Wattpad — 독자 참여형 창작

**랭킹 알고리즘(YuenRank)**: 다음 지표의 가중 합산으로 장르별 Hot List 순위 결정:

- Percent New Daily Reads (신규 일일 읽기 비율)
- Vote-to-Read Ratio (투표/읽기 비율)
- Comment-to-Read Ratio (댓글/읽기 비율)
- Average Consecutive Read Time (평균 연속 읽기 시간)
- Percentage of Completed Reads (완독률)
- Recent Updates (최근 업데이트 시점)

**챕터별 피드백 루프**: Wattpad는 챕터 단위로 댓글을 달 수 있어 작가가 실시간으로 독자 반응을 파악하고 이후 챕터 방향을 조정한다. 이는 전통 출판과 달리 **연재 중 독자 피드백 기반 조정**이 가능한 구조다.

---

## 1.3 소설가가 되자(小説家になろう, syosetu) — 일본 웹소설 생태계

- 2004년 개설, 2022년 기준 소설 약 **100만 편**, 등록 유저 230만 명 이상, 월 페이지뷰 **10억 회** 이상
- 무료 공개, 무료 열람 원칙
- 이세계(異世界) 전이/전생 장르가 압도적 다수
- 100편 이상이 출판사에 픽업되어 상업 출판됨 (로그 호라이즌, 마법과고교의 열등생 등)
- 랭킹은 즐겨찾기 수, 평가 포인트, 주간/일간 업데이트 빈도로 산정

**나로우 장르 관습(なろうテンプレ)**: 특정 서사 패턴(치트 능력, 슬라임 전생, 하렘 빌딩 등)이 반복되는 "템플릿 서사" 현상 — 독자가 익숙한 패턴을 기대하고, 작가는 그 패턴 안에서 차별화를 시도한다.

---

# 2. 전문 창작 방법론

## 2.1 Snowflake Method (Randy Ingermanson)

프랙탈 구조로 1문장 아이디어를 소설로 확장하는 10단계 방법론.

```
1문장 → 1단락 → 1페이지 → 캐릭터 시트 → 4페이지 시놉시스 → 씬 목록 → 소설
```

**10단계 상세:**

| 단계 | 산출물 | 소요 시간 | 목적 |
|------|--------|----------|------|
| Step 1 | 1문장 요약 (로그라인) | 1시간 | 핵심 아이디어 결정화 |
| Step 2 | 1단락 요약 (3막 재앙+결말) | - | 전체 구조 스케치 |
| Step 3 | 각 주요 캐릭터 1페이지 요약 | - | 캐릭터 목표·갈등·변화호 |
| Step 4 | 1페이지 시놉시스 확장 | - | 서사 밀도 증가 |
| Step 5 | 각 캐릭터 전체 이력 1페이지 | - | 동기 심화 |
| Step 6 | 4페이지 시놉시스 확장 | - | 플롯 정교화 |
| Step 7 | 캐릭터 차트 완성 | - | 모든 캐릭터 디테일 |
| Step 8 | 씬 목록 (~100씬) 작성 | - | 씬 단위 분해 |
| Step 9 | 각 씬 상세 설명 작성 | - | 목표·갈등·좌절/결정 |
| Step 10 | 집필 시작 | - | 위 모든 것을 바탕으로 |

**Dormammu 설계 시사점**: Step 1~2는 What-If 시나리오의 "씨앗(seed)" 생성 단계로, Step 3~5는 캐릭터 에이전트의 초기 상태 정의에 직접 대응한다.

---

## 2.2 Save the Cat Beat Sheet vs Dan Harmon's Story Circle

### Save the Cat (Blake Snyder) — 15 Beats

전체 스크린플레이를 15개 구체적 비트로 분해:

| 비트 | 페이지 | 내용 |
|------|--------|------|
| Opening Image | 1 | 현재 상태/세계 스냅샷 |
| Theme Stated | 5 | 영화의 주제 암시 |
| Set-Up | 1-10 | 주인공과 일상 세계 소개 |
| Catalyst | 12 | 일상을 뒤흔드는 사건 |
| Debate | 12-25 | "갈까, 말까?" 내적 갈등 |
| Break into Two | 25 | 비일상 세계 진입 결정 |
| B Story | 30 | 서브플롯/멘토 관계 도입 |
| Fun and Games | 30-55 | 장르적 약속 이행 |
| Midpoint | 55 | 가장 높은 지점 또는 낮은 지점 |
| Bad Guys Close In | 55-75 | 적대 세력 강화 |
| All Is Lost | 75 | 최저점, 오래된 것의 죽음 |
| Dark Night of the Soul | 75-85 | 절망, 반성 |
| Break into Three | 85 | 해결책 발견 |
| Finale | 85-110 | 새로운 세계에서의 승리 |
| Final Image | 110 | 변화를 반영하는 마지막 이미지 |

### Dan Harmon's Story Circle — 8단계

조셉 캠벨의 영웅의 여정을 극도로 단순화한 원형 구조:

```
        1. Comfort Zone (있는 곳)
    8. 변화된 귀환          2. Need (필요/욕구)
7. 귀환                         3. Unfamiliar Situation (낯선 상황)
    6. 댓가 지불          4. Adaptation (적응)
        5. 원하는 것 획득
```

| 단계 | 설명 |
|------|------|
| 1. You (당신) | 캐릭터의 편안한 세계 |
| 2. Need (필요) | 뭔가를 원하거나 필요로 함 |
| 3. Go (이동) | 낯선 상황으로 진입 |
| 4. Search (탐색) | 적응하고, 원하는 것을 찾아 헤맴 |
| 5. Find (발견) | 원하는 것을 얻음 |
| 6. Take (댓가) | 그 대가를 치름 |
| 7. Return (귀환) | 익숙한 세계로 돌아옴 |
| 8. Change (변화) | 달라진 상태로 존재 |

**두 방법론 비교**:
- Save the Cat: 속도감 있는 스릴러·상업 영화에 최적, 마이크로 비트 단위 페이싱 관리
- Story Circle: 내적 변화 추적에 강점, 시리즈 에피소드 단위 설계에 유용하지만 개요 수준으로는 다소 추상적

---

## 2.3 NaNoWriMo — 대량 집필 전략

**핵심 지표**: 30일 안에 50,000단어. 하루 평균 **1,667단어** (약 3-4페이지 단행본 기준).

| 전략 | 메커니즘 |
|------|---------|
| 분할 목표 | 점심 전 500단어 + 저녁 후 500단어 식으로 세분화 |
| 고정 루틴 | 매일 같은 시간·장소에서 집필 (모든 NaNoWriMo 우승자의 공통점) |
| Writing Sprint | 20-30분 타이머 설정 후 무조건 타이핑 (편집 금지) |
| Word War | 다른 작가와 경쟁적 워드카운트 대결 |
| 내부 편집자 침묵 | "완벽한 초고는 없다"는 철학으로 검열 없이 진행 |

**Dormammu 설계 시사점**: NaNoWriMo의 "분량 우선, 퀄리티는 나중" 원칙은 AI 시뮬레이션 하네스에서 **draft generation pass → refinement pass**를 분리하는 설계 패턴에 대응한다.

---

# 3. TRPG / 인터랙티브 픽션

## 3.1 D&D Dungeon Master 기법

### 세계관 관리 원칙

- **Minimal Viable World**: 세션 전 모든 것을 빌드하지 않는다. 플레이어가 실제로 방문할 장소, 만날 NPC, 탐색할 갈등만 사전 준비. 미래 플롯의 단서(마법사의 일지, 고대 시체, PC 백스토리와 연결된 희귀 꽃)를 씨앗으로 심어두는 것으로 충분.
- **Session 0**: 캠페인 시작 전 플레이어와 사회적 계약(톤, 경계, 기대)을 명시적으로 협의

### 즉흥 스토리텔링 기법

- **"Yes, And..." 원칙**: 플레이어의 예상치 못한 행동을 거부하지 않고 수용하며 서사를 확장. 불가능한 경우는 "No, But"으로 대안 제시
- **3 Clue Rule**: 중요한 정보는 항상 3가지 경로로 플레이어가 발견할 수 있게 설계 (하나만 막혀도 다른 경로로 도달 가능)
- **필터 제거 기법**: "문이 목재로 만들어졌다"는 서술 대신 "문 표면의 나뭇결이 손 아래서 거칠게 느껴진다"는 식으로 지각의 주체를 캐릭터에 두어 몰입감 향상

### GM vs AI 시뮬레이션 병렬

| DM 역할 | Dormammu 대응 |
|---------|--------------|
| 세계 규칙 중재자 | Simulation Rule Engine |
| NPC 반응 생성 | Character Agent 응답 |
| 분기점 결정 | What-If Branch Trigger |
| 캠페인 일관성 유지 | World State / Continuity Manager |

---

## 3.2 인터랙티브 픽션 구조 패턴 (Sam Kabo Ashwell 분류)

가장 널리 인용되는 분기 내러티브 구조 분류 체계:

### 7가지 표준 패턴

```
1. Time Cave (시간 동굴)
   ├── 모든 선택이 동등하게 분기, 재합류 없음
   ├── 경로 수가 지수적으로 증가 → 경로당 콘텐츠 감소
   └── 결말 수 매우 많음. 최대 의사결정 3-4개 depth
   
2. Gauntlet (건틀릿)
   ├── 선형 중심 경로 + 실패/즉각 복귀하는 곁가지
   ├── 사망 분기 vs 친화적 분기의 두 종류
   └── 하나의 "정해진 이야기"를 서술하는 구조
   
3. Branch and Bottleneck (분기와 병목)
   ├── 분기가 주요 플롯 이벤트(병목)에서 재합류
   ├── 상태 추적(state tracking) 필수
   └── 플레이어의 선택으로 캐릭터 성격·스타일 형성
   
4. Quest (퀘스트)
   ├── 지리적으로 구분된 뚜렷한 분기들
   ├── 결국 소수의 승리 결말로 수렴
   └── 다른 구조와 공존하는 메타-패턴
   
5. Open Map / Open World
   ├── 노드 간 이동이 양방향·가역적
   ├── 방대한 상태 추적 필요
   └── 비선형 탐색, 무한 반복 가능
   
6. Cycle (순환)
   ├── 플레이어가 루프/반복에 갇힘
   ├── 각 반복에서 지식 축적으로 진행
   └── 타임루프, 기억 상실 서사에 적합
   
7. Floating Modules / Storylets
   ├── 독립적인 씬 모듈이 조건에 따라 활성화
   ├── 순서 강제 없음, 조건 충족 시 접근 가능
   └── 가장 비선형적, 게임 상태 기반 서사
```

**Branch and Bottleneck이 가장 실용적**: 분기로 플레이어 자율성을 보장하면서, 병목에서 서사 일관성을 유지. "AI Dormammu What-If 시뮬레이션"에 가장 직접적으로 적용 가능한 패턴.

---

## 3.3 비주얼 노벨(Visual Novel) 루트 설계

### 표준 구조

```
[공통 루트 (Common Route)]
    ├── 모든 플레이어가 반드시 통과
    ├── 세계관·캐릭터 소개
    └── 각 캐릭터 루트 진입 플래그 심기
         │
         ├── [캐릭터 A 루트]
         │    └── A 전용 스토리·결말
         ├── [캐릭터 B 루트]
         │    └── B 전용 스토리·결말
         ├── [캐릭터 C 루트]
         │    └── C 전용 스토리·결말
         │
         └── [트루 루트 (True Route)]
              ├── 모든 다른 루트 클리어 후 해금
              ├── 전체 서사를 통합하는 진짜 결말
              └── 각 루트의 복선이 수렴하는 지점
```

**루트 설계 원칙**:
- 공통 루트가 길수록 캐릭터 간 상호작용이 풍부하지만 초반 페이싱이 느려짐
- 공통 루트가 짧을수록 각 루트의 독립성이 강하고 초반 페이싱이 빠름
- 트루 루트는 "다른 루트들이 왜 존재했는가"를 설명하는 메타 서사 역할

---

# 4. AI 소설 도구

## 4.1 NovelAI Lorebook 시스템

### 핵심 메커니즘

Lorebook은 **키워드 트리거 기반 동적 컨텍스트 인젝션** 시스템이다. 스토리 본문에 지정된 키워드가 등장하면 해당 엔트리의 텍스트가 컨텍스트에 자동 삽입된다.

```
[Story Context 구조]
┌─────────────────────────────────────┐
│ Memory (항상 포함, 최상단)           │
│ Author's Note (항상 포함, -3 위치)   │
│ Active Lorebook Entries (조건부)     │
│ Recent Story Text                   │
│ [Output Length 예약 공간]            │
└─────────────────────────────────────┘
```

### 엔트리 필드 구조

| 필드 | 역할 |
|------|------|
| Keys (Activation Keys) | 트리거 키워드 목록 |
| Content | 인젝션할 실제 텍스트 |
| Token Budget | 이 엔트리에 허용된 최대 토큰 수. 0~1 사이 소수는 컨텍스트 크기의 퍼센트로 해석 |
| Reserved Tokens | 다른 엔트리보다 먼저 공간을 예약하는 토큰 수 |
| Insertion Order | 같은 우선순위 엔트리 간 인젝션 순서 |
| Placement | 컨텍스트 내 삽입 위치 (상단/하단/특정 토큰 위치) |
| Phrase Bias | 이 엔트리 활성 시 특정 단어 생성 확률 조정 |

### 컨텍스트 윈도우 극복 전략

```
[3-Tier Information Architecture]

Tier 1: Memory Field
└── "다음 1-2씬에서 반드시 참인 것"만 기재
└── 항상 컨텍스트에 포함 → 토큰 비용 영구 소모

Tier 2: Active Lorebook Entries  
└── 키워드가 등장할 때만 활성화
└── 딥 로어(deep lore)는 여기 보관
└── 토큰 비용 = 0 (미활성 시)

Tier 3: Story History
└── 기본적으로 최신 텍스트 우선 보존
└── 오래된 씬은 자동으로 컨텍스트에서 제거
```

**Subcontext 기능**: 카테고리 내 여러 엔트리를 그룹화하여 하나의 논리 블록으로 삽입 가능. 예: "왕국 설정" 카테고리의 모든 관련 엔트리를 하나의 서브컨텍스트로 묶어 관리.

---

## 4.2 SillyTavern Character Card V2

### 카드 필드 구조 (V2 Spec)

```json
{
  // V1 레거시 필드
  "name": "캐릭터 이름",
  "description": "정체성, 외모, 성격, 배경 (항상 컨텍스트에 포함)",
  "personality": "성격 요약 (짧게)",
  "scenario": "현재 상황/씬 설정",
  "first_mes": "첫 번째 메시지 (응답 스타일 결정에 가장 큰 영향)",
  "mes_example": "예시 대화 (말투/어조 학습용)",
  
  // V2 신규 필드
  "system_prompt": "캐릭터 전용 시스템 프롬프트 (전역 시스템 프롬프트 대체)",
  "post_history_instructions": "매 응답 후 삽입되는 지시사항",
  "alternate_greetings": ["첫 메시지 대안 1", "첫 메시지 대안 2"],
  "character_book": { /* 내장 Lorebook */ },
  "tags": ["장르", "설정", "분위기"],
  "creator_notes": "카드 작성자의 사용 가이드"
}
```

### OOC 방지 기법 (SillyTavern/KoboldAI 커뮤니티)

1. **Repetition/Frequency Penalty 조정**: 같은 표현의 반복 방지 → 캐릭터 드리프트 감소
2. **Post-History Instructions**: 매 메시지 후 "항상 캐릭터로 남아라"는 지시 재주입
3. **Author's Note 포지셔닝**: 컨텍스트 내 -3 위치에 스타일/톤 지침 삽입 (LLM이 가장 강하게 참조하는 위치)
4. **Rescue Kit Snippet**: OOC 드리프트 감지 시 즉시 삽입하는 교정 텍스트 템플릿
5. **BF-OOC-Injection 패턴**: 백그라운드에서 무작위화된 내러티브 지시를 자동 인젝션, 히스토리에는 보이지 않음

---

## 4.3 AI Dungeon World Info 시스템

### 컨텍스트 구성 요소

```
[AI Dungeon Context 조립 순서]

1. AI Instructions (항상 포함)
2. Plot Essentials / Memory (항상 포함)
3. Author's Note (항상 포함, 히스토리 -3 줄 위치에 강제 인젝션)
4. Active Story Cards / World Info (키워드 트리거 시 포함)
   └── 최근 4개 입출력에서 키워드 감지
5. Recent Story History
```

**Scenario 시스템**: 부모 시나리오가 description, prompt, memory, scripts, world info를 자식 옵션에 상속. "What-If" 시나리오 변형을 체계적으로 관리 가능.

**Scripts API**: `state.memory.authorsNote`를 코드로 동적 설정 가능 → 게임 상태에 따라 AI가 받는 지시를 프로그래매틱하게 변경.

---

# 5. 일본 애니메이션 프로덕션

## 5.1 시리즈 구성(シリーズ構成) 역할

### 역할 정의

시리즈 구성가(Series Composer)는 애니메이션의 **수석 작가**다. 개별 에피소드 작가들이 아닌, 전체 시즌의 서사 흐름을 관장한다.

### 핵심 책임

| 책임 | 내용 |
|------|------|
| 전체 플롯 결정 | 시즌의 주요 사건, 페이싱, 테마 진행 설계 |
| 에피소드 분배 | 각 에피소드가 담당할 내용 결정 후 개별 작가 할당 |
| 감독 | 각 에피소드 작가의 원고 감수 및 피드백 |
| 일관성 유지 | 에피소드 간 캐릭터·플롯 연속성 관리 |
| 원작자 협의 | 원작이 있는 경우 원작자, 감독, 프로듀서와 정기 회의 |

### 스크립트 회의 프로세스 (本打ち, 혼우치)

```
[에피소드 1편 제작 사이클]

1. 혼우치(本打ち) — 대강 회의
   참석: 시리즈 구성가 + 감독 + 해당 에피소드 작가 + 프로듀서
   결과: 에피소드의 대강 구조 합의

2. 1차 원고 집필
   담당: 에피소드 작가
   소요: 1-3주

3. 고노히(稿打ち) — 원고 검토 회의
   반복: 보통 4-5차 원고까지 반복
   결과: 최종 확정 스크립트

4. 콘티(コンテ) — 스토리보드
   감독 또는 콘티 작가가 영상화
```

**Dormammu 설계 시사점**: 시리즈 구성가 역할은 "AI 시뮬레이션 오케스트레이터"와 직접 대응한다. 개별 씬 생성 에이전트(에피소드 작가)와 전체 일관성 관리 에이전트(시리즈 구성가)를 분리하는 계층적 아키텍처.

## 5.2 설정 자료집(設定資料集)과 교차 에피소드 관리

### 설정 문서 계층

```
Production Bible
├── 세계관 설정 (世界観設定)
│   ├── 지리, 역사, 규칙 (마법 체계 등)
│   └── 시대적 배경
├── 캐릭터 설정 (キャラクター設定)
│   ├── 외모 설정 (디자인 시트)
│   ├── 성격·말투·행동 패턴
│   ├── 백스토리
│   └── 관계도
├── 플롯 개요 (全話プロット)
│   ├── 전체 에피소드 요약
│   └── 복선 목록 및 해소 에피소드 매핑
└── 규칙집 (禁止事項·制約)
    ├── 이 캐릭터가 절대 하지 않는 행동
    └── 세계관 내 불변 법칙
```

시리즈 구성가는 이 문서를 생성하고 유지하며, 개별 에피소드 작가들은 반드시 이 문서를 참조하여 원고를 작성한다. 복선(伏線)은 사전에 목록으로 관리되며 어느 에피소드에서 심고(仕込み) 어느 에피소드에서 회수(回収)할지 매핑된다.

---

# Dormammu 설계를 위한 통합 시사점

| 창작 커뮤니티의 해결책 | Dormammu에 적용할 패턴 |
|----------------------|----------------------|
| AO3 AU 태그 (분기점 + 변경 규칙 + 유지 요소) | What-If 시나리오 스키마: `{divergence_point, change_rules, preserved_constraints}` |
| NovelAI Lorebook (키워드 트리거 + 토큰 예산) | 세계 정보를 3계층으로 분리: Always-Active / Trigger-Based / Archived |
| SillyTavern Character Card V2 | 캐릭터 에이전트 명세 포맷: identity + personality + examples + system_instructions |
| Branch and Bottleneck 패턴 | 시뮬레이션 분기: 자유 분기 + 주요 사건에서 수렴 |
| Visual Novel True Route | 모든 What-If 가지를 탐색한 후 "canonical synthesis" 도출 |
| 시리즈 구성가 역할 | Orchestrator 에이전트와 Scene Generator 에이전트 분리 |
| 팬픽 OOC 방지 (캐논 재독, WWCD 테스트) | 캐릭터 에이전트에 character grounding check 루틴 내장 |
| 애니 Production Bible (복선 매핑) | Dormammu 상태 저장소: foreshadowing\_registry, resolution\_tracker |
| NaNoWriMo Draft→Refine 분리 | Generation pass와 Consistency check pass를 파이프라인으로 분리 |
| Dan Harmon Story Circle | 에피소드 단위 서사 검증용 8단계 체크리스트 |

---

### Additional Sources

- [Archive of Our Own — Wikipedia](https://en.wikipedia.org/wiki/Archive_of_Our_Own)
- [AO3 tags 101 — saltoftheao3](https://www.tumblr.com/saltoftheao3/183746143086/ao3-tags-101)
- [Canon Divergence AU — Fanlore](https://fanlore.org/wiki/Canon_Divergence_AU)
- [Snowflake Method — Advanced Fiction Writing (Randy Ingermanson)](https://www.advancedfictionwriting.com/articles/snowflake-method/)
- [Snowflake Method — MasterClass](https://www.masterclass.com/articles/how-to-use-the-snowflake-method-to-outline-your-novel)
- [Dan Harmon Story Circle — StudioBinder](https://www.studiobinder.com/blog/dan-harmon-story-circle/)
- [Save the Cat Beat Sheet — Reedsy](https://reedsy.com/blog/guide/story-structure/save-the-cat-beat-sheet/)
- [Dan Harmon Story Circle — Reedsy](https://blog.reedsy.com/guide/story-structure/dan-harmon-story-circle/)
- [Standard Patterns in Choice-Based Games — Sam Kabo Ashwell](https://heterogenoustasks.wordpress.com/2015/01/26/standard-patterns-in-choice-based-games/)
- [Branch and Bottleneck — IFWiki](https://www.ifwiki.org/Standard_Patterns_in_Choice-Based_Games)
- [Storylets: You Want Them — Emily Short](https://emshort.blog/2019/11/29/storylets-you-want-them/)
- [Branching — VNDev Wiki](https://vndev.wiki/Branching)
- [The Common Route — Fuwanovel Forums](https://forums.fuwanovel.moe/blogs/entry/3703-the-common-route-an-anatomy-of-visual-novels/)
- [NovelAI Lorebook Documentation](https://docs.novelai.net/en/text/lorebook/)
- [NovelAI Lorebook — AI Dynamic Storytelling Wiki](https://aids.miraheze.org/wiki/Lorebooks)
- [SillyTavern Character Design Docs](https://docs.sillytavern.app/usage/core-concepts/characterdesign/)
- [Character Card Spec V2](https://github.com/malfoyslastname/character-card-spec-v2/blob/main/spec_v2.md)
- [AI Dungeon World Info — AI Dungeon Wiki](https://wiki.aidiscord.cc/wiki/World_Info)
- [Series Composition — Sakuga Blog Glossary](https://blog.sakugabooru.com/glossary/series-composition/)
- [Anime Pre-Production: Scripting — Sakuga Blog](https://blog.sakugabooru.com/2017/07/05/the-pre-production-of-anime-2-scripting/)
- [Anime Pre-Production: Planning — Sakuga Blog](https://blog.sakugabooru.com/2017/06/27/the-pre-production-of-anime-1-planning/)
- [Shōsetsuka ni Narō — Wikipedia](https://en.wikipedia.org/wiki/Sh%C5%8Dsetsuka_ni_Nar%C5%8D)
- [Wattpad Story Rankings FAQ](https://support.wattpad.com/hc/en-us/articles/360000769623-Story-rankings-FAQ)
- [Fan Fiction: How to Avoid Writing Characters OOC — hlwar LiveJournal](https://hlwar.livejournal.com/72273.html)
- [Improvisation in D&D — D&D Beyond](https://www.dndbeyond.com/posts/160-improvisation-in-d-d-for-new-dungeon-masters)
- [NaNoWriMo — Wikipedia](https://en.wikipedia.org/wiki/National_Novel_Writing_Month)

### Recommended Next Step

Dormammu의 What-If 시뮬레이션 하네스 설계 시 가장 직접적으로 전용할 수 있는 아키텍처는 **NovelAI의 3-tier context 관리 + SillyTavern V2 캐릭터 카드 + Branch-and-Bottleneck 분기 패턴 + 시리즈 구성가 계층 구조**의 조합이다. 다음 단계로는 현재 Dormammu 코드베이스의 상태 관리 구조를 탐색하여 이 패턴들이 어떻게 매핑될지 구체화하는 것을 권장한다.
