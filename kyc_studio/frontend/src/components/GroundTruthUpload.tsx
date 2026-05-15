import { useDropzone } from 'react-dropzone'
import { Database, Download } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ClearUploadButton } from './ClearUploadButton'
import { downloadGroundTruthTemplate } from '../lib/api'
import type { GroundTruth, GroundTruthManifest } from '../lib/types'

interface GroundTruthUploadProps {
  data: GroundTruth | null
  manifest: GroundTruthManifest | null
  onParsed: (payload: GroundTruth) => void
  onParsedManifest: (payload: GroundTruthManifest) => void
  onClear: () => void
}

function normalizeManifestToGroundTruth(input: unknown): { summary: GroundTruth; manifest: GroundTruthManifest } {
  if (!input || typeof input !== 'object') {
    throw new Error('Invalid JSON payload')
  }

  const root = input as Record<string, unknown>
  const person = (root.person && typeof root.person === 'object' ? root.person : {}) as Record<string, unknown>
  const documents = (root.documents && typeof root.documents === 'object' ? root.documents : {}) as Record<string, unknown>

  if (!Object.keys(person).length || !Object.keys(documents).length) {
    throw new Error('Ground truth must use manifest format with person and documents')
  }

  const passportFields = ((documents.passport as Record<string, unknown>)?.fields || {}) as Record<string, unknown>
  const panFields = ((documents.pan_card as Record<string, unknown>)?.fields || {}) as Record<string, unknown>
  const aadhaarFields = ((documents.aadhaar as Record<string, unknown>)?.fields || {}) as Record<string, unknown>

  const manifest: GroundTruthManifest = {
    ...(root as Record<string, unknown>),
    person,
    documents: documents as GroundTruthManifest['documents'],
  }

  return {
    summary: {
      name: String(person.name || ''),
      dob: String(person.dob || ''),
      gender: String(person.gender || ''),
      nationality: String(person.nationality || ''),
      address: String(aadhaarFields.address || ''),
      id_numbers: {
        passport: String(passportFields.passport_number || ''),
        pan: String(panFields.pan || ''),
        aadhaar: String(aadhaarFields.aadhaar || ''),
      },
    },
    manifest,
  }
}

export function GroundTruthUpload({ data, manifest, onParsed, onParsedManifest, onClear }: GroundTruthUploadProps) {
  const [showGroundTruthData, setShowGroundTruthData] = useState(false)
  const [uploadedFileName, setUploadedFileName] = useState('')

  useEffect(() => {
    if (!data) setUploadedFileName('')
  }, [data])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    maxFiles: 1,
    accept: { 'application/json': ['.json'] },
    onDropAccepted: async (files) => {
      const txt = await files[0].text()
      setUploadedFileName(files[0].name)
      const parsed = JSON.parse(txt)
      const normalized = normalizeManifestToGroundTruth(parsed)
      onParsed(normalized.summary)
      onParsedManifest(normalized.manifest)
    },
  })

  return (
    <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="flex items-center gap-2 font-heading text-sm font-semibold">
          <Database className="h-4 w-4 text-link" /> Ground Truth
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
        <div className="flex items-center justify-between gap-2">
          <span className="truncate">
            {uploadedFileName || (data ? 'Ground truth loaded' : 'Upload or drop ground truth JSON')}
          </span>
          {data || uploadedFileName ? <ClearUploadButton onClick={onClear} /> : null}
        </div>
      </div>

      {data ? (
        <div className="mt-2 rounded-xl border border-border bg-page/40 p-2 text-xs text-fg-muted">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide">Loaded Ground Truth</div>
          <div>Name: {data.name || 'N/A'}</div>
          <div>DOB: {data.dob || 'N/A'}</div>
          <div>Gender: {data.gender || 'N/A'}</div>
          <div>Nationality: {data.nationality || 'N/A'}</div>
          <div>Address: {data.address || 'N/A'}</div>
          <div>
            IDs:{' '}
            {data.id_numbers && Object.keys(data.id_numbers).length
              ? Object.entries(data.id_numbers)
                  .map(([k, v]) => `${k}: ${v}`)
                  .join(' | ')
              : 'N/A'}
          </div>
        </div>
      ) : null}

      {data ? (
        <div className="mt-2">
          <button
            type="button"
            onClick={() => setShowGroundTruthData((v) => !v)}
            className="text-xs font-medium text-link hover:opacity-80"
          >
            {showGroundTruthData ? 'Hide full uploaded ground truth' : 'Show full uploaded ground truth'}
          </button>
        </div>
      ) : null}

      {data && showGroundTruthData ? (
        <div className="mt-2 rounded-xl border border-border bg-page/40 p-2 text-xs text-fg-muted">
          <div className="mb-1 text-[11px] font-semibold uppercase tracking-wide">Full Uploaded Ground Truth (JSON)</div>
          <pre className="max-h-56 overflow-auto rounded-md border border-border/60 bg-panel-muted p-2 text-[11px] leading-relaxed text-fg">
            {JSON.stringify(manifest ?? data, null, 2)}
          </pre>
        </div>
      ) : null}
    </section>
  )
}
