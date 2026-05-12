import type { MethodType, ScopeType } from '../lib/types'

interface Props {
  method: MethodType
  scope: ScopeType
  onMethod: (v: MethodType) => void
  onScope: (v: ScopeType) => void
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="grid grid-cols-3 gap-1 rounded-xl border border-border bg-panel-muted p-1">
      {options.map((opt) => (
        <button
          key={opt.value}
          type="button"
          onClick={() => onChange(opt.value)}
          className={`rounded-lg px-2 py-1.5 text-xs font-medium transition ${
            value === opt.value ? 'bg-brand text-white' : 'text-fg-muted hover:bg-panel'
          }`}
        >
          {opt.label}
        </button>
      ))}
    </div>
  )
}

export function EvaluationConfig({ method, scope, onMethod, onScope }: Props) {
  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <h3 className="mb-2 font-heading text-sm font-semibold">Evaluation Config</h3>

      <div className="space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Method</div>
        <Segmented
          options={[
            { label: 'Rule-Based', value: 'rules' },
            { label: 'LLM Rubric', value: 'llm' },
            { label: 'Both', value: 'both' },
          ]}
          value={method}
          onChange={onMethod}
        />
      </div>

      <div className="mt-3 space-y-2">
        <div className="text-xs font-semibold uppercase tracking-wide text-fg-muted">Scope</div>
        <div className="grid grid-cols-2 gap-1 rounded-xl border border-border bg-panel-muted p-1">
          {[
            { label: 'Individual', value: 'individual' as const },
            { label: 'All Together', value: 'all' as const },
          ].map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => onScope(opt.value)}
              className={`rounded-lg px-2 py-1.5 text-xs font-medium transition ${
                scope === opt.value ? 'bg-brand text-white' : 'text-fg-muted hover:bg-panel'
              }`}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
    </section>
  )
}
