import { Download } from 'lucide-react'
import type { DocType, MethodType } from '../lib/types'
import { downloadActiveRubricsMarkdown, downloadRulesReference, downloadRubricReference } from '../lib/api'

const DOC_LABELS: Record<DocType, string> = {
  passport: 'Passport',
  aadhaar: 'Aadhaar',
  pan: 'PAN',
}

const ALL_DOC_TYPES: DocType[] = ['passport', 'aadhaar', 'pan']

interface Props {
  method: MethodType
  selectedDocs: DocType[]
}

function panelCopy(method: MethodType): { title: string; description: string } {
  if (method === 'rules') {
    return {
      title: 'Built-in rules',
      description: 'Rule-based checks run automatically. Download the reference to see every rule and weight.',
    }
  }
  if (method === 'llm') {
    return {
      title: 'Built-in rubrics',
      description:
        'Rubrics are selected per uploaded document at run time. Download the rubric(s) that apply to your selection.',
    }
  }
  return {
    title: 'Built-in rules & rubrics',
    description:
      'Rules and per-document rubrics run together. Download each reference below to review what will be used.',
  }
}

export function EvaluationReferencePanel({ method, selectedDocs }: Props) {
  const showRules = method === 'rules'
  const showRubrics = method === 'llm'
  const showBoth = method === 'both'
  const rubricDocTypes = selectedDocs.length ? selectedDocs : ALL_DOC_TYPES
  const { title, description } = panelCopy(method)

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <h3 className="mb-1 font-heading text-sm font-semibold">{title}</h3>
      <p className="mb-3 text-xs text-fg-muted">{description}</p>

      <div className="flex flex-col gap-3">
        {(showRules || showBoth) && (
          <div>
            {showBoth ? (
              <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-fg-muted">Rules</div>
            ) : null}
            <button
              type="button"
              onClick={downloadRulesReference}
              className="inline-flex w-full items-center gap-2 rounded-lg border border-border bg-panel-muted px-3 py-2 text-xs font-medium text-link hover:bg-panel"
            >
              <Download className="h-3.5 w-3.5" />
              Download rules reference (.md)
            </button>
          </div>
        )}

        {(showRubrics || showBoth) && (
          <div>
            {showBoth ? (
              <div className="mb-1.5 text-xs font-semibold uppercase tracking-wide text-fg-muted">Rubrics</div>
            ) : null}
            <button
              type="button"
              onClick={() => downloadActiveRubricsMarkdown(rubricDocTypes)}
              className="mb-2 inline-flex w-full items-center gap-2 rounded-lg border border-border bg-panel-muted px-3 py-2 text-xs font-medium text-link hover:bg-panel"
            >
              <Download className="h-3.5 w-3.5" />
              Download rubric{rubricDocTypes.length > 1 ? 's' : ''} ({rubricDocTypes.length} .md
              {rubricDocTypes.length > 1 ? ' files' : ''})
            </button>
            {!selectedDocs.length && showRubrics ? (
              <p className="mb-2 text-[11px] text-fg-muted">
                No document selected yet — showing all built-in rubrics. Only selected types are used at run time.
              </p>
            ) : null}
            <ul className="space-y-1 text-xs text-fg-muted">
              {rubricDocTypes.map((doc) => (
                <li key={doc} className="flex items-center justify-between gap-2 rounded-md bg-page/30 px-2 py-1">
                  <span>
                    {DOC_LABELS[doc]}
                    {selectedDocs.includes(doc) ? ' (will be used)' : ''}
                  </span>
                  <button
                    type="button"
                    onClick={() => downloadRubricReference(doc)}
                    className="shrink-0 font-medium text-link hover:opacity-80"
                  >
                    Download .md
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  )
}
