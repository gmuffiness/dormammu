import { useState, useMemo } from 'react'
import type { ScenarioTreeData, ScenarioNodeData, MetricKey } from '../types/simulation'
import { METRIC_WEIGHTS } from '../types/simulation'

interface Props {
  /** Tree state before evolve */
  beforeTree: ScenarioTreeData | null
  /** Tree state after evolve */
  afterTree: ScenarioTreeData | null
  /** Label for before state */
  beforeLabel?: string
  /** Label for after state */
  afterLabel?: string
  onClose: () => void
}

const METRIC_COLORS: Record<MetricKey, string> = {
  emergence: '#f59e0b',
  narrative: '#3b82f6',
  diversity: '#10b981',
  novelty: '#a855f7',
}

function computeTreeStats(tree: ScenarioTreeData | null) {
  if (!tree) return null
  const nodes = Object.values(tree.nodes)
  const completed = nodes.filter(n => n.status === 'complete')
  const pruned = nodes.filter(n => n.status === 'pruned')
  const maxDepth = nodes.reduce((max, n) => Math.max(max, n.depth), 0)

  const avgScores: Record<string, number> = {}
  const metricKeys: MetricKey[] = ['emergence', 'narrative', 'diversity', 'novelty']
  for (const key of metricKeys) {
    const scoreKey = `${key}_score` as keyof ScenarioNodeData
    const vals = completed
      .map(n => n[scoreKey])
      .filter((v): v is number => typeof v === 'number')
    avgScores[key] = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0
  }

  // Composite
  let composite = 0
  for (const key of metricKeys) {
    composite += (avgScores[key] ?? 0) * METRIC_WEIGHTS[key]
  }
  avgScores.composite = composite

  return {
    totalNodes: nodes.length,
    completed: completed.length,
    pruned: pruned.length,
    maxDepth,
    avgScores,
  }
}

function DeltaBadge({ before, after, label }: { before: number; after: number; label: string }) {
  const delta = after - before
  const pct = before > 0 ? Math.round((delta / before) * 100) : (after > 0 ? 100 : 0)
  const positive = delta >= 0
  return (
    <div className="flex items-center justify-between text-[10px]">
      <span className="text-surface-300 font-mono capitalize">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-surface-500 font-mono">{before.toFixed(2)}</span>
        <span className="text-surface-500">→</span>
        <span className="text-surface-200 font-mono">{after.toFixed(2)}</span>
        <span
          className={`font-mono font-semibold ${positive ? 'text-emerald-400' : 'text-red-400'}`}
        >
          {positive ? '+' : ''}{pct}%
        </span>
      </div>
    </div>
  )
}

function TreeMiniViz({ tree, label }: { tree: ScenarioTreeData | null; label: string }) {
  const stats = useMemo(() => computeTreeStats(tree), [tree])

  if (!tree || !stats) {
    return (
      <div className="flex-1 flex items-center justify-center text-surface-500 text-xs">
        No data
      </div>
    )
  }

  return (
    <div className="flex-1 p-3 space-y-3">
      <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em]">
        {label}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-lg font-display font-bold text-surface-50">{stats.totalNodes}</div>
          <div className="text-[9px] text-surface-400 font-mono">Nodes</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-lg font-display font-bold text-surface-50">{stats.maxDepth}</div>
          <div className="text-[9px] text-surface-400 font-mono">Max Depth</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-lg font-display font-bold text-emerald-400">{stats.completed}</div>
          <div className="text-[9px] text-surface-400 font-mono">Expanded</div>
        </div>
        <div className="bg-white/[0.03] rounded-lg p-2 text-center">
          <div className="text-lg font-display font-bold text-red-400">{stats.pruned}</div>
          <div className="text-[9px] text-surface-400 font-mono">Pruned</div>
        </div>
      </div>

      {/* Metric bars */}
      <div className="space-y-1.5">
        {(Object.keys(METRIC_WEIGHTS) as MetricKey[]).map(key => {
          const val = stats.avgScores[key] ?? 0
          return (
            <div key={key} className="flex items-center gap-2">
              <span className="text-[9px] text-surface-400 font-mono w-16 capitalize">{key}</span>
              <div className="flex-1 h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.round(val * 100)}%`,
                    background: METRIC_COLORS[key],
                  }}
                />
              </div>
              <span className="text-[9px] text-surface-400 font-mono w-8 text-right">
                {val.toFixed(2)}
              </span>
            </div>
          )
        })}
        {/* Composite */}
        <div className="flex items-center gap-2 pt-1 border-t border-white/[0.06]">
          <span className="text-[9px] text-surface-300 font-mono w-16 font-semibold">Composite</span>
          <div className="flex-1 h-2 bg-white/[0.06] rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.round((stats.avgScores.composite ?? 0) * 100)}%`,
                background: 'linear-gradient(90deg, #e8963c, #f0a030)',
              }}
            />
          </div>
          <span className="text-[10px] text-surface-200 font-mono w-8 text-right font-semibold">
            {(stats.avgScores.composite ?? 0).toFixed(2)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default function SplitCompareView({
  beforeTree,
  afterTree,
  beforeLabel = 'Before Evolve',
  afterLabel = 'After Evolve',
  onClose,
}: Props) {
  const [mode, setMode] = useState<'split' | 'delta'>('split')
  const beforeStats = useMemo(() => computeTreeStats(beforeTree), [beforeTree])
  const afterStats = useMemo(() => computeTreeStats(afterTree), [afterTree])

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center font-body">
      <div className="bg-bg-secondary rounded-xl border border-white/[0.08] shadow-2xl w-[700px] max-h-[80vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
          <div className="flex items-center gap-3">
            <h2 className="text-sm font-display font-semibold text-surface-50">
              Evolve Comparison
            </h2>
            <div className="flex bg-white/[0.04] rounded-lg p-0.5 gap-0.5">
              <button
                onClick={() => setMode('split')}
                className={`text-[10px] px-2 py-1 rounded transition-all font-mono ${
                  mode === 'split'
                    ? 'bg-accent-amber/15 text-accent-amber'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                Split View
              </button>
              <button
                onClick={() => setMode('delta')}
                className={`text-[10px] px-2 py-1 rounded transition-all font-mono ${
                  mode === 'delta'
                    ? 'bg-accent-amber/15 text-accent-amber'
                    : 'text-surface-400 hover:text-surface-200'
                }`}
              >
                Delta
              </button>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-surface-400 hover:text-surface-50 text-lg leading-none transition-colors w-6 h-6
                       flex items-center justify-center rounded hover:bg-white/[0.06]"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto">
          {mode === 'split' ? (
            <div className="flex divide-x divide-white/[0.06]">
              <TreeMiniViz tree={beforeTree} label={beforeLabel} />
              <TreeMiniViz tree={afterTree} label={afterLabel} />
            </div>
          ) : (
            <div className="p-4 space-y-3">
              <div className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em]">
                Improvement Delta
              </div>
              {beforeStats && afterStats ? (
                <>
                  <DeltaBadge
                    before={beforeStats.totalNodes}
                    after={afterStats.totalNodes}
                    label="Total Nodes"
                  />
                  <DeltaBadge
                    before={beforeStats.completed}
                    after={afterStats.completed}
                    label="Expanded"
                  />
                  <DeltaBadge
                    before={beforeStats.maxDepth}
                    after={afterStats.maxDepth}
                    label="Max Depth"
                  />
                  <div className="border-t border-white/[0.06] pt-2 space-y-1.5">
                    {(Object.keys(METRIC_WEIGHTS) as MetricKey[]).map(key => (
                      <DeltaBadge
                        key={key}
                        before={beforeStats.avgScores[key] ?? 0}
                        after={afterStats.avgScores[key] ?? 0}
                        label={key}
                      />
                    ))}
                  </div>
                  <div className="border-t border-white/[0.06] pt-2">
                    <DeltaBadge
                      before={beforeStats.avgScores.composite ?? 0}
                      after={afterStats.avgScores.composite ?? 0}
                      label="Composite"
                    />
                  </div>
                </>
              ) : (
                <div className="text-xs text-surface-500">No comparison data available</div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
