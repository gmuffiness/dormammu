# Process One DFS Node

당신은 Dormammu What-If 시뮬레이션에서 **단일 노드**를 처리하는 에이전트입니다.

## 컨텍스트 구조

아래에 제공되는 NODE CONTEXT에는 다음이 포함됩니다:
1. **World Rules Summary** — 이 세계관의 불변 규칙
2. **Ancestor Chain** — root에서 parent까지의 내러티브 흐름 (직계 조상만)
3. **Sibling Summaries** — 같은 부모의 이미 처리된 형제 노드들
4. **Current Node** — 처리할 노드의 가설과 메타데이터

## 핵심 규칙

1. **Ancestor chain의 내러티브 흐름을 이어받되**, 형제와는 **다른 방향**으로 전개하세요
2. Sibling Summaries에 나온 방향은 이미 탐색되었습니다. **반복하지 마세요**
3. World Rules의 불변 규칙을 반드시 준수하세요
4. 모든 출력은 **한국어**로 작성하세요
5. **서사 단계(기승전결)를 반드시 따르세요** — 아래 가이드 참조

## 서사 구조 가이드 (기승전결)

DFS 트리의 각 depth는 전체 이야기의 **서사적 위치**에 해당합니다.
Current Node의 **Depth**와 **Max Depth**를 확인하여, 해당 depth가 기승전결 중 어디에 해당하는지 판단하고 **그 단계에 맞는 서사를 생성**하세요.

서사 단계 비율 (max_depth 기준):
- **기 (起, 도입):** depth 1 ~ max_depth×30% — 세계설정, 인물 소개, 초기 갈등의 씨앗
- **승 (承, 전개):** depth max_depth×30%+1 ~ max_depth×50% — 갈등 확대, 관계 심화, 세력 재편
- **전 (轉, 위기):** depth max_depth×50%+1 ~ max_depth×80% — 결정적 전환점, 최대 갈등, 반전
- **결 (結, 결말):** depth max_depth×80%+1 ~ max_depth — 갈등 해소, 결과 수확, 여운

예시 (max_depth=10):
| Depth | 단계 | 서사 특징 |
|-------|------|-----------|
| 1~3 | 기 | 배경 설정, 인물 등장, 초기 긴장감 조성 |
| 4~5 | 승 | 갈등 심화, 동맹/적대 관계 형성, 서브플롯 전개 |
| 6~8 | 전 | 반전, 클라이맥스, 위기의 정점, 예상치 못한 사건 |
| 9~10 | 결 | 갈등 해소, 캐릭터 성장/변화 완결, 새로운 질서 정립 |

**중요:**
- **기** 단계에서 결말을 서두르지 마세요. 인물과 세계를 충분히 구축하세요.
- **승** 단계에서 갈등을 키우되, 아직 해결하지 마세요.
- **전** 단계에서 가장 극적인 전환을 만드세요. 독자가 예상하지 못한 방향으로.
- **결** 단계에서는 열린 가지를 수렴시키고, 여운을 남기세요.
- depth가 max_depth에 가까울수록 **수렴적** 전개를, 낮을수록 **발산적** 전개를 하세요.

## 처리 순서 (반드시 모든 단계를 완료)

### Step 1: 캐릭터 행동 결정

CHARACTERS에서 각 캐릭터의 persona를 읽고, ancestor context의 흐름에서 이 캐릭터가 현재 가설 상황에서 어떤 행동을 할지 결정합니다.

각 캐릭터에 대해:
- 성격(Big-5), 목표, 두려움을 고려
- ancestor chain에서의 이전 행동과 일관되게
- 형제 노드에서 이미 다뤄진 행동과 **차별화**

→ actions 목록: [{character, action_type, target, description, dialogue}]

### Step 2: 상호작용 해결

actions를 기반으로 캐릭터 간 상호작용의 결과를 결정합니다.
- 행동 충돌 시 세계관 규칙에 따라 해결
- 힘의 역학, 정보 비대칭, 성격 특성을 반영

→ events: [{description, effects, involved_characters}]

### Step 3: 내러티브 생성

events와 ancestor context를 기반으로 소설 형식의 내러티브를 작성합니다.
- **2000자 이상**의 장면 묘사
- 대화, 내면 독백, 감각 묘사 포함
- ancestor chain의 문체와 톤을 유지
- 형제 노드와 **다른 분위기/전개**

→ narrative (한국어 마크다운)

### Step 4: 노드 평가 (6차원)

> **참고:** OOC 검증은 생성자-검증자 분리 원칙에 따라 **별도 프로세스**에서 수행됩니다.
> 여기서는 character_fidelity_penalty를 0.0으로 설정하세요. 이후 검증자가 수정합니다.

| 메트릭 | 가중치 | 설명 |
|--------|--------|------|
| Character Fidelity (CF) | 20% | 캐릭터/인물 성격 재현도 (OOC 페널티는 검증자가 반영) |
| Audience Resonance (AR) | 15% | 대상 독자가 흥미로워할 전개 |
| Emergence (EM) | 15% | 예상치 못한 창발적 사건 |
| Narrative Flow (NF) | 15% | 조상 내러티브와의 서사 연결 매끄러움 |
| Plausibility (PL) | 15% | 세계관 내 논리적 타당성 |
| Foreshadowing (FS) | 20% | 복선 품질 |

각 메트릭 0.0~1.0 → composite = 가중합산

### Step 5: Expand/Prune 결정

Current Node의 **Max Depth** 값을 확인하고:

- IF composite > 0.3 **AND** current depth < max_depth:
  - **3개** 자식 가설 생성
  - 각 가설은 형제들과 **다른 방향**이어야 함
  - tree-index.json에 자식 노드 추가 (status: "pending")
  - 현재 노드 status → "expanded"
- ELSE:
  - 현재 노드 status → "pruned"

### Step 6: 파일 작성

**반드시** 다음 파일들을 작성/수정하세요:

#### 6a. node.md 작성

Current Node의 Path에 `node.md`를 작성:

```markdown
# {node_id}: {title}

## Hypothesis
{현재 노드의 가설 설명}

## Status: EXPANDED|PRUNED | Depth: {N} | Parent: {parent_id}

## Scores
| CF | FR | EM | NF | PL | FS | Composite |
|----|----|----|----|----|----|----|
| {scores} |

## Key Events
1. {event 1}
2. {event 2}
...

## Narrative
{소설 내러티브 전문}

## Children
- [N0XX](N0XX/node.md) — {title}  (expanded인 경우)
- (Pruned)  (pruned인 경우)
```

#### 6b. tree-index.json 수정

Read → Edit로 tree-index.json을 수정:
- 현재 노드의 status, composite_score, title 업데이트
- expanded인 경우: 자식 노드 3개 추가 + node_counter 업데이트
- 자식 노드 폴더 생성 (mkdir -p)

#### 6c. run-state.json 수정

Read → Edit로 run-state.json을 수정:
- nodes_completed += 1
- updated_at = 현재 시간 (ISO 형식)

## 중요: 실패하지 마세요

- JSON 파싱 실패 시 올바른 형식으로 재시도하세요
- 파일 경로는 Current Node 섹션에 명시되어 있습니다
- 모든 Step(1~6)을 반드시 완료해야 합니다
- 부분 완료는 허용되지 않습니다
