import { useMemo, useState } from 'react'
import { AlertCircle, Loader2, ShieldCheck } from 'lucide-react'
import { DocumentUploadCard } from './components/DocumentUploadCard'
import { EvaluationConfig } from './components/EvaluationConfig'
import { GroundTruthUpload } from './components/GroundTruthUpload'
import { RubricUpload } from './components/RubricUpload'
import { ThemeToggle } from './components/ThemeToggle'
import { DocumentResultCard } from './components/ResultsPanel/DocumentResultCard'
import { EvaluationModeBadge } from './components/ResultsPanel/EvaluationModeBadge'
import { OverallScoreCard } from './components/ResultsPanel/OverallScoreCard'
import { evaluateKyc, extractDocs } from './lib/api'
import type { BothResultEnvelope, DocType, KYCResult, Side } from './lib/types'
import { useKYC } from './context/KYCContext'

const DOCS: { type: DocType; title: string }[] = [
  { type: 'passport', title: 'Passport' },
  { type: 'aadhaar', title: 'Aadhaar' },
  { type: 'pan', title: 'PAN' },
]

function isBoth(v: unknown): v is BothResultEnvelope {
  return Boolean(v && typeof v === 'object' && (v as BothResultEnvelope).method === 'both')
}

export default function App() {
  const {
    uploads,
    extractedDocs,
    groundTruth,
    rubricYaml,
    method,
    scope,
    loading,
    error,
    result,
    setUploads,
    setExtractedDocs,
    setGroundTruth,
    setRubricYaml,
    setMethod,
    setScope,
    setLoading,
    setError,
    setResult,
  } = useKYC()

  const [showBack, setShowBack] = useState<Record<DocType, boolean>>({ passport: false, aadhaar: false, pan: false })

  const extractedByDoc = useMemo(() => {
    const map = new Set(extractedDocs.map((d) => d.doc_type))
    return {
      passport: map.has('passport'),
      aadhaar: map.has('aadhaar'),
      pan: map.has('pan'),
    }
  }, [extractedDocs])

  async function handleFileDrop(file: File, docType: DocType, side: Side) {
    setError(null)
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
      setLoading(false)
    }
  }

  async function runEvaluation() {
    if (!groundTruth) {
      setError('Ground truth JSON is required')
      return
    }
    if (!extractedDocs.length) {
      setError('Upload and extract at least one document first')
      return
    }
    if ((method === 'llm' || method === 'both') && !rubricYaml.trim()) {
      setError('Rubric YAML is required for LLM modes')
      return
    }

    try {
      setError(null)
      setLoading(true)
      const response = await evaluateKyc({
        extracted_docs: extractedDocs,
        ground_truth: groundTruth,
        method,
        scope,
        rubric: rubricYaml || undefined,
      })
      setResult(response.result)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Evaluation failed')
    } finally {
      setLoading(false)
    }
  }

  const resultSections: { label: string; data: KYCResult }[] = useMemo(() => {
    if (!result) return []
    if (isBoth(result)) {
      return [
        { label: 'Rule-Based', data: result.rules_result },
        { label: 'LLM Rubric', data: result.llm_result },
      ]
    }
    return [{ label: method.toUpperCase(), data: result as KYCResult }]
  }, [result, method])

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
          {DOCS.map((doc) => (
            <DocumentUploadCard
              key={doc.type}
              docType={doc.type}
              title={doc.title}
              front={uploads[doc.type]?.front}
              back={uploads[doc.type]?.back}
              extracted={extractedByDoc[doc.type]}
              showBack={showBack[doc.type]}
              onToggleBack={() => setShowBack((prev) => ({ ...prev, [doc.type]: true }))}
              onFileDrop={handleFileDrop}
            />
          ))}

          <GroundTruthUpload data={groundTruth} onParsed={setGroundTruth} />
          <EvaluationConfig method={method} scope={scope} onMethod={setMethod} onScope={setScope} />
          {(method === 'llm' || method === 'both') ? <RubricUpload value={rubricYaml} onParsed={setRubricYaml} /> : null}

          <button
            type="button"
            onClick={runEvaluation}
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-card transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-70"
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            Run KYC
          </button>
        </aside>

        <section className="flex min-h-0 w-[62%] flex-col gap-3 overflow-y-auto pl-1">
          {!result ? (
            <div className="surface-glass flex h-full items-center justify-center rounded-2xl border border-border bg-panel text-fg-muted">
              Results will appear after running KYC.
            </div>
          ) : (
            <div className={`grid gap-3 ${resultSections.length > 1 ? 'md:grid-cols-2' : 'grid-cols-1'}`}>
              {resultSections.map((section) => (
                <div key={section.label} className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h2 className="font-heading text-lg font-semibold">{section.label}</h2>
                    <EvaluationModeBadge mode={section.data.method} />
                  </div>

                  <OverallScoreCard score={section.data.overall_score} passed={section.data.passed} />

                  {scope === 'individual' ? (
                    <div className="space-y-2">
                      {section.data.per_document_results.map((doc) => (
                        <DocumentResultCard key={`${section.label}-${doc.document_id}`} result={doc} />
                      ))}
                    </div>
                  ) : (
                    <div className="surface-glass rounded-2xl border border-border bg-panel p-3 shadow-card">
                      <div className="mb-2 text-sm font-semibold">Combined Checks</div>
                      <div className="space-y-2">
                        {section.data.checks.map((check) => (
                          <div key={check.name} className="rounded-lg border border-border bg-panel-muted p-2 text-xs">
                            <div className="flex justify-between">
                              <span className="font-medium">{check.name}</span>
                              <span className={check.passed ? 'text-emerald-500' : 'text-rose-500'}>
                                {check.passed ? 'PASS' : 'FAIL'}
                              </span>
                            </div>
                            <p className="mt-1 text-fg-muted">{check.detail}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
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
