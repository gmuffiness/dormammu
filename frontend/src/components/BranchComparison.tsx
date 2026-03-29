import { ScenarioNodeData } from '../types/simulation'

interface Props {
  node1: ScenarioNodeData
  node2: ScenarioNodeData
  onClose: () => void
}

export default function BranchComparison({ node1, node2, onClose }: Props) {
  // Helper to format score with color
  const scoreColor = (value: number | undefined) => {
    if (value == null) return 'text-surface-400'
    if (value > 0.5) return 'text-emerald-400'
    if (value > 0.3) return 'text-amber-400'
    return 'text-red-400'
  }

  // Helper to get delta color (node1 vs node2)
  const deltaColor = (n1: number | undefined, n2: number | undefined) => {
    if (n1 == null || n2 == null) return 'text-surface-400'
    const delta = n1 - n2
    if (Math.abs(delta) < 0.01) return 'text-surface-400'
    if (delta > 0) return 'text-emerald-400'
    return 'text-red-400'
  }

  const deltaSymbol = (n1: number | undefined, n2: number | undefined) => {
    if (n1 == null || n2 == null) return '—'
    const delta = n1 - n2
    if (Math.abs(delta) < 0.01) return '='
    if (delta > 0) return '▲'
    return '▼'
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-bg-primary border border-white/[0.1] rounded-lg w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/[0.1]">
          <h2 className="text-lg font-semibold text-surface-50">🔀 Branch Comparison</h2>
          <button
            onClick={onClose}
            className="text-surface-400 hover:text-surface-200 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Main content */}
        <div className="flex-1 overflow-auto">
          <div className="grid grid-cols-3 gap-4 p-6">
            {/* Left: Node 1 */}
            <div className="flex flex-col gap-4">
              <div className="sticky top-0 bg-bg-primary pb-2 border-b border-white/[0.1]">
                <h3 className="text-sm font-semibold text-accent-teal mb-2">
                  Branch A (d{node1.depth})
                </h3>
                <p className="text-xs text-surface-300 leading-relaxed">
                  {node1.hypothesis}
                </p>
              </div>

              {/* Scores */}
              <div className="space-y-2 text-xs">
                {node1.emergence_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">✨ Emergence</span>
                    <span className={scoreColor(node1.emergence_score)}>
                      {node1.emergence_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.narrative_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">📖 Narrative</span>
                    <span className={scoreColor(node1.narrative_score)}>
                      {node1.narrative_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.diversity_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">🎭 Diversity</span>
                    <span className={scoreColor(node1.diversity_score)}>
                      {node1.diversity_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.novelty_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">🆕 Novelty</span>
                    <span className={scoreColor(node1.novelty_score)}>
                      {node1.novelty_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.score != null && (
                  <div className="flex justify-between border-t border-white/[0.1] pt-2 mt-2">
                    <span className="text-accent-amber font-semibold">⭐ Composite</span>
                    <span className={scoreColor(node1.score)}>
                      {node1.score.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="text-[10px] text-surface-400 space-y-1 border-t border-white/[0.1] pt-2 mt-2">
                <div>Turns: {node1.turns_simulated}</div>
                <div>Years: {node1.years_simulated}</div>
                <div>Status: {node1.status}</div>
              </div>
            </div>

            {/* Center: Delta / Comparison */}
            <div className="flex flex-col gap-4">
              <div className="sticky top-0 bg-bg-primary pb-2 border-b border-white/[0.1]">
                <h3 className="text-sm font-semibold text-surface-300 text-center">
                  Delta (A vs B)
                </h3>
              </div>

              {/* Score deltas */}
              <div className="space-y-2 text-xs">
                {node1.emergence_score != null && node2.emergence_score != null && (
                  <div className="flex justify-between items-center">
                    <span className="text-surface-400">✨</span>
                    <span className={`font-mono font-semibold ${deltaColor(node1.emergence_score, node2.emergence_score)}`}>
                      {deltaSymbol(node1.emergence_score, node2.emergence_score)} {Math.abs((node1.emergence_score - node2.emergence_score)).toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.narrative_score != null && node2.narrative_score != null && (
                  <div className="flex justify-between items-center">
                    <span className="text-surface-400">📖</span>
                    <span className={`font-mono font-semibold ${deltaColor(node1.narrative_score, node2.narrative_score)}`}>
                      {deltaSymbol(node1.narrative_score, node2.narrative_score)} {Math.abs((node1.narrative_score - node2.narrative_score)).toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.diversity_score != null && node2.diversity_score != null && (
                  <div className="flex justify-between items-center">
                    <span className="text-surface-400">🎭</span>
                    <span className={`font-mono font-semibold ${deltaColor(node1.diversity_score, node2.diversity_score)}`}>
                      {deltaSymbol(node1.diversity_score, node2.diversity_score)} {Math.abs((node1.diversity_score - node2.diversity_score)).toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.novelty_score != null && node2.novelty_score != null && (
                  <div className="flex justify-between items-center">
                    <span className="text-surface-400">🆕</span>
                    <span className={`font-mono font-semibold ${deltaColor(node1.novelty_score, node2.novelty_score)}`}>
                      {deltaSymbol(node1.novelty_score, node2.novelty_score)} {Math.abs((node1.novelty_score - node2.novelty_score)).toFixed(2)}
                    </span>
                  </div>
                )}
                {node1.score != null && node2.score != null && (
                  <div className="flex justify-between items-center border-t border-white/[0.1] pt-2 mt-2">
                    <span className="text-accent-amber">⭐</span>
                    <span className={`font-mono font-semibold ${deltaColor(node1.score, node2.score)}`}>
                      {deltaSymbol(node1.score, node2.score)} {Math.abs((node1.score - node2.score)).toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Legend */}
              <div className="text-[10px] text-surface-400 space-y-1 border-t border-white/[0.1] pt-2 mt-2">
                <div>▲ = A better</div>
                <div>▼ = B better</div>
                <div>= = equal</div>
              </div>
            </div>

            {/* Right: Node 2 */}
            <div className="flex flex-col gap-4">
              <div className="sticky top-0 bg-bg-primary pb-2 border-b border-white/[0.1]">
                <h3 className="text-sm font-semibold text-accent-orange mb-2">
                  Branch B (d{node2.depth})
                </h3>
                <p className="text-xs text-surface-300 leading-relaxed">
                  {node2.hypothesis}
                </p>
              </div>

              {/* Scores */}
              <div className="space-y-2 text-xs">
                {node2.emergence_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">✨ Emergence</span>
                    <span className={scoreColor(node2.emergence_score)}>
                      {node2.emergence_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node2.narrative_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">📖 Narrative</span>
                    <span className={scoreColor(node2.narrative_score)}>
                      {node2.narrative_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node2.diversity_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">🎭 Diversity</span>
                    <span className={scoreColor(node2.diversity_score)}>
                      {node2.diversity_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node2.novelty_score != null && (
                  <div className="flex justify-between">
                    <span className="text-surface-400">🆕 Novelty</span>
                    <span className={scoreColor(node2.novelty_score)}>
                      {node2.novelty_score.toFixed(2)}
                    </span>
                  </div>
                )}
                {node2.score != null && (
                  <div className="flex justify-between border-t border-white/[0.1] pt-2 mt-2">
                    <span className="text-accent-amber font-semibold">⭐ Composite</span>
                    <span className={scoreColor(node2.score)}>
                      {node2.score.toFixed(2)}
                    </span>
                  </div>
                )}
              </div>

              {/* Metadata */}
              <div className="text-[10px] text-surface-400 space-y-1 border-t border-white/[0.1] pt-2 mt-2">
                <div>Turns: {node2.turns_simulated}</div>
                <div>Years: {node2.years_simulated}</div>
                <div>Status: {node2.status}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
