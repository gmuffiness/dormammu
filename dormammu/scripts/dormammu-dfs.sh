#!/bin/bash
# dormammu-dfs.sh — Ralph-pattern DFS orchestrator with ancestor chain context
# Usage: ./scripts/dormammu-dfs.sh [--min-nodes N] [--max-iterations N] [--max-depth N] [--engine claude|codex]
#
# 핵심 설계:
# - 매 노드마다 새 claude 프로세스 = 새 컨텍스트 (컨텍스트 포화 방지)
# - bash가 게이트키퍼: MIN_NODES 미달 시 절대 Deepen 단계로 안 넘어감
# - ancestor chain + sibling summaries만 컨텍스트에 로드 (형제 다양성 보장)

set -euo pipefail

# ── 설정 ──
MIN_NODES=100
MAX_ITERATIONS=500
MAX_DEPTH=10
MAX_TIME_MIN=270  # 4시간 30분 = 270분. 초과 시 자동 deepen
MAX_TEMPLATE_RETRIES=2
MAX_OOC_REFINES=1
DFS_ENGINE=""  # run-state.json에서 읽거나 --engine으로 지정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# .dormammu/ 는 CWD 기준 상대 경로. --workspace로 오버라이드 가능.
WORKSPACE_DIR="$(pwd)"

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --min-nodes) MIN_NODES="$2"; shift 2 ;;
    --min-nodes=*) MIN_NODES="${1#*=}"; shift ;;
    --max-iterations) MAX_ITERATIONS="$2"; shift 2 ;;
    --max-iterations=*) MAX_ITERATIONS="${1#*=}"; shift ;;
    --max-depth) MAX_DEPTH="$2"; shift 2 ;;
    --max-depth=*) MAX_DEPTH="${1#*=}"; shift ;;
    --workspace) WORKSPACE_DIR="$2"; shift 2 ;;
    --workspace=*) WORKSPACE_DIR="${1#*=}"; shift ;;
    --engine) DFS_ENGINE="$2"; shift 2 ;;
    --engine=*) DFS_ENGINE="${1#*=}"; shift ;;
    --max-time) MAX_TIME_MIN="$2"; shift 2 ;;
    --max-time=*) MAX_TIME_MIN="${1#*=}"; shift ;;
    *) shift ;;
  esac
done

# ── 경로 설정 ──
ACTIVE_SIM_FILE="$WORKSPACE_DIR/.dormammu/active-sim-id"
if [ ! -f "$ACTIVE_SIM_FILE" ]; then
  echo "ERROR: active-sim-id not found. Run /dormammu:simulate first to complete Phase 0-4."
  exit 1
fi

SIM_ID=$(cat "$ACTIVE_SIM_FILE")
OUTPUT_DIR="$WORKSPACE_DIR/.dormammu/output/$SIM_ID"
RUN_STATE="$OUTPUT_DIR/run-state.json"
if [ ! -f "$RUN_STATE" ]; then
  echo "ERROR: run-state.json not found at $RUN_STATE"
  exit 1
fi
TREE_INDEX="$OUTPUT_DIR/tree-index.json"
PROGRESS_FILE="$OUTPUT_DIR/dfs-progress.txt"
CONTEXT_FILE="$OUTPUT_DIR/.node-context.md"
DEEPEN_PROMPT="$SCRIPT_DIR/deepen-best-path.md"
GENERATE_PROMPT_CHECK="$SCRIPT_DIR/node-generate.md"

if [ ! -f "$TREE_INDEX" ]; then
  echo "ERROR: tree-index.json not found at $TREE_INDEX"
  exit 1
fi

if [ ! -f "$GENERATE_PROMPT_CHECK" ]; then
  echo "ERROR: node-generate.md not found at $GENERATE_PROMPT_CHECK"
  exit 1
fi

# ── .env 로드 (.dormammu/.env 우선, 프로젝트 루트 .env 폴백) ──
if [ -f "$WORKSPACE_DIR/.dormammu/.env" ]; then
  set -a
  source "$WORKSPACE_DIR/.dormammu/.env"
  set +a
elif [ -f "$WORKSPACE_DIR/.env" ]; then
  set -a
  source "$WORKSPACE_DIR/.env"
  set +a
fi

# ── 엔진 결정 (CLI 인자 > run-state.json > 기본값) ──
if [ -z "$DFS_ENGINE" ]; then
  DFS_ENGINE=$(jq -r '.dfs_engine // "claude"' "$RUN_STATE")
fi

# ── 탐색 전략 결정 (scenario.json > 기본값) ──
SCENARIO_FILE="$OUTPUT_DIR/scenario.json"
if [ -f "$SCENARIO_FILE" ]; then
  EXPLORATION_STYLE=$(jq -r '.exploration_style // "best_first"' "$SCENARIO_FILE")
else
  EXPLORATION_STYLE="best_first"
fi
echo "Exploration: $EXPLORATION_STYLE"

# codex 엔진 검증
if [ "$DFS_ENGINE" == "codex" ]; then
  if ! command -v codex &>/dev/null; then
    echo "⚠ codex CLI not found. Falling back to claude."
    echo "  Install: npm install -g @openai/codex"
    DFS_ENGINE="claude"
  else
    # codex CLI는 ~/.codex/auth.json의 키를 우선 사용 (환경변수보다 높은 우선순위).
    # auth.json이 없으면 OPENAI_API_KEY 환경변수를 사용.
    CODEX_AUTH="$HOME/.codex/auth.json"
    if [ -f "$CODEX_AUTH" ]; then
      CODEX_KEY=$(jq -r '.OPENAI_API_KEY // empty' "$CODEX_AUTH" 2>/dev/null)
      if [ -z "$CODEX_KEY" ]; then
        echo "⚠ ~/.codex/auth.json exists but has no OPENAI_API_KEY. Falling back to claude."
        echo "  Run: codex auth   (또는 직접 ~/.codex/auth.json에 키를 설정)"
        DFS_ENGINE="claude"
      else
        echo "  codex auth: ~/.codex/auth.json (key configured)"
      fi
    elif [ -z "${OPENAI_API_KEY:-}" ]; then
      echo "⚠ OPENAI_API_KEY not set and ~/.codex/auth.json not found. Falling back to claude."
      echo "  설정 방법: codex auth  또는  echo '{\"auth_mode\":\"apikey\",\"OPENAI_API_KEY\":\"sk-...\"}' > ~/.codex/auth.json"
      DFS_ENGINE="claude"
    else
      echo "  codex auth: OPENAI_API_KEY env var (key configured)"
    fi
  fi
fi

# ── 엔진별 실행 함수 ──
run_engine() {
  local prompt="$1"
  local allowed_tools="${2:-Read,Write,Edit,Bash,Agent}"
  local max_turns="${3:-40}"

  if [ "$DFS_ENGINE" == "codex" ]; then
    codex exec --full-auto \
      --json \
      "$prompt" \
      2>/dev/null
  else
    claude -p "$prompt" \
      --allowedTools "$allowed_tools" \
      --output-format json \
      --max-turns "$max_turns" \
      2>/dev/null
  fi
}

# 검증용 (Read만 허용, 적은 턴)
run_engine_validate() {
  local prompt="$1"

  if [ "$DFS_ENGINE" == "codex" ]; then
    codex exec --sandbox read-only \
      --json \
      "$prompt" \
      2>/dev/null
  else
    claude -p "$prompt" \
      --allowedTools "Read" \
      --output-format json \
      --max-turns 5 \
      2>/dev/null
  fi
}

# refine용 (Read,Write,Edit 허용)
run_engine_refine() {
  local prompt="$1"

  if [ "$DFS_ENGINE" == "codex" ]; then
    codex exec --full-auto \
      --json \
      "$prompt" \
      2>/dev/null
  else
    claude -p "$prompt" \
      --allowedTools "Read,Write,Edit" \
      --output-format json \
      --max-turns 15 \
      2>/dev/null
  fi
}

echo "══════════════════════════════════════════════"
echo "  Dormammu DFS Orchestrator"
echo "══════════════════════════════════════════════"
echo "  SIM_ID:         $SIM_ID"
echo "  ENGINE:         $DFS_ENGINE"
echo "  MIN_NODES:      $MIN_NODES"
echo "  MAX_DEPTH:      $MAX_DEPTH"
echo "  MAX_TIME:       ${MAX_TIME_MIN}m ($(( MAX_TIME_MIN / 60 ))h $(( MAX_TIME_MIN % 60 ))m)"
echo "  MAX_ITERATIONS: $MAX_ITERATIONS"
echo "  Output:         $OUTPUT_DIR"
echo "══════════════════════════════════════════════"

# ── progress 초기화 ──
if [ ! -f "$PROGRESS_FILE" ]; then
  cat > "$PROGRESS_FILE" << EOF
# Dormammu DFS Progress
Started: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Config: min_nodes=$MIN_NODES, max_depth=$MAX_DEPTH
---
EOF
fi

# ── build_ancestor_context: ancestor chain + sibling summaries ──
build_node_context() {
  local node_id=$1
  local ctx="$CONTEXT_FILE"

  # ── Header ──
  cat > "$ctx" << 'CTXHEADER'
# Node Context (Auto-generated by dormammu-dfs.sh)

이 파일은 현재 노드 처리에 필요한 컨텍스트만 포함합니다:
1. **World Rules 요약** — 불변 규칙
2. **Ancestor Chain** — root에서 parent까지의 내러티브 흐름
3. **Sibling Summaries** — 같은 부모의 이미 처리된 형제 노드들 (다양성 확보용)
4. **Current Node** — 처리할 노드의 가설

형제 요약은 "이미 다뤄진 방향"을 보여줍니다. 현재 노드는 이들과 **다른 방향**으로 전개해야 합니다.
CTXHEADER

  # ── 1. World Rules Summary ──
  echo -e "\n---\n## World Rules Summary\n" >> "$ctx"
  local world_rules_file="$OUTPUT_DIR/artifacts/world-rules.json"
  if [ -f "$world_rules_file" ]; then
    # JSON이면 요약 추출
    jq -r 'if type == "object" then
      (.invariant_rules // [])[:5] | .[] |
      "- **" + (.name // .rule_name // "Rule") + "**: " + (.summary // .description // "")
    else empty end' "$world_rules_file" 2>/dev/null >> "$ctx" || true
  fi
  # 마크다운 world-rules에서 불변 규칙 섹션만 추출
  local world_rules_md="$OUTPUT_DIR/02-world-rules.md"
  if [ -f "$world_rules_md" ]; then
    echo -e "\n### 주요 불변 규칙 (원문 발췌)\n" >> "$ctx"
    awk '/^## 2\. 불변 규칙/{p=1} p{print} /^## 3\./ && p{exit}' "$world_rules_md" | head -80 >> "$ctx"
  fi

  # ── 2. Ancestor Chain (root → parent) ──
  echo -e "\n---\n## Ancestor Chain\n" >> "$ctx"
  echo "root에서 현재 노드의 parent까지의 내러티브 흐름입니다." >> "$ctx"

  # Build chain: walk from node to root
  local chain=()
  local current="$node_id"
  while true; do
    local parent=$(jq -r ".nodes[\"$current\"].parent // \"null\"" "$TREE_INDEX")
    if [ "$parent" == "null" ] || [ -z "$parent" ]; then
      break
    fi
    if [ ${#chain[@]} -eq 0 ]; then
      chain=("$parent")
    else
      chain=("$parent" "${chain[@]}")
    fi
    current="$parent"
  done

  if [ ${#chain[@]} -eq 0 ]; then
    echo -e "\n(Root 노드의 직접 자식 — ancestor chain 없음)\n" >> "$ctx"
  fi

  for ancestor_id in ${chain[@]+"${chain[@]}"}; do
    local a_path=$(jq -r ".nodes[\"$ancestor_id\"].path" "$TREE_INDEX")
    local a_title=$(jq -r ".nodes[\"$ancestor_id\"].title // \"\"" "$TREE_INDEX")
    local a_depth=$(jq -r ".nodes[\"$ancestor_id\"].depth" "$TREE_INDEX")
    local a_score=$(jq -r ".nodes[\"$ancestor_id\"].composite_score // \"N/A\"" "$TREE_INDEX")
    local a_file="$OUTPUT_DIR/$a_path/node.md"

    echo -e "\n### $ancestor_id (depth $a_depth, score $a_score) — $a_title\n" >> "$ctx"

    if [ -f "$a_file" ]; then
      # Hypothesis 섹션
      awk '/^## Hypothesis/{p=1} p{print} /^## [^H]/ && p{exit}' "$a_file" | head -20 >> "$ctx"
      # Key Events 섹션
      echo "" >> "$ctx"
      awk '/^## Key Events/{p=1} p{print} /^## [^K]/ && p{exit}' "$a_file" | head -30 >> "$ctx"
      # Summary (전개 요약)
      echo -e "\n**Summary:**\n" >> "$ctx"
      awk '/^## Summary/{p=1; next} /^## / && p{exit} p{print}' "$a_file" | head -20 >> "$ctx"
    else
      echo "(node.md 없음)" >> "$ctx"
    fi
  done

  # ── 3. Sibling Summaries (같은 parent의 이미 처리된 형제들) ──
  echo -e "\n---\n## Sibling Summaries (이미 처리된 형제 노드들)\n" >> "$ctx"
  echo "같은 부모 아래 이미 탐색된 형제들입니다. 현재 노드는 이들과 **다른 방향**으로 전개하세요." >> "$ctx"

  local my_parent=$(jq -r ".nodes[\"$node_id\"].parent // \"null\"" "$TREE_INDEX")

  if [ "$my_parent" != "null" ] && [ -n "$my_parent" ]; then
    # 같은 parent를 가진 노드 중 현재 노드 제외, status != "pending"인 것들
    local siblings=$(jq -r --arg parent "$my_parent" --arg me "$node_id" '
      [.nodes | to_entries[] |
       select(.value.parent == $parent and .key != $me and .value.status != "pending")]
      | .[].key
    ' "$TREE_INDEX" 2>/dev/null)

    if [ -z "$siblings" ]; then
      echo -e "\n(처리된 형제 노드 없음 — 첫 번째 형제입니다)\n" >> "$ctx"
    else
      for sib_id in $siblings; do
        local s_title=$(jq -r ".nodes[\"$sib_id\"].title // \"\"" "$TREE_INDEX")
        local s_status=$(jq -r ".nodes[\"$sib_id\"].status" "$TREE_INDEX")
        local s_score=$(jq -r ".nodes[\"$sib_id\"].composite_score // \"N/A\"" "$TREE_INDEX")
        local s_path=$(jq -r ".nodes[\"$sib_id\"].path" "$TREE_INDEX")
        local s_file="$OUTPUT_DIR/$s_path/node.md"

        echo -e "\n### $sib_id ($s_status, score $s_score) — $s_title\n" >> "$ctx"

        if [ -f "$s_file" ]; then
          # Hypothesis만 (간결하게)
          awk '/^## Hypothesis/{p=1; next} /^## / && p{exit} p{print}' "$s_file" | head -10 >> "$ctx"
          # Key Events만 (요약)
          echo -e "\n**Key Events:**" >> "$ctx"
          awk '/^## Key Events/{p=1; next} /^## / && p{exit} p{print}' "$s_file" | head -15 >> "$ctx"
        fi

        echo -e "\n> **이 방향은 이미 탐색됨. 다른 방향으로 전개하세요.**\n" >> "$ctx"
      done
    fi
  else
    echo -e "\n(Root 노드 — 형제 없음)\n" >> "$ctx"
  fi

  # ── 4. Current Node ──
  echo -e "\n---\n## Current Node: $node_id\n" >> "$ctx"
  local my_title=$(jq -r ".nodes[\"$node_id\"].title // \"\"" "$TREE_INDEX")
  local my_depth=$(jq -r ".nodes[\"$node_id\"].depth" "$TREE_INDEX")
  echo "- **Title:** $my_title" >> "$ctx"
  echo "- **Depth:** $my_depth" >> "$ctx"
  echo "- **Max Depth:** $MAX_DEPTH" >> "$ctx"
  local my_path=$(jq -r ".nodes[\"$node_id\"].path" "$TREE_INDEX")
  echo "- **Path:** $OUTPUT_DIR/$my_path/" >> "$ctx"
  echo "- **Tree Index:** $TREE_INDEX" >> "$ctx"
  echo "- **Run State:** $RUN_STATE" >> "$ctx"
}

# ── 연속 실패 카운터 ──
CONSECUTIVE_FAILURES=0
MAX_CONSECUTIVE_FAILURES=5

# ── 누적 통계 ──
TOTAL_COST_USD=0
TOTAL_INPUT_TOKENS=0
TOTAL_OUTPUT_TOKENS=0
TOTAL_NODE_CHARS=0

# ── 메인 루프 ──
START_TIME=$(date +%s)

for i in $(seq 1 $MAX_ITERATIONS); do

  # ── 1. 상태 체크 ──
  COMPLETED=$(jq '.nodes_completed' "$RUN_STATE")
  PENDING=$(jq '[.nodes | to_entries[] | select(.value.status == "pending")] | length' "$TREE_INDEX")
  TOTAL=$(jq '.nodes | length' "$TREE_INDEX")
  EXPANDED=$(jq '[.nodes | to_entries[] | select(.value.status == "expanded")] | length' "$TREE_INDEX")
  PRUNED=$(jq '[.nodes | to_entries[] | select(.value.status == "pruned")] | length' "$TREE_INDEX")
  ELAPSED=$(( $(date +%s) - START_TIME ))
  ELAPSED_MIN=$(( ELAPSED / 60 ))

  echo ""
  echo "── Iteration $i/$MAX_ITERATIONS | ${ELAPSED_MIN}m elapsed ──"
  echo "   Completed: $COMPLETED/$MIN_NODES | Pending: $PENDING | Total: $TOTAL (expanded: $EXPANDED, pruned: $PRUNED)"

  # ── 2. 종료 조건 (bash 게이트키퍼) ──
  if [ "$PENDING" -eq 0 ]; then
    if [ "$COMPLETED" -ge "$MIN_NODES" ]; then
      echo "✓ MIN_NODES ($MIN_NODES) reached with no pending nodes. Proceeding to Deepen."
      break
    else
      echo "⚠ Tree exhausted at $COMPLETED nodes (min: $MIN_NODES)."
      echo "  Pruning was too aggressive or max_depth too shallow."
      echo "  Consider: --max-depth $(( MAX_DEPTH + 2 )) or lowering prune threshold."
      # Don't exit — proceed to deepen with what we have if we have enough
      if [ "$COMPLETED" -ge $(( MIN_NODES / 2 )) ]; then
        echo "  Proceeding with $COMPLETED nodes (>50% of min)."
        break
      fi
      exit 1
    fi
  fi

  if [ "$COMPLETED" -ge "$MIN_NODES" ]; then
    echo "✓ MIN_NODES ($MIN_NODES) reached. Proceeding to Deepen."
    break
  fi

  if [ "$CONSECUTIVE_FAILURES" -ge "$MAX_CONSECUTIVE_FAILURES" ]; then
    echo "✗ $MAX_CONSECUTIVE_FAILURES consecutive failures. Pausing."
    echo "  Last state saved. Resume with: ./scripts/dormammu-dfs.sh"
    exit 1
  fi

  # ── 2b. 시간 초과 Heartbeat: MAX_TIME 도달 시 자동 Deepen ──
  MAX_TIME_SEC=$(( MAX_TIME_MIN * 60 ))
  if [ "$ELAPSED" -ge "$MAX_TIME_SEC" ]; then
    echo ""
    echo "⏰ HEARTBEAT: ${ELAPSED_MIN}m elapsed >= MAX_TIME ${MAX_TIME_MIN}m"
    echo "  Selecting best scored node and proceeding to Deepen..."

    # 최고 점수 노드 선택 (expanded/pruned 중)
    HEARTBEAT_BEST=$(jq -r '
      [.nodes | to_entries[] |
       select(.value.status == "expanded" or .value.status == "pruned") |
       select(.value.composite_score != null)]
      | sort_by(-.value.composite_score)
      | .[0].key // "NONE"
    ' "$TREE_INDEX")

    if [ "$HEARTBEAT_BEST" != "NONE" ]; then
      HEARTBEAT_SCORE=$(jq -r ".nodes[\"$HEARTBEAT_BEST\"].composite_score // \"N/A\"" "$TREE_INDEX")
      echo "  Best node: $HEARTBEAT_BEST (score: $HEARTBEAT_SCORE)"
      echo "## $(date +%H:%M:%S) — HEARTBEAT: time limit (${ELAPSED_MIN}m >= ${MAX_TIME_MIN}m) → auto-deepen from $HEARTBEAT_BEST" >> "$PROGRESS_FILE"
      break
    else
      echo "  ⚠ No scored nodes found yet. Continuing DFS..."
    fi
  fi

  # ── 3. 다음 노드 선택 (탐색 전략에 따라) ──
  if [ "$EXPLORATION_STYLE" == "dfs" ]; then
    # DFS: 깊은 노드 우선
    NEXT_NODE=$(jq -r '
      [.nodes | to_entries[] | select(.value.status == "pending")]
      | sort_by(-.value.depth, .key)
      | .[0].key // "NONE"
    ' "$TREE_INDEX")
  elif [ "$EXPLORATION_STYLE" == "bfs" ]; then
    # BFS: 얕은 노드 우선
    NEXT_NODE=$(jq -r '
      [.nodes | to_entries[] | select(.value.status == "pending")]
      | sort_by(.value.depth, .key)
      | .[0].key // "NONE"
    ' "$TREE_INDEX")
  else
    # Best-First (기본): 부모 점수 높은 노드 우선
    NEXT_NODE=$(jq -r '
      . as $root |
      [.nodes | to_entries[] | select(.value.status == "pending")
       | { key, parent_score: (
           if .value.parent then ($root.nodes[.value.parent].composite_score // 0) else 0 end
         )}]
      | sort_by(-.parent_score, .key)
      | .[0].key // "NONE"
    ' "$TREE_INDEX")
  fi

  if [ "$NEXT_NODE" == "NONE" ]; then
    echo "  No pending nodes found (race condition?). Retrying..."
    sleep 1
    continue
  fi

  NEXT_DEPTH=$(jq -r ".nodes[\"$NEXT_NODE\"].depth" "$TREE_INDEX")
  NEXT_TITLE=$(jq -r ".nodes[\"$NEXT_NODE\"].title // \"untitled\"" "$TREE_INDEX")

  echo "→ $NEXT_NODE (depth $NEXT_DEPTH) — $NEXT_TITLE"
  NODE_START_TIME=$(date +%s)

  # ── 3.5. current_activity 업데이트 (viewer 폴링용) ──
  jq --arg phase "dfs" \
     --arg detail "노드 $NEXT_NODE 처리 중 — $NEXT_TITLE" \
     --arg node_id "$NEXT_NODE" \
     --arg progress "$COMPLETED/$MIN_NODES" \
     '.current_activity = {phase: $phase, detail: $detail, node_id: $node_id, progress: $progress} | .updated_at = now | .updated_at = (now | todate)' \
     "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

  # ── 4. 컨텍스트 조립 (ancestor chain + sibling summaries) ──
  build_node_context "$NEXT_NODE"
  CTX_SIZE=$(wc -c < "$CONTEXT_FILE" | tr -d ' ')
  echo "  Context: ${CTX_SIZE} bytes (ancestor chain + siblings)"

  # ── 5. Characters 로드 ──
  CHARACTERS_FILE="$OUTPUT_DIR/artifacts/characters.json"
  CHARACTERS_CONTENT=""
  if [ -f "$CHARACTERS_FILE" ]; then
    CHARACTERS_CONTENT=$(cat "$CHARACTERS_FILE")
  fi

  # ── 6. 새 5단계 파이프라인 ──
  GENERATE_PROMPT="$SCRIPT_DIR/node-generate.md"
  EVALUATE_PROMPT="$SCRIPT_DIR/node-evaluate.md"
  EXPAND_PROMPT="$SCRIPT_DIR/node-expand.md"
  REFINE_PROMPT="$SCRIPT_DIR/validators/refine-node.md"

  NEXT_PATH=$(jq -r ".nodes[\"$NEXT_NODE\"].path" "$TREE_INDEX")
  NODE_DRAFT_FILE="$OUTPUT_DIR/$NEXT_PATH/node-draft.md"
  NODE_MD_FILE="$OUTPUT_DIR/$NEXT_PATH/node.md"
  EVAL_REPORT_FILE="$OUTPUT_DIR/$NEXT_PATH/evaluation-report.md"

  CONTEXT_CONTENT=$(cat "$CONTEXT_FILE")
  NODE_COST="0"
  NODE_INPUT_TOKENS="0"
  NODE_OUTPUT_TOKENS="0"
  NODE_TURNS="0"
  VALIDATION_RESULT="pass"
  OOC_PENALTY="0"
  TEMPLATE_RETRY_COUNT=0
  OOC_REFINE_COUNT=0

  # ── 파이프라인 비용 누적 헬퍼 ──
  accumulate_cost() {
    local output="$1"
    local cost input_tok output_tok turns
    if [ "$DFS_ENGINE" == "codex" ]; then
      local last_json
      last_json=$(echo "$output" | grep -E '^\{' | tail -1)
      cost="0"
      input_tok=$(echo "$last_json" | jq -r '.usage.input_tokens // 0' 2>/dev/null | head -1 || echo "0")
      output_tok=$(echo "$last_json" | jq -r '.usage.output_tokens // 0' 2>/dev/null | head -1 || echo "0")
      turns="1"
    else
      cost=$(echo "$output" | jq -r '.total_cost_usd // 0' 2>/dev/null | head -1 || echo "0")
      input_tok=$(echo "$output" | jq -r '(.usage.cache_creation_input_tokens // 0) + (.usage.cache_read_input_tokens // 0) + (.usage.input_tokens // 0)' 2>/dev/null | head -1 || echo "0")
      output_tok=$(echo "$output" | jq -r '.usage.output_tokens // 0' 2>/dev/null | head -1 || echo "0")
      turns=$(echo "$output" | jq -r '.num_turns // 0' 2>/dev/null | head -1 || echo "0")
    fi
    cost=$(echo "$cost" | tr -cd '0-9.' | head -c 20); : "${cost:=0}"
    input_tok=$(echo "$input_tok" | tr -cd '0-9' | head -c 20); : "${input_tok:=0}"
    output_tok=$(echo "$output_tok" | tr -cd '0-9' | head -c 20); : "${output_tok:=0}"
    TOTAL_COST_USD=$(echo "$TOTAL_COST_USD $cost" | awk '{printf "%.4f", $1 + $2}')
    NODE_COST=$(echo "$NODE_COST $cost" | awk '{printf "%.4f", $1 + $2}')
    NODE_INPUT_TOKENS=$(( NODE_INPUT_TOKENS + input_tok ))
    NODE_OUTPUT_TOKENS=$(( NODE_OUTPUT_TOKENS + output_tok ))
    NODE_TURNS=$(( NODE_TURNS + turns ))
  }

  # ── ① Generate ──
  echo "  → [1/5] Generate..."
  jq --arg detail "노드 $NEXT_NODE 내러티브 생성 중" \
     '.current_activity.detail = $detail' \
     "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

  GEN_FULL_PROMPT="$(cat "$GENERATE_PROMPT")

---
# NODE CONTEXT
${CONTEXT_CONTENT}

---
# CHARACTERS
${CHARACTERS_CONTENT}
"
  GEN_OUTPUT=$(run_engine "$GEN_FULL_PROMPT") || true
  accumulate_cost "$GEN_OUTPUT"

  # ── ② Validate (bash 직접 — claude 호출 없음) ──
  echo "  → [2/5] Template validation..."
  while [ "$TEMPLATE_RETRY_COUNT" -le "$MAX_TEMPLATE_RETRIES" ]; do
    TEMPLATE_ERRORS=""
    [ -f "$NODE_DRAFT_FILE" ] || TEMPLATE_ERRORS="${TEMPLATE_ERRORS}file_missing "
    if [ -f "$NODE_DRAFT_FILE" ]; then
      grep -q "^## Hypothesis" "$NODE_DRAFT_FILE" || TEMPLATE_ERRORS="${TEMPLATE_ERRORS}Hypothesis "
      grep -q "^## Key Events" "$NODE_DRAFT_FILE" || TEMPLATE_ERRORS="${TEMPLATE_ERRORS}KeyEvents "
      grep -q "^## Summary" "$NODE_DRAFT_FILE" || TEMPLATE_ERRORS="${TEMPLATE_ERRORS}Summary "
      SUMMARY_CHARS=$(awk '/^## Summary/,0' "$NODE_DRAFT_FILE" | wc -m | tr -d ' ')
      [ "$SUMMARY_CHARS" -gt 300 ] || TEMPLATE_ERRORS="${TEMPLATE_ERRORS}SummaryTooShort "
    fi

    if [ -z "$TEMPLATE_ERRORS" ]; then
      echo "  ✓ Template check passed"
      break
    fi

    if [ "$TEMPLATE_RETRY_COUNT" -ge "$MAX_TEMPLATE_RETRIES" ]; then
      echo "  ✗ Template check failed after $MAX_TEMPLATE_RETRIES retries: [${TEMPLATE_ERRORS}]"
      VALIDATION_RESULT="template_fail"
      break
    fi

    TEMPLATE_RETRY_COUNT=$((TEMPLATE_RETRY_COUNT + 1))
    echo "  ⚠ Template check failed: [${TEMPLATE_ERRORS}] → retry $TEMPLATE_RETRY_COUNT/$MAX_TEMPLATE_RETRIES"

    jq --arg detail "노드 $NEXT_NODE 템플릿 재생성 중 (retry $TEMPLATE_RETRY_COUNT)" \
       '.current_activity.detail = $detail' \
       "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

    RETRY_GEN_PROMPT="$(cat "$GENERATE_PROMPT")

---
# NODE CONTEXT
${CONTEXT_CONTENT}

---
# CHARACTERS
${CHARACTERS_CONTENT}

---
# RETRY INSTRUCTION
이전 생성에서 다음 필수 섹션이 누락되었거나 기준 미달입니다: [${TEMPLATE_ERRORS}]
반드시 모든 필수 섹션(Hypothesis, Key Events, Summary)을 포함하고, Summary는 500~800자로 작성하세요.
node-draft.md로 저장하세요 (node.md가 아님).
"
    RETRY_OUTPUT=$(run_engine "$RETRY_GEN_PROMPT") || true
    accumulate_cost "$RETRY_OUTPUT"
  done

  if [ "$VALIDATION_RESULT" == "template_fail" ]; then
    NODE_END_TIME=$(date +%s)
    NODE_DURATION=$(( NODE_END_TIME - NODE_START_TIME ))
    NODE_DURATION_MIN=$(( NODE_DURATION / 60 ))
    NODE_DURATION_SEC=$(( NODE_DURATION % 60 ))
    echo "  ✗ Node $NEXT_NODE template failed. [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s] (failure $((CONSECUTIVE_FAILURES + 1))/$MAX_CONSECUTIVE_FAILURES)"
    CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
    echo "## $(date +%H:%M:%S) — $NEXT_NODE FAILED (template) [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s]" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
    continue
  fi

  # ── ③ Evaluate ──
  echo "  → [3/5] Evaluate..."
  jq --arg detail "노드 $NEXT_NODE 평가 중 (OOC + 메트릭)" \
     '.current_activity.detail = $detail' \
     "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

  # 캐릭터 파일들 로드 (개별 .md)
  CHARACTERS_MD_CONTENT=""
  CHARS_DIR="$OUTPUT_DIR/characters"
  if [ -d "$CHARS_DIR" ]; then
    for char_file in "$CHARS_DIR"/*.md; do
      [ -f "$char_file" ] && CHARACTERS_MD_CONTENT="${CHARACTERS_MD_CONTENT}
$(cat "$char_file")"
    done
  fi

  EVAL_FULL_PROMPT="$(cat "$EVALUATE_PROMPT")

---
# node-draft.md
$(cat "$NODE_DRAFT_FILE")

---
# NODE CONTEXT
${CONTEXT_CONTENT}

---
# CHARACTER PROFILES
${CHARACTERS_MD_CONTENT:-$CHARACTERS_CONTENT}
"
  EVAL_OUTPUT=$(run_engine "$EVAL_FULL_PROMPT") || true
  accumulate_cost "$EVAL_OUTPUT"

  # evaluation-report.md에서 JSON 블록 파싱
  VERDICT="PRUNE"
  NEEDS_REFINE="false"
  EVAL_COMPOSITE="0"
  OOC_PENALTY="0"
  if [ -f "$EVAL_REPORT_FILE" ]; then
    EVAL_JSON=$(grep -A1 '```json' "$EVAL_REPORT_FILE" | tail -1 | tr -d '\n' || echo "{}")
    VERDICT=$(echo "$EVAL_JSON" | jq -r '.verdict // "PRUNE"' 2>/dev/null || echo "PRUNE")
    NEEDS_REFINE=$(echo "$EVAL_JSON" | jq -r '.needs_refine // false' 2>/dev/null || echo "false")
    EVAL_COMPOSITE=$(echo "$EVAL_JSON" | jq -r '.composite_score // 0' 2>/dev/null || echo "0")
    OOC_PENALTY=$(echo "$EVAL_JSON" | jq -r '.ooc_penalty // 0' 2>/dev/null || echo "0")
    echo "  ✓ Evaluation: composite=$EVAL_COMPOSITE verdict=$VERDICT needs_refine=$NEEDS_REFINE ooc_penalty=$OOC_PENALTY"
  else
    echo "  ⚠ evaluation-report.md not found — defaulting to PRUNE"
    VALIDATION_RESULT="eval_fail"
  fi

  # ── ④ Refine (조건부) ──
  if [ "$NEEDS_REFINE" == "true" ] && [ -f "$REFINE_PROMPT" ]; then
    OOC_REFINE_COUNT=$((OOC_REFINE_COUNT + 1))
    echo "  → [4/5] Refine (OOC violations found)..."
    jq --arg detail "노드 $NEXT_NODE OOC 수정 중" \
       '.current_activity.detail = $detail' \
       "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

    REFINE_FULL_PROMPT="$(cat "$REFINE_PROMPT")

---
# NODE_DRAFT
$(cat "$NODE_DRAFT_FILE")

---
# EVALUATION_REPORT
$(cat "$EVAL_REPORT_FILE")

---
# CHARACTER_PROFILES
${CHARACTERS_MD_CONTENT:-$CHARACTERS_CONTENT}

---
# NODE_PATH
$OUTPUT_DIR/$NEXT_PATH
"
    # node.md가 이미 있으면 삭제 (refine 성공 판단을 위해)
    rm -f "$NODE_MD_FILE"

    REFINE_OUTPUT=$(run_engine_refine "$REFINE_FULL_PROMPT") || true
    accumulate_cost "$REFINE_OUTPUT"

    # 성공 판단: refine 에이전트가 node.md를 Write했는지 확인
    if [ -f "$NODE_MD_FILE" ]; then
      echo "  ✓ Refine complete — node.md written"
    else
      echo "  ⚠ Refine failed — copying draft as node.md"
      cp "$NODE_DRAFT_FILE" "$NODE_MD_FILE"
    fi
  else
    echo "  → [4/5] Refine skipped (no OOC violations)"
    cp "$NODE_DRAFT_FILE" "$NODE_MD_FILE"
  fi

  # node.md 존재 확인
  if [ ! -f "$NODE_MD_FILE" ]; then
    echo "  ⚠ node.md missing after refine step — copying draft"
    cp "$NODE_DRAFT_FILE" "$NODE_MD_FILE"
  fi

  # ── Depth 게이트키퍼: MAX_DEPTH 도달 시 LLM verdict 무시하고 강제 PRUNE ──
  if [ "$VERDICT" == "EXPAND" ] && [ "$NEXT_DEPTH" -ge "$MAX_DEPTH" ]; then
    echo "  ⚠ Depth $NEXT_DEPTH >= MAX_DEPTH $MAX_DEPTH — forcing PRUNE (bash gatekeeper)"
    VERDICT="PRUNE"
  fi

  # ── ⑤ Expand ──
  echo "  → [5/5] Expand (verdict: $VERDICT)..."
  jq --arg detail "노드 $NEXT_NODE 트리 확장 중 ($VERDICT)" \
     '.current_activity.detail = $detail' \
     "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

  if [ "$VERDICT" == "EXPAND" ] && [ -f "$EXPAND_PROMPT" ]; then
    EXPAND_FULL_PROMPT="$(cat "$EXPAND_PROMPT")

---
# node.md
$(cat "$NODE_MD_FILE")

---
# evaluation-report.md
$(cat "$EVAL_REPORT_FILE")

---
# NODE CONTEXT
${CONTEXT_CONTENT}
"
    EXPAND_OUTPUT=$(run_engine "$EXPAND_FULL_PROMPT") || true
    accumulate_cost "$EXPAND_OUTPUT"
  else
    # PRUNE: bash에서 직접 처리
    PRUNE_SCORE=$(echo "$EVAL_COMPOSITE" | tr -cd '0-9.' | head -c 20); : "${PRUNE_SCORE:=0}"
    jq --arg node "$NEXT_NODE" --argjson score "$PRUNE_SCORE" \
       '.nodes[$node].status = "pruned" | .nodes[$node].composite_score = $score' \
       "$TREE_INDEX" > "${TREE_INDEX}.tmp" && mv "${TREE_INDEX}.tmp" "$TREE_INDEX"
    # run-state.json 업데이트
    jq '.nodes_completed += 1 | .updated_at = (now | todate)' \
       "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"
    echo "  ✓ Pruned (score: $PRUNE_SCORE)"
  fi

  # ── 7. 결과 확인 ──
  NODE_END_TIME=$(date +%s)
  NODE_DURATION=$(( NODE_END_TIME - NODE_START_TIME ))
  NODE_DURATION_MIN=$(( NODE_DURATION / 60 ))
  NODE_DURATION_SEC=$(( NODE_DURATION % 60 ))

  NODE_INPUT_TOKENS=$(echo "$NODE_INPUT_TOKENS" | tr -cd '0-9' | head -c 20); : "${NODE_INPUT_TOKENS:=0}"
  NODE_OUTPUT_TOKENS=$(echo "$NODE_OUTPUT_TOKENS" | tr -cd '0-9' | head -c 20); : "${NODE_OUTPUT_TOKENS:=0}"
  TOTAL_INPUT_TOKENS=$(( TOTAL_INPUT_TOKENS + NODE_INPUT_TOKENS ))
  TOTAL_OUTPUT_TOKENS=$(( TOTAL_OUTPUT_TOKENS + NODE_OUTPUT_TOKENS ))

  NEW_STATUS=$(jq -r ".nodes[\"$NEXT_NODE\"].status // \"unknown\"" "$TREE_INDEX")
  NEW_SCORE=$(jq -r ".nodes[\"$NEXT_NODE\"].composite_score // \"N/A\"" "$TREE_INDEX")

  NODE_CHARS=0
  if [ -f "$NODE_MD_FILE" ]; then
    NODE_CHARS=$(wc -m < "$NODE_MD_FILE" | tr -d ' ')
    TOTAL_NODE_CHARS=$(( TOTAL_NODE_CHARS + NODE_CHARS ))
  fi

  if [ "$NEW_STATUS" == "pending" ] || [ "$NEW_STATUS" == "unknown" ]; then
    echo "  ✗ Node $NEXT_NODE still pending after processing. [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s] (failure $((CONSECUTIVE_FAILURES + 1))/$MAX_CONSECUTIVE_FAILURES)"
    CONSECUTIVE_FAILURES=$((CONSECUTIVE_FAILURES + 1))
    echo "## $(date +%H:%M:%S) — $NEXT_NODE FAILED (still pending) [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s]" >> "$PROGRESS_FILE"
    echo "---" >> "$PROGRESS_FILE"
    continue
  fi

  # 성공
  CONSECUTIVE_FAILURES=0

  # tree-index.json에 노드별 메타데이터 저장 (duration, chars, cost, tokens)
  jq --arg node "$NEXT_NODE" \
     --argjson dur "$NODE_DURATION" \
     --argjson chars "$NODE_CHARS" \
     --arg cost "$NODE_COST" \
     --argjson in_tok "$NODE_INPUT_TOKENS" \
     --argjson out_tok "$NODE_OUTPUT_TOKENS" \
     '.nodes[$node].duration_sec = $dur | .nodes[$node].chars = $chars | .nodes[$node].cost = $cost | .nodes[$node].input_tokens = $in_tok | .nodes[$node].output_tokens = $out_tok' \
     "$TREE_INDEX" > "${TREE_INDEX}.tmp" && mv "${TREE_INDEX}.tmp" "$TREE_INDEX"

  NEW_CHILDREN=$(jq -r --arg parent "$NEXT_NODE" '
    [.nodes | to_entries[] | select(.value.parent == $parent)] | length
  ' "$TREE_INDEX")

  echo "  ✓ $NEXT_NODE → $NEW_STATUS (score: $NEW_SCORE, children: $NEW_CHILDREN) [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s] \$${NODE_COST} ${NODE_CHARS}chars"

  # ── 8. Progress 업데이트 ──
  cat >> "$PROGRESS_FILE" << EOF
## $(date +%H:%M:%S) — $NEXT_NODE (depth $NEXT_DEPTH) [${NODE_DURATION_MIN}m${NODE_DURATION_SEC}s]
- Status: $NEW_STATUS | Score: $NEW_SCORE | Children: $NEW_CHILDREN
- Title: $NEXT_TITLE
- Cost: \$${NODE_COST} | Tokens: ${NODE_INPUT_TOKENS}in + ${NODE_OUTPUT_TOKENS}out | Turns: $NODE_TURNS
- Content: ${NODE_CHARS} chars | Context: ${CTX_SIZE} bytes
- Validation: ${VALIDATION_RESULT} | OOC penalty: ${OOC_PENALTY} | Template retries: ${TEMPLATE_RETRY_COUNT} | OOC refines: ${OOC_REFINE_COUNT}
- Total elapsed: ${ELAPSED_MIN}m | Cumulative cost: \$${TOTAL_COST_USD}
---
EOF

  sleep 1
done

# ═══════════════════════════════════════
# Phase 6: Deepen Best Path
# ═══════════════════════════════════════
echo ""
echo "══════════════════════════════════════════════"
echo "  Phase 6: Deepen Best Path"
echo "══════════════════════════════════════════════"

FINAL_COMPLETED=$(jq '.nodes_completed' "$RUN_STATE")
FINAL_TOTAL=$(jq '.nodes | length' "$TREE_INDEX")
echo "  Nodes: $FINAL_COMPLETED completed / $FINAL_TOTAL total"

# Best leaf 찾기 (bash에서)
BEST_LEAF=$(jq -r '
  [.nodes | to_entries[] |
   select(.value.status == "expanded" or .value.status == "pruned") |
   select(.value.composite_score != null)]
  | sort_by(-.value.composite_score)
  | .[0].key // "NONE"
' "$TREE_INDEX")

BEST_SCORE=$(jq -r ".nodes[\"$BEST_LEAF\"].composite_score // \"N/A\"" "$TREE_INDEX")
echo "  Best leaf: $BEST_LEAF (score: $BEST_SCORE)"

if [ "$BEST_LEAF" == "NONE" ]; then
  echo "ERROR: No scored nodes found. Cannot deepen."
  exit 1
fi

if [ -f "$DEEPEN_PROMPT" ]; then
  echo "  Running deepen with fresh context..."

  # current_activity 업데이트
  jq '.current_activity = {phase: "deepen", detail: "최우수 경로 소설화 중...", node_id: null, progress: "6/7"}' \
    "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

  DEEPEN_FULL_PROMPT="$(cat "$DEEPEN_PROMPT")

Output Dir: $OUTPUT_DIR
Tree Index: $TREE_INDEX
Best Leaf: $BEST_LEAF
"

  run_engine "$DEEPEN_FULL_PROMPT" "Read,Write,Edit,Agent" 30 || true

  echo "  ✓ Deepen complete."
else
  echo "  WARN: deepen-best-path.md not found. Skipping."
fi

# ── 최종 상태 업데이트 ──
jq '.phase = "complete" | .current_activity = {phase: "complete", detail: "시뮬레이션 완료", node_id: null, progress: "7/7"}' \
  "$RUN_STATE" > "${RUN_STATE}.tmp" && mv "${RUN_STATE}.tmp" "$RUN_STATE"

TOTAL_ELAPSED=$(( $(date +%s) - START_TIME ))
TOTAL_MIN=$(( TOTAL_ELAPSED / 60 ))
TOTAL_HR=$(( TOTAL_MIN / 60 ))
REMAIN_MIN=$(( TOTAL_MIN % 60 ))

# ── 노드당 평균 계산 ──
if [ "$FINAL_COMPLETED" -gt 0 ]; then
  AVG_COST=$(echo "$TOTAL_COST_USD $FINAL_COMPLETED" | awk '{printf "%.4f", $1 / $2}')
  AVG_DURATION=$(( TOTAL_ELAPSED / FINAL_COMPLETED / 60 ))
  AVG_CHARS=$(( TOTAL_NODE_CHARS / FINAL_COMPLETED ))
  EST_100_COST=$(echo "$AVG_COST" | awk '{printf "%.2f", $1 * 100}')
  EST_100_HOURS=$(echo "$AVG_DURATION" | awk '{printf "%.1f", $1 * 100 / 60}')
else
  AVG_COST="N/A"; AVG_DURATION="N/A"; AVG_CHARS="N/A"
  EST_100_COST="N/A"; EST_100_HOURS="N/A"
fi

echo ""
echo "══════════════════════════════════════════════"
echo "  Simulation Complete"
echo "══════════════════════════════════════════════"
echo "  Duration:        ${TOTAL_HR}h ${REMAIN_MIN}m"
echo "  Nodes:           $FINAL_COMPLETED completed / $FINAL_TOTAL total"
echo "  Best:            $BEST_LEAF (score: $BEST_SCORE)"
echo "  Total cost:      \$${TOTAL_COST_USD}"
echo "  Total tokens:    ${TOTAL_INPUT_TOKENS} in + ${TOTAL_OUTPUT_TOKENS} out"
echo "  Total content:   ${TOTAL_NODE_CHARS} chars"
echo "  ──────────────────────────────────"
echo "  Avg/node:        \$${AVG_COST} | ${AVG_DURATION}m | ${AVG_CHARS} chars"
echo "  Est. 100 nodes:  \$${EST_100_COST} | ${EST_100_HOURS}h"
echo "  Output:          $OUTPUT_DIR"
echo "══════════════════════════════════════════════"

# ── Progress에 최종 요약 추가 ──
cat >> "$PROGRESS_FILE" << EOF

# ═══ SIMULATION SUMMARY ═══
- Duration: ${TOTAL_HR}h ${REMAIN_MIN}m
- Nodes: $FINAL_COMPLETED completed / $FINAL_TOTAL total
- Best: $BEST_LEAF (score: $BEST_SCORE)
- Total cost: \$${TOTAL_COST_USD}
- Total tokens: ${TOTAL_INPUT_TOKENS} in + ${TOTAL_OUTPUT_TOKENS} out
- Total content: ${TOTAL_NODE_CHARS} chars
- Avg per node: \$${AVG_COST} | ${AVG_DURATION}m | ${AVG_CHARS} chars
- Estimated 100 nodes: \$${EST_100_COST} | ${EST_100_HOURS}h
EOF
