from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

from models import CheckResult, DocumentKYCResult, FieldMatch, GroundTruth, KYCResult


NAME_MATCH_THRESHOLD = 0.85
AADHAAR_REGEX = re.compile(r"^\d{12}$")
PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


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

    def evaluate(self, docs: List[Dict[str, Any]], ground_truth: GroundTruth, scope: str) -> KYCResult:
        checks = self._build_checks(docs, ground_truth)
        total_weight = sum(c.weight for c in checks)
        passed_weight = sum(c.weight for c in checks if c.passed)
        overall = (passed_weight / total_weight) * 100 if total_weight else 0.0
        passed = overall >= 75.0

        field_matches = self._field_matches(docs, ground_truth)
        per_doc = self._per_doc_results(docs, checks, field_matches)

        return KYCResult(
            method="rules",
            scope=scope,
            overall_score=round(overall, 2),
            passed=passed,
            summary=f"Rule evaluation completed with score {round(overall, 2)}%",
            per_document_results=per_doc,
            checks=[c.to_model() for c in checks],
        )

    def _build_checks(self, docs: List[Dict[str, Any]], ground_truth: GroundTruth) -> List[WeightedCheck]:
        gt_name = self._norm(ground_truth.name)
        gt_dob = self._norm(ground_truth.dob)
        gt_gender = self._norm(ground_truth.gender).upper()

        doc_types = {str(d.get("document_type") or "unknown").lower() for d in docs}
        doc_names = [self._pick_name(d) for d in docs if self._pick_name(d)]
        best_name_sim = max((self._sim(gt_name, n) for n in doc_names), default=0.0)
        name_match = best_name_sim >= NAME_MATCH_THRESHOLD if gt_name else False

        aadhaar_doc = next((d for d in docs if d.get("document_type") == "aadhaar"), None)
        pan_doc = next((d for d in docs if d.get("document_type") == "pan"), None)
        passport_doc = next((d for d in docs if d.get("document_type") == "passport"), None)

        dob_candidates = [self._pick_dob(d) for d in docs if d.get("document_type") in {"aadhaar", "passport", "pan"}]
        dob_match = bool(gt_dob and any(self._dates_equal(d, gt_dob) for d in dob_candidates))

        aadhaar_value = self._norm((aadhaar_doc or {}).get("aadhaar_number"))
        aadhaar_ok = bool(aadhaar_value and AADHAAR_REGEX.match(aadhaar_value))

        pan_value = self._norm((pan_doc or {}).get("pan_number")).upper()
        pan_ok = bool(pan_value and PAN_REGEX.match(pan_value))

        expiry_raw = self._norm((passport_doc or {}).get("date_of_expiration"))
        expiry_dt = self._parse_date(expiry_raw)
        passport_expiry_ok = bool(expiry_dt and expiry_dt.date() > datetime.utcnow().date())

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
        gender_consistency = bool(passport_gender and aadhaar_gender and passport_gender == aadhaar_gender)
        if pan_gender and gt_gender:
            gender_consistency = pan_gender == gt_gender
        elif not (passport_gender and aadhaar_gender):
            gender_consistency = True

        field_matches = self._field_matches(docs, ground_truth)
        mandatory_failures: List[str] = []
        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            doc_type = str(doc.get("document_type") or "unknown")
            for match in field_matches.get(doc_id, []):
                if match.status != "match":
                    mandatory_failures.append(f"{doc_type}.{match.field} ({match.status})")

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
            checks.append(WeightedCheck("Aadhaar Format", aadhaar_ok, "Aadhaar number must be 12 digits", self.weights["Aadhaar Format"]))

        if "pan" in doc_types:
            checks.append(WeightedCheck("PAN Format", pan_ok, "PAN format must match AAAAA9999A", self.weights["PAN Format"]))

        if "passport" in doc_types:
            checks.append(WeightedCheck("Passport Expiry", passport_expiry_ok, "Passport expiration must be in the future", self.weights["Passport Expiry"]))

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
        if (passport_gender and aadhaar_gender) or (pan_gender and gt_gender):
            checks.append(WeightedCheck("Gender Consistency", gender_consistency, "Gender should match ground truth or across relevant docs", self.weights["Gender Consistency"]))

        checks.append(WeightedCheck("Mandatory Fields", mandatory_ok, mandatory_detail, self.weights["Mandatory Fields"]))

        if "aadhaar" in doc_types:
            checks.append(WeightedCheck("Address Present", address_present, "Aadhaar address should be present", self.weights["Address Present"]))

        return checks

    def _field_matches(self, docs: List[Dict[str, Any]], ground_truth: GroundTruth) -> Dict[str, List[FieldMatch]]:
        field_map: Dict[str, List[FieldMatch]] = {}
        gt_name = self._norm(ground_truth.name)
        gt_dob = self._norm(ground_truth.dob)
        gt_gender = self._norm(ground_truth.gender)
        gt_address = self._norm(ground_truth.address)

        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            doc_type = str(doc.get("document_type") or "unknown").lower().strip()

            if doc_type == "passport":
                matches = [
                    FieldMatch(field="passport_number", extracted=doc.get("passport_number"), ground_truth=ground_truth.id_numbers.get("passport"), status=self._compare_value("passport_number", doc.get("passport_number"), ground_truth.id_numbers.get("passport"))),
                    FieldMatch(field="given_names", extracted=doc.get("given_names"), ground_truth=gt_name, status=self._compare_value("given_names", doc.get("given_names"), gt_name)),
                    FieldMatch(field="surname", extracted=doc.get("surname"), ground_truth=doc.get("surname"), status=self._compare_value("surname", doc.get("surname"), doc.get("surname"))),
                    FieldMatch(field="date_of_birth", extracted=doc.get("date_of_birth") or doc.get("dob"), ground_truth=gt_dob, status=self._compare_value("date_of_birth", doc.get("date_of_birth") or doc.get("dob"), gt_dob)),
                    FieldMatch(field="nationality", extracted=doc.get("nationality"), ground_truth=ground_truth.nationality, status=self._compare_value("nationality", doc.get("nationality"), ground_truth.nationality)),
                ]
            elif doc_type == "aadhaar":
                matches = [
                    FieldMatch(field="aadhaar_number", extracted=doc.get("aadhaar_number"), ground_truth=ground_truth.id_numbers.get("aadhaar"), status=self._compare_value("aadhaar_number", doc.get("aadhaar_number"), ground_truth.id_numbers.get("aadhaar"))),
                    FieldMatch(field="name", extracted=doc.get("name"), ground_truth=gt_name, status=self._compare_value("name", doc.get("name"), gt_name)),
                    FieldMatch(field="dob", extracted=doc.get("dob"), ground_truth=gt_dob, status=self._compare_value("dob", doc.get("dob"), gt_dob)),
                    FieldMatch(field="gender", extracted=doc.get("gender"), ground_truth=gt_gender, status=self._compare_value("gender", doc.get("gender"), gt_gender)),
                    FieldMatch(field="address", extracted=doc.get("address"), ground_truth=gt_address, status=self._compare_value("address", doc.get("address"), gt_address)),
                    FieldMatch(field="pincode", extracted=doc.get("pincode"), ground_truth=None, status="missing" if not doc.get("pincode") else "match"),
                ]
            elif doc_type == "pan":
                matches = [
                    FieldMatch(field="pan_number", extracted=doc.get("pan_number"), ground_truth=ground_truth.id_numbers.get("pan"), status=self._compare_value("pan_number", doc.get("pan_number"), ground_truth.id_numbers.get("pan"))),
                    FieldMatch(field="name", extracted=doc.get("name"), ground_truth=gt_name, status=self._compare_value("name", doc.get("name"), gt_name)),
                    FieldMatch(field="father_name", extracted=doc.get("father_name"), ground_truth=doc.get("father_name"), status="missing" if not doc.get("father_name") else "match"),
                    FieldMatch(field="dob", extracted=doc.get("dob") or doc.get("date_of_birth"), ground_truth=gt_dob, status=self._compare_value("dob", doc.get("dob") or doc.get("date_of_birth"), gt_dob)),
                ]
            else:
                matches = []

            field_map[doc_id] = matches

        return field_map

    def _per_doc_results(
        self,
        docs: List[Dict[str, Any]],
        checks: List[WeightedCheck],
        field_matches: Dict[str, List[FieldMatch]],
    ) -> List[DocumentKYCResult]:
        shared_checks = [c.to_model() for c in checks]
        active_total_weight = sum(c.weight for c in checks)
        passed_weight = sum(c.weight for c in checks if c.passed)
        score = passed_weight / active_total_weight * 100 if active_total_weight else 0.0

        results: List[DocumentKYCResult] = []
        for doc in docs:
            doc_id = str(doc.get("_metadata", {}).get("source_file") or doc.get("document_type") or "document")
            results.append(
                DocumentKYCResult(
                    document_id=doc_id,
                    doc_type=str(doc.get("document_type") or "unknown"),
                    score=round(score, 2),
                    passed=score >= 75,
                    checks=shared_checks,
                    field_matches=field_matches.get(doc_id, []),
                )
            )

        return results
