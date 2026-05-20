import { BookOpen, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { fetchRulesReference } from '../lib/api'
import { MarkdownDoc } from './MarkdownDoc'

export function EvaluationReferencePanel() {
  const [showRules, setShowRules] = useState(false)
  const [rulesText, setRulesText] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function toggleRules() {
    if (showRules) {
      setShowRules(false)
      return
    }

    setShowRules(true)
    if (rulesText) return

    setLoading(true)
    setError(null)
    try {
      const text = await fetchRulesReference()
      setRulesText(text)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load rules reference')
      setShowRules(false)
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <h3 className="mb-1 flex items-center gap-2 font-heading text-sm font-semibold">
        <BookOpen className="h-4 w-4 text-link" />
        Built-in rules
      </h3>
      <p className="mb-2 text-xs text-fg-muted">
        Deterministic checks run against extracted fields and your ground truth manifest.
      </p>

      <button
        type="button"
        onClick={toggleRules}
        disabled={loading}
        className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-panel-muted px-3 py-2 text-xs font-medium text-link hover:bg-panel disabled:opacity-70"
      >
        {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
        {showRules ? 'Hide rules reference' : 'Show rules reference'}
      </button>

      {error ? <p className="mt-2 text-xs text-rose-500">{error}</p> : null}

      {showRules && rulesText ? (
        <div className="mt-2">
          <MarkdownDoc content={rulesText} />
        </div>
      ) : null}
    </section>
  )
}
