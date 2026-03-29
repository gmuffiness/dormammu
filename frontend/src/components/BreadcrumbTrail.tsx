import React from 'react'
import type { ScenarioNodeData, ScenarioTreeData } from '../types/simulation'

interface Props {
  tree: ScenarioTreeData | null
  selectedNodeId: string | null
  onNodeClick: (nodeId: string) => void
}

/**
 * Builds navigation path from root to selected node
 * Returns array of nodes, with root first
 */
function buildPath(tree: ScenarioTreeData | null, selectedNodeId: string | null): ScenarioNodeData[] {
  if (!selectedNodeId || !tree || !tree.nodes[selectedNodeId]) return []

  const path: ScenarioNodeData[] = []
  let current = tree.nodes[selectedNodeId]

  // Trace backwards to root
  while (current) {
    path.unshift(current)
    if (!current.parent_id) break
    current = tree.nodes[current.parent_id]
  }

  return path
}

export default function BreadcrumbTrail({ tree, selectedNodeId, onNodeClick }: Props) {
  const path = buildPath(tree, selectedNodeId)

  if (!tree || path.length === 0) return null

  // Calculate truncation threshold based on path length
  // Longer paths get more truncation to fit on screen
  const maxNodeWidth = path.length > 5 ? 60 : path.length > 3 ? 100 : 150

  return (
    <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/[0.06] bg-bg-tertiary overflow-x-auto scrollbar-thin flex-shrink-0">
      {/* Path breadcrumb */}
      <div className="flex items-center gap-1.5 min-w-max">
        {path.map((node, i) => (
          <React.Fragment key={node.node_id}>
            {/* Node button */}
            <button
              onClick={() => onNodeClick(node.node_id)}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg hover:bg-white/[0.08] transition-colors flex-shrink-0 group"
              title={node.hypothesis}
            >
              {/* Status indicator */}
              <div
                className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                style={{
                  background: node.status === 'complete' ? '#34d399' :
                             node.status === 'in_progress' ? '#e8963c' :
                             node.status === 'pending' ? '#585450' :
                             node.status === 'pruned' ? '#383430' : '#585450'
                }}
              />

              {/* Label */}
              <span className="text-[11px] text-surface-300 group-hover:text-surface-50 transition-colors whitespace-nowrap font-body">
                {i === 0 ? 'Genesis' : `${node.hypothesis.slice(0, maxNodeWidth / 8)}${node.hypothesis.length > maxNodeWidth / 8 ? '…' : ''}`}
              </span>
            </button>

            {/* Separator (except after last) */}
            {i < path.length - 1 && (
              <span className="text-surface-500 text-xs flex-shrink-0">›</span>
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Score display (right side, fixed) */}
      {selectedNodeId && tree.nodes[selectedNodeId] && (
        <div className="ml-auto flex items-center gap-2 pl-4 border-l border-white/[0.06] flex-shrink-0">
          <span className="text-[10px] text-surface-400 font-mono">
            d{tree.nodes[selectedNodeId].depth}
          </span>
          {tree.nodes[selectedNodeId].score != null && (
            <span className="text-[10px] font-mono text-accent-amber font-semibold">
              {tree.nodes[selectedNodeId].score!.toFixed(2)}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
