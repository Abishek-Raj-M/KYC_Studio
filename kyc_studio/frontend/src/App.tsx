import { useMemo, useState } from 'react'
import { AlertCircle, Loader2, ShieldCheck } from 'lucide-react'
import { DocumentUploadCard } from './components/DocumentUploadCard'
import { EvaluationConfig } from './components/EvaluationConfig'
import { GroundTruthUpload } from './components/GroundTruthUpload'
import { EvaluationReferencePanel } from './components/EvaluationReferencePanel'
import { ThemeToggle } from './components/ThemeToggle'
import { CombinedCheckCard } from './components/ResultsPanel/CombinedCheckCard'
import { DocumentResultCard } from './components/ResultsPanel/DocumentResultCard'
import { OverallScoreCard } from './components/ResultsPanel/OverallScoreCard'
import { evaluateKyc, extractDocs } from './lib/api'
import type { DocType, Side } from './lib/types'
import { useKYC } from './context/KYCContext'

const DOCS: { type: DocType; title: string }[] = [
  { type: 'passport', title: 'Passport' },
  { type: 'aadhaar', title: 'Aadhaar' },
  { type: 'pan', title: 'PAN' },
]

export default function App() {
  const {
    uploads,
    extractedDocs,
    groundTruth,
    groundTruthManifest,
    scope,
    loading,
    error,
    result,
    setUploads,
    setExtractedDocs,
    setGroundTruth,
    setGroundTruthManifest,
    setScope,
    setLoading,
    setError,
    setResult,
  } = useKYC()

  const [showBack, setShowBack] = useState<Record<DocType, boolean>>({ passport: false, aadhaar: false, pan: false })
  const [selectedDocs, setSelectedDocs] = useState<DocType[]>([])
  const [extractingSlots, setExtractingSlots] = useState<Set<string>>(new Set())

  function extractionSlotKey(docType: DocType, side: Side) {
    return `${docType}:${side}`
  }

  function isDocExtracting(docType: DocType) {
    return extractingSlots.has(extractionSlotKey(docType, 'front')) || extractingSlots.has(extractionSlotKey(docType, 'back'))
  }

  function clearStaleResults() {
    setResult(null)
    setError(null)
  }

  function changeScope(next: typeof scope) {
    if (next !== scope) clearStaleResults()
    setScope(next)
  }

  const extractedByDoc = useMemo(() => {
    const map = new Set(extractedDocs.map((d) => d.doc_type))
    return {
      passport: map.has('passport'),
      aadhaar: map.has('aadhaar'),
      pan: map.has('pan'),
    }
  }, [extractedDocs])

  function clearDocumentImage(docType: DocType, side: Side) {
    clearStaleResults()
    setUploads((prev) => {
      const existing = prev[docType]
      if (!existing?.[side]) return prev

      const image = existing[side]
      if (image?.previewUrl) URL.revokeObjectURL(image.previewUrl)

      const updated = { ...existing }
      delete updated[side]

      if (!updated.front && !updated.back) {
        const next = { ...prev }
        delete next[docType]
        return next
      }
      return { ...prev, [docType]: updated }
    })
    setExtractedDocs((prev) => prev.filter((d) => !(d.doc_type === docType && d.side === side)))
    setExtractingSlots((prev) => {
      const next = new Set(prev)
      next.delete(extractionSlotKey(docType, side))
      return next
    })
    if (side === 'back') {
      setShowBack((prev) => ({ ...prev, [docType]: false }))
    }
  }

  function clearGroundTruth() {
    clearStaleResults()
    setGroundTruth(null)
    setGroundTruthManifest(null)
  }

  async function handleFileDrop(file: File, docType: DocType, side: Side) {
    setError(null)
    clearStaleResults()
    const slotKey = extractionSlotKey(docType, side)
    const previewUrl = URL.createObjectURL(file)
    setUploads((prev) => ({
      ...prev,
      [docType]: {
        ...(prev[docType] || {}),
        [side]: { file, side, docType, previewUrl },
      },
    }))

    const formData = new FormData()
    formData.append('files', file)
    formData.append('doc_types', docType)
    formData.append('sides', side)

    setExtractingSlots((prev) => new Set(prev).add(slotKey))
    try {
      setLoading(true)
      const data = await extractDocs(formData)
      setExtractedDocs((prev) => {
        const next = [...prev]
        for (const doc of data.documents) {
          const idx = next.findIndex((d) => d.doc_type === doc.doc_type && d.side === doc.side)
          if (idx >= 0) next[idx] = doc
          else next.push(doc)
        }
        return next
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Extraction failed')
    } finally {
      setExtractingSlots((prev) => {
        const next = new Set(prev)
        next.delete(slotKey)
        return next
      })
      setLoading(false)
    }
  }

  async function runEvaluation() {
    if (!selectedDocs.length) {
      setError('Select at least one document for evaluation')
      return
    }

    const activeExtractedDocs = extractedDocs.filter((d) => selectedDocs.includes(d.doc_type))

    if (!groundTruth) {
      setError('Ground truth JSON is required')
      return
    }
    if (!activeExtractedDocs.length) {
      setError('Upload and extract at least one document first')
      return
    }
    try {
      setError(null)
      setLoading(true)
      const response = await evaluateKyc({
        extracted_docs: activeExtractedDocs,
        ground_truth: groundTruth,
        ground_truth_manifest: groundTruthManifest || undefined,
        scope,
      })
      setResult(response.result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const isIndividual = result?.scope === 'individual'
  const canRunKyc = Boolean(groundTruth) && !loading

  function toggleSelectedDoc(docType: DocType) {
    setSelectedDocs((prev) => {
      const next = prev.includes(docType) ? prev.filter((d) => d !== docType) : [...prev, docType]

      if (prev.includes(docType)) {
        setUploads((current) => {
          const updated = { ...current }
          delete updated[docType]
          return updated
        })
        setExtractedDocs((current) => current.filter((d) => d.doc_type !== docType))
        setShowBack((current) => ({ ...current, [docType]: false }))
        setResult(null)
        setError(null)
      }

      return next
    })
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <header className="surface-glass flex h-12 shrink-0 items-center justify-between border-b border-border bg-raised px-4 shadow-panel">
        <div className="flex items-center gap-2 font-heading text-lg font-semibold">
          <ShieldCheck className="h-5 w-5 text-link" /> KYC Studio
        </div>
        <ThemeToggle />
      </header>

      <main className="flex min-h-0 flex-1 gap-3 p-3">
        <aside className="flex min-h-0 w-[38%] flex-col gap-3 overflow-y-auto pr-1">
          <section className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
            <h3 className="mb-2 font-heading text-sm font-semibold">Choose Documents For Evaluation</h3>
            <div className="grid grid-cols-3 gap-2">
              {DOCS.map((doc) => {
                const active = selectedDocs.includes(doc.type)
                return (
                  <button
                    key={doc.type}
                    type="button"
                    onClick={() => toggleSelectedDoc(doc.type)}
                    className={`rounded-lg border px-2 py-2 text-xs font-semibold transition ${
                      active ? 'border-link bg-brand text-white' : 'border-border bg-panel-muted text-fg-muted hover:bg-panel'
                    }`}
                  >
                    {doc.title}
                  </button>
                )
              })}
            </div>
          </section>

          {DOCS.filter((doc) => selectedDocs.includes(doc.type)).map((doc) => (
            <DocumentUploadCard
              key={doc.type}
              docType={doc.type}
              title={doc.title}
              front={uploads[doc.type]?.front}
              back={uploads[doc.type]?.back}
              extracted={extractedByDoc[doc.type]}
              extracting={isDocExtracting(doc.type)}
              extractedData={extractedDocs.find((item) => item.doc_type === doc.type && item.side === 'front')?.extracted}
              showBack={showBack[doc.type]}
              onToggleBack={() => setShowBack((prev) => ({ ...prev, [doc.type]: true }))}
              onFileDrop={handleFileDrop}
              onClearImage={clearDocumentImage}
            />
          ))}

          {!selectedDocs.length ? (
            <div className="surface-glass rounded-2xl border border-border bg-panel p-3 text-xs text-fg-muted shadow-card">
              No documents selected. Choose at least one document type above.
            </div>
          ) : null}

          <GroundTruthUpload
            data={groundTruth}
            manifest={groundTruthManifest}
            onParsed={setGroundTruth}
            onParsedManifest={setGroundTruthManifest}
            onClear={clearGroundTruth}
          />
          <EvaluationConfig scope={scope} onScope={changeScope} />
          <EvaluationReferencePanel />

          <button
            type="button"
            onClick={runEvaluation}
            disabled={!canRunKyc}
            title={!groundTruth ? 'Upload ground truth JSON to enable evaluation' : undefined}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-card transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Run KYC
          </button>

          {!groundTruth ? (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
              Upload Ground Truth JSON to continue.
            </div>
          ) : null}
        </aside>

        <section className="flex min-h-0 w-[62%] flex-col gap-3 overflow-y-auto pl-1">
          {!result ? (
            <div className="surface-glass flex h-full items-center justify-center rounded-2xl border border-border bg-panel text-fg-muted">
              Results will appear after running KYC.
            </div>
          ) : (
            <div className="space-y-4">
              {!isIndividual ? (
                <section className="space-y-3">
                  <h2 className="font-heading text-lg font-semibold">Combined evaluation</h2>
                  <OverallScoreCard score={result.overall_score} passed={result.passed} />
                  <div className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
                    <p className="mb-2 text-sm font-semibold">Combined checks</p>
                    <p className="mb-3 text-xs text-fg-muted">Expand a check to see the field rows it uses.</p>
                    <div className="space-y-2">
                      {result.checks.map((check) => (
                        <CombinedCheckCard key={check.name} check={check} />
                      ))}
                    </div>
                  </div>
                </section>
              ) : (
                <section className="space-y-2">
                  <h2 className="font-heading text-lg font-semibold">Per-document results</h2>
                  {result.per_document_results.map((doc) => (
                    <DocumentResultCard key={doc.document_id} result={doc} />
                  ))}
                </section>
              )}

              {!isIndividual ? (
                <section className="space-y-2">
                  <h2 className="font-heading text-lg font-semibold">Per-document breakdown</h2>
                  {result.per_document_results.map((doc) => (
                    <DocumentResultCard key={doc.document_id} result={doc} />
                  ))}
                </section>
              ) : null}
            </div>
          )}
        </section>
      </main>

      {error ? (
        <div className="pointer-events-none fixed bottom-3 right-3 z-20 inline-flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/15 px-3 py-2 text-xs text-rose-500">
          <AlertCircle className="h-4 w-4" /> {error}
        </div>
      ) : null}
    </div>
  )
}
