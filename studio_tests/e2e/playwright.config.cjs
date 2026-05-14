const path = require('node:path')
const { defineConfig } = require('@playwright/test')

const baseURL = process.env.KYC_BASE_URL || 'http://127.0.0.1:6969'

module.exports = defineConfig({
  testDir: './specs',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: {
    baseURL,
    trace: 'on-first-retry',
  },
  retries: process.env.CI ? 1 : 0,
})
