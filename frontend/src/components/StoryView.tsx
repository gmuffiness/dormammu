import { useState, useEffect } from 'react'
import { api } from '../api/client'
import DecisionTree from './DecisionTree'
import BreadcrumbTrail from './BreadcrumbTrail'
import MetricsDashboard from './MetricsDashboard'
import WorldStatePanel from './WorldStatePanel'
import type { TurnRecord, ScenarioTreeData, RenderedAgent } from '../types/simulation'

interface ResearchData {
  topic: string
  summary: string
  key_characters?: { name: string; role: string; description: string }[]
  key_factions?: { name: string; stance: string; goals: string }[]
  world_setting?: string
  conflict_structure?: string
  historical_context?: string
  thematic_elements?: string[]
  topic_specific_metrics?: { name: string; description: string }[]
}

interface Props {
  simulationId: string
  turns: TurnRecord[]
  currentTurnIndex: number
  tree: ScenarioTreeData | null
  agents: RenderedAgent[]
  onSeek: (index: number) => void
}

export default function StoryView({ simulationId, turns, currentTurnIndex, tree, agents, onSeek }: Props) {
  const [research, setResearch] = useState<ResearchData | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [sideTab, setSideTab] = useState<'node' | 'world' | 'research' | 'characters' | 'metrics'>('research')
  // All turns expanded by default
  const [collapsedTurns, setCollapsedTurns] = useState<Set<number>>(new Set())

  useEffect(() => {
    if (simulationId) {
      api.getResearch(simulationId).then(setResearch).catch(() => {})
    }
  }, [simulationId])

  const selectedNode = selectedNodeId && tree ? tree.nodes[selectedNodeId] : null

  // Filter turns belonging to selected node
  const nodeTurns = selectedNodeId
    ? turns.filter(t => {
        try {
          // API returns parsed agent_actions, but raw DB has agent_actions_json
          let actions: Record<string, unknown> = {}
          if (t.agent_actions && typeof t.agent_actions === 'object') {
            actions = t.agent_actions as Record<string, unknown>
          } else if (typeof t.agent_actions_json === 'string') {
            actions = JSON.parse(t.agent_actions_json)
          }
          return actions._node_id === selectedNodeId
        } catch { return false }
      })
    : turns

  const toggleTurn = (turnNum: number) => {
    setCollapsedTurns(prev => {
      const next = new Set(prev)
      if (next.has(turnNum)) next.delete(turnNum)
      else next.add(turnNum)
      return next
    })
  }

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── Main: Decision Tree ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Breadcrumb Navigation */}
        <BreadcrumbTrail
          tree={tree}
          selectedNodeId={selectedNodeId}
          onNodeClick={(nodeId) => {
            setSelectedNodeId(nodeId)
            setSideTab('node')
          }}
        />

        {/* Tree Visualization */}
        <DecisionTree
          tree={tree}
          selectedNodeId={selectedNodeId}
          onNodeClick={(nodeId) => {
            setSelectedNodeId(nodeId)
            setSideTab('node')
          }}
        />
      </div>

      {/* ── Right sidebar: context panel ── */}
      <div className="w-96 flex-shrink-0 border-l border-white/[0.06] flex flex-col overflow-hidden bg-bg-secondary">
        {/* Tab bar */}
        <div className="flex border-b border-white/[0.06] flex-shrink-0">
          {(['node', 'world', 'research', 'characters', 'metrics'] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setSideTab(tab)}
              className={`flex-1 text-[9px] uppercase tracking-[0.08em] font-display font-semibold py-2.5 transition-all
                ${sideTab === tab
                  ? 'text-accent-amber border-b-2 border-accent-amber'
                  : 'text-surface-400 hover:text-surface-200'
                }`}
            >
              {tab === 'node'
                ? (selectedNode ? 'Detail' : 'Node')
                : tab === 'world'
                ? 'World'
                : tab === 'research'
                ? 'Research'
                : tab === 'characters'
                ? 'Cast'
                : 'Metrics'}
            </button>
          ))}
        </div>

        {/* Tab content — World State uses its own scroll container */}
        {sideTab === 'world' && (
          <div className="flex-1 overflow-hidden">
            <WorldStatePanel
              tree={tree}
              simulationId={simulationId}
              selectedNodeId={selectedNodeId}
              onSelectNode={(nodeId) => {
                setSelectedNodeId(nodeId)
              }}
            />
          </div>
        )}

        {/* Tab content */}
        <div className={`flex-1 overflow-y-auto scrollbar-thin p-4 ${sideTab === 'world' ? 'hidden' : ''}`}>
          {/* ── Node Detail Tab ── */}
          {sideTab === 'node' && (
            selectedNode ? (
              <div className="animate-fade-in space-y-4">
                {/* Node header */}
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                      selectedNode.status === 'complete' ? 'bg-emerald-500/15 text-emerald-400' :
                      selectedNode.status === 'pruned' ? 'bg-red-500/10 text-red-400/70' :
                      selectedNode.status === 'in_progress' ? 'bg-amber-500/15 text-amber-400' :
                      'bg-white/[0.06] text-surface-400'
                    }`}>
                      {selectedNode.status}
                    </span>
                    <span className="text-[10px] font-mono text-surface-400">depth {selectedNode.depth}</span>
                    {selectedNode.score != null && (
                      <span className="text-[10px] font-mono text-accent-amber">score {selectedNode.score.toFixed(2)}</span>
                    )}
                  </div>
                  <h3 className="text-sm text-surface-50 font-display font-semibold leading-snug">
                    {selectedNode.hypothesis}
                  </h3>
                </div>

                {/* Turns for this node */}
                <div>
                  <div className="text-[10px] text-accent-amber font-display font-semibold mb-2 uppercase tracking-[0.15em]">
                    Turns ({nodeTurns.length})
                  </div>
                  {nodeTurns.length === 0 && (
                    <p className="text-xs text-surface-400 italic">No turn data for this node. Execute the node to generate events.</p>
                  )}
                  {nodeTurns.map((turn) => {
                    const isExpanded = !collapsedTurns.has(turn.turn_number)
                    const events = turn.events ?? []
                    return (
                      <div key={turn.turn_number} className="mb-1">
                        <button
                          onClick={() => { onSeek(turns.indexOf(turn)); toggleTurn(turn.turn_number) }}
                          className={`w-full text-left flex items-start gap-2.5 p-2.5 rounded-lg transition-all
                            ${turns.indexOf(turn) === currentTurnIndex
                              ? 'bg-accent-amber/[0.06] border border-accent-amber/20'
                              : 'hover:bg-white/[0.03] border border-transparent'
                            }`}
                        >
                          <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5
                            ${turns.indexOf(turn) === currentTurnIndex
                              ? 'bg-accent-amber/20 border border-accent-amber/40'
                              : 'bg-white/[0.04] border border-white/[0.08]'
                            }`}
                          >
                            <span className={`text-[8px] font-mono font-bold ${turns.indexOf(turn) === currentTurnIndex ? 'text-accent-amber' : 'text-surface-400'}`}>
                              {turn.turn_number}
                            </span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-0.5">
                              <span className={`text-[11px] font-display font-semibold ${turns.indexOf(turn) === currentTurnIndex ? 'text-accent-amber' : 'text-surface-200'}`}>
                                Year {turn.year}
                              </span>
                              <span className="text-[10px] text-surface-500 font-mono">{events.length} events</span>
                            </div>
                            {isExpanded ? (
                              <div className="animate-fade-in">
                                <p className="text-[11px] text-surface-100 leading-relaxed whitespace-pre-wrap">
                                  {turn.narrative || <span className="text-surface-400 italic">No narrative</span>}
                                </p>
                                {events.length > 0 && (
                                  <div className="mt-2 space-y-1">
                                    {events.map((ev, i) => {
                                      const attrs = (ev as Record<string, unknown>).attributes as Record<string, number> | undefined
                                      return (
                                        <div key={i} className="p-2 rounded-lg border border-white/[0.04] bg-white/[0.02]">
                                          <div className="flex gap-1.5 items-start">
                                            <span className="text-[10px] flex-shrink-0">
                                              {ev.type?.includes('interact') ? '💬' : ev.type?.includes('cooperat') ? '🤝' : ev.type?.includes('conflict') ? '⚔️' : ev.type?.includes('discover') ? '✨' : ev.type?.includes('observ') ? '👁' : ev.type?.includes('movement') ? '🚶' : ev.type?.includes('world') ? '🌍' : '◎'}
                                            </span>
                                            <div className="flex-1">
                                              <p className="text-[10px] text-surface-200 leading-snug">{ev.description}</p>
                                              {attrs && Object.keys(attrs).length > 0 && (
                                                <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
                                                  {Object.entries(attrs).map(([key, val]) => (
                                                    <div key={key} className="flex items-center gap-1">
                                                      <span className="text-[9px] text-surface-400">{key}</span>
                                                      <div className="w-12 h-1 bg-white/[0.06] rounded-full overflow-hidden">
                                                        <div
                                                          className="h-full rounded-full"
                                                          style={{
                                                            width: `${Math.abs(val) * 100}%`,
                                                            background: val < 0 ? '#ef4444' : val > 0.6 ? '#34d399' : '#e8963c'
                                                          }}
                                                        />
                                                      </div>
                                                      <span className="text-[9px] font-mono text-surface-500">{val.toFixed(1)}</span>
                                                    </div>
                                                  ))}
                                                </div>
                                              )}
                                            </div>
                                          </div>
                                        </div>
                                      )
                                    })}
                                  </div>
                                )}
                              </div>
                            ) : (
                              <p className="text-[11px] text-surface-300 line-clamp-2">
                                {turn.narrative?.slice(0, 120) || 'No narrative'}
                                {(turn.narrative?.length ?? 0) > 120 ? '…' : ''}
                              </p>
                            )}
                          </div>
                        </button>
                      </div>
                    )
                  })}
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center h-48 text-center">
                <div className="w-12 h-12 rounded-xl bg-white/[0.03] border border-white/[0.06] flex items-center justify-center mb-3">
                  <span className="text-xl text-surface-400">🌳</span>
                </div>
                <p className="text-xs text-surface-400">Click a node in the tree to see its details</p>
              </div>
            )
          )}

          {/* ── Research Tab ── */}
          {sideTab === 'research' && (
            research && research.summary ? (
              <div className="animate-fade-in space-y-4">
                <p className="text-[11px] text-surface-200 leading-relaxed">{research.summary}</p>

                {research.world_setting && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1">World Setting</div>
                    <p className="text-[11px] text-surface-300 leading-relaxed">{research.world_setting}</p>
                  </div>
                )}

                {research.conflict_structure && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1">Conflict</div>
                    <p className="text-[11px] text-surface-300 leading-relaxed">{research.conflict_structure}</p>
                  </div>
                )}

                {research.historical_context && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1">Historical Parallels</div>
                    <p className="text-[11px] text-surface-300 leading-relaxed">{research.historical_context}</p>
                  </div>
                )}

                {research.key_factions && research.key_factions.length > 0 && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1.5">Factions</div>
                    {research.key_factions.map((f, i) => (
                      <div key={i} className="mb-2 p-2.5 rounded-lg border border-white/[0.04] bg-white/[0.02]">
                        <div className="text-[11px] text-surface-100 font-semibold">{f.name}</div>
                        <div className="text-[10px] text-surface-400 mt-0.5">{f.stance} — {f.goals}</div>
                      </div>
                    ))}
                  </div>
                )}

                {research.thematic_elements && research.thematic_elements.length > 0 && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1.5">Themes</div>
                    <div className="flex flex-wrap gap-1.5">
                      {research.thematic_elements.map((t, i) => (
                        <span key={i} className="text-[10px] text-surface-300 bg-white/[0.04] border border-white/[0.06] rounded-full px-2.5 py-0.5">
                          {t}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {research.topic_specific_metrics && research.topic_specific_metrics.length > 0 && (
                  <div>
                    <div className="text-[10px] text-surface-400 font-semibold mb-1.5">Domain Metrics</div>
                    {research.topic_specific_metrics.map((m, i) => (
                      <div key={i} className="text-[10px] text-surface-300 mb-1">
                        • <span className="text-surface-200 font-semibold">{m.name}</span>: {m.description}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <p className="text-xs text-surface-400 italic text-center mt-8">No research data available.</p>
            )
          )}

          {/* ── Characters Tab ── */}
          {sideTab === 'characters' && (
            <div className="animate-fade-in space-y-3">
              {agents.length === 0 && research?.key_characters ? (
                // Show research characters if no runtime agents
                research.key_characters.map((c, i) => (
                  <div key={i} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                    <div className="text-xs text-surface-50 font-semibold">{c.name}</div>
                    <div className="text-[10px] text-accent-amber/70 mt-0.5">{c.role}</div>
                    <p className="text-[11px] text-surface-300 leading-relaxed mt-1.5">{c.description}</p>
                  </div>
                ))
              ) : (
                agents.map(agent => (
                  <div key={agent.id} className="p-3 rounded-lg border border-white/[0.06] bg-white/[0.02]">
                    <div className="flex items-center gap-2 mb-1.5">
                      <div className="w-4 h-4 rounded" style={{ background: agent.color }} />
                      <span className="text-xs text-surface-50 font-semibold">{agent.name}</span>
                    </div>
                    {agent.snapshot && (
                      <div className="flex gap-4 mt-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] text-surface-400">Mood</span>
                          <div className="w-16 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-emerald-400" style={{ width: `${(agent.snapshot.mood ?? 0.5) * 100}%` }} />
                          </div>
                        </div>
                        <div className="flex items-center gap-1.5">
                          <span className="text-[10px] text-surface-400">Energy</span>
                          <div className="w-16 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                            <div className="h-full rounded-full bg-accent-amber" style={{ width: `${(agent.snapshot.energy ?? 0.5) * 100}%` }} />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))
              )}
              {agents.length === 0 && !research?.key_characters && (
                <p className="text-xs text-surface-400 italic text-center mt-8">No character data available.</p>
              )}
            </div>
          )}

          {/* ── Metrics Tab ── */}
          {sideTab === 'metrics' && (
            <div className="animate-fade-in -mx-4 -mt-4">
              <MetricsDashboard tree={tree} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
