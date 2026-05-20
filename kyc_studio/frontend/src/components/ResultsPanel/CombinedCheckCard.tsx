import { useState } from 'react'
import type { CheckResult } from '../../lib/types'
import { FieldMatchTable } from './FieldMatchTable'

export function CombinedCheckCard({ check }: { check: CheckResult }) {
  const [open, setOpen] = useState(false)
  const fieldRows = check.field_matches ?? []

  return (
    <article className="rounded-lg border border-border bg-panel-muted">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start justify-between gap-2 p-2 text-left text-xs"
      >
        <span className="font-medium">
          {check.name}
          <span className="ml-2 text-fg-muted">
            ({check.score.toFixed(1)} / 100, w={check.weight.toFixed(2)})
          </span>
        </span>
        <span className={`shrink-0 ${check.passed ? 'text-emerald-500' : 'text-rose-500'}`}>
          {check.passed ? 'PASS' : 'FAIL'}
        </span>
      </button>

      {open ? (
        <div className="space-y-2 border-t border-border/70 px-2 pb-2 pt-2">
          <p className="text-xs text-fg-muted">{check.detail}</p>
          {fieldRows.length ? (
            <FieldMatchTable rows={fieldRows} showSource />
          ) : (
            <p className="text-[11px] text-fg-muted">No linked field rows for this check.</p>
          )}
        </div>
      ) : (
        <p className="line-clamp-2 px-2 pb-2 text-[11px] text-fg-muted">{check.detail}</p>
      )}
    </article>
  )
}
