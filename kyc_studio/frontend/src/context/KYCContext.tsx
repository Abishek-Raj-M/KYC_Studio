import { createContext, useContext, useMemo, useState } from 'react'
import type {
  BothResultEnvelope,
  DocType,
  ExtractedDocument,
  GroundTruth,
  GroundTruthManifest,
  KYCResult,
  MethodType,
  ScopeType,
  UploadedDocImage,
} from '../lib/types'

interface KYCContextValue {
  uploads: Partial<Record<DocType, { front?: UploadedDocImage; back?: UploadedDocImage }>>
  extractedDocs: ExtractedDocument[]
  groundTruth: GroundTruth | null
  groundTruthManifest: GroundTruthManifest | null
  method: MethodType
  scope: ScopeType
  loading: boolean
  error: string | null
  result: KYCResult | BothResultEnvelope | null
  setUploads: React.Dispatch<React.SetStateAction<Partial<Record<DocType, { front?: UploadedDocImage; back?: UploadedDocImage }>>>>
  setExtractedDocs: React.Dispatch<React.SetStateAction<ExtractedDocument[]>>
  setGroundTruth: React.Dispatch<React.SetStateAction<GroundTruth | null>>
  setGroundTruthManifest: React.Dispatch<React.SetStateAction<GroundTruthManifest | null>>
  setMethod: React.Dispatch<React.SetStateAction<MethodType>>
  setScope: React.Dispatch<React.SetStateAction<ScopeType>>
  setLoading: React.Dispatch<React.SetStateAction<boolean>>
  setError: React.Dispatch<React.SetStateAction<string | null>>
  setResult: React.Dispatch<React.SetStateAction<KYCResult | BothResultEnvelope | null>>
}

const KYCContext = createContext<KYCContextValue | undefined>(undefined)

export function KYCProvider({ children }: { children: React.ReactNode }) {
  const [uploads, setUploads] = useState<Partial<Record<DocType, { front?: UploadedDocImage; back?: UploadedDocImage }>>>({})
  const [extractedDocs, setExtractedDocs] = useState<ExtractedDocument[]>([])
  const [groundTruth, setGroundTruth] = useState<GroundTruth | null>(null)
  const [groundTruthManifest, setGroundTruthManifest] = useState<GroundTruthManifest | null>(null)
  const [method, setMethod] = useState<MethodType>('rules')
  const [scope, setScope] = useState<ScopeType>('individual')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<KYCResult | BothResultEnvelope | null>(null)

  const value = useMemo(
    () => ({
      uploads,
      extractedDocs,
      groundTruth,
      groundTruthManifest,
      method,
      scope,
      loading,
      error,
      result,
      setUploads,
      setExtractedDocs,
      setGroundTruth,
      setGroundTruthManifest,
      setMethod,
      setScope,
      setLoading,
      setError,
      setResult,
    }),
    [uploads, extractedDocs, groundTruth, groundTruthManifest, method, scope, loading, error, result],
  )

  return <KYCContext.Provider value={value}>{children}</KYCContext.Provider>
}

export function useKYC() {
  const ctx = useContext(KYCContext)
  if (!ctx) {
    throw new Error('useKYC must be used inside KYCProvider')
  }
  return ctx
}
