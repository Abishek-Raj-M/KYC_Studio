import { useDropzone } from 'react-dropzone'
import { Database, Download } from 'lucide-react'
import { downloadGroundTruthTemplate } from '../lib/api'
import type { GroundTruth } from '../lib/types'

interface GroundTruthUploadProps {
  data: GroundTruth | null
  onParsed: (payload: GroundTruth) => void
}

export function GroundTruthUpload({ data, onParsed }: GroundTruthUploadProps) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: 1,
    accept: { 'application/json': ['.json'] },
    onDropAccepted: async (files) => {
      const txt = await files[0].text()
      onParsed(JSON.parse(txt))
    },
  })

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-heading text-sm font-semibold">
          <Database className="h-4 w-4 text-link" /> Ground Truth JSON
        </h3>
        <button
          type="button"
          onClick={downloadGroundTruthTemplate}
          className="inline-flex items-center gap-1 rounded-lg border border-border px-2 py-1 text-xs hover:bg-panel-muted"
        >
          <Download className="h-3.5 w-3.5" /> Template
        </button>
      </div>

      <div
        {...getRootProps()}
        className={`cursor-pointer rounded-xl border border-dashed p-3 text-sm ${
          isDragActive ? 'border-link bg-panel' : 'border-border bg-panel-muted'
        }`}
      >
        <input {...getInputProps()} />
        Upload or drop ground-truth JSON
      </div>

      {data ? (
        <div className="mt-2 rounded-xl border border-border bg-page/40 p-2 text-xs text-fg-muted">
          <div>Name: {data.name || 'N/A'}</div>
          <div>DOB: {data.dob || 'N/A'}</div>
        </div>
      ) : null}
    </section>
  )
}
