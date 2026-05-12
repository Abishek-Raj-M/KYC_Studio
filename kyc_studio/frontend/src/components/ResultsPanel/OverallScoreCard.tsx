interface Props {
  score: number
  passed: boolean
  label?: string
}

export function OverallScoreCard({ score, passed, label = 'Overall Score' }: Props) {
  return (
    <article className="surface-glass rounded-2xl border border-border bg-panel p-4 shadow-card">
      <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">{label}</div>
      <div className="flex items-end justify-between">
        <div className="font-heading text-4xl font-bold">{score.toFixed(2)}%</div>
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            passed ? 'bg-emerald-500/20 text-emerald-500' : 'bg-rose-500/20 text-rose-500'
          }`}
        >
          {passed ? 'PASS' : 'FAIL'}
        </span>
      </div>
    </article>
  )
}
