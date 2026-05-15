import { X } from 'lucide-react'

interface Props {
  label?: string
  onClick: () => void
  className?: string
}

export function ClearUploadButton({ label = 'Clear', onClick, className = '' }: Props) {
  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation()
        onClick()
      }}
      className={`inline-flex items-center gap-1 rounded-md border border-border bg-panel px-2 py-1 text-[11px] font-medium text-fg-muted transition hover:border-rose-500/40 hover:bg-rose-500/10 hover:text-rose-500 ${className}`}
      title={label}
    >
      <X className="h-3 w-3" />
      {label}
    </button>
  )
}
