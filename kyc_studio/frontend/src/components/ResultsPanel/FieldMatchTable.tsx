import type { FieldMatch } from '../../lib/types'

export function FieldMatchTable({ rows }: { rows: FieldMatch[] }) {
  if (!rows.length) {
    return <div className="rounded-xl border border-border bg-panel-muted p-3 text-xs text-fg-muted">No field-level details.</div>
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[380px] text-left text-xs">
        <thead className="bg-panel-muted text-fg-muted">
          <tr>
            <th className="px-2 py-2">Field</th>
            <th className="px-2 py-2">Extracted</th>
            <th className="px-2 py-2">Ground Truth</th>
            <th className="px-2 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.field} className="border-t border-border/70">
              <td className="px-2 py-2 font-semibold">{row.field}</td>
              <td className="px-2 py-2">{String(row.extracted ?? '')}</td>
              <td className="px-2 py-2">{String(row.ground_truth ?? '')}</td>
              <td className="px-2 py-2">
                <span
                  className={`rounded px-1.5 py-0.5 ${
                    row.status === 'match' ? 'bg-emerald-500/15 text-emerald-500' : 'bg-rose-500/15 text-rose-500'
                  }`}
                >
                  {row.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
