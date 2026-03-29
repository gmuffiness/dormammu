/**
 * useScenarioTree — centralized state management for the DFS scenario tree.
 *
 * Responsibilities:
 *  - Fetch & auto-refresh tree data from the API
 *  - Track which node is selected
 *  - Track which nodes are expanded / collapsed
 *  - Lazy-fetch the world-state snapshot for the selected node
 *  - Compute the breadcrumb path from root to the selected node
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { api } from '../api/client'
import type {
  ScenarioTreeData,
  ScenarioNodeData,
  WorldState,
  NodeStatus,
  NodePathStep,
} from '../types/simulation'

// ─── Return type ─────────────────────────────────────────────────────────────

export interface UseScenarioTreeResult {
  // ── Data ──────────────────────────────────────────────────────────────────
  tree: ScenarioTreeData | null

  // ── Selection state ───────────────────────────────────────────────────────
  selectedNodeId: string | null
  selectedNode: ScenarioNodeData | null
  /** Ordered breadcrumb path from root → selectedNode. */
  selectedNodePath: NodePathStep[]
  /** World state at exit of the selected node (lazy-fetched). */
  selectedNodeWorldState: WorldState | null

  // ── Expansion state ───────────────────────────────────────────────────────
  /** Check whether a given node is expanded. */
  isExpanded: (nodeId: string) => boolean

  // ── Actions ───────────────────────────────────────────────────────────────
  selectNode: (nodeId: string | null) => void
  toggleExpand: (nodeId: string) => void
  /** Expand all nodes up to and including the given depth. */
  expandToDepth: (maxDepth: number) => void
  /** Collapse all nodes below a given depth. */
  collapseBelow: (minDepth: number) => void
  /** Manually trigger a re-fetch of the tree. */
  refresh: () => void

  // ── Loading state ─────────────────────────────────────────────────────────
  loading: boolean
  refreshing: boolean
  error: string | null
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Default expansion: auto-expand all nodes at depth < 2. */
function buildDefaultExpandedSet(
  nodes: Record<string, ScenarioNodeData>
): Set<string> {
  const expanded = new Set<string>()
  for (const node of Object.values(nodes)) {
    if (node.depth < 2) {
      expanded.add(node.node_id)
    }
  }
  return expanded
}

/** Walk tree from root to find the path to a target node id. */
function computePath(
  nodes: Record<string, ScenarioNodeData>,
  targetId: string
): NodePathStep[] {
  // Build parent-lookup map
  const parentOf: Record<string, string | null> = {}
  for (const node of Object.values(nodes)) {
    parentOf[node.node_id] = node.parent_id
  }

  // Walk up from target to root
  const reversed: NodePathStep[] = []
  let current: string | null = targetId
  while (current !== null) {
    const node = nodes[current]
    if (!node) break
    reversed.push({
      nodeId: node.node_id,
      hypothesis: node.hypothesis,
      depth: node.depth,
      status: node.status as NodeStatus,
    })
    current = parentOf[current] ?? null
  }
  return reversed.reverse()
}

// ─── Hook ────────────────────────────────────────────────────────────────────

/**
 * @param simulationId  The simulation to track. Pass `undefined` to disable.
 * @param autoRefreshMs Poll interval in ms when simulation is still running.
 *                      Pass `0` or `undefined` to disable auto-refresh.
 */
export function useScenarioTree(
  simulationId: string | undefined,
  autoRefreshMs: number = 5000
): UseScenarioTreeResult {
  const [tree, setTree] = useState<ScenarioTreeData | null>(null)
  const [expandedNodes, setExpandedNodes] = useState<Set<string>>(new Set())
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedNodeWorldState, setSelectedNodeWorldState] =
    useState<WorldState | null>(null)

  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Keep a ref to avoid stale closure in polling effect
  const treeRef = useRef<ScenarioTreeData | null>(null)
  treeRef.current = tree

  // ─── Fetch tree ─────────────────────────────────────────────────────────
  const fetchTree = useCallback(
    async (isRefresh = false) => {
      if (!simulationId) return
      if (isRefresh) {
        setRefreshing(true)
      } else {
        setLoading(true)
      }
      setError(null)
      try {
        const data = await api.getTree(simulationId)
        setTree(data)
        // On first load, apply default expansion
        if (!treeRef.current) {
          setExpandedNodes(buildDefaultExpandedSet(data.nodes))
        }
      } catch (e) {
        setError(String(e))
      } finally {
        setLoading(false)
        setRefreshing(false)
      }
    },
    [simulationId]
  )

  // Initial fetch
  useEffect(() => {
    if (!simulationId) {
      setTree(null)
      setSelectedNodeId(null)
      setSelectedNodeWorldState(null)
      setExpandedNodes(new Set())
      return
    }
    fetchTree(false)
  }, [simulationId, fetchTree])

  // Auto-refresh while simulation is still running
  useEffect(() => {
    if (!simulationId || !autoRefreshMs) return
    const id = setInterval(() => {
      const currentTree = treeRef.current
      // Stop polling once the simulation is complete
      if (currentTree && !hasRunningNodes(currentTree)) return
      fetchTree(true)
    }, autoRefreshMs)
    return () => clearInterval(id)
  }, [simulationId, autoRefreshMs, fetchTree])

  // ─── Lazy-fetch world state for selected node ────────────────────────────
  useEffect(() => {
    if (!simulationId || !selectedNodeId || !tree) {
      setSelectedNodeWorldState(null)
      return
    }
    const node = tree.nodes[selectedNodeId]
    if (!node) {
      setSelectedNodeWorldState(null)
      return
    }

    // Use turns_simulated as the turn number to fetch world state
    // Falls back to 0 if no turns have been simulated yet
    const turnForState = node.turns_simulated > 0 ? node.turns_simulated : 0
    api
      .getWorldState(simulationId, turnForState)
      .then(ws => setSelectedNodeWorldState(ws))
      .catch(() => setSelectedNodeWorldState(null))
  }, [simulationId, selectedNodeId, tree])

  // ─── Derived values ──────────────────────────────────────────────────────
  const selectedNode: ScenarioNodeData | null = useMemo(() => {
    if (!selectedNodeId || !tree) return null
    return tree.nodes[selectedNodeId] ?? null
  }, [selectedNodeId, tree])

  const selectedNodePath: NodePathStep[] = useMemo(() => {
    if (!selectedNodeId || !tree) return []
    return computePath(tree.nodes, selectedNodeId)
  }, [selectedNodeId, tree])

  // ─── Actions ─────────────────────────────────────────────────────────────
  const isExpanded = useCallback(
    (nodeId: string) => expandedNodes.has(nodeId),
    [expandedNodes]
  )

  const selectNode = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId)
  }, [])

  const toggleExpand = useCallback((nodeId: string) => {
    setExpandedNodes(prev => {
      const next = new Set(prev)
      if (next.has(nodeId)) {
        next.delete(nodeId)
      } else {
        next.add(nodeId)
      }
      return next
    })
  }, [])

  const expandToDepth = useCallback(
    (maxDepth: number) => {
      if (!tree) return
      setExpandedNodes(prev => {
        const next = new Set(prev)
        for (const node of Object.values(tree.nodes)) {
          if (node.depth <= maxDepth) {
            next.add(node.node_id)
          }
        }
        return next
      })
    },
    [tree]
  )

  const collapseBelow = useCallback(
    (minDepth: number) => {
      if (!tree) return
      setExpandedNodes(prev => {
        const next = new Set(prev)
        for (const node of Object.values(tree.nodes)) {
          if (node.depth >= minDepth) {
            next.delete(node.node_id)
          }
        }
        return next
      })
    },
    [tree]
  )

  const refresh = useCallback(() => fetchTree(true), [fetchTree])

  return {
    tree,
    selectedNodeId,
    selectedNode,
    selectedNodePath,
    selectedNodeWorldState,
    isExpanded,
    selectNode,
    toggleExpand,
    expandToDepth,
    collapseBelow,
    refresh,
    loading,
    refreshing,
    error,
  }
}

// ─── Utility: check if any node is still in-progress/pending ─────────────────

function hasRunningNodes(tree: ScenarioTreeData): boolean {
  return Object.values(tree.nodes).some(
    n => n.status === 'in_progress' || n.status === 'pending'
  )
}
