import { test, expect } from '@playwright/test'

async function frontendReachable(request: { get: (url: string) => Promise<{ status: () => number }> }): Promise<boolean> {
  try {
    const res = await request.get('/')
    return res.status() === 200
  } catch {
    return false
  }
}

test('KYC Studio shell renders when dev server is up', async ({ page, request }) => {
  test.skip(!(await frontendReachable(request)), 'Frontend not reachable at baseURL (start Vite: kyc_studio/frontend npm run dev)')

  await page.goto('/')
  await expect(page.getByText('KYC Studio')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Run KYC' })).toBeVisible()
  await expect(page.getByText('Evaluation Config')).toBeVisible()
})
