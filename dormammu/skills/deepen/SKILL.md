---
name: deepen
description: "시나리오 심화 — 선택된 경로를 상세 소설로 확장"
---

# /dormammu:deepen

완료된 시뮬레이션에서 특정 경로를 선택하여 풀 길이 소설로 심화합니다.
simulate의 Phase 6만 단독으로 실행하는 것과 같습니다.

**사용법:**
```
/dormammu:deepen                    — 최고 점수 경로 자동 선택
/dormammu:deepen --node N042        — 특정 leaf 노드까지의 경로
/dormammu:deepen --sim-id <uuid>    — 특정 시뮬레이션 지정
```

---

## Instructions

1. 시뮬레이션 찾기:
   - `--sim-id` 지정되면 해당 시뮬레이션 사용
   - 아니면 `.dormammu/output/` 에서 가장 최근 시뮬레이션 선택
   - Glob `.dormammu/output/*/tree-index.json` 으로 검색

2. Read `<output_dir>/tree-index.json`

3. 경로 선택:
   - `--node` 지정: 해당 노드에서 root까지 역추적
   - 미지정: `best_path` 사용. 없으면 가장 높은 composite_score의 leaf 찾아서 경로 구성

4. 경로의 각 `node.md`를 순서대로 읽어서 전체 내러티브 수집

5. Read `${CLAUDE_PLUGIN_ROOT}/agents/novelist.md` — 소설화 서브에이전트 프롬프트

6. 추가 컨텍스트 수집:
   - Read `<output_dir>/characters/*.md` (캐릭터 프로필)
   - Read `<output_dir>/02-world-rules.md` (세계관 규칙)

7. Agent(prompt=novelist_prompt + full_path_narratives + characters + world_rules)
   - 챕터 구조, 대화/독백/서술 포함
   - 한국어 기본

8. Write `<output_dir>/05-deepen-best-path.md`
   - 8000자 초과 시 `05-deepen-best-path-part2.md`로 분할

9. `tree-index.json`의 `best_path` 필드 업데이트

10. 이미지 생성 (조건부):
    - Read `<output_dir>/scenario.json`의 `image_generation` 필드 확인
    - `image_generation.enabled`가 `true`이면:
      a. Read `${CLAUDE_PLUGIN_ROOT}/agents/scene-illustrator.md` — 삽화 생성 에이전트 프롬프트
      b. Agent(prompt=scene_illustrator_prompt + novel_text + characters + best_path_nodes + scenario)
         - 각 챕터에서 핵심 장면 1개 선정
         - provider/model에 맞는 API로 이미지 생성
         - `<output_dir>/<node_path>/images/scene-XX-{slug}.png`로 저장
      c. 이미지 생성 실패 시 스킵하고 소설은 유지
    - `image_generation.enabled`가 `false`이면 스킵

11. 결과 요약 표시:
    - 경로: N001 → N... → N<leaf>
    - 챕터 수, 총 글자 수
    - 이미지: {N}장 생성됨 (또는 "이미지 생성 비활성")
    - 파일 경로
