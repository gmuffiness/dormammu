---
name: research
description: "팬덤 리서치 — 웹검색으로 팬 반응/이론 수집, 캐릭터 프로파일 추출, 세계관 규칙 정의"
---

# /dormammu:research

시뮬레이션 전 사전 조사 단계. 웹검색으로 팬덤 반응/이론을 수집하고,
캐릭터 프로파일과 세계관 규칙을 추출합니다.

## Usage

```
/dormammu:research
/dormammu:research --skip-fandom
```

**Trigger keywords:** "research", "리서치", "사전조사", "팬덤 조사", "캐릭터 분석"

## Instructions

### Step 1: Load Scenario

```bash
cat .ese/scenario.json 2>/dev/null || echo "NO_SCENARIO"
```

시나리오 없으면: "먼저 /dormammu:imagine으로 시나리오를 설정해주세요."

### Step 2: Fandom Research (웹검색)

시나리오의 `source.title`과 `topic`을 기반으로 웹검색 수행:

**검색 쿼리 (3-5개 병렬):**
1. `"<작품명>" "<What-If 키워드>" 팬 이론 site:reddit.com OR site:dcinside.com OR site:arca.live`
2. `"<작품명>" what if "<핵심 분기점>" fan theory`
3. `"<작품명>" "<주인공>" character analysis personality`
4. `"<작품명>" world building rules lore`
5. `"<작품명>" best alternate timeline fanfiction`

WebSearch 도구로 검색하고, 유의미한 결과는 WebFetch로 상세 내용 수집.

**수집 대상:**
- 팬 이론/예측 (이 What-If에 대한 기존 팬 논의)
- 캐릭터 분석 (성격, 동기, 말투, 관계 분석글)
- 세계관 규칙 정리 (나무위키, 팬 위키 등)
- 유사 팬픽/2차창작의 인기 전개 패턴

### Step 3: Character Profile Extraction

수집된 정보 + LLM 지식을 결합하여 캐릭터 프로파일 생성:

시나리오의 `protagonists` 각각에 대해:
```json
{
  "name": "<캐릭터명>",
  "original_name": "<원어 이름>",
  "role": "<역할>",
  "personality": {
    "big5": {
      "openness": 0.0-1.0,
      "conscientiousness": 0.0-1.0,
      "extraversion": 0.0-1.0,
      "agreeableness": 0.0-1.0,
      "neuroticism": 0.0-1.0
    },
    "key_traits": ["trait1", "trait2"],
    "speech_pattern": "<말투 특징 설명>",
    "catchphrases": ["대사1", "대사2"]
  },
  "motivation": "<핵심 동기>",
  "relationships": [
    {"target": "<다른 캐릭터>", "type": "<관계 유형>", "affinity": -1.0~1.0}
  ],
  "arc_in_original": "<원작에서의 캐릭터 아크>",
  "divergence_impact": "<이 What-If에서 이 캐릭터가 받는 영향>"
}
```

주인공뿐만 아니라 시나리오에 등장할 주요 조연 캐릭터도 3-5명 추가 생성.

### Step 4: World Rules Extraction

세계관의 불변 규칙을 정리:
```json
[
  {
    "rule": "<규칙 설명>",
    "category": "physics|society|magic|technology|politics",
    "source": "<근거 — 원작 어디에서 확인 가능>",
    "affected_by_divergence": true/false,
    "divergence_note": "<분기로 인해 변경되는 경우 설명>"
  }
]
```

### Step 5: Inspiration Sources

동일 장르의 명작에서 스토리텔링 패턴 추출:

웹검색: `"<장르>" best story alternate timeline narrative techniques`

```json
[
  {
    "title": "<작품명>",
    "relevance": "<이 시나리오와의 관련성>",
    "narrative_technique": "<차용 가능한 서사 기법>",
    "example": "<구체적 예시>"
  }
]
```

### Step 6: Save Research Results

`.ese/research.json`에 저장:
```json
{
  "scenario_topic": "<대주제>",
  "fandom_insights": [
    {"source": "<URL>", "summary": "<요약>", "sentiment": "positive|negative|mixed", "relevance": 0.0-1.0}
  ],
  "character_profiles": [...],
  "supporting_characters": [...],
  "world_rules": [...],
  "inspiration_sources": [...],
  "researched_at": "<ISO timestamp>"
}
```

### Step 7: Show Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Research Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Fandom Insights:    <N>개 수집
Character Profiles: <N>명 (주인공 <N> + 조연 <N>)
World Rules:        <N>개
Inspiration Sources: <N>개

Top Fan Theory:
  "<가장 관련성 높은 팬 이론 요약>"

Key Character Insight:
  <주인공> — "<성격/동기에 대한 핵심 인사이트>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Next:
  /dormammu:run          — 시뮬레이션 시작 (리서치 데이터 자동 주입)
  /dormammu:status       — 현재 상태 확인
```
