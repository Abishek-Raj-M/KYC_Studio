export type DocType = 'passport' | 'aadhaar' | 'pan'
export type Side = 'front' | 'back'
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

export interface GroundTruthManifest {
  person?: Record<string, unknown>
  documents?: Record<string, { fields?: Record<string, unknown> }>
  [key: string]: unknown
}

export interface CheckResult {
  name: string
  passed: boolean
  score: number
  detail: string
  weight: number
  field_matches?: FieldMatch[]
}

export interface FieldMatch {
  field: string
  extracted: unknown
  ground_truth: unknown
  status: 'match' | 'mismatch' | 'missing' | 'partial'
  coverage_percent?: number | null
  doc_type?: string
  document_id?: string
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
  method: 'rules'
  scope: ScopeType
  overall_score: number
  passed: boolean
  summary: string
  per_document_results: DocumentKYCResult[]
  checks: CheckResult[]
}

export interface ExtractResponse {
  documents: ExtractedDocument[]
}

export interface EvaluatePayload {
  extracted_docs: ExtractedDocument[]
  ground_truth: GroundTruth
  ground_truth_manifest?: GroundTruthManifest
  scope: ScopeType
}
