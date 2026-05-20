#!/usr/bin/env python3
"""
Build six Rajesh Sharma test CSVs for Custom flow Extract Eval.

Prerequisite for CSV #1 output column: KYC API running with POST /api/batch-extract.

Usage:
  python prepare_rajesh_test_csvs.py
  python prepare_rajesh_test_csvs.py --skip-batch-extract
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
MANIFEST_PATH = BASE.parent / "manifest.json"
KYC_BATCH_URL = "http://127.0.0.1:8000/api/batch-extract"

DOC_MANIFEST_KEYS = {
    "passport": "passport",
    "pan": "pan_card",
    "aadhaar": "aadhaar",
}

CLEAN_IMAGES = [
    ("1", "passport", BASE / "clean" / "passport_clean.png"),
    ("2", "pan", BASE / "clean" / "pan_card_clean.png"),
    ("3", "aadhaar", BASE / "clean" / "aadhaar_clean.png"),
]

NEGATIVE_SETS = {
    "rajesh_negative_blur.csv": [
        ("1", "passport", BASE / "negative cases" / "blur_passport.jpeg"),
        ("2", "pan", BASE / "negative cases" / "blur_pan.png"),
        ("3", "aadhaar", BASE / "negative cases" / "blur_aadhar.png"),
    ],
    "rajesh_negative_frame_blur.csv": [
        ("1", "passport", BASE / "negative cases" / "frame_blur_passport.png"),
        ("2", "pan", BASE / "negative cases" / "frame_blur_pan.png"),
        ("3", "aadhaar", BASE / "negative cases" / "frame_blur_aadhar.png"),
    ],
    "rajesh_negative_stain.csv": [
        ("1", "passport", BASE / "negative cases" / "stain_passport.jpeg"),
        ("2", "pan", BASE / "negative cases" / "stain_pan.jpeg"),
        ("3", "aadhaar", BASE / "negative cases" / "stain_aadhar.jpeg"),
    ],
    "rajesh_negative_mixed.csv": [
        ("1", "passport", BASE / "negative cases" / "stain_passport.jpeg"),
        ("2", "pan", BASE / "negative cases" / "frame_blur_pan.png"),
        ("3", "aadhaar", BASE / "negative cases" / "blur_aadhar.png"),
    ],
}


def load_manifest() -> dict[str, Any]:
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def split_groundtruth(manifest: dict[str, Any], doc_type: str) -> dict[str, Any]:
    key = DOC_MANIFEST_KEYS[doc_type]
    return {
        "person": manifest.get("person", {}),
        "documents": {key: manifest.get("documents", {}).get(key, {})},
    }


def call_batch_extract(items: list[dict[str, str]]) -> dict[str, Any]:
    if httpx is None:
        raise RuntimeError("httpx required: pip install httpx")
    with httpx.Client(timeout=600.0) as client:
        response = client.post(KYC_BATCH_URL, json={"items": items})
    if response.status_code >= 400:
        raise RuntimeError(f"batch-extract failed: {response.status_code} {response.text}")
    return response.json()


def write_csv(
    path: Path,
    rows: list[dict[str, Any]],
    *,
    include_output: bool,
) -> None:
    fieldnames = ["id", "input", "groundtruth", "doc_type"]
    if include_output:
        fieldnames.append("output")
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            out = {
                "id": row["id"],
                "input": row["input"],
                "groundtruth": json.dumps(row["groundtruth"], ensure_ascii=False),
                "doc_type": row["doc_type"],
            }
            if include_output and row.get("output") is not None:
                out["output"] = json.dumps(row["output"], ensure_ascii=False)
            writer.writerow(out)


def build_rows(
    manifest: dict[str, Any],
    image_specs: list[tuple[str, str, Path]],
    outputs_by_type: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_id, doc_type, image_path in image_specs:
        resolved = str(image_path.resolve())
        row: dict[str, Any] = {
            "id": row_id,
            "input": resolved,
            "doc_type": doc_type,
            "groundtruth": split_groundtruth(manifest, doc_type),
        }
        if outputs_by_type and doc_type in outputs_by_type:
            row["output"] = outputs_by_type[doc_type]
        rows.append(row)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-batch-extract",
        action="store_true",
        help="Skip KYC API call; write CSVs without output column on #1",
    )
    args = parser.parse_args()

    if not MANIFEST_PATH.is_file():
        print(f"Manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        return 1

    manifest = load_manifest()
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)

    outputs_by_type: dict[str, dict[str, Any]] = {}
    if not args.skip_batch_extract:
        missing = [p for _, _, p in CLEAN_IMAGES if not p.is_file()]
        if missing:
            print("Clean images missing (skip batch-extract or add images):", file=sys.stderr)
            for p in missing:
                print(f"  {p}", file=sys.stderr)
            return 1
        items = [
            {"doc_type": doc_type, "file_path": str(path.resolve())}
            for _, doc_type, path in CLEAN_IMAGES
        ]
        print(f"Calling {KYC_BATCH_URL} …")
        response = call_batch_extract(items)
        for doc in response.get("documents", []):
            dt = str(doc.get("doc_type"))
            outputs_by_type[dt] = {
                "doc_type": dt,
                "side": doc.get("side", "front"),
                "filename": doc.get("filename"),
                "extracted": doc.get("extracted"),
            }

    clean_rows = build_rows(manifest, CLEAN_IMAGES, outputs_by_type or None)
    write_csv(
        SCRIPT_DIR / "rajesh_clean_with_output.csv",
        clean_rows,
        include_output=bool(outputs_by_type),
    )
    write_csv(SCRIPT_DIR / "rajesh_clean_no_output.csv", clean_rows, include_output=False)

    for filename, specs in NEGATIVE_SETS.items():
        rows = build_rows(manifest, specs)
        write_csv(SCRIPT_DIR / filename, rows, include_output=False)

    print(f"Wrote CSVs to {SCRIPT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
