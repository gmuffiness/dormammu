---
name: research
description: "배경 리서치 — simulate의 Phase 1만 단독 실행"
---

# /dormammu:research

시뮬레이션의 Phase 1(배경 리서치)만 단독으로 실행합니다.
이미 simulate를 돌렸더라도 리서치만 다시 하고 싶을 때 사용합니다.

**사용법:** `/dormammu:research` 또는 `/dormammu:research "주제"`

---

## Instructions

1. sim_id 결정:
   - `.dormammu/active-sim-id` 파일이 있으면 해당 sim_id 사용
   - 없으면 새로 생성하고 `.dormammu/output/<sim-id>/` 디렉토리 생성
2. output_dir = `.dormammu/output/<sim-id>/`
3. Read `<output_dir>/scenario.json` — 시나리오가 있으면 topic 사용
   - 없으면 `$ARGUMENTS`에서 topic 추출
   - 둘 다 없으면 사용자에게 주제 질문

4. Read `${CLAUDE_PLUGIN_ROOT}/agents/researcher.md` — 서브에이전트 프롬프트

5. Agent(prompt=researcher_prompt + topic) 실행
   - 원작/팬덤 분석, 캐릭터, 세력, 갈등 구조, 팬 이론 등

6. 산출물 생성:
   - `<output_dir>/01-background-research.md`
   - `<output_dir>/artifacts/research.json`

7. 결과 요약을 사용자에게 표시
