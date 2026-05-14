from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

STUDIO_TESTS = Path(__file__).resolve().parent.parent
REPO_ROOT = STUDIO_TESTS.parent
BACKEND_ROOT = REPO_ROOT / "kyc_studio" / "backend"
FIXTURES = STUDIO_TESTS / "fixtures"

sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def manifest() -> Dict[str, Any]:
    path = FIXTURES / "ground_truth" / "rajesh_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def doc_uploads() -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for key in ("passport", "aadhaar", "pan"):
        path = FIXTURES / "extracted" / f"{key}_front.json"
        out[key] = json.loads(path.read_text(encoding="utf-8"))
    return out


def build_extracted_docs(selected: List[str], doc_uploads: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [doc_uploads[k] for k in selected]


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    import main as app_main

    return TestClient(app_main.app)
