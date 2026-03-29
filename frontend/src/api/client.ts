import type {
  Simulation,
  TurnRecord,
  WorldState,
  ScenarioTreeData,
  Hypothesis,
  SimEvent,
  AgentAction,
} from '../types/simulation'

const BASE = '/api'

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) {
    throw new Error(`API ${path} → ${res.status} ${res.statusText}`)
  }
  return res.json() as Promise<T>
}

// Parse JSON string fields that the backend stores as raw JSON strings
// The backend may return events/agent_actions directly (already parsed) or as _json strings
function parseTurn(t: TurnRecord): TurnRecord {
  // If backend already returned parsed arrays/objects, use them directly
  if (Array.isArray((t as unknown as Record<string, unknown>).events)) {
    t.events = (t as unknown as Record<string, unknown>).events as TurnRecord['events']
  } else {
    try {
      t.events = typeof t.events_json === 'string' ? JSON.parse(t.events_json) : []
    } catch {
      t.events = []
    }
  }

  const rawActions = (t as unknown as Record<string, unknown>).agent_actions
  if (rawActions && typeof rawActions === 'object' && !Array.isArray(rawActions)) {
    t.agent_actions = rawActions as TurnRecord['agent_actions']
  } else {
    try {
      t.agent_actions =
        typeof t.agent_actions_json === 'string' ? JSON.parse(t.agent_actions_json) : {}
    } catch {
      t.agent_actions = {}
    }
  }
  return t
}

export const api = {
  getSimulations: (): Promise<Simulation[]> => get<Simulation[]>('/simulations'),

  getSimulation: (id: string): Promise<Simulation> => get<Simulation>(`/simulations/${id}`),

  getTurns: async (id: string): Promise<TurnRecord[]> => {
    const turns = await get<TurnRecord[]>(`/simulations/${id}/turns`)
    return turns.map(parseTurn)
  },

  getEnvironment: (id: string): Promise<Record<string, unknown>> =>
    get<Record<string, unknown>>(`/simulations/${id}/environment`),

  getAgents: (id: string): Promise<Record<string, unknown>[]> =>
    get<Record<string, unknown>[]>(`/simulations/${id}/agents`),

  getTree: (id: string): Promise<ScenarioTreeData> =>
    get<ScenarioTreeData>(`/simulations/${id}/tree`),

  getHypotheses: (id: string): Promise<Hypothesis[]> =>
    get<Hypothesis[]>(`/simulations/${id}/hypotheses`),

  getWorldState: (simId: string, turn: number): Promise<WorldState> =>
    get<WorldState>(`/simulations/${simId}/world-state/${turn}`),

  getExport: (id: string): Promise<Record<string, unknown>> =>
    get<Record<string, unknown>>(`/simulations/${id}/export`),

  getResearch: (simId: string): Promise<any> =>
    get<any>(`/simulations/${simId}/research`),

  getMetrics: (simId: string): Promise<MetricsSummary> =>
    get<MetricsSummary>(`/simulations/${simId}/metrics`),
}

// ─── Types for the /metrics endpoint ─────────────────────────────────────────

export interface NodeMetricSnapshot {
  node_id: string
  node_title: string
  emergence: number
  narrative: number
  diversity: number
  novelty: number
  composite: number
}

export interface MetricsSummary {
  simulation_id: string
  evaluated_count: number
  nodes: NodeMetricSnapshot[]
}

export type { SimEvent, AgentAction }
