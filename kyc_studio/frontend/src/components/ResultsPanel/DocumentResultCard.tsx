import { useState } from 'react'
import type { DocumentKYCResult } from '../../lib/types'
import { FieldMatchTable } from './FieldMatchTable'

export function DocumentResultCard({ result }: { result: DocumentKYCResult }) {
  const [open, setOpen] = useState(false)

  return (
    <article className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <button type="button" onClick={() => setOpen((v) => !v)} className="flex w-full items-center justify-between text-left">
        <div>
          <div className="text-xs uppercase tracking-wide text-fg-muted">{result.doc_type}</div>
          <div className="font-heading text-lg font-semibold">{result.document_id}</div>
        </div>
        <span className="rounded-full bg-panel-muted px-3 py-1 text-xs font-semibold">{result.score.toFixed(1)}%</span>
      </button>

      {open ? (
        <div className="mt-3 space-y-3">
          <div className="rounded-xl border border-border bg-panel-muted p-2">
            {result.checks.map((check) => (
              <div key={check.name} className="flex items-start justify-between gap-2 py-1 text-xs">
                <span>{check.name}</span>
                <span className={check.passed ? 'text-emerald-500' : 'text-rose-500'}>{check.passed ? 'PASS' : 'FAIL'}</span>
              </div>
            ))}
          </div>
          <FieldMatchTable rows={result.field_matches} />
        </div>
      ) : null}
    </article>
  )
}
