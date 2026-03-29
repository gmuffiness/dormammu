import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { Simulation } from '../types/simulation'

function StatusIndicator({ status }: { status: string }) {
  const config: Record<string, { color: string; label: string }> = {
    complete: { color: '#34d399', label: 'Complete' },
    running: { color: '#f0a030', label: 'Running' },
    failed: { color: '#ef4444', label: 'Failed' },
  }
  const c = config[status] ?? { color: '#585450', label: status }

  return (
    <div className="flex items-center gap-1.5 flex-shrink-0">
      <div
        className="w-1.5 h-1.5 rounded-full"
        style={{ background: c.color, boxShadow: `0 0 6px ${c.color}40` }}
      />
      <span
        className="text-[10px] font-mono uppercase tracking-widest"
        style={{ color: c.color }}
      >
        {c.label}
      </span>
    </div>
  )
}

function MetricCell({ value, label, unit }: { value: string | number; label: string; unit?: string }) {
  return (
    <div className="flex flex-col items-center px-3 py-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
      <span className="text-[15px] font-mono font-semibold text-surface-50 tabular-nums leading-none">
        {unit}{value}
      </span>
      <span className="text-[9px] text-surface-300 uppercase tracking-[0.15em] mt-1.5 font-body">
        {label}
      </span>
    </div>
  )
}

function SimCard({ sim, onClick, index }: { sim: Simulation; onClick: () => void; index: number }) {
  const criteria =
    typeof sim.evaluation_criteria === 'string'
      ? (() => { try { return JSON.parse(sim.evaluation_criteria) } catch { return [sim.evaluation_criteria] } })()
      : sim.evaluation_criteria ?? []

  const date = new Date(sim.created_at)
  const formatted = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    + ' · '
    + date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false })

  return (
    <button
      onClick={onClick}
      className="group relative text-left w-full rounded-xl bg-bg-card border border-white/[0.06]
                 hover:border-accent-amber/20 hover:bg-bg-hover
                 transition-all duration-300 ease-out overflow-hidden
                 animate-slide-up"
      style={{ animationDelay: `${index * 70}ms` }}
    >
      {/* Top hover accent */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-accent-amber/40 to-transparent
                      opacity-0 group-hover:opacity-100 transition-opacity duration-500" />

      <div className="p-5">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <h2 className="font-display text-[15px] font-semibold text-surface-50 leading-snug line-clamp-2
                         group-hover:text-accent-amber transition-colors duration-300">
            {sim.topic || '(Untitled simulation)'}
          </h2>
          <StatusIndicator status={sim.status} />
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-3 gap-2 mb-4">
          <MetricCell value={sim.turns ?? 0} label="Turns" />
          <MetricCell value={sim.max_depth ?? 0} label="Depth" />
          <MetricCell value={(sim.total_cost_usd ?? 0).toFixed(3)} label="Cost" unit="$" />
        </div>

        {/* Criteria tags */}
        {criteria.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {(criteria as string[]).slice(0, 3).map((c, i) => (
              <span
                key={i}
                className="text-[10px] font-body text-surface-200 bg-white/[0.03] border border-white/[0.05]
                           rounded-full px-2.5 py-0.5 truncate max-w-[160px]"
              >
                {c}
              </span>
            ))}
            {criteria.length > 3 && (
              <span className="text-[10px] text-surface-400 font-mono px-1">+{criteria.length - 3}</span>
            )}
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-white/[0.04]">
          <span className="text-[11px] font-mono text-surface-400">{formatted}</span>
          <span className="text-[11px] text-surface-300 opacity-0 group-hover:opacity-100
                           -translate-x-1 group-hover:translate-x-0
                           transition-all duration-300 font-body">
            Open &rarr;
          </span>
        </div>
      </div>
    </button>
  )
}

export default function Dashboard() {
  const [sims, setSims] = useState<Simulation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const navigate = useNavigate()

  const loadSims = () => {
    api.getSimulations()
      .then(setSims)
      .catch(e => setError(String(e)))
      .finally(() => { setLoading(false); setRefreshing(false) })
  }

  useEffect(() => { loadSims() }, [])

  const handleRefresh = () => {
    setRefreshing(true)
    setError(null)
    loadSims()
  }

  return (
    <div className="min-h-screen bg-bg-primary overflow-y-auto scrollbar-thin font-body">
      {/* Background texture */}
      <div className="fixed inset-0 bg-dot-grid pointer-events-none" />

      {/* Ambient top glow */}
      <div
        className="fixed top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] pointer-events-none"
        style={{ background: 'radial-gradient(ellipse at center top, rgba(232, 150, 60, 0.035) 0%, transparent 70%)' }}
      />

      <div className="relative max-w-5xl mx-auto px-6 py-10">
        {/* ── Header ── */}
        <header className="mb-12 animate-fade-in">
          <div className="flex items-end justify-between">
            <div className="flex items-center gap-4">
              {/* Logo mark */}
              <div className="relative w-11 h-11 rounded-xl bg-accent-amber/10 border border-accent-amber/20
                              flex items-center justify-center overflow-hidden flex-shrink-0">
                <div className="absolute inset-0 bg-gradient-to-br from-accent-amber/20 to-transparent" />
                <span className="relative font-display font-bold text-accent-amber text-xl leading-none">E</span>
              </div>
              <div>
                <h1 className="font-display text-[22px] font-bold text-surface-50 tracking-tight leading-none">
                  Emergent Simulation Engine
                </h1>
                <p className="text-[13px] text-surface-400 font-body mt-1">
                  DFS scenario explorer · Living world simulations
                </p>
              </div>
            </div>

            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="btn-ghost flex items-center gap-2 flex-shrink-0"
            >
              <svg
                className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`}
                viewBox="0 0 16 16"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.5"
              >
                <path d="M2.5 8a5.5 5.5 0 0 1 9.6-3.6M13.5 8a5.5 5.5 0 0 1-9.6 3.6" strokeLinecap="round" />
                <path d="M12.5 2.5v2.5H10M3.5 13.5V11H6" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
              Refresh
            </button>
          </div>

          {/* Divider */}
          <div className="mt-8 h-px bg-gradient-to-r from-accent-amber/20 via-white/[0.06] to-transparent" />
        </header>

        {/* ── Loading ── */}
        {loading && (
          <div className="flex flex-col items-center justify-center h-64 animate-fade-in">
            <div className="relative w-10 h-10 mb-5">
              <div className="absolute inset-0 rounded-full border-2 border-white/[0.06]" />
              <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent-amber/80 animate-spin" />
            </div>
            <span className="text-sm text-surface-400 font-body">Loading simulations…</span>
          </div>
        )}

        {/* ── Error ── */}
        {error && (
          <div className="rounded-xl border border-red-500/15 bg-red-500/[0.04] p-5 mb-8 animate-fade-in">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-red-400" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <circle cx="8" cy="8" r="6.5" />
                  <path d="M8 5v3.5M8 10.5v.5" strokeLinecap="round" />
                </svg>
              </div>
              <div>
                <p className="text-sm text-red-400 font-body font-medium">Failed to connect to backend</p>
                <p className="text-xs text-red-400/50 font-body mt-1 break-all">{error}</p>
                <p className="text-xs text-surface-400 font-mono mt-2">
                  Make sure the FastAPI server is running at localhost:8000
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ── Empty ── */}
        {!loading && !error && sims.length === 0 && (
          <div className="flex flex-col items-center justify-center h-72 animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-white/[0.02] border border-white/[0.06]
                            flex items-center justify-center mb-5">
              <svg className="w-7 h-7 text-surface-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8v4l2.5 1.5" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="text-base text-surface-200 font-display font-semibold mb-1.5">No simulations yet</p>
            <p className="text-sm text-surface-400 font-body">
              Run{' '}
              <code className="font-mono text-accent-amber/80 bg-accent-amber/[0.08] px-1.5 py-0.5 rounded text-xs">
                ese run
              </code>
              {' '}to start your first simulation
            </p>
          </div>
        )}

        {/* ── Grid ── */}
        {!loading && sims.length > 0 && (
          <>
            <div className="flex items-center gap-3 mb-6 animate-fade-in">
              <span className="text-sm text-surface-300 font-body">
                {sims.length} simulation{sims.length !== 1 ? 's' : ''}
              </span>
              <div className="h-px flex-1 bg-white/[0.04]" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {sims.map((sim, i) => (
                <SimCard
                  key={sim.id}
                  sim={sim}
                  index={i}
                  onClick={() => navigate(`/simulation/${sim.id}`)}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
