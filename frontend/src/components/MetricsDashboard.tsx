/**
 * MetricsDashboard — D2 component of the Dormammu Harness Triangle P0.
 *
 * Displays the 4-dimensional quality evaluation scores produced by
 * HypothesisEvaluator:
 *
 *   emergence  — unexpected, unscripted events               (weight 35 %)
 *   narrative  — story interest and drama                    (weight 30 %)
 *   diversity  — agent behavioural distinctness              (weight 20 %)
 *   novelty    — difference from sibling branches            (weight 15 %)
 *
 * Props:
 *   tree         — ScenarioTreeData from the API (used as the data source)
 *   className    — optional additional Tailwind classes for the container
 */

import type { ScenarioTreeData } from '../types/simulation'
import { METRIC_WEIGHTS, type MetricKey, type EvaluationMetrics, type MetricStat } from '../types/simulation'
import { useMetrics } from '../hooks/useMetrics'
import MetricsBarChart from './MetricsBarChart'

// ─── Palette ─────────────────────────────────────────────────────────────────

const METRIC_META: Record<
  MetricKey,
  { label: string; shortLabel: string; description: string; color: string; trackColor: string }
> = {
  emergence: {
    label: 'Emergence',
    shortLabel: 'EMG',
    description: 'Unexpected, unscripted events arose',
    color: '#e8963c',
    trackColor: 'rgba(232,150,60,0.15)',
  },
  narrative: {
    label: 'Narrative',
    shortLabel: 'NAR',
    description: 'Story is interesting and dramatic',
    color: '#60a5fa',
    trackColor: 'rgba(96,165,250,0.15)',
  },
  diversity: {
    label: 'Diversity',
    shortLabel: 'DIV',
    description: 'Agents behaved distinctly from one another',
    color: '#34d399',
    trackColor: 'rgba(52,211,153,0.15)',
  },
  novelty: {
    label: 'Novelty',
    shortLabel: 'NOV',
    description: 'Branch differs from sibling branches',
    color: '#a78bfa',
    trackColor: 'rgba(167,139,250,0.15)',
  },
}

const METRIC_KEYS: MetricKey[] = ['emergence', 'narrative', 'diversity', 'novelty']

// ─── Sub-components ──────────────────────────────────────────────────────────

interface GaugeBarProps {
  value: number   // 0–1
  color: string
  trackColor: string
  /** If true, shows a thin secondary bar at the stat value */
  statValue?: number
  statColor?: string
}

function GaugeBar({ value, color, trackColor, statValue, statColor }: GaugeBarProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100)
  return (
    <div
      className="relative h-2 rounded-full overflow-hidden"
      style={{ background: trackColor }}
      role="progressbar"
      aria-valuenow={pct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className="absolute inset-y-0 left-0 rounded-full transition-all duration-500"
        style={{ width: `${pct}%`, background: color }}
      />
      {statValue !== undefined && (
        <div
          className="absolute inset-y-0 w-0.5 rounded-full opacity-70"
          style={{
            left: `${Math.round(Math.max(0, Math.min(1, statValue)) * 100)}%`,
            background: statColor ?? '#ffffff',
          }}
        />
      )}
    </div>
  )
}

interface MetricCardProps {
  metricKey: MetricKey
  stat: MetricStat
  /** If a node is selected, show its individual value instead of aggregate */
  nodeValue?: number
  isSelected: boolean
  onClick?: () => void
}

function MetricCard({ metricKey, stat, nodeValue, isSelected, onClick }: MetricCardProps) {
  const meta = METRIC_META[metricKey]
  const weight = METRIC_WEIGHTS[metricKey]
  const displayValue = nodeValue ?? stat.current

  return (
    <button
      onClick={onClick}
      className={[
        'relative text-left rounded-xl p-4 border transition-all duration-200 group',
        isSelected
          ? 'border-white/20 bg-white/[0.06]'
          : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-white/10',
      ].join(' ')}
    >
      {/* Top accent line */}
      {isSelected && (
        <div
          className="absolute top-0 inset-x-0 h-px rounded-t-xl"
          style={{ background: meta.color }}
        />
      )}

      {/* Header row */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div
            className="w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: meta.color, boxShadow: `0 0 6px ${meta.color}60` }}
          />
          <span className="text-[11px] font-display font-semibold uppercase tracking-[0.12em]"
                style={{ color: meta.color }}>
            {meta.label}
          </span>
        </div>
        <span className="text-[9px] font-mono text-surface-400">
          {(weight * 100).toFixed(0)} %
        </span>
      </div>

      {/* Score value */}
      <div className="mb-3">
        <span className="text-[26px] font-mono font-bold tabular-nums leading-none text-surface-50">
          {(displayValue * 100).toFixed(0)}
        </span>
        <span className="text-[11px] font-mono text-surface-400 ml-0.5">/ 100</span>
      </div>

      {/* Progress bar — fill = current/node, tick = avg */}
      <GaugeBar
        value={displayValue}
        color={meta.color}
        trackColor={meta.trackColor}
        statValue={stat.avg}
        statColor="rgba(255,255,255,0.4)"
      />

      {/* Min / avg / max */}
      <div className="flex items-center justify-between mt-2.5">
        <span className="text-[9px] font-mono text-surface-500">
          {(stat.min * 100).toFixed(0)}
        </span>
        <span className="text-[9px] font-mono text-surface-400">
          avg {(stat.avg * 100).toFixed(0)}
        </span>
        <span className="text-[9px] font-mono text-surface-500">
          {(stat.max * 100).toFixed(0)}
        </span>
      </div>

      {/* Description tooltip-like */}
      <p className="text-[9px] text-surface-500 mt-2 leading-tight font-body">
        {meta.description}
      </p>
    </button>
  )
}

interface CompositeRingProps {
  value: number   // 0–1
  size?: number
}

/** Simple SVG arc gauge for the composite score */
function CompositeRing({ value, size = 72 }: CompositeRingProps) {
  const r = (size - 10) / 2
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * r
  const arc = circumference * Math.max(0, Math.min(1, value))

  return (
    <svg width={size} height={size} className="flex-shrink-0">
      {/* Track */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke="rgba(255,255,255,0.06)"
        strokeWidth={5}
      />
      {/* Fill arc — starts at top (−90 °) */}
      <circle
        cx={cx} cy={cy} r={r}
        fill="none"
        stroke="#e8963c"
        strokeWidth={5}
        strokeLinecap="round"
        strokeDasharray={`${arc} ${circumference}`}
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ transition: 'stroke-dasharray 0.5s ease' }}
      />
      {/* Label */}
      <text
        x={cx} y={cy + 1}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="#f0f0f0"
        fontSize="14"
        fontFamily="monospace"
        fontWeight="bold"
      >
        {(value * 100).toFixed(0)}
      </text>
    </svg>
  )
}

interface BestNodeBadgeProps {
  metrics: EvaluationMetrics
  onSelect: (id: string) => void
}

function BestNodeBadge({ metrics, onSelect }: BestNodeBadgeProps) {
  return (
    <button
      onClick={() => onSelect(metrics.nodeId)}
      className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-accent-amber/[0.08]
                 border border-accent-amber/20 hover:bg-accent-amber/[0.12] transition-colors"
    >
      <span className="text-[9px] font-mono text-accent-amber/70 uppercase tracking-widest">best</span>
      <span className="text-[11px] font-body text-surface-200 truncate max-w-[120px]">
        {metrics.nodeTitle}
      </span>
      <span className="text-[10px] font-mono text-accent-amber">
        {(metrics.composite * 100).toFixed(0)}
      </span>
    </button>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

export interface MetricsDashboardProps {
  tree: ScenarioTreeData | null
  className?: string
}

export default function MetricsDashboard({ tree, className = '' }: MetricsDashboardProps) {
  const { aggregate, selectedNodeId, selectedMetrics, selectNode, isEmpty } = useMetrics(tree)

  const compositeValue = selectedMetrics
    ? selectedMetrics.composite
    : (aggregate.stats.emergence?.avg ?? 0) * METRIC_WEIGHTS.emergence +
      (aggregate.stats.narrative?.avg ?? 0) * METRIC_WEIGHTS.narrative +
      (aggregate.stats.diversity?.avg ?? 0) * METRIC_WEIGHTS.diversity +
      (aggregate.stats.novelty?.avg   ?? 0) * METRIC_WEIGHTS.novelty

  return (
    <div className={`flex flex-col ${className}`}>
      {/* ── Section header ── */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-accent-amber font-display font-semibold uppercase tracking-[0.15em]">
            Metrics
          </span>
          {!isEmpty && (
            <span className="text-[10px] text-surface-400 font-mono">
              {aggregate.evaluatedCount} node{aggregate.evaluatedCount !== 1 ? 's' : ''} scored
            </span>
          )}
        </div>

        {/* Composite ring + best-node badge */}
        {!isEmpty && (
          <div className="flex items-center gap-3">
            {aggregate.best && !selectedNodeId && (
              <BestNodeBadge metrics={aggregate.best} onSelect={selectNode} />
            )}
            {selectedNodeId && (
              <button
                onClick={() => selectNode(null)}
                className="text-[9px] font-mono text-surface-400 hover:text-surface-200
                           transition-colors px-2 py-1 rounded bg-white/[0.03]"
              >
                clear ×
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Empty state ── */}
      {isEmpty && (
        <div className="flex flex-col items-center justify-center py-8 px-4">
          <div className="w-10 h-10 rounded-xl bg-white/[0.02] border border-white/[0.05]
                          flex items-center justify-center mb-3">
            <svg className="w-4 h-4 text-surface-500" viewBox="0 0 16 16" fill="none"
                 stroke="currentColor" strokeWidth="1.5">
              <path d="M8 3v5l3 2" strokeLinecap="round" strokeLinejoin="round" />
              <circle cx="8" cy="8" r="6" />
            </svg>
          </div>
          <p className="text-[11px] text-surface-400 font-body text-center">
            No scored nodes yet
          </p>
          <p className="text-[10px] text-surface-500 font-mono mt-1 text-center">
            Scores appear after hypothesis evaluation
          </p>
        </div>
      )}

      {/* ── Scores ── */}
      {!isEmpty && (
        <div className="p-4 flex flex-col gap-4">
          {/* Composite ring + label row */}
          <div className="flex items-center gap-4 pb-3 border-b border-white/[0.04]">
            <CompositeRing value={compositeValue} size={64} />
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-display font-semibold text-surface-50 mb-0.5">
                {selectedMetrics ? selectedMetrics.nodeTitle : 'Aggregate Score'}
              </p>
              <p className="text-[9px] text-surface-400 font-body leading-snug">
                {selectedMetrics
                  ? `Node · composite ${(selectedMetrics.composite * 100).toFixed(1)}`
                  : `Weighted composite across ${aggregate.evaluatedCount} evaluated branch${aggregate.evaluatedCount !== 1 ? 'es' : ''}`}
              </p>
              {/* Weight legend */}
              <div className="flex items-center gap-2 mt-1.5 flex-wrap">
                {METRIC_KEYS.map(k => (
                  <span key={k} className="text-[8px] font-mono"
                        style={{ color: METRIC_META[k].color + 'cc' }}>
                    {METRIC_META[k].shortLabel} {(METRIC_WEIGHTS[k] * 100).toFixed(0)}%
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Bar chart — 4 metrics at a glance */}
          <div className="pb-3 border-b border-white/[0.04]">
            <p className="text-[9px] font-mono text-surface-500 uppercase tracking-wider mb-2 px-0.5">
              Score distribution
            </p>
            <MetricsBarChart
              stats={aggregate.stats}
              nodeMetrics={selectedMetrics}
              height={140}
              className="w-full"
            />
          </div>

          {/* 4 metric cards */}
          <div className="grid grid-cols-2 gap-2">
            {METRIC_KEYS.map(key => (
              <MetricCard
                key={key}
                metricKey={key}
                stat={aggregate.stats[key]}
                nodeValue={selectedMetrics ? selectedMetrics[key] : undefined}
                isSelected={false}
                onClick={undefined}
              />
            ))}
          </div>

          {/* Node list */}
          {aggregate.snapshots.length > 1 && (
            <div className="mt-1">
              <p className="text-[9px] font-mono text-surface-500 uppercase tracking-wider mb-1.5 px-1">
                All scored nodes
              </p>
              <div className="flex flex-col gap-1 max-h-32 overflow-y-auto scrollbar-thin pr-1">
                {aggregate.snapshots.map(snap => (
                  <button
                    key={snap.nodeId}
                    onClick={() => selectNode(selectedNodeId === snap.nodeId ? null : snap.nodeId)}
                    className={[
                      'flex items-center justify-between px-2.5 py-1.5 rounded-lg text-left',
                      'transition-colors text-[10px] font-body',
                      selectedNodeId === snap.nodeId
                        ? 'bg-accent-amber/10 border border-accent-amber/20 text-surface-50'
                        : 'hover:bg-white/[0.04] text-surface-300 border border-transparent',
                    ].join(' ')}
                  >
                    <span className="truncate max-w-[140px]">{snap.nodeTitle}</span>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      {METRIC_KEYS.map(k => (
                        <span key={k}
                              className="text-[8px] font-mono tabular-nums"
                              style={{ color: METRIC_META[k].color + 'bb' }}>
                          {(snap[k] * 100).toFixed(0)}
                        </span>
                      ))}
                      <span className="text-[9px] font-mono font-bold text-accent-amber tabular-nums">
                        {(snap.composite * 100).toFixed(0)}
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
