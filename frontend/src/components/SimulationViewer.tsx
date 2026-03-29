import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSimulation } from '../hooks/useSimulation'
import { useScenarioTree } from '../hooks/useScenarioTree'
import { useReplay } from '../hooks/useReplay'
import { api } from '../api/client'
import TimelineControls from './TimelineControls'
import StoryView from './StoryView'
import type { RenderedAgent } from '../types/simulation'

function StatusDot({ status }: { status: string }) {
  const colors: Record<string, string> = {
    complete: '#34d399',
    running: '#f0a030',
    failed: '#ef4444',
  }
  const color = colors[status] ?? '#585450'
  return (
    <div className="flex items-center gap-1.5">
      <div
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: color, boxShadow: `0 0 6px ${color}40` }}
      />
      <span className="text-[10px] font-mono uppercase tracking-widest" style={{ color }}>
        {status}
      </span>
    </div>
  )
}

export default function SimulationViewer() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { simulation, turns, worldStates, tree: initialTree, loading, error } = useSimulation(id)
  // useScenarioTree provides auto-refresh (5 s) so metrics stay live while the simulation runs
  const { tree: liveTree } = useScenarioTree(id, 5000)
  // Prefer the live (auto-refreshed) tree; fall back to the initial fetch while liveTree loads
  const tree = liveTree ?? initialTree
  const replay = useReplay(turns)

  const [fetchingWs, setFetchingWs] = useState(false)
  const [renderedAgents] = useState<RenderedAgent[]>([])

  // Fetch world state when turn changes (keeps fetchingWs indicator accurate)
  useEffect(() => {
    if (!id || !replay.currentTurn) return
    const turnNum = replay.currentTurn.turn_number

    if (worldStates.has(turnNum)) return

    setFetchingWs(true)
    api.getWorldState(id, turnNum)
      .catch(() => {})
      .finally(() => setFetchingWs(false))
  }, [id, replay.currentTurn, worldStates])

  if (loading) {
    return (
      <div className="h-screen bg-bg-primary flex flex-col items-center justify-center font-body">
        <div className="relative w-10 h-10 mb-5">
          <div className="absolute inset-0 rounded-full border-2 border-white/[0.06]" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent-amber/80 animate-spin" />
        </div>
        <span className="text-sm text-surface-300">Loading simulation…</span>
      </div>
    )
  }

  if (error || !simulation) {
    return (
      <div className="h-screen bg-bg-primary flex flex-col items-center justify-center gap-4 font-body">
        <div className="w-12 h-12 rounded-xl bg-red-500/10 flex items-center justify-center mb-2">
          <svg className="w-5 h-5 text-red-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="8" cy="8" r="6.5" />
            <path d="M8 5v3.5M8 10.5v.5" strokeLinecap="round" />
          </svg>
        </div>
        <p className="text-sm text-red-400">{error || 'Simulation not found'}</p>
        <button onClick={() => navigate('/')} className="btn-ghost text-xs">
          &larr; Back to Dashboard
        </button>
      </div>
    )
  }

  return (
    <div className="h-screen bg-bg-primary flex flex-col overflow-hidden font-body">
      {/* ── Top bar ── */}
      <div className="flex items-center gap-3 px-4 h-11 bg-bg-secondary border-b border-white/[0.06] flex-shrink-0">
        <button
          onClick={() => navigate('/')}
          className="text-xs text-surface-400 hover:text-surface-50 transition-colors font-body flex items-center gap-1.5"
        >
          <svg className="w-3 h-3" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d="M7 2L3 6l4 4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Dormammu
        </button>
        <div className="w-px h-4 bg-white/[0.08]" />
        <h1 className="text-xs text-surface-50 font-display font-semibold truncate flex-1">
          {simulation.topic}
        </h1>
        <div className="flex items-center gap-3 flex-shrink-0">
          {fetchingWs && (
            <span className="text-[10px] text-surface-400 font-mono animate-pulse">syncing…</span>
          )}
          <span className="text-[10px] text-surface-400 font-mono">
            {simulation.turns ?? turns.length} turns · ${(simulation.total_cost_usd ?? 0).toFixed(4)}
          </span>
          <StatusDot status={simulation.status} />
        </div>
      </div>

      {/* ── Main content ── */}
      <div className="flex-1 flex overflow-hidden">
        <StoryView
          simulationId={id ?? ''}
          turns={turns}
          currentTurnIndex={replay.currentTurnIndex}
          tree={tree}
          agents={renderedAgents}
          onSeek={replay.seek}
        />
      </div>

      {/* ── Timeline ── */}
      <TimelineControls
        turns={turns}
        currentTurnIndex={replay.currentTurnIndex}
        isPlaying={replay.isPlaying}
        speed={replay.speed}
        onPlay={replay.play}
        onPause={replay.pause}
        onSeek={replay.seek}
        onSetSpeed={replay.setSpeed}
      />
    </div>
  )
}
