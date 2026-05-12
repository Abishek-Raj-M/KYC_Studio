import { CheckCircle2, FileImage, PlusCircle, Scan } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import type { DocType, Side, UploadedDocImage } from '../lib/types'

interface DocumentUploadCardProps {
  docType: DocType
  title: string
  front?: UploadedDocImage
  back?: UploadedDocImage
  extracted: boolean
  showBack: boolean
  onToggleBack: () => void
  onFileDrop: (file: File, docType: DocType, side: Side) => void
}

function UploadZone({
  label,
  docType,
  side,
  image,
  onFileDrop,
}: {
  label: string
  docType: DocType
  side: Side
  image?: UploadedDocImage
  onFileDrop: (file: File, docType: DocType, side: Side) => void
}) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: 1,
    accept: { 'image/*': [] },
    onDropAccepted: (files) => {
      if (files[0]) onFileDrop(files[0], docType, side)
    },
  })

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-xl border border-dashed p-3 transition ${
        isDragActive ? 'border-link bg-panel' : 'border-border bg-panel-muted'
      }`}
    >
      <input {...getInputProps()} />
      <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">
        <Scan className="h-3.5 w-3.5" />
        {label}
      </div>
      {image ? (
        <img src={image.previewUrl} alt={`${docType}-${side}`} className="h-24 w-full rounded-lg object-cover" />
      ) : (
        <div className="flex h-24 items-center justify-center rounded-lg border border-border/60 bg-page/40 text-xs text-fg-muted">
          Drag image or click to upload
        </div>
      )}
    </div>
  )
}

export function DocumentUploadCard(props: DocumentUploadCardProps) {
  const { docType, title, front, back, extracted, showBack, onToggleBack, onFileDrop } = props

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileImage className="h-4 w-4 text-link" />
          <h3 className="font-heading text-sm font-semibold">{title}</h3>
        </div>
        {extracted ? (
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/15 px-2 py-1 text-xs text-emerald-500">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Extracted
          </span>
        ) : (
          <span className="text-xs text-fg-muted">Awaiting image</span>
        )}
      </div>

      <div className="space-y-3">
        <UploadZone label="Front (Required)" docType={docType} side="front" image={front} onFileDrop={onFileDrop} />

        {!showBack ? (
          <button
            type="button"
            onClick={onToggleBack}
            className="inline-flex items-center gap-1 text-xs font-medium text-link hover:opacity-80"
          >
            <PlusCircle className="h-3.5 w-3.5" />
            Add back side
          </button>
        ) : (
          <UploadZone label="Back (Optional)" docType={docType} side="back" image={back} onFileDrop={onFileDrop} />
        )}
      </div>
    </section>
  )
}
