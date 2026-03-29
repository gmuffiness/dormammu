import { useState, useMemo } from 'react'
import type { ScenarioTreeData, ScenarioNodeData, NodeStatus } from '../types/simulation'
import BranchComparison from './BranchComparison'

interface Props {
  tree: ScenarioTreeData | null
  /** Externally-controlled selected node id. When provided, the component uses
   *  this value for highlighting instead of its own internal state. */
  selectedNodeId?: string | null
  onNodeClick?: (nodeId: string) => void
}

interface LayoutNode {
  id: string
  x: number
  y: number
  width: number
  height: number
  node: ScenarioNodeData
  children: string[]
  parentId: string | null
  depth: number
  hasChildren: boolean
  isExpanded: boolean
}

const NODE_W = 220
const NODE_H = 80
const H_GAP = 20   // horizontal gap between siblings
const V_GAP = 80   // vertical gap between levels

const STATUS_FILL: Record<NodeStatus, string> = {
  complete:    '#052e1a',
  in_progress: '#2d1800',
  pending:     '#1a1714',
  pruned:      '#111010',
}

const STATUS_STROKE: Record<NodeStatus, string> = {
  complete:    '#34d399',
  in_progress: '#e8963c',
  pending:     '#585450',
  pruned:      '#2a2522',
}

const STATUS_LABEL: Record<NodeStatus, string> = {
  complete:    '#34d399',
  in_progress: '#e8963c',
  pending:     '#585450',
  pruned:      '#383430',
}

const OUTCOME_COLORS: Record<string, { fill: string; text: string; emoji: string }> = {
  optimistic:   { fill: '#34d399', text: '#34d399', emoji: '🌟' },
  hopeful:      { fill: '#60a5fa', text: '#60a5fa', emoji: '🕊️' },
  ambiguous:    { fill: '#fbbf24', text: '#fbbf24', emoji: '⚖️' },
  pessimistic:  { fill: '#f97316', text: '#f97316', emoji: '⚠️' },
  catastrophic: { fill: '#ef4444', text: '#ef4444', emoji: '💀' },
  pruned:       { fill: '#585450', text: '#585450', emoji: '✂️' },
}

// ─── Layout algorithm ─────────────────────────────────────────────────────────

function buildLayout(tree: ScenarioTreeData, expandedNodes: Set<string>): Map<string, LayoutNode> {
  const { nodes, root_id } = tree
  if (!root_id || !nodes[root_id]) return new Map()

  // 1. Calculate subtree width for each node (DFS post-order, respecting collapsed nodes)
  const subtreeWidths = new Map<string, number>()

  function calcWidth(id: string): number {
    const node = nodes[id]
    if (!node) return NODE_W

    // If node is collapsed, treat as leaf (only count itself)
    if (!expandedNodes.has(id)) {
      subtreeWidths.set(id, NODE_W)
      return NODE_W
    }

    const children = node.children.filter(c => nodes[c])
    if (children.length === 0) {
      subtreeWidths.set(id, NODE_W)
      return NODE_W
    }
    const childrenTotal = children.reduce((sum, cid) => sum + calcWidth(cid), 0)
    const totalWithGaps = childrenTotal + (children.length - 1) * H_GAP
    const w = Math.max(NODE_W, totalWithGaps)
    subtreeWidths.set(id, w)
    return w
  }
  calcWidth(root_id)

  // 2. Position nodes top-down
  const layout = new Map<string, LayoutNode>()

  const rootWidth = subtreeWidths.get(root_id) ?? NODE_W

  function place(id: string, left: number, d: number): void {
    const node = nodes[id]
    if (!node) return
    const w = subtreeWidths.get(id) ?? NODE_W
    const cx = left + w / 2
    const y = d * (NODE_H + V_GAP)

    const childrenRaw = node.children.filter(c => nodes[c])
    const isExpanded = expandedNodes.has(id)

    layout.set(id, {
      id,
      x: cx - NODE_W / 2,
      y,
      width: NODE_W,
      height: NODE_H,
      node,
      children: isExpanded ? childrenRaw : [],
      parentId: node.parent_id,
      depth: d,
      hasChildren: childrenRaw.length > 0,
      isExpanded,
    })

    // Only recurse into expanded children
    if (isExpanded) {
      let cursor = left
      for (const cid of childrenRaw) {
        const cw = subtreeWidths.get(cid) ?? NODE_W
        place(cid, cursor, d + 1)
        cursor += cw + H_GAP
      }
    }
  }

  place(root_id, 0, 0)

  // Center root if rootWidth > NODE_W
  const rootLayout = layout.get(root_id)
  if (rootLayout) {
    const expectedRootX = (rootWidth - NODE_W) / 2
    const delta = expectedRootX - rootLayout.x
    if (Math.abs(delta) > 0.01) {
      layout.set(root_id, { ...rootLayout, x: expectedRootX })
    }
  }

  return layout
}

// ─── Tooltip ─────────────────────────────────────────────────────────────────

interface TooltipState {
  nodeId: string
  x: number
  y: number
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function DecisionTree({ tree, selectedNodeId: externalSelectedId, onNodeClick }: Props) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const [internalSelectedId, setInternalSelectedId] = useState<string | null>(null)
  const [tooltip, setTooltip] = useState<TooltipState | null>(null)
  const [compareMode, setCompareMode] = useState<{ node1: string; node2?: string } | null>(null)
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; nodeId: string } | null>(null)

  // Prefer externally-controlled selection when the prop is explicitly provided
  const selectedId = externalSelectedId !== undefined ? externalSelectedId : internalSelectedId

  // Initialize expandedNodes: depth <= 2 starts expanded
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(() => {
    if (!tree) return new Set()
    const expanded = new Set<string>()
    const { nodes, root_id } = tree
    if (!root_id) return expanded

    function mark(id: string, depth: number): void {
      if (depth <= 2) {
        expanded.add(id)
      }
      const node = nodes[id]
      if (node) {
        for (const childId of node.children) {
          if (nodes[childId]) {
            mark(childId, depth + 1)
          }
        }
      }
    }

    mark(root_id, 0)
    return expanded
  })

  const layout = useMemo(() => tree ? buildLayout(tree, expandedNodes) : new Map<string, LayoutNode>(), [tree, expandedNodes])

  if (!tree || layout.size === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-surface-400 italic">
        No tree data
      </div>
    )
  }

  // Compute SVG canvas size
  let maxX = 0
  let maxY = 0
  for (const ln of layout.values()) {
    maxX = Math.max(maxX, ln.x + ln.width)
    maxY = Math.max(maxY, ln.y + ln.height)
  }
  const svgW = maxX + 40   // padding
  const svgH = maxY + 40

  const handleNodeClick = (id: string) => {
    // Only manage internal state when not externally controlled
    if (externalSelectedId === undefined) {
      setInternalSelectedId(prev => prev === id ? null : id)
    }
    onNodeClick?.(id)
  }

  const handleToggleExpand = (e: React.MouseEvent, id: string) => {
    e.stopPropagation()
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleMouseEnter = (id: string, lx: number, ly: number) => {
    setHoveredId(id)
    setTooltip({ nodeId: id, x: lx, y: ly })
  }

  const handleMouseLeave = () => {
    setHoveredId(null)
    setTooltip(null)
    setContextMenu(null)
  }

  const handleContextMenu = (e: React.MouseEvent, nodeId: string) => {
    e.preventDefault()
    setContextMenu({ x: e.clientX, y: e.clientY, nodeId })
  }

  const startComparison = (nodeId: string) => {
    setCompareMode({ node1: nodeId })
    setContextMenu(null)
  }

  const selectForComparison = (nodeId: string) => {
    if (compareMode && compareMode.node1 !== nodeId) {
      compareMode.node2 = nodeId
      setCompareMode({ ...compareMode })
    }
    setContextMenu(null)
  }

  // Build edges list
  const edges: Array<{ from: LayoutNode; to: LayoutNode }> = []
  for (const ln of layout.values()) {
    for (const childId of ln.children) {
      const childLn = layout.get(childId)
      if (childLn) edges.push({ from: ln, to: childLn })
    }
  }

  return (
    <div className="relative w-full h-full overflow-auto scrollbar-thin bg-bg-primary">
      <svg
        width={svgW}
        height={svgH}
        style={{ display: 'block', minWidth: svgW, minHeight: svgH }}
      >
        {/* ── Edges ── */}
        <g>
          {edges.map(({ from, to }) => {
            const x1 = from.x + from.width / 2
            const y1 = from.y + from.height
            const x2 = to.x + to.width / 2
            const y2 = to.y
            const midY = (y1 + y2) / 2
            const d = `M ${x1} ${y1} C ${x1} ${midY} ${x2} ${midY} ${x2} ${y2}`
            const isActive =
              selectedId === from.id || selectedId === to.id ||
              hoveredId === from.id || hoveredId === to.id
            return (
              <path
                key={`${from.id}-${to.id}`}
                d={d}
                fill="none"
                stroke={isActive ? '#e8963c' : '#2e2b27'}
                strokeWidth={isActive ? 1.5 : 1}
                strokeOpacity={isActive ? 0.8 : 0.5}
              />
            )
          })}
        </g>

        {/* ── Nodes ── */}
        <g>
          {Array.from(layout.values()).map(ln => {
            const { id, x, y, width, height, node, hasChildren, isExpanded } = ln
            const status = node.status as NodeStatus
            const fill = STATUS_FILL[status] ?? STATUS_FILL.pending
            const stroke = STATUS_STROKE[status] ?? STATUS_STROKE.pending
            const labelColor = STATUS_LABEL[status] ?? STATUS_LABEL.pending
            const isSelected = selectedId === id
            const isHovered = hoveredId === id
            const isPruned = status === 'pruned'

            // Truncate hypothesis to ~28 chars
            const hyp = node.hypothesis || `Node ${node.node_id.slice(0, 8)}`
            const truncated = hyp.length > 28 ? hyp.slice(0, 27) + '…' : hyp

            return (
              <g
                key={id}
                transform={`translate(${x}, ${y})`}
                style={{ cursor: 'pointer' }}
                onClick={() => handleNodeClick(id)}
                onMouseEnter={() => handleMouseEnter(id, x + width / 2, y + height)}
                onMouseLeave={handleMouseLeave}
                onContextMenu={(e) => handleContextMenu(e, id)}
              >
                {/* Selection glow halo (stronger when externally selected) */}
                {isSelected && (
                  <>
                    <rect
                      x={-6}
                      y={-6}
                      width={width + 12}
                      height={height + 12}
                      rx={13}
                      ry={13}
                      fill="rgba(232,150,60,0.06)"
                      stroke="#e8963c"
                      strokeWidth={0.5}
                      strokeOpacity={0.2}
                    />
                    <rect
                      x={-3}
                      y={-3}
                      width={width + 6}
                      height={height + 6}
                      rx={10}
                      ry={10}
                      fill="none"
                      stroke="#e8963c"
                      strokeWidth={1.5}
                      strokeOpacity={0.6}
                    />
                  </>
                )}
                {/* Hover ring (only when not selected) */}
                {!isSelected && isHovered && (
                  <rect
                    x={-3}
                    y={-3}
                    width={width + 6}
                    height={height + 6}
                    rx={10}
                    ry={10}
                    fill="none"
                    stroke={stroke}
                    strokeWidth={1}
                    strokeOpacity={0.4}
                  />
                )}

                {/* Node body */}
                <rect
                  x={0}
                  y={0}
                  width={width}
                  height={height}
                  rx={7}
                  ry={7}
                  fill={isSelected ? (isPruned ? fill : `${fill}cc`) : fill}
                  stroke={isSelected ? '#e8963c' : stroke}
                  strokeWidth={isSelected ? 2 : 1}
                  opacity={isPruned ? 0.45 : 1}
                />

                {/* Status color bar on left edge */}
                <rect
                  x={0}
                  y={8}
                  width={3}
                  height={height - 16}
                  rx={1.5}
                  fill={labelColor}
                  opacity={isPruned ? 0.3 : 0.8}
                />

                {/* Hypothesis text */}
                <text
                  x={14}
                  y={22}
                  fontSize={11}
                  fontFamily="inherit"
                  fill={isPruned ? '#585450' : isSelected ? '#f0a030' : '#e8e4e0'}
                  fontWeight={isSelected ? '600' : 'normal'}
                  style={{ textDecoration: isPruned ? 'line-through' : 'none' }}
                >
                  {truncated}
                </text>

                {/* Depth + turns row */}
                <text
                  x={14}
                  y={38}
                  fontSize={9}
                  fontFamily="monospace"
                  fill="#585450"
                >
                  {`d${node.depth} · ${node.turns_simulated}t`}
                  {node.score != null ? `  · score ${node.score.toFixed(2)}` : ''}
                </text>

                {/* Expand/collapse button (right side if has children) */}
                {hasChildren && (
                  <g
                    onClick={(e) => handleToggleExpand(e as any, id)}
                    style={{ cursor: 'pointer' }}
                  >
                    {/* Button background */}
                    <circle
                      cx={width - 8}
                      cy={8}
                      r={6}
                      fill={isExpanded ? '#34d399' : '#e8963c'}
                      opacity={isHovered ? 0.8 : 0.4}
                    />
                    {/* Arrow icon */}
                    <text
                      x={width - 8}
                      y={11}
                      fontSize={8}
                      fontFamily="monospace"
                      fontWeight="bold"
                      fill="#0a0a0a"
                      textAnchor="middle"
                      style={{ pointerEvents: 'none' }}
                    >
                      {isExpanded ? '▼' : '▶'}
                    </text>
                  </g>
                )}

                {/* Outcome badge for leaf nodes, status badge for others */}
                {(() => {
                  const isLeaf = node.children.length === 0
                  // Try to parse outcome from description (stored as JSON)
                  let outcome: { outcome: string; outcome_label: string } | null = null
                  if (isLeaf) {
                    try {
                      const meta = node.metadata as Record<string, unknown>
                      if (meta?.outcome) {
                        outcome = meta as { outcome: string; outcome_label: string }
                      }
                    } catch {}
                  }

                  if (outcome && OUTCOME_COLORS[outcome.outcome]) {
                    const oc = OUTCOME_COLORS[outcome.outcome]
                    const badgeW = Math.min(width - 16, 8 * outcome.outcome.length + 24)
                    return (
                      <>
                        <rect x={8} y={height - 22} width={badgeW} height={16} rx={4} fill={oc.fill} fillOpacity={0.15} />
                        <text x={14} y={height - 10} fontSize={9} fontFamily="monospace" fill={oc.text}>
                          {oc.emoji} {outcome.outcome}
                        </text>
                      </>
                    )
                  }

                  return (
                    <>
                      <rect x={width - 56} y={height - 20} width={50} height={14} rx={3} fill={labelColor} fillOpacity={0.12} />
                      <text x={width - 31} y={height - 9} fontSize={8} fontFamily="monospace" fill={labelColor} textAnchor="middle" opacity={isPruned ? 0.5 : 1}>
                        {status}
                      </text>
                    </>
                  )
                })()}
              </g>
            )
          })}
        </g>
      </svg>

      {/* ── Context Menu ── */}
      {contextMenu && tree && (() => {
        const node = tree.nodes[contextMenu.nodeId]
        if (!node) return null

        const isComparing = compareMode?.node1 === contextMenu.nodeId
        const showSelectForComparison = compareMode && compareMode.node1 !== contextMenu.nodeId

        return (
          <>
            {/* Overlay to close menu on click */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setContextMenu(null)}
            />
            {/* Menu */}
            <div
              className="fixed z-50 bg-bg-secondary border border-white/[0.1] rounded-lg shadow-lg overflow-hidden"
              style={{
                left: contextMenu.x,
                top: contextMenu.y,
              }}
            >
              <button
                onClick={() => startComparison(contextMenu.nodeId)}
                className={`w-full px-4 py-2 text-sm text-left hover:bg-white/[0.1] transition ${isComparing ? 'bg-accent-teal/20 text-accent-teal' : 'text-surface-200'}`}
              >
                {isComparing ? '✓ Comparing...' : '🔀 Compare with...'}
              </button>
              {showSelectForComparison && (
                <button
                  onClick={() => selectForComparison(contextMenu.nodeId)}
                  className="w-full px-4 py-2 text-sm text-left hover:bg-white/[0.1] transition text-accent-orange border-t border-white/[0.1]"
                >
                  ✓ Select as Branch B
                </button>
              )}
            </div>
          </>
        )
      })()}

      {/* ── Floating tooltip ── */}
      {tooltip && (() => {
        const ln = layout.get(tooltip.nodeId)
        if (!ln) return null
        const node = ln.node
        const tags = Array.isArray((node.metadata as Record<string, unknown>)?.tags)
          ? (node.metadata as Record<string, unknown>).tags as string[]
          : []

        // Check if evaluation scores are available
        const hasScores = node.emergence_score != null || node.narrative_score != null ||
                         node.diversity_score != null || node.novelty_score != null

        return (
          <div
            className="absolute z-50 pointer-events-none max-w-sm bg-bg-secondary border border-white/[0.1] rounded-lg p-3 shadow-xl"
            style={{
              left: tooltip.x + 20,
              top: tooltip.y - 10,
            }}
          >
            {/* Hypothesis */}
            <p className="text-xs text-surface-50 leading-relaxed mb-2 font-semibold">
              {node.hypothesis || `Node ${node.node_id.slice(0, 8)}`}
            </p>

            {/* Basic info */}
            <div className="flex items-center gap-3 text-[10px] font-mono text-surface-400 mb-2">
              <span>d{node.depth}</span>
              <span>{node.turns_simulated}t</span>
            </div>

            {/* Quality scores (if available) */}
            {hasScores && (
              <div className="mb-2 p-2.5 bg-white/[0.02] rounded border border-white/[0.06]">
                <div className="text-[9px] text-surface-400 font-semibold mb-2 uppercase tracking-[0.1em]">
                  📊 Quality Scores
                </div>
                <div className="space-y-1.5">
                  {node.emergence_score != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-surface-400">✨ Emergence</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(node.emergence_score * 100, 4)}%`,
                              background: node.emergence_score > 0.5 ? '#34d399' : node.emergence_score > 0.3 ? '#fbbf24' : '#ef4444'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-surface-200 w-8 text-right">
                          {node.emergence_score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}
                  {node.narrative_score != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-surface-400">📖 Narrative</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(node.narrative_score * 100, 4)}%`,
                              background: node.narrative_score > 0.5 ? '#34d399' : node.narrative_score > 0.3 ? '#fbbf24' : '#ef4444'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-surface-200 w-8 text-right">
                          {node.narrative_score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}
                  {node.diversity_score != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-surface-400">🎭 Diversity</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(node.diversity_score * 100, 4)}%`,
                              background: node.diversity_score > 0.5 ? '#34d399' : node.diversity_score > 0.3 ? '#fbbf24' : '#ef4444'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-surface-200 w-8 text-right">
                          {node.diversity_score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}
                  {node.novelty_score != null && (
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] text-surface-400">🆕 Novelty</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(node.novelty_score * 100, 4)}%`,
                              background: node.novelty_score > 0.5 ? '#34d399' : node.novelty_score > 0.3 ? '#fbbf24' : '#ef4444'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono text-surface-200 w-8 text-right">
                          {node.novelty_score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}
                  {node.score != null && (
                    <div className="flex items-center justify-between border-t border-white/[0.08] pt-1.5 mt-1.5">
                      <span className="text-[10px] font-semibold text-accent-amber">⭐ Composite</span>
                      <div className="flex items-center gap-1.5">
                        <div className="w-12 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full transition-all"
                            style={{
                              width: `${Math.max(node.score * 100, 4)}%`,
                              background: node.score > 0.3 ? '#34d399' : '#f97316'
                            }}
                          />
                        </div>
                        <span className="text-[10px] font-mono font-semibold text-accent-amber w-8 text-right">
                          {node.score.toFixed(2)}
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tags */}
            {tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {tags.map((tag, i) => (
                  <span
                    key={i}
                    className="text-[9px] text-surface-300 bg-white/[0.04] border border-white/[0.06] rounded-full px-1.5 py-0.5"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        )
      })()}

      {/* ── Branch Comparison Modal ── */}
      {compareMode?.node2 && tree && (() => {
        const node1 = tree.nodes[compareMode.node1]
        const node2 = tree.nodes[compareMode.node2]
        if (!node1 || !node2) return null

        return (
          <BranchComparison
            node1={node1}
            node2={node2}
            onClose={() => {
              setCompareMode(null)
              setContextMenu(null)
            }}
          />
        )
      })()}
    </div>
  )
}
