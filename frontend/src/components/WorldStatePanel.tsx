/**
 * WorldStatePanel — Detailed world-state panel for the selected scenario node.
 *
 * Features:
 *  - Shows detailed world state (agents, resources, events) at the selected node
 *  - Prev/Next navigation across all DFS-ordered nodes
 *  - Animated transition on node switch
 *  - Loading & empty-state handling
 */

import { useState, useEffect, useMemo, useCallback } from 'react'
import { api } from '../api/client'
import type {
  ScenarioTreeData,
  ScenarioNodeData,
  WorldState,
  NodeStatus,
  AgentSnapshot,
} from '../types/simulation'

// ─── DFS order helper ─────────────────────────────────────────────────────────

/** Returns all node IDs in DFS pre-order (root → children left-to-right). */
function dfsOrder(tree: ScenarioTreeData): string[] {
  if (!tree.root_id || !tree.nodes[tree.root_id]) return []
  const result: string[] = []
  const stack = [tree.root_id]
  while (stack.length > 0) {
    const id = stack.pop()!
    result.push(id)
    const node = tree.nodes[id]
    if (node) {
      // Push children in reverse so left-most child is processed first
      for (let i = node.children.length - 1; i >= 0; i--) {
        const childId = node.children[i]
        if (tree.nodes[childId]) stack.push(childId)
      }
    }
  }
  return result
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function StatusBadge({ status }: { status: NodeStatus }) {
  const styles: Record<NodeStatus, string> = {
    complete:    'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
    in_progress: 'bg-amber-500/15 text-amber-400 border-amber-500/20',
    pending:     'bg-white/[0.04] text-surface-400 border-white/[0.08]',
    pruned:      'bg-red-500/10 text-red-400/60 border-red-500/15',
  }
  return (
    <span
      className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${styles[status] ?? styles.pending}`}
    >
      {status}
    </span>
  )
}

function ScoreBar({
  label,
  value,
  icon,
}: {
  label: string
  value: number
  icon: string
}) {
  const color =
    value > 0.6 ? '#34d399' : value > 0.35 ? '#e8963c' : '#ef4444'
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[10px] text-surface-400 flex-shrink-0">
        {icon} {label}
      </span>
      <div className="flex items-center gap-1.5 flex-shrink-0">
        <div className="w-14 h-1 bg-white/[0.06] rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-300"
            style={{ width: `${Math.max(value * 100, 4)}%`, background: color }}
          />
        </div>
        <span className="text-[10px] font-mono text-surface-300 w-7 text-right">
          {value.toFixed(2)}
        </span>
      </div>
    </div>
  )
}

function AgentCard({ agentId, snapshot }: { agentId: string; snapshot: AgentSnapshot }) {
  const [expanded, setExpanded] = useState(false)
  const name = snapshot.name ?? agentId.slice(0, 10)
  const mood = typeof snapshot.mood === 'number' ? snapshot.mood : 0.5
  const energy = typeof snapshot.energy === 'number' ? snapshot.energy : 0.5
  const location = snapshot.location ?? '—'

  const moodColor = mood > 0.65 ? '#34d399' : mood > 0.35 ? '#e8963c' : '#ef4444'
  const energyColor = energy > 0.65 ? '#60a5fa' : energy > 0.35 ? '#e8963c' : '#ef4444'

  return (
    <div className="rounded-lg border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center gap-2.5 p-2.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        {/* Avatar */}
        <div
          className="w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-[9px] font-bold text-bg-primary"
          style={{ background: `hsl(${hashCode(agentId) % 360}, 55%, 55%)` }}
        >
          {name.charAt(0).toUpperCase()}
        </div>

        <div className="flex-1 min-w-0">
          <div className="text-[11px] text-surface-100 font-semibold truncate">{name}</div>
          <div className="text-[10px] text-surface-400 font-mono truncate">{location}</div>
        </div>

        {/* Compact bars */}
        <div className="flex flex-col gap-1 flex-shrink-0">
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-surface-500 w-4">M</span>
            <div className="w-10 h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${mood * 100}%`, background: moodColor }} />
            </div>
          </div>
          <div className="flex items-center gap-1">
            <span className="text-[9px] text-surface-500 w-4">E</span>
            <div className="w-10 h-1 bg-white/[0.06] rounded-full overflow-hidden">
              <div className="h-full rounded-full" style={{ width: `${energy * 100}%`, background: energyColor }} />
            </div>
          </div>
        </div>

        <span className="text-[10px] text-surface-500 flex-shrink-0">
          {expanded ? '▾' : '▸'}
        </span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-2 border-t border-white/[0.04] pt-2 animate-fade-in">
          {/* Goals */}
          {snapshot.goals && snapshot.goals.length > 0 && (
            <div>
              <div className="text-[9px] text-accent-amber/70 font-semibold uppercase tracking-[0.1em] mb-1">
                Goals
              </div>
              {snapshot.goals.map((g, i) => (
                <div key={i} className="flex items-start gap-1.5 mb-0.5">
                  <span className="text-[9px] text-surface-500 mt-0.5 flex-shrink-0">•</span>
                  <span className="text-[10px] text-surface-300 leading-snug">{g}</span>
                </div>
              ))}
            </div>
          )}

          {/* Traits */}
          {snapshot.traits && Object.keys(snapshot.traits).length > 0 && (
            <div>
              <div className="text-[9px] text-surface-500 font-semibold uppercase tracking-[0.1em] mb-1.5">
                Traits
              </div>
              <div className="space-y-1">
                {Object.entries(snapshot.traits as Record<string, number>).slice(0, 5).map(([k, v]) => (
                  <div key={k} className="flex items-center gap-2">
                    <span className="text-[9px] text-surface-400 w-20 truncate flex-shrink-0 capitalize">{k}</span>
                    <div className="flex-1 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.abs(v) * 100}%`,
                          background: v >= 0 ? '#60a5fa' : '#f87171',
                        }}
                      />
                    </div>
                    <span className="text-[9px] font-mono text-surface-500 w-6 text-right flex-shrink-0">
                      {v.toFixed(1)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Backstory snippet */}
          {snapshot.backstory && (
            <div>
              <div className="text-[9px] text-surface-500 font-semibold uppercase tracking-[0.1em] mb-1">
                Backstory
              </div>
              <p className="text-[10px] text-surface-400 leading-relaxed line-clamp-3">
                {snapshot.backstory}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/** Simple non-cryptographic hash for colorizing agent avatars */
function hashCode(str: string): number {
  let h = 0
  for (let i = 0; i < str.length; i++) {
    h = (Math.imul(31, h) + str.charCodeAt(i)) | 0
  }
  return Math.abs(h)
}

// ─── Main component ──────────────────────────────────────────────────────────

interface Props {
  tree: ScenarioTreeData | null
  simulationId: string
  selectedNodeId: string | null
  onSelectNode: (nodeId: string) => void
}

export default function WorldStatePanel({
  tree,
  simulationId,
  selectedNodeId,
  onSelectNode,
}: Props) {
  const [worldState, setWorldState] = useState<WorldState | null>(null)
  const [loadingWs, setLoadingWs] = useState(false)
  const [activeTab, setActiveTab] = useState<'agents' | 'resources' | 'events'>('agents')

  // DFS-ordered node list for navigation
  const dfsNodes = useMemo<string[]>(
    () => (tree ? dfsOrder(tree) : []),
    [tree]
  )

  const currentIndex = useMemo(
    () => (selectedNodeId ? dfsNodes.indexOf(selectedNodeId) : -1),
    [dfsNodes, selectedNodeId]
  )

  const prevNodeId = currentIndex > 0 ? dfsNodes[currentIndex - 1] : null
  const nextNodeId = currentIndex < dfsNodes.length - 1 ? dfsNodes[currentIndex + 1] : null

  const selectedNode: ScenarioNodeData | null = useMemo(
    () => (selectedNodeId && tree ? (tree.nodes[selectedNodeId] ?? null) : null),
    [selectedNodeId, tree]
  )

  // Navigate to previous node
  const handlePrev = useCallback(() => {
    if (prevNodeId) onSelectNode(prevNodeId)
  }, [prevNodeId, onSelectNode])

  // Navigate to next node
  const handleNext = useCallback(() => {
    if (nextNodeId) onSelectNode(nextNodeId)
  }, [nextNodeId, onSelectNode])

  // Lazy-fetch world state when selected node changes
  useEffect(() => {
    if (!simulationId || !selectedNode) {
      setWorldState(null)
      return
    }

    const turn = selectedNode.turns_simulated > 0 ? selectedNode.turns_simulated : 0
    setLoadingWs(true)
    setWorldState(null)

    api
      .getWorldState(simulationId, turn)
      .then(ws => setWorldState(ws))
      .catch(() => setWorldState(null))
      .finally(() => setLoadingWs(false))
  }, [simulationId, selectedNode])

  // ── Empty state ────────────────────────────────────────────────────────────
  if (!tree || dfsNodes.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center px-4">
        <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-3">
          <span className="text-lg text-surface-500">🌐</span>
        </div>
        <p className="text-xs text-surface-400">No scenario tree available</p>
      </div>
    )
  }

  if (!selectedNode) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center px-4">
        <div className="w-10 h-10 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-3">
          <span className="text-lg text-surface-400">🌐</span>
        </div>
        <p className="text-xs text-surface-400">
          Click a node in the tree to inspect its world state
        </p>
        <p className="text-[10px] text-surface-500 mt-1">
          {dfsNodes.length} nodes available
        </p>
      </div>
    )
  }

  const agents = worldState?.agents ?? {}
  const resources = worldState?.resources ?? {}
  const events = worldState?.events ?? []
  const agentIds = Object.keys(agents)

  // Quality scores availability
  const hasScores =
    selectedNode.emergence_score != null ||
    selectedNode.narrative_score != null ||
    selectedNode.diversity_score != null ||
    selectedNode.novelty_score != null

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* ── Navigation header ─────────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex items-center gap-2 px-3 py-2 border-b border-white/[0.06] bg-bg-tertiary/50">
        <button
          onClick={handlePrev}
          disabled={!prevNodeId}
          className={`w-6 h-6 rounded flex items-center justify-center transition-all flex-shrink-0
            ${prevNodeId
              ? 'bg-white/[0.06] hover:bg-white/[0.12] text-surface-300 hover:text-surface-50'
              : 'opacity-25 cursor-not-allowed text-surface-500'
            }`}
          title={prevNodeId && tree.nodes[prevNodeId] ? tree.nodes[prevNodeId].hypothesis : undefined}
        >
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M7 2L3 6l4 4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>

        <div className="flex-1 min-w-0 text-center">
          <span className="text-[10px] font-mono text-surface-400">
            {currentIndex + 1} / {dfsNodes.length}
          </span>
        </div>

        <button
          onClick={handleNext}
          disabled={!nextNodeId}
          className={`w-6 h-6 rounded flex items-center justify-center transition-all flex-shrink-0
            ${nextNodeId
              ? 'bg-white/[0.06] hover:bg-white/[0.12] text-surface-300 hover:text-surface-50'
              : 'opacity-25 cursor-not-allowed text-surface-500'
            }`}
          title={nextNodeId && tree.nodes[nextNodeId] ? tree.nodes[nextNodeId].hypothesis : undefined}
        >
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M5 2l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </button>
      </div>

      {/* ── Node info card ────────────────────────────────────────────────── */}
      <div className="flex-shrink-0 px-3 py-3 border-b border-white/[0.06] space-y-2">
        {/* Status + depth + turns row */}
        <div className="flex items-center gap-2 flex-wrap">
          <StatusBadge status={selectedNode.status} />
          <span className="text-[10px] font-mono text-surface-500">
            d{selectedNode.depth}
          </span>
          <span className="text-[10px] font-mono text-surface-500">
            {selectedNode.turns_simulated}t
          </span>
          {selectedNode.score != null && (
            <span className="text-[10px] font-mono text-accent-amber font-semibold ml-auto">
              ⭐ {selectedNode.score.toFixed(2)}
            </span>
          )}
        </div>

        {/* Hypothesis */}
        <p className="text-xs text-surface-100 font-semibold leading-snug">
          {selectedNode.hypothesis || `Node ${selectedNode.node_id.slice(0, 8)}`}
        </p>

        {/* Tags */}
        {selectedNode.tags && selectedNode.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {selectedNode.tags.map((tag, i) => (
              <span
                key={i}
                className="text-[9px] text-surface-300 bg-white/[0.04] border border-white/[0.06] rounded-full px-2 py-0.5"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Quality scores */}
        {hasScores && (
          <div className="pt-1 space-y-1.5">
            {selectedNode.emergence_score != null && (
              <ScoreBar label="Emergence" value={selectedNode.emergence_score} icon="✨" />
            )}
            {selectedNode.narrative_score != null && (
              <ScoreBar label="Narrative" value={selectedNode.narrative_score} icon="📖" />
            )}
            {selectedNode.diversity_score != null && (
              <ScoreBar label="Diversity" value={selectedNode.diversity_score} icon="🎭" />
            )}
            {selectedNode.novelty_score != null && (
              <ScoreBar label="Novelty" value={selectedNode.novelty_score} icon="🆕" />
            )}
          </div>
        )}
      </div>

      {/* ── World state section ───────────────────────────────────────────── */}
      <div className="flex-shrink-0 flex border-b border-white/[0.06]">
        {(['agents', 'resources', 'events'] as const).map(tab => {
          const counts: Record<string, number> = {
            agents: agentIds.length,
            resources: Object.keys(resources).length,
            events: events.length,
          }
          return (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 text-[10px] py-2 uppercase tracking-[0.1em] font-display font-semibold transition-all
                ${activeTab === tab
                  ? 'text-accent-amber border-b-2 border-accent-amber'
                  : 'text-surface-400 hover:text-surface-200'
                }`}
            >
              {tab}
              {counts[tab] > 0 && (
                <span className="ml-1 text-[9px] opacity-60">({counts[tab]})</span>
              )}
            </button>
          )
        })}
      </div>

      {/* ── Tab content ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3">
        {/* Loading state */}
        {loadingWs && (
          <div className="flex items-center justify-center py-8 gap-2">
            <div className="w-4 h-4 rounded-full border-2 border-transparent border-t-accent-amber/70 animate-spin" />
            <span className="text-[11px] text-surface-400">Loading world state…</span>
          </div>
        )}

        {/* No world state available */}
        {!loadingWs && !worldState && (
          <div className="text-center py-6">
            <p className="text-[11px] text-surface-500 italic">
              No world state recorded for this node
            </p>
            <p className="text-[10px] text-surface-500/60 mt-1">
              Turn {selectedNode.turns_simulated}
            </p>
          </div>
        )}

        {/* ── Agents tab ──────────────────────────────────────────────── */}
        {!loadingWs && worldState && activeTab === 'agents' && (
          <div className="space-y-2 animate-fade-in">
            {agentIds.length === 0 ? (
              <p className="text-[11px] text-surface-500 italic text-center py-4">
                No agents in this world state
              </p>
            ) : (
              agentIds.map(agentId => (
                <AgentCard
                  key={agentId}
                  agentId={agentId}
                  snapshot={agents[agentId]}
                />
              ))
            )}
          </div>
        )}

        {/* ── Resources tab ───────────────────────────────────────────── */}
        {!loadingWs && worldState && activeTab === 'resources' && (
          <div className="animate-fade-in">
            {Object.keys(resources).length === 0 ? (
              <p className="text-[11px] text-surface-500 italic text-center py-4">
                No resource data
              </p>
            ) : (
              <div className="space-y-2">
                {Object.entries(resources).map(([key, val]) => {
                  const numVal = typeof val === 'number' ? val : null
                  return (
                    <div key={key} className="flex items-center gap-3">
                      <span className="text-[11px] text-surface-300 capitalize flex-1 truncate">
                        {key.replace(/_/g, ' ')}
                      </span>
                      {numVal !== null ? (
                        <div className="flex items-center gap-2 flex-shrink-0">
                          <div className="w-20 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                            <div
                              className="h-full rounded-full transition-all duration-300"
                              style={{
                                width: `${Math.min(Math.abs(numVal) * 100, 100)}%`,
                                background: numVal > 0.5 ? '#34d399' : numVal > 0.2 ? '#e8963c' : '#ef4444',
                              }}
                            />
                          </div>
                          <span className="text-[10px] font-mono text-surface-400 w-10 text-right">
                            {typeof numVal === 'number' && numVal % 1 !== 0
                              ? numVal.toFixed(2)
                              : String(numVal)}
                          </span>
                        </div>
                      ) : (
                        <span className="text-[10px] font-mono text-surface-400 flex-shrink-0 max-w-[120px] truncate">
                          {String(val)}
                        </span>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )}

        {/* ── Events tab ──────────────────────────────────────────────── */}
        {!loadingWs && worldState && activeTab === 'events' && (
          <div className="space-y-2 animate-fade-in">
            {events.length === 0 ? (
              <p className="text-[11px] text-surface-500 italic text-center py-4">
                No events recorded
              </p>
            ) : (
              events.map((ev, i) => {
                const type = ev.type ?? ''
                const emoji =
                  type.includes('interact') ? '💬'
                  : type.includes('cooperat') ? '🤝'
                  : type.includes('conflict') ? '⚔️'
                  : type.includes('discover') ? '✨'
                  : type.includes('observ') ? '👁'
                  : type.includes('movement') ? '🚶'
                  : type.includes('world') ? '🌍'
                  : '◎'
                return (
                  <div
                    key={i}
                    className="flex items-start gap-2 p-2 rounded-lg border border-white/[0.04] bg-white/[0.02]"
                  >
                    <span className="text-[11px] flex-shrink-0 mt-0.5">{emoji}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-[10px] text-surface-200 leading-snug">
                        {ev.description}
                      </p>
                      {ev.participants && ev.participants.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {ev.participants.map((p, pi) => (
                            <span
                              key={pi}
                              className="text-[9px] text-surface-400 bg-white/[0.04] rounded px-1.5 py-0.5"
                            >
                              {p}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        )}
      </div>

      {/* ── Node path footer ──────────────────────────────────────────────── */}
      {selectedNode && tree && (
        <NodePathFooter
          tree={tree}
          selectedNodeId={selectedNode.node_id}
          onNodeClick={onSelectNode}
        />
      )}
    </div>
  )
}

// ─── Node path breadcrumb footer ─────────────────────────────────────────────

interface PathFooterProps {
  tree: ScenarioTreeData
  selectedNodeId: string
  onNodeClick: (nodeId: string) => void
}

function NodePathFooter({ tree, selectedNodeId, onNodeClick }: PathFooterProps) {
  const path = useMemo(() => {
    const result: ScenarioNodeData[] = []
    let current = tree.nodes[selectedNodeId]
    while (current) {
      result.unshift(current)
      if (!current.parent_id) break
      current = tree.nodes[current.parent_id]
    }
    return result
  }, [tree, selectedNodeId])

  if (path.length <= 1) return null

  return (
    <div className="flex-shrink-0 border-t border-white/[0.06] px-3 py-2 bg-bg-tertiary/30">
      <div className="flex items-center gap-1 overflow-x-auto scrollbar-thin">
        {path.map((node, i) => (
          <div key={node.node_id} className="flex items-center gap-1 flex-shrink-0">
            {i > 0 && <span className="text-[9px] text-surface-600">›</span>}
            <button
              onClick={() => onNodeClick(node.node_id)}
              title={node.hypothesis}
              className={`text-[9px] px-1.5 py-0.5 rounded transition-colors truncate max-w-[80px]
                ${node.node_id === selectedNodeId
                  ? 'text-accent-amber font-semibold'
                  : 'text-surface-500 hover:text-surface-200'
                }`}
            >
              {i === 0 ? 'Root' : node.hypothesis.slice(0, 10) + (node.hypothesis.length > 10 ? '…' : '')}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
