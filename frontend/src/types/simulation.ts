// ─── Core simulation types mirroring the Python backend ─────────────────────

export interface Simulation {
  id: string
  topic: string
  status: 'running' | 'complete' | 'failed' | string
  max_depth: number
  node_years: number
  cost_limit: number
  openai_model: string
  total_cost_usd: number
  turns: number
  current_node_id: string
  evaluation_criteria: string | string[]
  created_at: string
  updated_at: string
}

export interface TurnRecord {
  id: number
  simulation_id: string
  turn_number: number
  year: number
  narrative: string
  tokens_used: number
  cost_usd: number
  events_json: string
  agent_actions_json: string
  created_at: string
  // parsed from JSON strings:
  events?: SimEvent[]
  agent_actions?: Record<string, AgentAction>
}

export interface SimEvent {
  turn?: number
  year?: number
  description: string
  timestamp?: string
  type?: string
  participants?: string[]
  [key: string]: unknown
}

export interface AgentAction {
  action_type?: string
  target?: string
  speech?: string
  thought?: string
  location?: string
  [key: string]: unknown
}

// ─── World state (from world_states table) ──────────────────────────────────

export interface WorldState {
  state_id: string
  simulation_id: string
  turn: number
  year: number
  agents: Record<string, AgentSnapshot>
  relationships: Record<string, Record<string, number>>
  events: SimEvent[]
  resources: Record<string, number>
  metadata: Record<string, unknown>
  created_at: string
}

export interface AgentSnapshot {
  name?: string
  age?: number
  backstory?: string
  goals?: string[]
  traits?: Record<string, number>
  fears?: string[]
  values?: string[]
  speech_style?: string
  mood?: number
  energy?: number
  location?: string
  persona_id?: string
  [key: string]: unknown
}

// ─── Scenario tree ──────────────────────────────────────────────────────────

export type NodeStatus = 'pending' | 'in_progress' | 'complete' | 'pruned'

export interface ScenarioNodeData {
  node_id: string
  simulation_id: string
  parent_id: string | null
  depth: number
  hypothesis: string
  status: NodeStatus
  children: string[]
  entry_world_state_id: string
  exit_world_state_id: string
  turns_simulated: number
  years_simulated: number
  metadata: Record<string, unknown>
  score?: number
  tags?: string[]
  // Quality evaluation scores (from HypothesisEvaluator)
  emergence_score?: number
  narrative_score?: number
  diversity_score?: number
  novelty_score?: number
}

export interface ScenarioTreeData {
  simulation_id: string
  max_depth: number
  root_id: string | null
  nodes: Record<string, ScenarioNodeData>
}

// ─── Scenario tree UI state ──────────────────────────────────────────────────

/** One step in the breadcrumb path from root to a selected node. */
export interface NodePathStep {
  nodeId: string
  hypothesis: string
  depth: number
  status: NodeStatus
}

/** Centralized scenario-tree UI state, managed by useScenarioTree hook. */
export interface ScenarioTreeUIState {
  tree: ScenarioTreeData | null
  /** Currently highlighted/selected node id. */
  selectedNodeId: string | null
  /** Set of explicitly expanded node ids (nodes at depth < 2 are auto-expanded). */
  expandedNodes: Set<string>
  /** World state snapshot associated with the selected node (lazy-fetched). */
  selectedNodeWorldState: WorldState | null
  /** Ordered breadcrumb path: root → … → selectedNode. */
  selectedNodePath: NodePathStep[]
  loading: boolean
  refreshing: boolean
  error: string | null
}

// ─── Hypotheses ─────────────────────────────────────────────────────────────

export interface Hypothesis {
  node_id: string
  simulation_id: string
  parent_id: string
  depth: number
  title: string
  description: string
  probability: number
  tags_json: string
  sf_inspired: number
  created_at: string
}

// ─── Evaluation metrics (4-dimensional quality scores) ───────────────────────

/** Weights used by HypothesisEvaluator.composite_score (must sum to 1.0) */
export const METRIC_WEIGHTS = {
  emergence: 0.35,
  narrative: 0.30,
  diversity: 0.20,
  novelty: 0.15,
} as const

export type MetricKey = keyof typeof METRIC_WEIGHTS

/** A single evaluation snapshot for one scenario node */
export interface EvaluationMetrics {
  /** Unexpected, unscripted events arose (emergence_score) */
  emergence: number
  /** Story is interesting to observe (narrative_score) */
  narrative: number
  /** Agents behaved distinctly from one another (agent_diversity_score) */
  diversity: number
  /** Branch is different from sibling branches (novelty_score) */
  novelty: number
  /** Weighted composite across all dimensions */
  composite: number
  /** Associated scenario-tree node ID */
  nodeId: string
  /** Human-readable hypothesis title */
  nodeTitle: string
}

/** Aggregated statistics across multiple evaluated nodes */
export interface MetricsAggregate {
  /** Per-dimension statistics */
  stats: Record<MetricKey, MetricStat>
  /** Node with the highest composite score */
  best: EvaluationMetrics | null
  /** All individual node snapshots, sorted by composite score descending */
  snapshots: EvaluationMetrics[]
  /** Total number of evaluated nodes */
  evaluatedCount: number
}

export interface MetricStat {
  min: number
  max: number
  avg: number
  /** Most recent value (last evaluated node in tree order) */
  current: number
}

// ─── Canvas/rendering helpers ────────────────────────────────────────────────

export interface AgentPosition {
  x: number
  y: number
}

export interface RenderedAgent {
  id: string
  name: string
  color: string
  pos: AgentPosition
  targetPos: AgentPosition
  /**
   * Normalized linear interpolation progress for the current move: 0.0 = just
   * started, 1.0 = arrived at targetPos.  Updated every animation frame by the
   * renderer's tickPositions() loop.  External consumers (e.g. AgentDetail
   * panel) can read this to show a movement progress indicator without coupling
   * to renderer-private easing internals.
   */
  interpT: number
  speech?: string
  speechTimer?: number
  state: 'idle' | 'interacting' | 'observing'
  snapshot: AgentSnapshot
}

export interface Zone {
  id: string
  label: string
  x: number
  y: number
  w: number
  h: number
  type: 'water' | 'land' | 'residential' | 'building' | 'path'
}
