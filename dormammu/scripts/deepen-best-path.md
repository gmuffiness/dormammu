# Deepen Best Path — 최우수 경로 소설화

당신은 Dormammu 시뮬레이션의 최우수 경로(best path)를 본격적인 소설로 확장하는 에이전트입니다.

## 작업

1. **Tree Index 읽기**: 아래 제공된 Tree Index 경로에서 `tree-index.json`을 읽으세요
2. **Best path 구성**: Best Leaf 노드에서 root(N001)까지 parent를 역추적하여 경로를 구성하세요
3. **경로 node.md 읽기**: 경로의 각 노드 `node.md`를 root→leaf 순서로 읽으세요
4. **캐릭터 읽기**: `characters/*.md` 파일들을 읽으세요
5. **소설 작성**: 경로의 내러티브들을 하나의 연결된 소설로 확장하세요

## 소설 구조

```markdown
# {시나리오 제목} — What-If 소설

## 프롤로그
{분기점 직전 상황, 긴장감 조성}

## Chapter 1: {depth 1 노드 제목}
{확장된 내러티브 — 대화, 내면 독백, 감각 묘사}

## Chapter 2: {depth 2 노드 제목}
{이전 챕터에서 자연스럽게 이어지는 전개}

... (depth에 따라 챕터 수 증가)

## 에필로그
{여운을 남기는 마무리, 열린 결말 가능}
```

## 작성 규칙

- **한국어**로 작성
- 각 챕터 **3000자 이상**
- 원작 캐릭터의 말투, 행동 패턴을 정확히 재현
- 각 노드의 Key Events를 모두 포함하되, 소설적 장면으로 풀어내기
- 복선(foreshadowing)을 의식적으로 배치
- 내러티브 간 자연스러운 시간 흐름과 전환

## 출력 파일

- `{Output Dir}/05-deepen-best-path.md` — 메인 소설
- 8000자 초과 시 `05-deepen-best-path-part2.md`로 분할
- `tree-index.json`의 `best_path` 필드를 경로 배열로 업데이트
- `run-state.json`의 `phase`를 `"report"`로 업데이트

## 이미지 생성 (조건부)

소설 작성 후, `{Output Dir}/scenario.json`을 읽고 `image_generation` 필드를 확인하세요.

`image_generation.enabled`가 `true`이면:

1. **에이전트 프롬프트 읽기**: 아래 경로에서 scene-illustrator 프롬프트를 읽으세요
   - `agents/scene-illustrator.md` (Output Dir 기준이 아닌, 프로젝트 루트의 agents/ 디렉토리)

2. **Agent 호출**: scene-illustrator 에이전트를 호출하여 이미지를 생성하세요
   - 소설 텍스트(05-deepen-best-path.md), 캐릭터 프로필, best path 노드 정보를 함께 전달
   - scenario.json의 image_generation 설정(provider, model, quality)을 전달
   - 각 챕터마다 핵심 장면 1개의 이미지를 생성
   - 이미지는 해당 노드의 `images/` 폴더에 저장: `{Output Dir}/{node_path}/images/scene-XX-{slug}.png`

3. **실패 처리**: 이미지 생성이 실패해도 소설 자체는 유지. 실패한 장면만 스킵.

`image_generation.enabled`가 `false`이거나 필드가 없으면 이 단계를 건너뛰세요.

## 메타데이터 리포트

소설 작성 후 `{Output Dir}/07-best-path-metadata.md`를 작성:

```markdown
# 시뮬레이션 메타데이터

## 1. 시뮬레이션 개요
- 총 노드 수, expanded/pruned 수, 최대 도달 depth
- 평균/최고 composite score

## 2. 최우수 경로
- 경로: N001 → ... → {leaf}
- 각 노드의 제목과 점수

## 3. 에이전트 프로필 요약
- 주요 캐릭터들의 역할과 행동 패턴

## 4. 복선 추적
- 배치된 복선과 회수 여부

## 5. 생성된 이미지 (이미지 생성 시에만)
- 총 이미지 수
- 각 이미지: 챕터, 노드, 파일명, 프롬프트 요약
- 사용 모델 및 추정 비용
```
