---
name: status
description: "시뮬레이션 진행 상황 확인"
---

# /dormammu:status

현재 시뮬레이션 진행 상황을 tree-index.json 기반으로 표시합니다.

**사용법:** `/dormammu:status`

---

## Instructions

1. sim_id 결정:
   - $ARGUMENTS가 있으면 해당 sim_id 사용
   - 없으면 `.dormammu/active-sim-id` 파일에서 읽음
   - 둘 다 없으면: "진행 중인 시뮬레이션이 없습니다." 표시 후 종료
2. Read `.dormammu/output/<sim-id>/run-state.json`
   - 없으면: "해당 시뮬레이션을 찾을 수 없습니다." 표시 후 종료

2. 기본 정보 표시:
   ```
   Topic: <topic>
   Output: .dormammu/output/<sim-id>/
   Phase: <current phase>
   Started: <started_at>
   ```

3. Read `<output_dir>/tree-index.json`
   - 없으면 Phase 1-3 진행 중이므로 산출물 존재 여부만 확인

4. 트리 통계 표시:
   ```
   Scenario Tree
   ├── Total nodes: 42
   ├── Expanded: 28
   ├── Pruned: 9
   ├── Pending: 5
   ├── Max depth: 6
   └── Best score: 0.91 (N083)
   ```

5. 트리를 간단하게 시각화 (depth 0-2만):
   ```
   N001 (0.83) ■
   ├── N002 (0.81) ■
   │   ├── N005 (0.91) ★
   │   └── N006 (0.25) ✕
   ├── N003 (0.72) ■
   └── N004 (0.68) ■
   ```
   - ■ = expanded, ★ = best path, ✕ = pruned

6. 산출물 체크리스트:
   ```
   Artifacts
   ✅ 01-background-research.md
   ✅ 02-world-rules.md
   ✅ 03-character-profiles.md (5 characters)
   ✅ Scenario tree (42 nodes)
   ⬜ 05-deepen-best-path.md
   ⬜ 07-best-path-metadata.md
   ```

7. 뷰어 안내:
   ```
   View in browser: python ${CLAUDE_PLUGIN_ROOT}/viewer/serve.py <output_dir>
   ```
