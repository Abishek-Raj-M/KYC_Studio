import { useDropzone } from 'react-dropzone'
import { ChevronDown, ChevronUp, Download, FileCode2 } from 'lucide-react'
import { downloadRubricTemplate } from '../lib/api'
import { useState } from 'react'
import type { DocType, RubricMode } from '../lib/types'

interface Props {
  selectedDocs: DocType[]
  rubricMode: RubricMode
  value: string
  byDocType: Partial<Record<DocType, string>>
  onRubricModeChange: (mode: RubricMode) => void
  onParsed: (yaml: string) => void
  onParsedForDocType: (docType: DocType, yaml: string) => void
}

function UploadZone({
  label,
  value,
  onParsed,
}: {
  label: string
  value: string
  onParsed: (yaml: string) => void
}) {
  const [showRubricData, setShowRubricData] = useState(false)
  const [uploadedFileName, setUploadedFileName] = useState('')

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: 1,
    accept: {
      'application/x-yaml': ['.yaml', '.yml'],
      'text/yaml': ['.yaml', '.yml'],
      'text/plain': ['.yaml', '.yml'],
    },
    onDropAccepted: async (files) => {
      const txt = await files[0].text()
      setUploadedFileName(files[0].name)
      onParsed(txt)
    },
  })

  return (
    <div>
      <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-fg-muted">{label}</div>
      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border border-dashed p-3 text-sm ${
          isDragActive ? 'border-link bg-panel' : 'border-border bg-panel-muted'
        }`}
      >
        <input {...getInputProps()} />
        {uploadedFileName ? uploadedFileName : 'Upload or drop rubric'}
      </div>
      <div className="mt-1 flex items-center justify-between gap-2 text-xs text-fg-muted">
        <p className="truncate">{value ? uploadedFileName || 'Rubric loaded' : 'No rubric loaded'}</p>
        {value ? (
          <button
            type="button"
            onClick={() => setShowRubricData((prev) => !prev)}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-[11px] font-medium hover:bg-panel"
          >
            {showRubricData ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
            {showRubricData ? 'Hide' : 'Show'}
          </button>
        ) : null}
      </div>
      {value && showRubricData ? (
        <div className="mt-2 rounded-xl border border-border bg-page/40 p-2 text-xs text-fg-muted">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide">Full Uploaded Rubric</div>
          <pre className="max-h-56 overflow-auto rounded-md border border-border/60 bg-panel-muted p-2 text-[11px] leading-relaxed text-fg">
            {value}
          </pre>
        </div>
      ) : null}
    </div>
  )
}

export function RubricUpload({
  selectedDocs,
  rubricMode,
  value,
  byDocType,
  onRubricModeChange,
  onParsed,
  onParsedForDocType,
}: Props) {

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-heading text-sm font-semibold">
          <FileCode2 className="h-4 w-4 text-link" /> Rubric
        </h3>
        <button
          type="button"
          onClick={downloadRubricTemplate}
          className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs hover:bg-panel-muted"
        >
          <Download className="h-3.5 w-3.5" /> Template
        </button>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-1 rounded-xl border border-border bg-panel-muted p-1">
        {[
          { label: 'One Rubric For All', value: 'single' as const },
          { label: 'Rubric Per Document', value: 'per_doc' as const },
        ].map((opt) => (
          <button
            key={opt.value}
            type="button"
            onClick={() => onRubricModeChange(opt.value)}
            className={`rounded-lg px-2 py-1.5 text-xs font-medium transition ${
              rubricMode === opt.value ? 'bg-brand text-white' : 'text-fg-muted hover:bg-panel'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {rubricMode === 'single' ? (
        <UploadZone label="Common Rubric" value={value} onParsed={onParsed} />
      ) : (
        <div className="space-y-3">
          {selectedDocs.map((docType) => (
            <UploadZone
              key={docType}
              label={`${docType.toUpperCase()} Rubric`}
              value={byDocType[docType] || ''}
              onParsed={(yaml) => onParsedForDocType(docType, yaml)}
            />
          ))}
        </div>
      )}
    </section>
  )
}
