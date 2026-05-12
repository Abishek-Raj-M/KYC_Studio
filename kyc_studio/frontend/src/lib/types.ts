export type DocType = 'passport' | 'aadhaar' | 'pan'
export type Side = 'front' | 'back'
export type MethodType = 'rules' | 'llm' | 'both'
export type ScopeType = 'individual' | 'all'

export interface UploadedDocImage {
  docType: DocType
  side: Side
  file: File
  previewUrl: string
}

export interface ExtractedDocument {
  doc_type: DocType
  side: Side
  filename: string
  extracted: Record<string, unknown>
}

export interface GroundTruth {
  name?: string
  dob?: string
  gender?: string
  address?: string
  nationality?: string
  id_numbers?: Record<string, string>
}

export interface CheckResult {
  name: string
  passed: boolean
  score: number
  detail: string
  weight: number
}

export interface FieldMatch {
  field: string
  extracted: unknown
  ground_truth: unknown
  status: 'match' | 'mismatch' | 'missing'
}

export interface DocumentKYCResult {
  document_id: string
  doc_type: string
  score: number
  passed: boolean
  checks: CheckResult[]
  field_matches: FieldMatch[]
}

export interface KYCResult {
  method: MethodType
  scope: ScopeType
  overall_score: number
  passed: boolean
  summary: string
  per_document_results: DocumentKYCResult[]
  checks: CheckResult[]
}

export interface BothResultEnvelope {
  method: 'both'
  scope: ScopeType
  overall_score: number
  passed: boolean
  summary: string
  rules_result: KYCResult
  llm_result: KYCResult
}

export interface ExtractResponse {
  documents: ExtractedDocument[]
}

export interface EvaluatePayload {
  extracted_docs: ExtractedDocument[]
  ground_truth: GroundTruth
  method: MethodType
  scope: ScopeType
  rubric?: string
}
