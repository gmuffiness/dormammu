#!/bin/bash
# test-heartbeat.sh — Heartbeat 자동 deepen 전환 테스트
# 가짜 시뮬레이션 데이터를 생성하고 --max-time 0으로 즉시 heartbeat를 트리거합니다.
#
# Usage: ./scripts/test-heartbeat.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
TEST_SIM_ID="test-heartbeat-$(date +%s)"
OUTPUT_DIR="$WORKSPACE_DIR/.dormammu/output/$TEST_SIM_ID"

echo "══════════════════════════════════════════════"
echo "  Heartbeat Test"
echo "══════════════════════════════════════════════"
echo "  SIM_ID: $TEST_SIM_ID"
echo "  Output: $OUTPUT_DIR"
echo ""

# ── 1. 가짜 시뮬레이션 디렉토리 구조 생성 ──
echo "→ Creating fake simulation data..."

mkdir -p "$OUTPUT_DIR/N001/N002"
mkdir -p "$OUTPUT_DIR/N001/N003"
mkdir -p "$OUTPUT_DIR/N001/N004"
mkdir -p "$OUTPUT_DIR/artifacts"
mkdir -p "$OUTPUT_DIR/characters"

# active-sim-id 백업 & 설정
mkdir -p "$WORKSPACE_DIR/.dormammu"
ACTIVE_SIM_BAK=""
if [ -f "$WORKSPACE_DIR/.dormammu/active-sim-id" ]; then
  ACTIVE_SIM_BAK=$(cat "$WORKSPACE_DIR/.dormammu/active-sim-id")
fi
echo "$TEST_SIM_ID" > "$WORKSPACE_DIR/.dormammu/active-sim-id"

# run-state.json
cat > "$OUTPUT_DIR/run-state.json" << 'EOF'
{
  "phase": "dfs",
  "nodes_completed": 3,
  "updated_at": "2026-03-29T00:00:00Z",
  "dfs_engine": "claude",
  "current_activity": {
    "phase": "dfs",
    "detail": "test",
    "node_id": null,
    "progress": "3/5"
  }
}
EOF

# tree-index.json — 3개 완료(expanded/pruned) + 1개 pending
cat > "$OUTPUT_DIR/tree-index.json" << 'EOF'
{
  "node_counter": 5,
  "nodes": {
    "N001": {
      "path": "N001",
      "depth": 1,
      "parent": null,
      "status": "expanded",
      "composite_score": 0.72,
      "title": "루트: 엘빈 생존"
    },
    "N002": {
      "path": "N001/N002",
      "depth": 2,
      "parent": "N001",
      "status": "expanded",
      "composite_score": 0.85,
      "title": "지하실의 진실"
    },
    "N003": {
      "path": "N001/N003",
      "depth": 2,
      "parent": "N001",
      "status": "pruned",
      "composite_score": 0.25,
      "title": "권력 투쟁"
    },
    "N004": {
      "path": "N001/N004",
      "depth": 2,
      "parent": "N001",
      "status": "pending",
      "composite_score": null,
      "title": "마레의 그림자"
    }
  }
}
EOF

# 가짜 node.md 파일들
for node in N001 N001/N002 N001/N003; do
  cat > "$OUTPUT_DIR/$node/node.md" << EOF
# Node

## Hypothesis
테스트 가설

## Key Events
1. 테스트 이벤트

## Summary
테스트 요약입니다. 이것은 heartbeat 테스트를 위한 더미 데이터입니다.
EOF
done

# 가짜 world-rules, scenario
cat > "$OUTPUT_DIR/02-world-rules.md" << 'EOF'
# World Rules
## 2. 불변 규칙
- 테스트 규칙
EOF

cat > "$OUTPUT_DIR/scenario.json" << 'EOF'
{"exploration_style": "best_first"}
EOF

# node-generate.md 존재 확인용 (실제 실행되진 않음)
echo "→ Fake data created."
echo ""

# ── 2. deepen 프롬프트를 임시 이동 (claude -p 실행 방지) ──
DEEPEN_FILE="$SCRIPT_DIR/deepen-best-path.md"
DEEPEN_BAK="${DEEPEN_FILE}.test-bak"
if [ -f "$DEEPEN_FILE" ]; then
  mv "$DEEPEN_FILE" "$DEEPEN_BAK"
  echo "→ Temporarily moved deepen-best-path.md (prevents claude -p call)"
fi

# ── 3. --max-time 0 으로 실행 (즉시 heartbeat 트리거) ──
echo "→ Running dormammu-dfs.sh with --max-time 0 ..."
echo "  (pending 노드 1개 존재 → heartbeat가 deepen으로 넘겨야 함)"
echo ""

OUTPUT=$("$SCRIPT_DIR/dormammu-dfs.sh" \
  --max-time 0 \
  --min-nodes 999 \
  --max-depth 5 \
  --workspace "$WORKSPACE_DIR" \
  2>&1) || true

# deepen 프롬프트 복원
if [ -f "$DEEPEN_BAK" ]; then
  mv "$DEEPEN_BAK" "$DEEPEN_FILE"
  echo "→ Restored deepen-best-path.md"
fi

echo "$OUTPUT"
echo ""

# ── 3. 결과 검증 ──
echo "══════════════════════════════════════════════"
echo "  Test Results"
echo "══════════════════════════════════════════════"

PASS=true

# heartbeat 메시지가 출력되었는지
if echo "$OUTPUT" | grep -q "HEARTBEAT"; then
  echo "  ✓ HEARTBEAT triggered"
else
  echo "  ✗ HEARTBEAT not triggered"
  PASS=false
fi

# best node가 N002 (최고 점수 0.85)인지
if echo "$OUTPUT" | grep -q "N002"; then
  echo "  ✓ Best node selected: N002 (score 0.85)"
else
  echo "  ✗ Best node N002 not selected"
  PASS=false
fi

# Deepen 단계로 넘어갔는지
if echo "$OUTPUT" | grep -q "Phase 6: Deepen"; then
  echo "  ✓ Proceeded to Deepen phase"
else
  echo "  ✗ Did not proceed to Deepen phase"
  PASS=false
fi

# progress 파일에 heartbeat 기록이 있는지
PROGRESS_FILE="$OUTPUT_DIR/dfs-progress.txt"
if [ -f "$PROGRESS_FILE" ] && grep -q "HEARTBEAT" "$PROGRESS_FILE"; then
  echo "  ✓ HEARTBEAT logged in progress file"
else
  echo "  ✗ HEARTBEAT not logged in progress file"
  PASS=false
fi

echo ""
if [ "$PASS" = true ]; then
  echo "  ★ ALL TESTS PASSED ★"
else
  echo "  ✗ SOME TESTS FAILED"
fi

# ── 5. 정리 ──
echo ""
echo "→ Cleaning up test data..."
rm -rf "$OUTPUT_DIR"
# active-sim-id 복원
if [ -n "$ACTIVE_SIM_BAK" ]; then
  echo "$ACTIVE_SIM_BAK" > "$WORKSPACE_DIR/.dormammu/active-sim-id"
  echo "  Restored active-sim-id: $ACTIVE_SIM_BAK"
else
  rm -f "$WORKSPACE_DIR/.dormammu/active-sim-id"
fi
echo "  Done."
