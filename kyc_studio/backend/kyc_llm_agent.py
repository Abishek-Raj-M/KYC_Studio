from __future__ import annotations

import json
import os
from typing import Any, Dict, List

import yaml
from openai import AzureOpenAI

from models import CheckResult, DocumentKYCResult, KYCResult


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
        rubric_yaml: str,
        scope: str,
    ) -> KYCResult:
        rubric = yaml.safe_load(rubric_yaml or "") or {}
        checks = rubric.get("checks", [])

        prompt = self._build_prompt(rubric, docs, ground_truth)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
        )

        content = response.choices[0].message.content or "{}"
        payload = self._parse_llm_json(content)
        check_results = self._check_results_from_payload(checks, payload)

        total_weight = sum(c.weight for c in check_results) or 1.0
        passed_weight = sum(c.weight for c in check_results if c.passed)
        overall = (passed_weight / total_weight) * 100

        per_doc_results = [
            DocumentKYCResult(
                document_id=str(d.get("_metadata", {}).get("source_file") or d.get("document_type") or "document"),
                doc_type=str(d.get("document_type") or "unknown"),
                score=round(overall, 2),
                passed=overall >= 75,
                checks=check_results,
                field_matches=[],
            )
            for d in docs
        ]

        return KYCResult(
            method="llm",
            scope=scope,
            overall_score=round(overall, 2),
            passed=overall >= 75,
            summary="LLM rubric evaluation completed",
            per_document_results=per_doc_results,
            checks=check_results,
        )

    def _build_prompt(self, rubric: Dict[str, Any], docs: List[Dict[str, Any]], ground_truth: Dict[str, Any]) -> str:
        return (
            "You are a KYC auditor. Evaluate extracted documents against the rubric and return only JSON.\n"
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
            score = float(entry.get("score", 100.0 if entry.get("passed") else 0.0))
            passed = bool(entry.get("passed", score >= 75.0))
            result.append(
                CheckResult(
                    name=check_id,
                    passed=passed,
                    score=score,
                    detail=str(entry.get("detail") or check.get("description") or "No detail"),
                    weight=float(check.get("weight", 1.0)),
                )
            )

        return result
