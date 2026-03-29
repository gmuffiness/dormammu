import { useState } from 'react'
import type { ScenarioTreeData, ScenarioNodeData, NodeStatus } from '../types/simulation'

const STATUS_COLOR: Record<NodeStatus, string> = {
  complete: '#34d399',
  in_progress: '#e8963c',
  pending: '#585450',
  pruned: '#383430',
}

interface NodeProps {
  node: ScenarioNodeData
  allNodes: Record<string, ScenarioNodeData>
  selectedNodeId: string | null
  onSelect: (nodeId: string) => void
}

function TreeNode({ node, allNodes, selectedNodeId, onSelect }: NodeProps) {
  const [expanded, setExpanded] = useState(node.depth < 2)
  const hasChildren = node.children.length > 0
  const color = STATUS_COLOR[node.status] ?? '#585450'
  const isSelected = node.node_id === selectedNodeId
  const isPruned = node.status === 'pruned'

  const handleClick = () => {
    onSelect(node.node_id)
    if (hasChildren) setExpanded(e => !e)
  }

  const visibleChildren = node.children.filter(id => allNodes[id])

  return (
    <div className="select-none">
      {/* Node button */}
      <button
        onClick={handleClick}
        className={`flex items-start gap-2 w-full text-left rounded-lg px-2 py-1.5 transition-all duration-150 group
          ${isSelected
            ? 'bg-accent-amber/[0.08] border border-accent-amber/25 shadow-[0_0_0_1px_rgba(232,150,60,0.08)]'
            : 'hover:bg-white/[0.04] border border-transparent'
          }`}
      >
        {/* Expand / leaf indicator + status dot */}
        <div className="flex-shrink-0 flex items-center gap-1 mt-[3px]">
          <span className="text-surface-500 text-[10px] leading-none w-3 text-center">
            {hasChildren ? (expanded ? '▾' : '▸') : '·'}
          </span>
          <div
            className="w-2 h-2 rounded-sm flex-shrink-0"
            style={{
              background: color,
              boxShadow: node.status === 'in_progress' ? `0 0 5px ${color}60` : 'none',
              opacity: isPruned ? 0.4 : 1,
            }}
          />
        </div>

        {/* Text content */}
        <div className="flex-1 min-w-0">
          <div
            className={`text-xs truncate leading-snug transition-colors font-body
              ${isSelected
                ? 'text-accent-amber font-medium'
                : isPruned
                  ? 'text-surface-500 line-through'
                  : 'text-surface-200 group-hover:text-surface-50'
              }`}
          >
            {node.hypothesis || `Node ${node.node_id.slice(0, 8)}`}
          </div>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] text-surface-500 font-mono">
              d{node.depth} · {node.turns_simulated}t
            </span>
            {node.status === 'complete' && (
              <span className="text-[10px] text-emerald-400/70">✓</span>
            )}
            {node.status === 'in_progress' && (
              <span className="text-[10px] text-amber-400/70 animate-pulse">●</span>
            )}
            {node.status === 'pruned' && (
              <span className="text-[10px] text-surface-500">pruned</span>
            )}
            {node.score != null && (
              <span className={`text-[10px] font-mono ${isSelected ? 'text-accent-amber' : 'text-accent-amber/60'}`}>
                {node.score.toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </button>

      {/* Children — border-left creates the vertical tree guide line */}
      {expanded && hasChildren && visibleChildren.length > 0 && (
        <div
          className="ml-[14px] pl-2"
          style={{ borderLeft: '1px solid rgba(88, 84, 80, 0.22)' }}
        >
          {visibleChildren.map(childId => (
            <TreeNode
              key={childId}
              node={allNodes[childId]}
              allNodes={allNodes}
              selectedNodeId={selectedNodeId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  )
}

interface Props {
  tree: ScenarioTreeData | null
  /** Externally controlled selected node id (for highlight). */
  selectedNodeId?: string | null
  /** Called when user clicks a node — should seek replay to this node. */
  onJump: (nodeId: string) => void
  /** Optional additional callback when a node is selected. */
  onSelectNode?: (nodeId: string) => void
}

export default function ScenarioTree({ tree, selectedNodeId = null, onJump, onSelectNode }: Props) {
  const [open, setOpen] = useState(false)

  if (!tree) return null

  const rootNode = tree.root_id ? tree.nodes[tree.root_id] : null
  const allNodes = tree.nodes
  const nodeCount = Object.keys(allNodes).length
  const completeCount = Object.values(allNodes).filter(n => n.status === 'complete').length
  const inProgressCount = Object.values(allNodes).filter(n => n.status === 'in_progress').length

  const handleSelect = (nodeId: string) => {
    onJump(nodeId)
    onSelectNode?.(nodeId)
  }

  return (
    <div className="border-t border-white/[0.06]">
      {/* Toggle header */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.04] transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em]">
            Scenario Tree
          </span>
          <span className="text-[10px] text-surface-400 font-mono">
            {completeCount}/{nodeCount}
          </span>
          {inProgressCount > 0 && (
            <span className="text-[10px] text-amber-400/70 font-mono animate-pulse">
              +{inProgressCount} active
            </span>
          )}
        </div>
        <span className="text-surface-400 text-xs">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="max-h-72 overflow-y-auto scrollbar-thin pb-2 px-1">
          {rootNode ? (
            <TreeNode
              node={rootNode}
              allNodes={allNodes}
              selectedNodeId={selectedNodeId}
              onSelect={handleSelect}
            />
          ) : (
            <div className="text-xs text-surface-400 px-4 py-2 italic">No tree data</div>
          )}
        </div>
      )}
    </div>
  )
}
