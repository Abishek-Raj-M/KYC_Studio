from __future__ import annotations

import json
import os
import logging
from datetime import datetime
from typing import Any, Dict, List

import yaml
from openai import AzureOpenAI

from check_scoping import checks_for_document_card, score_from_checks
from manifest_field_matches import field_matches_from_manifest, mandatory_field_failures
from models import CheckResult, DocumentKYCResult, FieldMatch, KYCResult


logger = logging.getLogger("uvicorn.error")


def _extract_text(response: Any) -> str:
    if isinstance(response, str):
        return response
    if hasattr(response, "content"):
        content = getattr(response, "content")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(str(part) for part in content)
    if isinstance(response, dict):
        return json.dumps(response)
    return str(response)


class KycLLMAgent:
    """Runs rubric-based KYC checks through the configured LLM."""

    def __init__(self) -> None:
        api_key = os.getenv("DIAL_API_KEY")
        if not api_key:
            raise ValueError("DIAL_API_KEY missing in environment")

        self.client = AzureOpenAI(
            azure_endpoint="https://ai-proxy.lab.epam.com",
            api_key=api_key,
            api_version="2024-02-01",
        )
        self.model = os.getenv("KYC_LLM_MODEL", "gpt-4o")

    def evaluate(
        self,
        docs: List[Dict[str, Any]],
        ground_truth: Dict[str, Any],
        ground_truth_manifest: Dict[str, Any] | None,
        rubric_yaml: str,
        scope: str,
        doc_types_in_scope: List[str] | None = None,
    ) -> KYCResult:
        rubric = yaml.safe_load(rubric_yaml or "") or {}
        checks = rubric.get("checks", [])

        prompt = self._build_prompt(rubric, docs, ground_truth, ground_truth_manifest or {}, doc_types_in_scope or [])
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        content = response.choices[0].message.content or "{}"
        logger.info("LLM raw response content=%s", content)
        payload = self._parse_llm_json(content)
        logger.info("LLM parsed payload=%s", payload)
        check_results = self._check_results_from_payload(checks, payload)
        multi_document = len(docs) > 1

        per_doc_results: List[DocumentKYCResult] = []
        mandatory_failures: List[str] = []
        for d in docs:
            doc_id = str(d.get("_metadata", {}).get("source_file") or d.get("document_type") or "document")
            doc_type = str(d.get("document_type") or "unknown")
            manifest = ground_truth_manifest or ground_truth
            field_matches = field_matches_from_manifest(d, manifest)
            mandatory_failures.extend(mandatory_field_failures(field_matches, doc_type))

            doc_checks = checks_for_document_card(
                check_results,
                doc_type,
                field_matches,
                is_rubric=True,
                multi_document=multi_document,
            )
            doc_score = score_from_checks(doc_checks)
            per_doc_results.append(
                DocumentKYCResult(
                    document_id=doc_id,
                    doc_type=doc_type,
                    score=doc_score,
                    passed=doc_score >= 75,
                    checks=doc_checks,
                    field_matches=field_matches,
                )
            )

        mandatory_passed = not mandatory_failures
        check_results.append(
            CheckResult(
                name="mandatory_fields",
                passed=mandatory_passed,
                score=100.0 if mandatory_passed else 0.0,
                detail="All mandatory fields matched" if mandatory_passed else "Missing or mismatched mandatory fields: " + ", ".join(mandatory_failures),
                weight=1.0,
            )
        )

        overall = score_from_checks(check_results)

        return KYCResult(
            method="llm",
            scope=scope,
            overall_score=round(overall, 2),
            passed=overall >= 75,
            summary="LLM rubric evaluation completed",
            per_document_results=per_doc_results,
            checks=check_results,
        )

    def _build_prompt(
        self,
        rubric: Dict[str, Any],
        docs: List[Dict[str, Any]],
        ground_truth: Dict[str, Any],
        ground_truth_manifest: Dict[str, Any],
        doc_types_in_scope: List[str],
    ) -> str:
        scope_line = f"Uploaded document types in scope: {', '.join(doc_types_in_scope) if doc_types_in_scope else 'unknown'}"
        return (
            "You are a KYC auditor. Use the Ground Truth JSON as the source of truth for verification.\n"
            "Evaluate extracted documents only by comparing them against Ground Truth JSON and the rubric.\n"
            "ONLY evaluate checks relevant to uploaded document types in scope and ignore non-uploaded document requirements.\n"
            "Do not invent facts. If data is missing, mark checks as failed with clear detail. Return only JSON.\n"
            f"{scope_line}\n"
            "Raw uploaded manifest ground truth (contains per-document fields):\n"
            f"{json.dumps(ground_truth_manifest, indent=2)}\n\n"
            "Expected JSON shape:\n"
            "{\n"
            '  "checks": [{"id":"string","passed":true,"score":0-100,"detail":"string"}],\n'
            '  "summary": "string"\n'
            "}\n\n"
            f"Rubric:\n{json.dumps(rubric, indent=2)}\n\n"
            f"Ground truth:\n{json.dumps(ground_truth, indent=2)}\n\n"
            f"Extracted documents:\n{json.dumps(docs, indent=2)}\n"
        )

    def _parse_llm_json(self, text: str) -> Dict[str, Any]:
        cleaned = text.strip().replace("```json", "").replace("```", "")
        return json.loads(cleaned)

    def _check_results_from_payload(self, rubric_checks: List[Dict[str, Any]], payload: Dict[str, Any]) -> List[CheckResult]:
        by_id = {str(item.get("id")): item for item in payload.get("checks", [])}
        result: List[CheckResult] = []

        for check in rubric_checks:
            check_id = str(check.get("id"))
            entry = by_id.get(check_id, {})
            weight = float(check.get("weight", 1.0))
            raw_score = entry.get("score")
            passed_hint = entry.get("passed")

            if raw_score is None:
                score = 100.0 if bool(passed_hint) else 0.0
            else:
                score = float(raw_score)
                weighted_cap = max(weight * 100.0, 0.0)
                # Some rubric outputs return weighted points (e.g., 30 with w=0.30).
                if weighted_cap > 0.0 and 0.0 <= score <= weighted_cap + 1e-6:
                    score = score / weight

            score = max(0.0, min(100.0, score))
            passed = bool(passed_hint) if passed_hint is not None else score >= 75.0

            # Keep pass/fail and score aligned for downstream display.
            if passed and score < 75.0:
                score = 100.0
            if (not passed) and score >= 75.0:
                score = 0.0

            result.append(
                CheckResult(
                    name=check_id,
                    passed=passed,
                    score=score,
                    detail=str(entry.get("detail") or check.get("description") or "No detail"),
                    weight=weight,
                )
            )

        return result

    def _field_matches_for_doc(self, doc: Dict[str, Any], ground_truth: Dict[str, Any]) -> List[FieldMatch]:
        return field_matches_from_manifest(doc, ground_truth)
