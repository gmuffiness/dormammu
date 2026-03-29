import { useState, useEffect, useRef, useCallback } from 'react'
import type { TurnRecord } from '../types/simulation'

export type Speed = 0.5 | 1 | 2 | 4

interface ReplayState {
  currentTurnIndex: number
  isPlaying: boolean
  speed: Speed
  play: () => void
  pause: () => void
  seek: (index: number) => void
  setSpeed: (s: Speed) => void
  currentTurn: TurnRecord | null
}

export function useReplay(turns: TurnRecord[]): ReplayState {
  const [currentTurnIndex, setCurrentTurnIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState<Speed>(1)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearTimer = () => {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }

  const advance = useCallback(() => {
    setCurrentTurnIndex(prev => {
      if (prev >= turns.length - 1) {
        setIsPlaying(false)
        return prev
      }
      return prev + 1
    })
  }, [turns.length])

  useEffect(() => {
    if (!isPlaying || turns.length === 0) return
    const delay = Math.round(1000 / speed)
    timerRef.current = setTimeout(() => {
      advance()
    }, delay)
    return clearTimer
  }, [isPlaying, currentTurnIndex, speed, advance, turns.length])

  // Reset on new simulation data
  useEffect(() => {
    setCurrentTurnIndex(0)
    setIsPlaying(false)
  }, [turns])

  const play = useCallback(() => {
    if (currentTurnIndex >= turns.length - 1) {
      setCurrentTurnIndex(0)
    }
    setIsPlaying(true)
  }, [currentTurnIndex, turns.length])

  const pause = useCallback(() => {
    clearTimer()
    setIsPlaying(false)
  }, [])

  const seek = useCallback((index: number) => {
    clearTimer()
    setCurrentTurnIndex(Math.max(0, Math.min(index, turns.length - 1)))
  }, [turns.length])

  const currentTurn = turns[currentTurnIndex] ?? null

  return { currentTurnIndex, isPlaying, speed, play, pause, seek, setSpeed, currentTurn }
}
