export function EvaluationModeBadge({ mode }: { mode: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-panel-muted px-2 py-1 text-xs font-semibold uppercase tracking-wide text-fg-muted">
      {mode}
    </span>
  )
}
