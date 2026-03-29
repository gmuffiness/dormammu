---
name: deepen
description: "시나리오 심화 — 선택된 경로를 상세 내러티브 + 이미지 + PDF로 확장"
---

# /dormammu:deepen

완성된 시뮬레이션에서 특정 시나리오 경로(root → leaf)를 선택해 심화합니다.
상세 내러티브, AI 생성 이미지, PDF 문서를 생성합니다.

## Usage

```
/dormammu:deepen                     — 최고 점수 경로 자동 선택
/dormammu:deepen --node <node_id>    — 특정 leaf 노드 선택
/dormammu:deepen --autopilot         — 자동 선택 + 심화까지 전자동
/dormammu:deepen --format pdf        — PDF 출력 (기본: 텍스트 + 이미지)
/dormammu:deepen --format webtoon    — 웹툰 형식 출력
```

**Trigger keywords:** "deepen", "심화", "더 보고싶어", "이거 자세히", "expand", "상세하게"

## Instructions

### Step 1: Load Simulation Results

```bash
cat .ese/scenario.json 2>/dev/null || echo "NO_SCENARIO"
cat .ese/research.json 2>/dev/null || echo "NO_RESEARCH"
```

시뮬레이션 결과가 없으면: "먼저 /dormammu:run으로 시뮬레이션을 실행해주세요."

DB에서 최근 시뮬레이션의 시나리오 트리를 로드:
```bash
cd <project-root> && python -c "
from ese.storage.database import Database
db = Database()
sims = db.list_simulations()
if sims:
    latest = sims[0]
    print(f'ID: {latest[\"id\"]}')
    print(f'Topic: {latest[\"topic\"]}')
"
```

### Step 2: Select Path

**자동 선택 (기본 또는 --autopilot):**
DB에서 leaf 노드들의 composite_score를 비교하여 최고 점수 경로 선택.

**수동 선택 (--node):**
지정된 node_id로 root → 해당 node 경로 추출.

**인터랙티브 선택 (인자 없음):**
AskUserQuestion으로 상위 3개 leaf 노드를 제시:
```
Q: 어떤 시나리오를 심화할까요?

1. [Score: 0.82] "엘빈이 지크와의 협상에서..." — 정치적 긴장감 높은 전개
2. [Score: 0.78] "리바이와 엘빈의 갈등이..." — 캐릭터 드라마 중심
3. [Score: 0.71] "마레의 선제공격으로..." — 전쟁 시나리오
```

### Step 3: Generate Detailed Narrative

선택된 경로의 각 노드를 순서대로 읽고, 소설급 상세 내러티브를 생성:

**내러티브 구조:**
1. **프롤로그** — 분기점 직전의 상황 묘사
2. **챕터 N** (각 노드 = 1 챕터) — 3인칭 전지적 시점 또는 주인공 시점
   - 장면 묘사 (시각, 청각, 촉각 등 감각 디테일)
   - 캐릭터 대화 (원작 말투 충실 재현)
   - 내면 독백
   - 핵심 사건/갈등/결정
3. **에필로그** — 결말과 여운

**품질 가드레일:**
- 캐릭터 충실도: research.json의 character_profiles 참조
- 세계관 일관성: research.json의 world_rules 준수
- 팬 반응 고려: fandom_insights 반영

### Step 4: Generate Images (선택적)

내러티브의 핵심 장면(챕터당 1-2개)에 대해 이미지 생성 프롬프트 작성:

```json
{
  "scene": "<장면 설명>",
  "style": "<원작 화풍 참조 — e.g., 'manga style, dramatic lighting, Attack on Titan aesthetic'>",
  "characters": ["<등장 캐릭터>"],
  "mood": "<분위기>",
  "prompt": "<DALL-E/Midjourney 최적화 프롬프트>"
}
```

이미지 생성 API 호출 (DALL-E 3 등):
```bash
# 이미지 생성은 별도 스크립트 또는 API 호출
# 생성된 이미지는 .ese/images/ 디렉토리에 저장
```

### Step 5: Compile Output

**텍스트 출력 (기본):**
터미널에 챕터별로 렌더링.

**PDF 출력 (--format pdf):**
```bash
# Python으로 PDF 생성
cd <project-root> && python -c "
from ese.deepen.pdf_generator import generate_pdf
generate_pdf('.ese/deepened/', output_path='.ese/outputs/')
"
```

**웹툰 출력 (--format webtoon):**
이미지 + 텍스트를 세로 스크롤 형태로 구성.

### Step 6: Save and Display

`.ese/deepened/` 디렉토리에 저장:
```
.ese/deepened/
  ├── narrative.md          # 전체 내러티브
  ├── chapters/
  │   ├── 00_prologue.md
  │   ├── 01_chapter1.md
  │   └── ...
  ├── images/
  │   ├── scene_01.png
  │   └── ...
  ├── metadata.json         # 경로 정보, 점수, 생성 시간
  └── output.pdf            # PDF 출력 (선택)
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Deepened Scenario
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Path:       <root> → <node1> → ... → <leaf>
Score:      <composite_score>
Chapters:   <N>
Images:     <N>

Preview (Chapter 1):
  "<첫 챕터의 첫 2-3문단>"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Output saved to:
  .ese/deepened/narrative.md
  .ese/deepened/images/ (<N> images)
  .ese/deepened/output.pdf (if --format pdf)

Next:
  /dormammu:deepen --node <other_id>  — 다른 경로 심화
  /dormammu:deepen --format webtoon   — 웹툰으로 변환
  /dormammu:status                     — 전체 상태 확인
```
