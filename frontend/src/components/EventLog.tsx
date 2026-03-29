import { useState } from 'react'
import type { TurnRecord, SimEvent, RenderedAgent } from '../types/simulation'

const EVENT_ICONS: Record<string, string> = {
  interaction: '💬',
  observation: '👁',
  movement: '🚶',
  conflict: '⚔️',
  cooperation: '🤝',
  discovery: '✨',
  default: '◎',
}

function eventIcon(ev: SimEvent): string {
  const type = (ev.type ?? '').toLowerCase()
  for (const [k, v] of Object.entries(EVENT_ICONS)) {
    if (type.includes(k)) return v
  }
  const desc = (ev.description ?? '').toLowerCase()
  if (desc.includes('speak') || desc.includes('said') || desc.includes('told')) return '💬'
  if (desc.includes('attack') || desc.includes('fight')) return '⚔️'
  if (desc.includes('help') || desc.includes('cooperat')) return '🤝'
  if (desc.includes('mov') || desc.includes('walk') || desc.includes('travel')) return '🚶'
  if (desc.includes('observ') || desc.includes('watch')) return '👁'
  return EVENT_ICONS.default
}

interface Props {
  currentTurn: TurnRecord | null
  agents: RenderedAgent[]
  onAgentClick: (id: string) => void
}

export default function EventLog({ currentTurn, agents, onAgentClick }: Props) {
  const [narrativeExpanded, setNarrativeExpanded] = useState(false)
  const events = currentTurn?.events ?? []
  const agentMap = new Map(agents.map(a => [a.id, a]))

  return (
    <div className="flex flex-col h-full bg-bg-secondary border-l border-white/[0.06] overflow-hidden font-body">
      {/* Narrative panel */}
      <div className="p-3.5 border-b border-white/[0.06] flex-shrink-0">
        <div className="text-[10px] text-accent-amber font-display font-semibold mb-1.5 uppercase tracking-[0.15em]">
          Narrative
        </div>
        <div key={currentTurn?.turn_number} className="animate-fade-in">
          <p className={`text-xs text-surface-100 leading-relaxed min-h-[48px] ${narrativeExpanded ? '' : 'line-clamp-5'}`}>
            {currentTurn?.narrative || <span className="text-surface-400 italic">No narrative for this turn.</span>}
          </p>
          {currentTurn?.narrative && currentTurn.narrative.length > 200 && (
            <button
              onClick={() => setNarrativeExpanded(prev => !prev)}
              className="text-[10px] text-accent-amber/70 hover:text-accent-amber mt-1 transition-colors"
            >
              {narrativeExpanded ? '▲ 접기' : '▼ 더보기'}
            </button>
          )}
        </div>
      </div>

      {/* Agent list */}
      <div className="p-3.5 border-b border-white/[0.06] flex-shrink-0">
        <div className="text-[10px] text-accent-amber font-display font-semibold mb-2.5 uppercase tracking-[0.15em]">
          Agents
        </div>
        <div className="flex flex-col gap-1">
          {agents.map(agent => {
            const mood = typeof agent.snapshot?.mood === 'number' ? agent.snapshot.mood : 0.5
            const energy = typeof agent.snapshot?.energy === 'number' ? agent.snapshot.energy : 0.5
            return (
              <button
                key={agent.id}
                onClick={() => onAgentClick(agent.id)}
                className="flex items-center gap-2 hover:bg-white/[0.04] rounded-lg p-1.5 transition-colors text-left w-full group"
              >
                <div
                  className="w-3 h-3 rounded flex-shrink-0"
                  style={{ background: agent.color, imageRendering: 'pixelated' }}
                />
                <span className="text-xs text-surface-100 flex-1 truncate group-hover:text-surface-50 transition-colors">
                  {agent.name}
                </span>
                <div className="flex gap-1.5 flex-shrink-0">
                  <div className="w-10 h-1.5 bg-white/[0.06] rounded-full overflow-hidden" title="Mood">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${mood * 100}%`, background: '#34d399' }}
                    />
                  </div>
                  <div className="w-10 h-1.5 bg-white/[0.06] rounded-full overflow-hidden" title="Energy">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{ width: `${energy * 100}%`, background: '#e8963c' }}
                    />
                  </div>
                </div>
              </button>
            )
          })}
          {agents.length === 0 && (
            <span className="text-xs text-surface-400 italic">No agents</span>
          )}
        </div>
      </div>

      {/* Events list */}
      <div className="flex-1 overflow-y-auto scrollbar-thin p-3.5">
        <div className="text-[10px] text-accent-amber font-display font-semibold mb-2.5 uppercase tracking-[0.15em]">
          Events ({events.length})
        </div>
        {events.length === 0 && (
          <div className="text-xs text-surface-400 italic">No events this turn.</div>
        )}
        <div className="flex flex-col gap-2.5">
          {events.map((ev, i) => {
            const participants = ev.participants ?? []
            return (
              <div key={i} className="flex gap-2 group">
                <span className="text-sm flex-shrink-0 leading-none mt-0.5">{eventIcon(ev)}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-surface-100 leading-snug">{ev.description}</p>
                  {participants.length > 0 && (
                    <div className="flex gap-1.5 mt-1 flex-wrap">
                      {participants.map(pid => {
                        const ag = agentMap.get(pid)
                        return ag ? (
                          <button
                            key={pid}
                            onClick={() => onAgentClick(pid)}
                            className="flex items-center gap-1 hover:opacity-80 transition-opacity"
                          >
                            <div
                              className="w-2 h-2 rounded-sm"
                              style={{ background: ag.color }}
                            />
                            <span className="text-[10px] text-surface-300 hover:text-surface-100 transition-colors">
                              {ag.name}
                            </span>
                          </button>
                        ) : (
                          <span key={pid} className="text-[10px] text-surface-400">{pid}</span>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
