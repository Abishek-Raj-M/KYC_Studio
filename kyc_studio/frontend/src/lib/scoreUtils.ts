import type { CheckResult } from './types'

export function scoreFromChecks(checks: CheckResult[]): number {
  if (!checks.length) return 0
  const totalWeight = checks.reduce((sum, c) => sum + c.weight, 0) || 1
  const passedWeight = checks.filter((c) => c.passed).reduce((sum, c) => sum + c.weight, 0)
  return Math.round((passedWeight / totalWeight) * 10000) / 100
}
