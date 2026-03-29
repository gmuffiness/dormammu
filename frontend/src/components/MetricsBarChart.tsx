/**
 * MetricsBarChart — D2 sub-component for the Dormammu Harness Triangle P0.
 *
 * Renders a grouped SVG bar chart for the 4-dimensional quality scores:
 *   emergence  (EMG, weight 35 %) — orange
 *   narrative  (NAR, weight 30 %) — blue
 *   diversity  (DIV, weight 20 %) — green
 *   novelty    (NOV, weight 15 %) — purple
 *
 * Each bar column shows:
 *   • A filled bar up to the current/selected value
 *   • A faint range band from min to max (aggregate)
 *   • A tick line at the aggregate avg
 *   • Y-axis grid lines at 25 / 50 / 75 / 100
 *   • Animated transitions on value change
 */

import { useMemo } from 'react'
import type { MetricKey, MetricStat, EvaluationMetrics } from '../types/simulation'
import { METRIC_WEIGHTS } from '../types/simulation'

// ─── Palette ─────────────────────────────────────────────────────────────────

interface MetricMeta {
  label: string
  shortLabel: string
  color: string
  trackColor: string
  rangeColor: string
  weight: number
}

const METRIC_META: Record<MetricKey, MetricMeta> = {
  emergence: {
    label: 'Emergence',
    shortLabel: 'EMG',
    color: '#e8963c',
    trackColor: 'rgba(232,150,60,0.12)',
    rangeColor: 'rgba(232,150,60,0.22)',
    weight: METRIC_WEIGHTS.emergence,
  },
  narrative: {
    label: 'Narrative',
    shortLabel: 'NAR',
    color: '#60a5fa',
    trackColor: 'rgba(96,165,250,0.12)',
    rangeColor: 'rgba(96,165,250,0.22)',
    weight: METRIC_WEIGHTS.narrative,
  },
  diversity: {
    label: 'Diversity',
    shortLabel: 'DIV',
    color: '#34d399',
    trackColor: 'rgba(52,211,153,0.12)',
    rangeColor: 'rgba(52,211,153,0.22)',
    weight: METRIC_WEIGHTS.diversity,
  },
  novelty: {
    label: 'Novelty',
    shortLabel: 'NOV',
    color: '#a78bfa',
    trackColor: 'rgba(167,139,250,0.12)',
    rangeColor: 'rgba(167,139,250,0.22)',
    weight: METRIC_WEIGHTS.novelty,
  },
}

const METRIC_KEYS: MetricKey[] = ['emergence', 'narrative', 'diversity', 'novelty']

// ─── Types ────────────────────────────────────────────────────────────────────

export interface MetricsBarChartProps {
  /** Per-metric aggregate stats derived from all evaluated nodes */
  stats: Record<MetricKey, MetricStat>
  /** Optional: individual node metrics to highlight (e.g. selected node) */
  nodeMetrics?: EvaluationMetrics | null
  /** Chart width in px (defaults to 100% via viewBox) */
  width?: number
  /** Chart height in px */
  height?: number
  /** Extra className applied to the outer <div> */
  className?: string
}

// ─── Chart geometry constants ─────────────────────────────────────────────────

const PADDING = { top: 12, right: 10, bottom: 36, left: 28 }
const GRID_LINES = [0.25, 0.5, 0.75, 1.0]

// ─── Sub-components ──────────────────────────────────────────────────────────

interface BarColumnProps {
  meta: MetricMeta
  stat: MetricStat
  nodeValue: number | null
  /** x-center of the column */
  cx: number
  barWidth: number
  chartH: number
  /** Convert a 0-1 value to chart-space Y */
  toY: (v: number) => number
}

function BarColumn({ meta, stat, nodeValue, cx, barWidth, chartH, toY }: BarColumnProps) {
  const hasNodeValue = nodeValue !== null
  const displayValue = hasNodeValue ? (nodeValue as number) : stat.current
  const halfBar = barWidth / 2
  const trackX = cx - halfBar

  // Min-max range band
  const rangeY = toY(stat.max)
  const rangeH = toY(stat.min) - rangeY

  // Filled bar (value)
  const barY = toY(displayValue)
  const barH = chartH - barY

  // Avg tick and node-specific bar
  const avgY = toY(stat.avg)
  const nodeBarY = hasNodeValue ? toY(nodeValue as number) : barY
  const nodeBarH = chartH - nodeBarY

  return (
    <g>
      {/* Track */}
      <rect
        x={trackX}
        y={0}
        width={barWidth}
        height={chartH}
        rx={3}
        fill={meta.trackColor}
      />

      {/* Min-max range band */}
      {stat.max > stat.min && (
        <rect
          x={trackX}
          y={rangeY}
          width={barWidth}
          height={Math.max(1, rangeH)}
          rx={2}
          fill={meta.rangeColor}
        />
      )}

      {/* Aggregate avg bar (faint, shown behind node bar) */}
      {!hasNodeValue && (
        <rect
          x={trackX}
          y={barY}
          width={barWidth}
          height={Math.max(2, barH)}
          rx={3}
          fill={meta.color}
          opacity={0.75}
          style={{ transition: 'y 0.45s ease, height 0.45s ease' }}
        />
      )}

      {/* Node value bar (full opacity when a node is selected) */}
      {hasNodeValue && (
        <>
          {/* Aggregate avg as ghost bar */}
          <rect
            x={trackX}
            y={toY(stat.avg)}
            width={barWidth}
            height={Math.max(2, chartH - toY(stat.avg))}
            rx={3}
            fill={meta.color}
            opacity={0.18}
          />
          {/* Node bar */}
          <rect
            x={trackX}
            y={nodeBarY}
            width={barWidth}
            height={Math.max(2, nodeBarH)}
            rx={3}
            fill={meta.color}
            opacity={0.9}
            style={{ transition: 'y 0.45s ease, height 0.45s ease' }}
          />
        </>
      )}

      {/* Avg tick line */}
      <line
        x1={trackX - 2}
        x2={trackX + barWidth + 2}
        y1={avgY}
        y2={avgY}
        stroke="rgba(255,255,255,0.35)"
        strokeWidth={1}
        strokeDasharray="2 2"
      />

      {/* Glow highlight at top of filled bar */}
      <rect
        x={trackX + barWidth * 0.1}
        y={hasNodeValue ? nodeBarY : barY}
        width={barWidth * 0.8}
        height={2}
        rx={1}
        fill={meta.color}
        opacity={0.9}
        style={{ transition: 'y 0.45s ease' }}
      />
    </g>
  )
}

// ─── Main component ──────────────────────────────────────────────────────────

export default function MetricsBarChart({
  stats,
  nodeMetrics = null,
  width = 320,
  height = 160,
  className = '',
}: MetricsBarChartProps) {
  const chartW = width - PADDING.left - PADDING.right
  const chartH = height - PADDING.top - PADDING.bottom

  // Map 0-1 value → SVG y coordinate (top = max, bottom = 0)
  const toY = (v: number) => chartH - Math.max(0, Math.min(1, v)) * chartH

  // Column layout: evenly space 4 bars
  const colWidth = chartW / METRIC_KEYS.length
  const barWidth = Math.max(12, colWidth * 0.45)

  const columns = useMemo(() => {
    return METRIC_KEYS.map((key, i) => {
      const stat = stats[key]
      const nodeValue = nodeMetrics ? nodeMetrics[key] : null
      const cx = colWidth * i + colWidth / 2
      return { key, meta: METRIC_META[key], stat, nodeValue, cx }
    })
  }, [stats, nodeMetrics, colWidth])

  return (
    <div className={`relative ${className}`}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        height={height}
        aria-label="Metrics bar chart"
        role="img"
      >
        <g transform={`translate(${PADDING.left}, ${PADDING.top})`}>
          {/* ── Grid lines ── */}
          {GRID_LINES.map(v => {
            const y = toY(v)
            return (
              <g key={v}>
                <line
                  x1={0}
                  x2={chartW}
                  y1={y}
                  y2={y}
                  stroke="rgba(255,255,255,0.05)"
                  strokeWidth={1}
                />
                <text
                  x={-4}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  fill="rgba(255,255,255,0.25)"
                  fontSize={7}
                  fontFamily="monospace"
                >
                  {(v * 100).toFixed(0)}
                </text>
              </g>
            )
          })}

          {/* Zero baseline */}
          <line
            x1={0}
            x2={chartW}
            y1={chartH}
            y2={chartH}
            stroke="rgba(255,255,255,0.12)"
            strokeWidth={1}
          />

          {/* ── Bar columns ── */}
          {columns.map(({ key, meta, stat, nodeValue, cx }) => (
            <BarColumn
              key={key}
              meta={meta}
              stat={stat}
              nodeValue={nodeValue}
              cx={cx}
              barWidth={barWidth}
              chartH={chartH}
              toY={toY}
            />
          ))}

          {/* ── X-axis labels ── */}
          {columns.map(({ key, meta, cx, stat, nodeValue }) => {
            const displayValue = nodeValue !== null ? nodeValue : stat.current
            return (
              <g key={`label-${key}`}>
                {/* Metric short label */}
                <text
                  x={cx}
                  y={chartH + 10}
                  textAnchor="middle"
                  fill={meta.color}
                  fontSize={8}
                  fontFamily="monospace"
                  fontWeight="600"
                  letterSpacing="0.08em"
                >
                  {meta.shortLabel}
                </text>
                {/* Numeric value below */}
                <text
                  x={cx}
                  y={chartH + 21}
                  textAnchor="middle"
                  fill="rgba(255,255,255,0.55)"
                  fontSize={8}
                  fontFamily="monospace"
                >
                  {(displayValue * 100).toFixed(0)}
                </text>
                {/* Weight badge */}
                <text
                  x={cx}
                  y={chartH + 31}
                  textAnchor="middle"
                  fill={meta.color}
                  fontSize={6.5}
                  fontFamily="monospace"
                  opacity={0.5}
                >
                  {(meta.weight * 100).toFixed(0)}%
                </text>
              </g>
            )
          })}
        </g>
      </svg>

      {/* Legend row */}
      <div className="flex items-center justify-center gap-3 mt-0.5 flex-wrap">
        <div className="flex items-center gap-1.5">
          <div
            className="w-3 h-0.5 rounded"
            style={{
              backgroundImage:
                'repeating-linear-gradient(90deg, rgba(255,255,255,0.35) 0, rgba(255,255,255,0.35) 2px, transparent 2px, transparent 4px)',
            }}
          />
          <span className="text-[8px] font-mono text-surface-500">avg</span>
        </div>
        {nodeMetrics && (
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2 rounded-sm bg-white/20" />
            <span className="text-[8px] font-mono text-surface-400">aggregate</span>
          </div>
        )}
        {nodeMetrics && (
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-2 rounded-sm bg-accent-amber/70" />
            <span className="text-[8px] font-mono text-surface-300">selected node</span>
          </div>
        )}
        {!nodeMetrics && (
          <div className="flex items-center gap-1.5">
            <div className="w-2.5 h-3 rounded-sm" style={{ background: 'rgba(232,150,60,0.22)' }} />
            <span className="text-[8px] font-mono text-surface-500">min–max range</span>
          </div>
        )}
      </div>
    </div>
  )
}
