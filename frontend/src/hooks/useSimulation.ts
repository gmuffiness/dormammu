import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type {
  Simulation,
  TurnRecord,
  WorldState,
  ScenarioTreeData,
} from '../types/simulation'

interface SimulationData {
  simulation: Simulation | null
  turns: TurnRecord[]
  worldStates: Map<number, WorldState>
  tree: ScenarioTreeData | null
  loading: boolean
  error: string | null
}

export function useSimulation(id: string | undefined): SimulationData {
  const [simulation, setSimulation] = useState<Simulation | null>(null)
  const [turns, setTurns] = useState<TurnRecord[]>([])
  const [worldStates, setWorldStates] = useState<Map<number, WorldState>>(new Map())
  const [tree, setTree] = useState<ScenarioTreeData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchWorldState = useCallback(
    async (simId: string, turn: number, map: Map<number, WorldState>) => {
      if (map.has(turn)) return
      try {
        const ws = await api.getWorldState(simId, turn)
        setWorldStates(prev => {
          const next = new Map(prev)
          next.set(turn, ws)
          return next
        })
      } catch {
        // world state may not exist for every turn; ignore
      }
    },
    []
  )

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)

    Promise.all([api.getSimulation(id), api.getTurns(id), api.getTree(id).catch(() => null)])
      .then(([sim, ts, tr]) => {
        setSimulation(sim)
        setTurns(ts)
        setTree(tr)
        // Pre-fetch first world state
        if (ts.length > 0) {
          fetchWorldState(id, ts[0].turn_number, new Map())
        }
      })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [id, fetchWorldState])

  return { simulation, turns, worldStates, tree, loading, error }
}
