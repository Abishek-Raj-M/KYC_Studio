import type { EvaluatePayload, ExtractResponse, KYCResult, BothResultEnvelope } from './types'

export async function extractDocs(formData: FormData): Promise<ExtractResponse> {
  const res = await fetch('/api/extract', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    throw new Error(`Extraction failed: ${res.status}`)
  }
  return res.json()
}

export async function evaluateKyc(payload: EvaluatePayload): Promise<{ result: KYCResult | BothResultEnvelope }> {
  const res = await fetch('/api/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(`Evaluation failed: ${res.status}`)
  }
  return res.json()
}

export function downloadRulesReference() {
  window.open('/api/reference/rules', '_blank', 'noopener,noreferrer')
}

export function downloadRubricReference(docType: string) {
  window.open(`/api/reference/rubric/${docType}?format=md`, '_blank', 'noopener,noreferrer')
}

export function downloadActiveRubricsMarkdown(docTypes: string[]) {
  for (const docType of docTypes) {
    downloadRubricReference(docType)
  }
}

export function downloadGroundTruthTemplate() {
  window.open('/api/ground-truth/template', '_blank', 'noopener,noreferrer')
}
