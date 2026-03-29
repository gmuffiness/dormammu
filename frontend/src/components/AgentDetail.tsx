import type { RenderedAgent, TurnRecord } from '../types/simulation'

interface Props {
  agent: RenderedAgent
  onClose: () => void
  /** Recent turns for memory viewer (last N) */
  recentTurns?: TurnRecord[]
  /** All agent names: id → name */
  allAgentNames?: Record<string, string>
  /** Relationship scores from WorldState */
  relationships?: Record<string, number>
}

function TraitBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100)
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-surface-300 font-mono w-20 truncate capitalize">{label}</span>
      <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, #e8963c, #f0a030)`,
          }}
        />
      </div>
      <span className="text-[10px] text-surface-400 font-mono w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function AgentDetail({ agent, onClose, recentTurns, allAgentNames, relationships }: Props) {
  const snap = agent.snapshot
  const traits = (snap.traits as Record<string, number>) ?? {}
  const goals = (snap.goals as string[]) ?? []
  const fears = (snap.fears as string[]) ?? []
  const values = (snap.values as string[]) ?? []
  const mood = typeof snap.mood === 'number' ? snap.mood : null
  const energy = typeof snap.energy === 'number' ? snap.energy : null

  return (
    <div className="absolute top-12 right-4 w-72 bg-bg-secondary/95 backdrop-blur-sm rounded-xl border border-white/[0.08]
                    z-20 shadow-2xl overflow-hidden font-body">
      {/* Header accent */}
      <div className="h-1.5 w-full" style={{ background: agent.color }} />

      <div className="p-3.5 border-b border-white/[0.06] flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-3.5 h-3.5 rounded" style={{ background: agent.color }} />
            <span className="text-sm font-display font-semibold text-surface-50">{agent.name}</span>
          </div>
          {snap.age && (
            <div className="text-[11px] text-surface-400 font-mono mt-0.5">Age {snap.age}</div>
          )}
        </div>
        <button
          onClick={onClose}
          className="text-surface-400 hover:text-surface-50 text-lg leading-none transition-colors w-6 h-6
                     flex items-center justify-center rounded hover:bg-white/[0.06]"
        >
          ×
        </button>
      </div>

      <div className="p-3.5 max-h-96 overflow-y-auto scrollbar-thin space-y-4">
        {/* Backstory */}
        {snap.backstory && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Backstory
            </div>
            <p className="text-xs text-surface-200 leading-relaxed">{snap.backstory as string}</p>
          </div>
        )}

        {/* State bars */}
        {(mood !== null || energy !== null) && (
          <div className="space-y-2">
            {mood !== null && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-surface-300 font-mono w-14">Mood</span>
                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-400 rounded-full transition-all duration-500" style={{ width: `${mood * 100}%` }} />
                </div>
                <span className="text-[10px] text-surface-400 font-mono w-8 text-right">{Math.round(mood * 100)}%</span>
              </div>
            )}
            {energy !== null && (
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-surface-300 font-mono w-14">Energy</span>
                <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                  <div className="h-full bg-accent-amber rounded-full transition-all duration-500" style={{ width: `${energy * 100}%` }} />
                </div>
                <span className="text-[10px] text-surface-400 font-mono w-8 text-right">{Math.round(energy * 100)}%</span>
              </div>
            )}
          </div>
        )}

        {/* Traits — Radar chart for Big-5, fallback to bars */}
        {Object.keys(traits).length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-2">
              Personality
            </div>
            <div className="space-y-1.5">
              {Object.entries(traits).map(([k, v]) => (
                <TraitBar key={k} label={k} value={v} />
              ))}
            </div>
          </div>
        )}

        {/* Goals */}
        {goals.length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Goals
            </div>
            <ol className="space-y-1">
              {goals.map((g, i) => (
                <li key={i} className="flex gap-2 text-xs text-surface-200">
                  <span className="text-surface-400 flex-shrink-0">{i + 1}.</span>
                  {g}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Fears */}
        {fears.length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Fears
            </div>
            <div className="flex flex-wrap gap-1">
              {fears.map((f, i) => (
                <span key={i} className="text-[10px] bg-red-500/[0.08] text-red-400/80 border border-red-500/15 rounded px-2 py-0.5">
                  {f}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Values */}
        {values.length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Values
            </div>
            <div className="flex flex-wrap gap-1">
              {values.map((v, i) => (
                <span key={i} className="text-[10px] bg-accent-amber/[0.08] text-accent-amber/80 border border-accent-amber/15 rounded px-2 py-0.5">
                  {v}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Speech style */}
        {snap.speech_style && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Speech
            </div>
            <span className="text-xs text-surface-300 italic">{snap.speech_style as string}</span>
          </div>
        )}

        {/* Rolling Memory Viewer — last 5 turns */}
        {recentTurns && recentTurns.length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Recent Actions
            </div>
            <div className="space-y-1.5 max-h-32 overflow-y-auto scrollbar-thin">
              {recentTurns.slice(-5).reverse().map(turn => {
                const actions = turn.agent_actions ?? {}
                const action = actions[agent.id]
                if (!action) return null
                return (
                  <div key={turn.turn_number} className="flex gap-2 text-[10px]">
                    <span className="text-surface-500 font-mono flex-shrink-0 w-6">T{turn.turn_number}</span>
                    <div className="flex-1 text-surface-300">
                      {action.speech && (
                        <span className="text-surface-200 italic">&ldquo;{(action.speech as string).slice(0, 60)}&rdquo; </span>
                      )}
                      {action.action_type && (
                        <span className="text-surface-400">[{action.action_type}]</span>
                      )}
                      {!action.speech && !action.action_type && (
                        <span className="text-surface-500">idle</span>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {/* Relationships */}
        {relationships && Object.keys(relationships).length > 0 && (
          <div>
            <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em] mb-1.5">
              Relationships
            </div>
            <div className="space-y-1.5">
              {Object.entries(relationships).map(([targetId, score]) => (
                <div key={targetId} className="flex items-center gap-2">
                  <span className="text-[10px] text-surface-300 font-mono w-20 truncate">
                    {allAgentNames?.[targetId] ?? targetId.slice(0, 8)}
                  </span>
                  <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.max(0, Math.min(100, ((score + 1) / 2) * 100))}%`,
                        background: score >= 0
                          ? `linear-gradient(90deg, #34d399, #6ee7b7)`
                          : `linear-gradient(90deg, #ef4444, #f87171)`,
                      }}
                    />
                  </div>
                  <span className="text-[10px] text-surface-400 font-mono w-8 text-right">
                    {score > 0 ? '+' : ''}{score.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
