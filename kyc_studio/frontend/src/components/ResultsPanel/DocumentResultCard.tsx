import { useState } from 'react'
import type { DocumentKYCResult } from '../../lib/types'
import { scoreFromChecks, splitRulesRubricChecks } from '../../lib/scoreUtils'
import { FieldMatchTable } from './FieldMatchTable'

export function DocumentResultCard({
  result,
  showScoreBreakdown = false,
}: {
  result: DocumentKYCResult
  showScoreBreakdown?: boolean
}) {
  const [open, setOpen] = useState(false)
  const prettyDocType = result.doc_type.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase())
  const { rules, rubric } = splitRulesRubricChecks(result.checks)
  const hasDualScores = showScoreBreakdown && rules.length > 0 && rubric.length > 0
  const rulesScore = hasDualScores ? scoreFromChecks(rules) : null
  const rubricScore = hasDualScores ? scoreFromChecks(rubric) : null

  return (
    <article className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <button type="button" onClick={() => setOpen((v) => !v)} className="flex w-full items-center justify-between text-left">
        <div>
          <div className="text-xs uppercase tracking-wide text-fg-muted">{prettyDocType}</div>
          <div className="font-heading text-lg font-semibold">{result.document_id}</div>
        </div>
        <div className="text-right">
          <span className="rounded-full bg-panel-muted px-3 py-1 text-xs font-semibold">{result.score.toFixed(1)}%</span>
          {hasDualScores ? (
            <div className="mt-1 text-[10px] text-fg-muted">
              Rules {rulesScore?.toFixed(1)}% · Rubric {rubricScore?.toFixed(1)}%
            </div>
          ) : null}
        </div>
      </button>

      {open ? (
        <div className="mt-3 space-y-3">
          {hasDualScores ? (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="rounded-lg border border-border bg-panel-muted p-2">
                <div className="text-fg-muted">Rules</div>
                <div className="font-semibold">{rulesScore?.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-border bg-panel-muted p-2">
                <div className="text-fg-muted">Rubric</div>
                <div className="font-semibold">{rubricScore?.toFixed(1)}%</div>
              </div>
              <div className="rounded-lg border border-border bg-panel-muted p-2">
                <div className="text-fg-muted">Card score</div>
                <div className="font-semibold">{result.score.toFixed(1)}%</div>
              </div>
            </div>
          ) : null}
          <div className="rounded-xl border border-border bg-panel-muted p-2">
            {result.checks.map((check) => (
              <div key={check.name} className="flex items-start justify-between gap-2 py-1 text-xs">
                <span>
                  {check.name}
                  <span className="ml-2 text-fg-muted">
                    ({check.score.toFixed(1)} / 100, w={check.weight.toFixed(2)})
                  </span>
                </span>
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
