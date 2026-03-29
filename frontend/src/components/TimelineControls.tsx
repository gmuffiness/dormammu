import type { TurnRecord } from '../types/simulation'
import type { Speed } from '../hooks/useReplay'

interface Props {
  turns: TurnRecord[]
  currentTurnIndex: number
  isPlaying: boolean
  speed: Speed
  onPlay: () => void
  onPause: () => void
  onSeek: (index: number) => void
  onSetSpeed: (s: Speed) => void
}

const SPEEDS: Speed[] = [0.5, 1, 2, 4]

export default function TimelineControls({
  turns,
  currentTurnIndex,
  isPlaying,
  speed,
  onPlay,
  onPause,
  onSeek,
  onSetSpeed,
}: Props) {
  if (turns.length === 0) return null

  const current = turns[currentTurnIndex]
  const total = turns.length

  // Collect year labels for tick marks
  const yearSet = new Set<number>()
  const yearTicks: { index: number; year: number }[] = []
  turns.forEach((t, i) => {
    if (!yearSet.has(t.year)) {
      yearSet.add(t.year)
      yearTicks.push({ index: i, year: t.year })
    }
  })
  const step = Math.ceil(yearTicks.length / 8)
  const displayedYearTicks = yearTicks.filter((_, i) => i % step === 0)

  const progress = currentTurnIndex / Math.max(total - 1, 1)

  return (
    <div className="bg-bg-secondary border-t border-white/[0.06] px-4 py-3 select-none font-body">
      {/* Top row: counter + speed */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-surface-300 font-mono">
          Turn {current?.turn_number ?? 0}/{turns[total - 1]?.turn_number ?? 0}
          {current ? `  ·  Year ${current.year}` : ''}
        </span>
        <div className="flex items-center gap-1">
          {SPEEDS.map(s => (
            <button
              key={s}
              onClick={() => onSetSpeed(s)}
              className={`text-xs px-2 py-0.5 rounded-md font-mono transition-all duration-200 ${
                speed === s
                  ? 'bg-accent-amber/15 text-accent-amber border border-accent-amber/25'
                  : 'text-surface-400 hover:text-surface-200 border border-transparent'
              }`}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Slider row */}
      <div className="flex items-center gap-3">
        {/* Play/Pause */}
        <button
          onClick={isPlaying ? onPause : onPlay}
          className="w-8 h-8 flex items-center justify-center rounded-lg
                     bg-accent-amber/15 text-accent-amber border border-accent-amber/25
                     hover:bg-accent-amber/25 transition-all duration-200 flex-shrink-0"
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        {/* Timeline */}
        <div className="relative flex-1">
          {/* Year tick labels */}
          <div className="relative h-4 mb-1">
            {displayedYearTicks.map(({ index, year }) => (
              <span
                key={year}
                className="absolute text-[9px] text-surface-400 font-mono -translate-x-1/2"
                style={{ left: `${(index / Math.max(total - 1, 1)) * 100}%` }}
              >
                {year}
              </span>
            ))}
          </div>

          {/* Slider */}
          <input
            type="range"
            min={0}
            max={total - 1}
            value={currentTurnIndex}
            onChange={e => onSeek(Number(e.target.value))}
            className="w-full h-1.5 appearance-none bg-white/[0.06] rounded-full cursor-pointer"
            style={{
              background: `linear-gradient(to right, #e8963c ${progress * 100}%, rgba(255,255,255,0.06) 0%)`,
            }}
          />
        </div>

        {/* Cost indicator */}
        <span className="text-xs text-surface-400 font-mono flex-shrink-0">
          ${(current?.cost_usd ?? 0).toFixed(4)}
        </span>
      </div>
    </div>
  )
}
