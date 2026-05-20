import * as fs from 'node:fs'
import * as path from 'node:path'

import { test, expect } from '@playwright/test'

async function frontendReachable(request: { get: (url: string) => Promise<{ status: () => number }> }): Promise<boolean> {
  try {
    const res = await request.get('/')
    return res.status() === 200
  } catch {
    return false
  }
}

const fixturesDir = path.join(__dirname, '../../fixtures')
const panDoc = JSON.parse(fs.readFileSync(path.join(fixturesDir, 'extracted/pan_front.json'), 'utf-8'))
const manifestPath = path.join(fixturesDir, 'ground_truth/rajesh_manifest.json')

const tinyPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
  'base64',
)

test('changing scope after a run clears results until Run KYC (mocked APIs)', async ({ page, request }) => {
  test.skip(!(await frontendReachable(request)), 'Frontend not reachable at baseURL')

  await page.route('**/api/extract', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ documents: [panDoc] }),
    })
  })

  await page.route('**/api/evaluate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        result: {
          method: 'rules',
          scope: 'individual',
          overall_score: 95,
          passed: true,
          summary: 'mock',
          checks: [
            {
              name: 'Mandatory Fields',
              passed: true,
              score: 100,
              detail: 'ok',
              weight: 1,
            },
          ],
          per_document_results: [
            {
              document_id: 'pan_front_clean.jpg',
              doc_type: 'pan',
              score: 95,
              passed: true,
              checks: [],
              field_matches: [],
            },
          ],
        },
      }),
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'PAN' }).click()

  await page.locator('section').filter({ hasText: 'Ground Truth' }).locator('input[type="file"]').setInputFiles(manifestPath)

  await page.locator('section').filter({ hasText: 'Front (Required)' }).locator('input[type="file"]').setInputFiles({
    name: 'pan.png',
    mimeType: 'image/png',
    buffer: tinyPng,
  })

  await expect(page.getByText('Extracted').first()).toBeVisible()

  await page.getByRole('button', { name: 'Run KYC' }).click()
  await expect(page.getByText('95.00%')).toBeVisible()

  await page.getByRole('button', { name: 'Combined' }).click()
  await expect(page.getByText('Results will appear after running KYC.')).toBeVisible()
})
