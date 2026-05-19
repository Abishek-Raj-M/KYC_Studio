import { CheckCircle2, FileImage, PlusCircle, Scan } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { useState } from 'react'
import { ClearUploadButton } from './ClearUploadButton'
import type { DocType, Side, UploadedDocImage } from '../lib/types'

interface DocumentUploadCardProps {
  docType: DocType
  title: string
  front?: UploadedDocImage
  back?: UploadedDocImage
  extracted: boolean
  extractedData?: Record<string, unknown>
  showBack: boolean
  onToggleBack: () => void
  onFileDrop: (file: File, docType: DocType, side: Side) => void
  onClearImage: (docType: DocType, side: Side) => void
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return 'N/A'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function UploadZone({
  label,
  docType,
  side,
  image,
  onFileDrop,
  onClearImage,
}: {
  label: string
  docType: DocType
  side: Side
  image?: UploadedDocImage
  onFileDrop: (file: File, docType: DocType, side: Side) => void
  onClearImage: (docType: DocType, side: Side) => void
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
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-fg-muted">
          <Scan className="h-3.5 w-3.5" />
          {label}
        </div>
        {image ? <ClearUploadButton onClick={() => onClearImage(docType, side)} /> : null}
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
  const { docType, title, front, back, extracted, extractedData, showBack, onToggleBack, onFileDrop, onClearImage } = props
  const [showExtractedData, setShowExtractedData] = useState(false)

  const extractedDocType = String(extractedData?.document_type ?? '')
  const slotMismatch =
    extracted && extractedDocType && extractedDocType !== docType && extractedDocType !== 'unknown'

  const previewFields = Object.entries(extractedData || {})
    .filter(([key]) => !key.startsWith('_'))
    .sort(([a], [b]) => a.localeCompare(b))

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

      {slotMismatch ? (
        <p className="mb-2 rounded-lg border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-xs text-amber-600">
          Extracted type is <span className="font-semibold">{extractedDocType}</span> but slot is{' '}
          <span className="font-semibold">{docType}</span>.
        </p>
      ) : null}

      {extracted && previewFields.length ? (
        <div className="mb-2">
          <button
            type="button"
            onClick={() => setShowExtractedData((v) => !v)}
            className="text-xs font-medium text-link hover:opacity-80"
          >
            {showExtractedData ? 'Hide extracted data' : 'Show extracted data'}
          </button>
        </div>
      ) : null}

      {extracted && previewFields.length && showExtractedData ? (
        <div className="mb-3 rounded-xl border border-border bg-page/40 p-2">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-fg-muted">Extracted Data</div>
          <div className="grid grid-cols-1 gap-1 text-xs">
            {previewFields.map(([key, value]) => (
              <div key={key} className="flex items-start justify-between gap-2 rounded-md bg-panel-muted px-2 py-1">
                <span className="font-medium text-fg-muted">{key}</span>
                <span className="max-w-[58%] break-words text-right text-fg">{formatValue(value)}</span>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="space-y-3">
        <UploadZone
          label="Front (Required)"
          docType={docType}
          side="front"
          image={front}
          onFileDrop={onFileDrop}
          onClearImage={onClearImage}
        />

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
          <UploadZone
            label="Back (Optional)"
            docType={docType}
            side="back"
            image={back}
            onFileDrop={onFileDrop}
            onClearImage={onClearImage}
          />
        )}
      </div>
    </section>
  )
}
