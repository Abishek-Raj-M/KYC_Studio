import type { ScopeType } from '../lib/types'

interface Props {
  scope: ScopeType
  onScope: (v: ScopeType) => void
}

const SCOPE_OPTIONS: { label: string; hint: string; value: ScopeType }[] = [
  {
    label: 'Per document',
    hint: 'One score card per uploaded document',
    value: 'individual',
  },
  {
    label: 'Combined',
    hint: 'Overall score, combined checks with fields, plus per-document cards',
    value: 'all',
  },
]

export function EvaluationConfig({ scope, onScope }: Props) {
  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <h3 className="mb-1 font-heading text-sm font-semibold">Evaluation scope</h3>
      <p className="mb-3 text-xs text-fg-muted">Rule-based checks run automatically against your ground truth manifest.</p>

      <div className="grid grid-cols-2 gap-2">
        {SCOPE_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onScope(opt.value)}
            className={`rounded-xl border px-3 py-2.5 text-left transition ${
              scope === opt.value
                ? 'border-link bg-brand text-white'
                : 'border-border bg-panel-muted text-fg-muted hover:bg-panel'
            }`}
          >
            <span className="block text-xs font-semibold">{opt.label}</span>
            <span className={`mt-0.5 block text-[11px] ${scope === opt.value ? 'text-white/80' : 'text-fg-muted'}`}>
              {opt.hint}
            </span>
          </button>
        ))}
      </div>
    </section>
  )
}
