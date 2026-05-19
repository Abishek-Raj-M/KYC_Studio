from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

BUILTIN_RUBRICS_DIR = Path(__file__).resolve().parent / "builtin_rubrics"
REFERENCE_DIR = Path(__file__).resolve().parent / "reference"
RULES_REFERENCE_MD = REFERENCE_DIR / "kyc-rules-reference.md"

DOC_TYPE_ALIASES = {
    "pan_card": "pan",
    "pancard": "pan",
    "aadhar": "aadhaar",
}

RUBRIC_FILES = {
    "passport": "passport_rubric.yaml",
    "aadhaar": "aadhaar_rubric.yaml",
    "pan": "pan_rubric.yaml",
    "combined": "indian_kyc_combined_rubric.yaml",
}


def normalize_doc_type(doc_type: str) -> str:
    key = str(doc_type or "unknown").lower().strip()
    return DOC_TYPE_ALIASES.get(key, key)


def load_builtin_rubric_yaml(doc_type: str) -> str:
    canonical = normalize_doc_type(doc_type)
    filename = RUBRIC_FILES.get(canonical)
    if not filename:
        raise KeyError(f"No built-in rubric for document type: {doc_type}")
    path = BUILTIN_RUBRICS_DIR / filename
    return path.read_text(encoding="utf-8")


def builtin_rubric_map_for_doc_types(doc_types: List[str]) -> Dict[str, str]:
    """One rubric YAML per uploaded document type."""
    out: Dict[str, str] = {}
    for raw in doc_types:
        canonical = normalize_doc_type(raw)
        if canonical in out:
            continue
        out[canonical] = load_builtin_rubric_yaml(canonical)
    return out


def rubric_yaml_to_markdown(yaml_text: str, *, title: str | None = None) -> str:
    data = yaml.safe_load(yaml_text) or {}
    lines = [
        f"# {title or data.get('name') or 'KYC Rubric'}",
        "",
        f"- **Version:** {data.get('rubric_version', '1.0')}",
    ]
    if data.get("scope"):
        lines.append(f"- **Scope:** {data['scope']}")
    lines.extend(["", "## Checks", ""])
    for check in data.get("checks", []):
        cid = check.get("id", "check")
        lines.append(f"### `{cid}`")
        lines.append(f"- **Description:** {check.get('description', '')}")
        lines.append(f"- **Weight:** {check.get('weight', 1.0)}")
        lines.append(f"- **Criteria:** {check.get('criteria', '')}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rubric_markdown_for_doc_type(doc_type: str) -> str:
    yaml_text = load_builtin_rubric_yaml(doc_type)
    return rubric_yaml_to_markdown(yaml_text)


def list_builtin_rubric_doc_types() -> List[str]:
    return sorted(k for k in RUBRIC_FILES if k != "combined")
