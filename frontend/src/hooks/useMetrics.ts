/**
 * useMetrics — state management for the 4-dimensional Dormammu quality metrics.
 *
 * Derives EvaluationMetrics snapshots from ScenarioTreeData (each node that
 * has been scored) and computes per-dimension aggregate statistics.
 *
 * Dimensions:
 *   emergence  — unexpected, unscripted events               (weight 35 %)
 *   narrative  — story interest and drama                    (weight 30 %)
 *   diversity  — agent behavioural distinctness              (weight 20 %)
 *   novelty    — difference from sibling branches            (weight 15 %)
 */

import { useMemo, useState, useCallback } from 'react'
import type {
  ScenarioTreeData,
  ScenarioNodeData,
  EvaluationMetrics,
  MetricsAggregate,
  MetricStat,
  MetricKey,
} from '../types/simulation'
import { METRIC_WEIGHTS } from '../types/simulation'

// ─── helpers ────────────────────────────────────────────────────────────────

function computeComposite(m: Omit<EvaluationMetrics, 'composite' | 'nodeId' | 'nodeTitle'>): number {
  return (
    m.emergence * METRIC_WEIGHTS.emergence +
    m.narrative * METRIC_WEIGHTS.narrative +
    m.diversity * METRIC_WEIGHTS.diversity +
    m.novelty  * METRIC_WEIGHTS.novelty
  )
}

function nodeToMetrics(node: ScenarioNodeData): EvaluationMetrics | null {
  // A node is "evaluated" when at least one score field is present and non-zero.
  const emergence = node.emergence_score ?? 0
  const narrative = node.narrative_score ?? 0
  const diversity = node.diversity_score ?? 0
  const novelty   = node.novelty_score   ?? 0

  // Skip nodes that have never been scored (all zeros from absent fields)
  if (
    node.emergence_score === undefined &&
    node.narrative_score === undefined &&
    node.diversity_score === undefined &&
    node.novelty_score   === undefined
  ) {
    return null
  }

  const partial = { emergence, narrative, diversity, novelty }
  return {
    ...partial,
    composite: node.score ?? computeComposite(partial),
    nodeId: node.node_id,
    nodeTitle: node.hypothesis || `Node ${node.node_id.slice(0, 8)}`,
  }
}

function buildStat(values: number[]): MetricStat {
  if (values.length === 0) {
    return { min: 0, max: 0, avg: 0, current: 0 }
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const avg = values.reduce((a, b) => a + b, 0) / values.length
  const current = values[values.length - 1]
  return { min, max, avg, current }
}

function buildAggregate(snapshots: EvaluationMetrics[]): MetricsAggregate {
  const sorted = [...snapshots].sort((a, b) => b.composite - a.composite)
  const best   = sorted[0] ?? null

  const keys: MetricKey[] = ['emergence', 'narrative', 'diversity', 'novelty']
  const stats = {} as Record<MetricKey, MetricStat>
  for (const key of keys) {
    stats[key] = buildStat(snapshots.map(s => s[key]))
  }

  return {
    stats,
    best,
    snapshots: sorted,
    evaluatedCount: snapshots.length,
  }
}

// ─── hook ────────────────────────────────────────────────────────────────────

export interface UseMetricsReturn {
  /** Aggregated statistics derived from the scenario tree */
  aggregate: MetricsAggregate
  /** Currently "pinned" node for detailed inspection (null = show aggregate) */
  selectedNodeId: string | null
  /** Metrics for the selected node, or null when none is selected */
  selectedMetrics: EvaluationMetrics | null
  /** Pin a node for detailed view (pass null to clear) */
  selectNode: (nodeId: string | null) => void
  /** True when no node in the tree has been evaluated yet */
  isEmpty: boolean
}

/**
 * Derive and manage quality-metric state from a ScenarioTreeData object.
 *
 * @param tree  The scenario tree returned by the API (may be null while loading).
 */
export function useMetrics(tree: ScenarioTreeData | null): UseMetricsReturn {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)

  const snapshots = useMemo<EvaluationMetrics[]>(() => {
    if (!tree) return []
    return Object.values(tree.nodes)
      .map(nodeToMetrics)
      .filter((m): m is EvaluationMetrics => m !== null)
  }, [tree])

  const aggregate = useMemo(() => buildAggregate(snapshots), [snapshots])

  const selectedMetrics = useMemo<EvaluationMetrics | null>(() => {
    if (!selectedNodeId) return null
    return snapshots.find(s => s.nodeId === selectedNodeId) ?? null
  }, [selectedNodeId, snapshots])

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId)
  }, [])

  return {
    aggregate,
    selectedNodeId,
    selectedMetrics,
    selectNode,
    isEmpty: snapshots.length === 0,
  }
}
