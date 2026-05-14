# Clean document images (optional for Tier B)

Tier A API tests use JSON snapshots under `../extracted/` and do not require images.

For **Tier B** (`pytest -m integration`), place clean **front-only** scans here or under `test_set/rajesh_sharma/indian_doc/clean/`:

- `passport_front_clean.jpg` (or `.png`)
- `aadhaar_front_clean.jpg`
- `pan_front_clean.jpg`

Expected content should align with [`../ground_truth/rajesh_manifest.json`](../ground_truth/rajesh_manifest.json). The studio copy uses a **12-digit Aadhaar** string (no spaces) in the manifest so rule-based ID matching matches OCR-style digits.

**Tier A passport fixture note:** `passport_front.json` uses a **non-expired** `date_of_expiration` and a placeholder `surname` so the rule engine’s cross-document name logic and mandatory field checks stay consistent in CI. This is a synthetic evaluation fixture, not a claim about the real scan.
