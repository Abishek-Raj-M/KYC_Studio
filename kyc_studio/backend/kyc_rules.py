from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from check_field_links import checks_with_field_matches
from check_scoping import checks_for_document_card, score_from_checks
from manifest_field_matches import (
    field_matches_from_manifest,
    genders_compatible,
    mandatory_field_failures,
    manifest_doc_fields,
)
from models import CheckResult, DocumentKYCResult, FieldMatch, GroundTruth, KYCResult


NAME_MATCH_THRESHOLD = 0.85
AADHAAR_REGEX = re.compile(r"^\d{12}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _normalize_aadhaar_number(value: Any) -> str:
    return re.sub(r"\D", "", str(value or "").strip())


@dataclass
class WeightedCheck:
    name: str
    passed: bool
    detail: str
    weight: float

    def to_model(self) -> CheckResult:
        return CheckResult(
            name=self.name,
            passed=self.passed,
            score=100.0 if self.passed else 0.0,
            detail=self.detail,
            weight=self.weight,
        )


class RuleBasedKYCEngine:
    def __init__(self) -> None:
        self.weights: Dict[str, float] = {
            "Name Match": 0.16,
            "DOB Match": 0.14,
            "Aadhaar Format": 0.08,
            "PAN Format": 0.08,
            "Passport Expiry": 0.10,
            "Cross-Document Name Consistency": 0.12,
            "Age Eligibility": 0.10,
            "Gender Consistency": 0.08,
            "Mandatory Fields": 1.00,
            "Address Present": 0.06,
        }

    @staticmethod
    def _norm(value: Any) -> str:
        return str(value or "").strip()

    @staticmethod
    def _sim(a: str, b: str) -> float:
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    @staticmethod
    def _pick_name(doc: Dict[str, Any]) -> str:
        if doc.get("document_type") == "passport":
            return " ".join(
                [
                    str(doc.get("given_names") or "").strip(),
                    str(doc.get("surname") or "").strip(),
                ]
            ).strip()
        return str(doc.get("name") or "").strip()

    @staticmethod
    def _pick_dob(doc: Dict[str, Any]) -> str:
        return str(doc.get("date_of_birth") or doc.get("dob") or "").strip()

    @staticmethod
    def _pick_gender(doc: Dict[str, Any]) -> str:
        return str(doc.get("sex") or doc.get("gender") or "").strip().upper()

    @staticmethod
    def _parse_date(date_str: str) -> Optional[datetime]:
        if not date_str:
            return None
        for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None

    @classmethod
    def _dates_equal(cls, left: str, right: str) -> bool:
        left_dt = cls._parse_date(left)
        right_dt = cls._parse_date(right)
        if left_dt and right_dt:
            return left_dt.date() == right_dt.date()
        return cls._norm(left) == cls._norm(right)

    @staticmethod
    def _is_complete(doc_type: str, doc: Dict[str, Any]) -> bool:
        required = {
            "passport": ["passport_number", "given_names", "surname", "date_of_birth", "date_of_expiration"],
            "aadhaar": ["aadhaar_number", "name", "dob", "gender", "address"],
            "pan": ["pan_number", "name", "dob"],
        }
        fields = required.get(doc_type, [])
        return all(bool(str(doc.get(f, "")).strip()) for f in fields)

    @staticmethod
    def _compare_value(field: str, extracted: Any, expected: Any) -> str:
        extracted_text = str(extracted or "").strip()
        expected_text = str(expected or "").strip()
        if not extracted_text or not expected_text:
            return "missing"
        if field in {"dob", "date_of_birth", "date_of_issue", "date_of_expiration"}:
            return "match" if RuleBasedKYCEngine._dates_equal(extracted_text, expected_text) else "mismatch"
        if field in {"name", "given_names", "surname", "father_name", "mother_name", "address", "nationality"}:
            return "match" if extracted_text.lower() == expected_text.lower() else "mismatch"
        return "match" if extracted_text.lower() == expected_text.lower() else "mismatch"

    def evaluate(
        self,
        docs: List[Dict[str, Any]],
        ground_truth: GroundTruth,
        scope: str,
        ground_truth_manifest: Dict[str, Any] | None = None,
    ) -> KYCResult:
        manifest = ground_truth_manifest or {}
        checks = self._build_checks(docs, ground_truth, manifest)
        total_weight = sum(c.weight for c in checks)
        passed_weight = sum(c.weight for c in checks if c.passed)
        overall = (passed_weight / total_weight) * 100 if total_weight else 0.0
        passed = overall >= 75.0

        field_matches = self._field_matches(docs, manifest)
        per_doc = self._per_doc_results(docs, checks, field_matches)
        top_checks = [c.to_model() for c in checks]
        if scope == "all":
            top_checks = checks_with_field_matches(top_checks, per_doc)

        return KYCResult(
            method="rules",
            scope=scope,
            overall_score=round(overall, 2),
            passed=passed,
            summary=f"Rule evaluation completed with score {round(overall, 2)}%",
            per_document_results=per_doc,
            checks=top_checks,
        )

    def _passport_name_match(self, passport_doc: Dict[str, Any], manifest: Dict[str, Any]) -> tuple[bool, float]:
        passport_fields = manifest_doc_fields(manifest, "passport")
        gt_given = self._norm(passport_fields.get("given_name"))
        gt_surname = self._norm(passport_fields.get("surname"))
        extracted_given = self._norm(passport_doc.get("given_names"))
        extracted_surname = self._norm(passport_doc.get("surname"))
        if gt_given and extracted_given:
            given_sim = self._sim(gt_given, extracted_given)
            if given_sim >= NAME_MATCH_THRESHOLD:
                if gt_surname and extracted_surname:
                    surname_ok = self._sim(gt_surname, extracted_surname) >= NAME_MATCH_THRESHOLD
                    return surname_ok, min(given_sim, self._sim(gt_surname, extracted_surname))
                return True, given_sim
        combined = self._pick_name(passport_doc)
        if gt_given and combined:
            sim = self._sim(gt_given, combined)
            return sim >= NAME_MATCH_THRESHOLD, sim
        return False, 0.0

    def _build_checks(
        self,
        docs: List[Dict[str, Any]],
        ground_truth: GroundTruth,
        manifest: Dict[str, Any],
    ) -> List[WeightedCheck]:
        gt_name = self._norm(ground_truth.name)
        gt_dob = self._norm(ground_truth.dob)
        gt_gender = self._norm(ground_truth.gender).upper()

        doc_types = {str(d.get("document_type") or "unknown").lower() for d in docs}
        doc_names = [self._pick_name(d) for d in docs if self._pick_name(d)]
        passport_doc = next((d for d in docs if d.get("document_type") == "passport"), None)
        if passport_doc and manifest:
            name_match, best_name_sim = self._passport_name_match(passport_doc, manifest)
        else:
            best_name_sim = max((self._sim(gt_name, n) for n in doc_names), default=0.0)
            name_match = best_name_sim >= NAME_MATCH_THRESHOLD if gt_name else False

        aadhaar_doc = next((d for d in docs if d.get("document_type") == "aadhaar"), None)
        pan_doc = next((d for d in docs if d.get("document_type") == "pan"), None)
        passport_doc = next((d for d in docs if d.get("document_type") == "passport"), None)

        dob_candidates = [self._pick_dob(d) for d in docs if d.get("document_type") in {"aadhaar", "passport", "pan"}]
        dob_match = bool(gt_dob and any(self._dates_equal(d, gt_dob) for d in dob_candidates))

        aadhaar_raw = self._norm((aadhaar_doc or {}).get("aadhaar_number"))
        aadhaar_value = _normalize_aadhaar_number(aadhaar_raw)
        aadhaar_ok = bool(aadhaar_value and AADHAAR_REGEX.match(aadhaar_value))
        aadhaar_format_detail = (
            "Aadhaar number is 12 digits after normalization"
            if aadhaar_ok
            else (
                f"Aadhaar number must be 12 digits (got {len(aadhaar_value)} digits from '{aadhaar_raw}')"
                if aadhaar_value
                else "Aadhaar number missing or empty"
            )
        )

        pan_value = self._norm((pan_doc or {}).get("pan_number")).upper()
        pan_ok = bool(pan_value and PAN_REGEX.match(pan_value))

        expiry_raw = self._norm((passport_doc or {}).get("date_of_expiration"))
        expiry_dt = self._parse_date(expiry_raw)
        passport_expiry_ok = bool(expiry_dt and expiry_dt.date() > datetime.utcnow().date())
        passport_expiry_detail = (
            "Passport expiration is in the future"
            if passport_expiry_ok
            else (
                f"Passport expired on {expiry_raw} (extracted value may still match manifest; not valid for travel)"
                if expiry_raw
                else "Passport expiration date missing"
            )
        )

        cross_doc_consistency = True
        if len(doc_names) > 1:
            for i in range(len(doc_names) - 1):
                if self._sim(doc_names[i], doc_names[i + 1]) < NAME_MATCH_THRESHOLD:
                    cross_doc_consistency = False
                    break

        age_ok = False
        dob_for_age = self._parse_date(gt_dob) or self._parse_date(self._pick_dob(aadhaar_doc or {}))
        if dob_for_age:
            today = datetime.utcnow().date()
            years = today.year - dob_for_age.date().year - ((today.month, today.day) < (dob_for_age.date().month, dob_for_age.date().day))
            age_ok = years >= 18

        passport_gender = self._pick_gender(passport_doc or {})
        aadhaar_gender = self._pick_gender(aadhaar_doc or {})
        pan_gender = self._pick_gender(pan_doc or {})
        gender_consistency = True
        gender_detail = "Gender consistent across uploaded documents"
        if passport_gender and aadhaar_gender:
            gender_consistency = genders_compatible(passport_gender, aadhaar_gender)
            gender_detail = (
                "Passport sex aligns with Aadhaar gender"
                if gender_consistency
                else f"Passport sex ({passport_gender}) does not align with Aadhaar gender ({aadhaar_gender})"
            )
        elif pan_gender and gt_gender:
            gender_consistency = genders_compatible(pan_gender, gt_gender)
            gender_detail = "PAN gender aligns with ground truth" if gender_consistency else "PAN gender conflicts with ground truth"
        elif passport_gender and gt_gender and not aadhaar_gender:
            gender_consistency = genders_compatible(passport_gender, gt_gender)
            gender_detail = "Passport sex aligns with ground truth" if gender_consistency else "Passport sex conflicts with ground truth"

        field_matches = self._field_matches(docs, manifest)
        mandatory_failures: List[str] = []
        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            doc_type = str(doc.get("document_type") or "unknown")
            mandatory_failures.extend(mandatory_field_failures(field_matches.get(doc_id, []), doc_type))

        mandatory_ok = not mandatory_failures
        mandatory_detail = (
            "All mandatory fields matched"
            if mandatory_ok
            else "Missing or mismatched mandatory fields: " + ", ".join(mandatory_failures)
        )
        address_present = bool(self._norm((aadhaar_doc or {}).get("address"))) if aadhaar_doc else False

        checks: List[WeightedCheck] = []

        checks.append(WeightedCheck("Name Match", name_match, f"Best similarity to ground truth name: {best_name_sim:.2f}", self.weights["Name Match"]))
        checks.append(WeightedCheck("DOB Match", dob_match, "DOB normalized match checked against uploaded identity documents", self.weights["DOB Match"]))

        if "aadhaar" in doc_types:
            checks.append(WeightedCheck("Aadhaar Format", aadhaar_ok, aadhaar_format_detail, self.weights["Aadhaar Format"]))

        if "pan" in doc_types:
            checks.append(WeightedCheck("PAN Format", pan_ok, "PAN format must match AAAAA9999A", self.weights["PAN Format"]))

        if "passport" in doc_types:
            checks.append(WeightedCheck("Passport Expiry", passport_expiry_ok, passport_expiry_detail, self.weights["Passport Expiry"]))

        if len(doc_names) > 1:
            checks.append(
                WeightedCheck(
                    "Cross-Document Name Consistency",
                    cross_doc_consistency,
                    "All extracted names are consistent across documents",
                    self.weights["Cross-Document Name Consistency"],
                )
            )

        checks.append(WeightedCheck("Age Eligibility", age_ok, "Customer age must be >= 18", self.weights["Age Eligibility"]))
        show_gender_check = bool(
            (passport_gender and aadhaar_gender)
            or (pan_gender and gt_gender and pan_gender)
            or (passport_gender and gt_gender and "passport" in doc_types and not aadhaar_gender)
        )
        if show_gender_check:
            checks.append(WeightedCheck("Gender Consistency", gender_consistency, gender_detail, self.weights["Gender Consistency"]))

        checks.append(WeightedCheck("Mandatory Fields", mandatory_ok, mandatory_detail, self.weights["Mandatory Fields"]))

        if "aadhaar" in doc_types:
            checks.append(WeightedCheck("Address Present", address_present, "Aadhaar address should be present", self.weights["Address Present"]))

        return checks

    def _field_matches(self, docs: List[Dict[str, Any]], manifest: Dict[str, Any]) -> Dict[str, List[FieldMatch]]:
        field_map: Dict[str, List[FieldMatch]] = {}
        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            field_map[doc_id] = field_matches_from_manifest(doc, manifest)
        return field_map

    def _per_doc_results(
        self,
        docs: List[Dict[str, Any]],
        checks: List[WeightedCheck],
        field_matches: Dict[str, List[FieldMatch]],
    ) -> List[DocumentKYCResult]:
        shared_checks = [c.to_model() for c in checks]
        multi_document = len(docs) > 1

        results: List[DocumentKYCResult] = []
        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            doc_type = str(doc.get("document_type") or "unknown")
            doc_field_matches = field_matches.get(doc_id, [])
            doc_checks = checks_for_document_card(
                shared_checks,
                doc_type,
                doc_field_matches,
                multi_document=multi_document,
            )
            doc_score = score_from_checks(doc_checks)
            results.append(
                DocumentKYCResult(
                    document_id=doc_id,
                    doc_type=doc_type,
                    score=doc_score,
                    passed=doc_score >= 75,
                    checks=doc_checks,
                    field_matches=doc_field_matches,
                )
            )

        return results
