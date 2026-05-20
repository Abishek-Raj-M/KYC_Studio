import type { EvaluatePayload, ExtractResponse, KYCResult } from './types'

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

export async function evaluateKyc(payload: EvaluatePayload): Promise<{ result: KYCResult }> {
  const res = await fetch('/api/evaluate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...payload, method: 'rules' }),
  })
  if (!res.ok) {
    throw new Error(`Evaluation failed: ${res.status}`)
  }
  return res.json()
}

export async function fetchRulesReference(): Promise<string> {
  const res = await fetch('/api/reference/rules')
  if (!res.ok) {
    throw new Error(`Failed to load rules reference: ${res.status}`)
  }
  return res.text()
}

export function downloadGroundTruthTemplate() {
  window.open('/api/ground-truth/template', '_blank', 'noopener,noreferrer')
}
