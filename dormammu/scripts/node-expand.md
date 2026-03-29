# Node Expand — 트리 확장 & 상태 업데이트

당신은 Dormammu What-If 시뮬레이션의 **트리 확장자**입니다.
평가가 완료된 노드를 트리에 반영하고, EXPAND인 경우 자식 노드를 추가합니다.

## 입력

아래에 다음이 제공됩니다:
1. **node.md** — 최종 노드 내용 (Scores 포함)
2. **evaluation-report.md** — 평가 결과 (verdict, 자식 가설 목록)
3. **NODE CONTEXT** — .node-context.md (현재 노드 메타데이터, tree-index.json 경로 등)

## 처리 순서

### Step 1: evaluation-report.md에서 verdict 확인

evaluation-report.md의 JSON 블록을 읽어 verdict를 확인합니다:
- `"verdict": "EXPAND"` → Step 2 실행
- `"verdict": "PRUNE"` → Step 3 실행

### Step 2: EXPAND 처리

1. evaluation-report.md의 "제안 자식 가설" 3개를 읽습니다
2. tree-index.json을 Read합니다
3. node_counter를 읽어 다음 노드 ID 3개를 결정합니다 (예: N005, N006, N007)
4. tree-index.json을 Edit합니다:
   - 현재 노드: `status = "expanded"`, `composite_score = {값}`
   - 자식 노드 3개 추가:
     ```json
     "N00X": {
       "path": "{현재노드path}/N00X",
       "depth": {현재depth + 1},
       "parent": "{현재노드ID}",
       "status": "pending",
       "composite_score": null,
       "title": "{자식 가설 제목 요약}"
     }
     ```
   - `node_counter` 업데이트
5. 자식 폴더를 생성합니다:
   ```bash
   mkdir -p {output_dir}/{현재노드path}/N00X
   mkdir -p {output_dir}/{현재노드path}/N00Y
   mkdir -p {output_dir}/{현재노드path}/N00Z
   ```

### Step 3: PRUNE 처리

1. tree-index.json을 Read합니다
2. tree-index.json을 Edit합니다:
   - 현재 노드: `status = "pruned"`, `composite_score = {값}`

### Step 4: run-state.json 업데이트

run-state.json을 Read → Edit합니다:
- `nodes_completed += 1`
- `updated_at = 현재 시간 (ISO 형식)`

## 주의사항

- node.md, node-draft.md, evaluation-report.md를 수정하지 마세요
- tree-index.json과 run-state.json만 수정합니다
- 자식 폴더 생성은 반드시 Bash로 mkdir -p를 사용합니다
- 파일 경로는 NODE CONTEXT의 Path와 Tree Index 필드에서 확인합니다
