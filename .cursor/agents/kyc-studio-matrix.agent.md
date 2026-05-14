# KYC Studio matrix runner

Read [`studio_tests/AGENT.md`](../../studio_tests/AGENT.md) for layout and commands.

**Goal:** Run Tier A pytest (`-m "not integration"`), then Tier C Playwright (`studio_tests/e2e`) with the frontend dev server up. If anything fails, apply the **smallest** fix in `kyc_studio/backend` or `kyc_studio/frontend`, re-run until green, and summarize what changed.

Do not edit the plan file in `.cursor/plans/`.
