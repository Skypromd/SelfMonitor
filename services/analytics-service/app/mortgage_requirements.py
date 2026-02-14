from __future__ import annotations

from dataclasses import dataclass
import datetime
from typing import Iterable, Literal
import re

MORTGAGE_TYPE_METADATA: dict[str, dict[str, str]] = {
    "first_time_buyer": {
        "label": "First-time buyer mortgage",
        "description": "Purchase of first residential home in England.",
    },
    "home_mover": {
        "label": "Home mover mortgage",
        "description": "Purchase of next residential property while selling current home.",
    },
    "remortgage": {
        "label": "Remortgage",
        "description": "Replacing existing mortgage with a new lender or product.",
    },
    "buy_to_let": {
        "label": "Buy-to-let mortgage",
        "description": "Purchase or refinance of rental investment property.",
    },
    "let_to_buy": {
        "label": "Let-to-buy mortgage",
        "description": "Keep current home as rental and buy new residential home.",
    },
    "shared_ownership": {
        "label": "Shared ownership mortgage",
        "description": "Buying a share in property with housing association.",
    },
    "right_to_buy": {
        "label": "Right to buy mortgage",
        "description": "Council tenant purchase under right-to-buy scheme.",
    },
    "new_build": {
        "label": "New-build mortgage",
        "description": "Purchase of newly built property.",
    },
    "self_build": {
        "label": "Self-build mortgage",
        "description": "Finance for building your own home in stages.",
    },
    "interest_only": {
        "label": "Interest-only mortgage",
        "description": "Mortgage where capital repayment vehicle evidence is required.",
    },
    "adverse_credit": {
        "label": "Adverse credit mortgage",
        "description": "Mortgage application with previous credit issues.",
    },
    "guarantor": {
        "label": "Guarantor mortgage",
        "description": "Mortgage supported by guarantor affordability.",
    },
    "joint_borrower_sole_proprietor": {
        "label": "Joint borrower sole proprietor",
        "description": "Family-assisted mortgage with non-owning joint borrower.",
    },
    "offset_mortgage": {
        "label": "Offset mortgage",
        "description": "Mortgage linked to savings/current account balances.",
    },
}

LENDER_PROFILE_METADATA: dict[str, dict[str, str]] = {
    "high_street_mainstream": {
        "label": "High-street mainstream lender",
        "description": "Typical policy set used by major UK high-street banks.",
    },
    "specialist_self_employed": {
        "label": "Specialist self-employed lender",
        "description": "Flexible underwriting for complex self-employed income patterns.",
    },
    "buy_to_let_specialist": {
        "label": "Specialist buy-to-let lender",
        "description": "Portfolio and rental-stress focused underwriting for landlords.",
    },
    "adverse_credit_specialist": {
        "label": "Specialist adverse-credit lender",
        "description": "Enhanced evidence pack for applicants with historic credit impairments.",
    },
}

EMPLOYMENT_PROFILE_METADATA: dict[str, str] = {
    "sole_trader": "Self-employed sole trader",
    "limited_company_director": "Limited company director",
    "contractor": "Contractor / day-rate worker",
    "employed": "PAYE employed",
    "mixed": "Mixed income profile",
}


@dataclass(frozen=True)
class DocumentTemplate:
    code: str
    title: str
    reason: str


BASE_REQUIRED_DOCUMENTS: tuple[DocumentTemplate, ...] = (
    DocumentTemplate("photo_id", "Valid photo ID", "Required for identity and anti-fraud checks."),
    DocumentTemplate("proof_of_address", "Proof of current address", "Required for KYC and credit referencing."),
    DocumentTemplate(
        "bank_statements_6m",
        "Personal bank statements (last 6 months)",
        "Used to verify affordability, spending patterns, and regular commitments.",
    ),
    DocumentTemplate(
        "deposit_source_evidence",
        "Deposit source evidence",
        "Lender must verify source of funds under AML regulations.",
    ),
    DocumentTemplate(
        "credit_commitments",
        "Credit commitments summary",
        "Supports affordability calculation with existing debts and liabilities.",
    ),
)

EMPLOYMENT_REQUIRED_DOCUMENTS: dict[str, tuple[DocumentTemplate, ...]] = {
    "sole_trader": (
        DocumentTemplate(
            "sa302_2y",
            "SA302 tax calculations (2 years, preferably 3)",
            "Primary income evidence for self-employed underwriting.",
        ),
        DocumentTemplate(
            "tax_year_overviews_2y",
            "HMRC tax year overviews (matching SA302)",
            "Cross-checks tax position and submitted returns.",
        ),
    ),
    "limited_company_director": (
        DocumentTemplate(
            "company_accounts_2y",
            "Filed company accounts (2 years)",
            "Used to assess sustainable company income and retained profits.",
        ),
        DocumentTemplate(
            "dividend_vouchers",
            "Dividend vouchers and payslips",
            "Validates director remuneration structure.",
        ),
    ),
    "contractor": (
        DocumentTemplate(
            "current_contract",
            "Current contract and previous contract history",
            "Supports contractor annualized income assessment.",
        ),
        DocumentTemplate(
            "invoice_history_6m",
            "Invoices / remittance history (last 6 months)",
            "Confirms continuity of contract income.",
        ),
    ),
    "employed": (
        DocumentTemplate(
            "payslips_3m",
            "Latest payslips (3 months)",
            "Core PAYE income verification.",
        ),
        DocumentTemplate(
            "p60_latest",
            "Latest P60",
            "Validates annual PAYE earnings.",
        ),
    ),
    "mixed": (
        DocumentTemplate(
            "mixed_income_pack",
            "Combined income pack (PAYE + self-employed evidence)",
            "Underwriter needs full picture of all income sources.",
        ),
    ),
}

MORTGAGE_TYPE_REQUIRED_DOCUMENTS: dict[str, tuple[DocumentTemplate, ...]] = {
    "first_time_buyer": (
        DocumentTemplate(
            "deposit_gift_letter",
            "Gifted deposit letter (if applicable)",
            "Lender requires formal declaration for gifted deposit funds.",
        ),
    ),
    "home_mover": (
        DocumentTemplate(
            "sale_memorandum",
            "Sale memorandum for existing property",
            "Confirms onward chain and expected sale proceeds.",
        ),
    ),
    "remortgage": (
        DocumentTemplate(
            "existing_mortgage_statement",
            "Latest mortgage statement",
            "Required to verify outstanding loan and repayment history.",
        ),
    ),
    "buy_to_let": (
        DocumentTemplate(
            "expected_rental_income",
            "Expected rental income evidence (valuation/AST/projection)",
            "Lender stress-tests rent coverage ratio for BTL lending.",
        ),
        DocumentTemplate(
            "property_portfolio_schedule",
            "Property portfolio schedule (if portfolio landlord)",
            "Required for portfolio risk and affordability review.",
        ),
    ),
    "let_to_buy": (
        DocumentTemplate(
            "consent_to_let_or_btl_offer",
            "Consent-to-let or BTL mortgage offer for current home",
            "Demonstrates legal ability to let current property.",
        ),
    ),
    "shared_ownership": (
        DocumentTemplate(
            "housing_association_pack",
            "Housing association affordability and lease pack",
            "Required for shared ownership eligibility and lease terms.",
        ),
    ),
    "right_to_buy": (
        DocumentTemplate(
            "right_to_buy_notice",
            "Right-to-buy section 125 offer notice",
            "Contains valuation, discount, and legal terms for purchase.",
        ),
    ),
    "new_build": (
        DocumentTemplate(
            "reservation_form",
            "Developer reservation form",
            "Confirms new-build timeline and reservation commitments.",
        ),
    ),
    "self_build": (
        DocumentTemplate(
            "planning_permission",
            "Planning permission and building regulation approvals",
            "Mandatory for staged self-build funding releases.",
        ),
        DocumentTemplate(
            "build_cost_schedule",
            "Detailed build cost schedule and contractor quotes",
            "Required for stage-by-stage self-build drawdown underwriting.",
        ),
    ),
    "interest_only": (
        DocumentTemplate(
            "repayment_vehicle_evidence",
            "Repayment vehicle evidence",
            "Lender needs evidence of strategy to repay capital at term end.",
        ),
    ),
    "adverse_credit": (
        DocumentTemplate(
            "credit_issue_explanation",
            "Written explanation of credit issues",
            "Supports manual underwriter review for adverse credit cases.",
        ),
    ),
    "guarantor": (
        DocumentTemplate(
            "guarantor_income_pack",
            "Guarantor ID, income, and liability declarations",
            "Required to assess guarantor affordability and obligations.",
        ),
    ),
    "joint_borrower_sole_proprietor": (
        DocumentTemplate(
            "jbsp_declaration",
            "JBSP declaration and occupier waiver documents",
            "Required to confirm ownership/borrowing rights and liabilities.",
        ),
    ),
    "offset_mortgage": (
        DocumentTemplate(
            "offset_account_statements",
            "Offset savings/current account statements",
            "Lender validates balances used to reduce charged interest.",
        ),
    ),
}

CONDITIONAL_DOCUMENTS: tuple[DocumentTemplate, ...] = (
    DocumentTemplate(
        "credit_report_copy",
        "Latest credit report copy",
        "Helps pre-check issues before formal lender credit pull.",
    ),
    DocumentTemplate(
        "accountant_reference",
        "Accountant reference letter",
        "Often requested for complex or recently changed income profiles.",
    ),
    DocumentTemplate(
        "proof_of_residency_status",
        "Residency/visa evidence (if applicable)",
        "Needed for applicants with immigration restrictions.",
    ),
)

LENDER_PROFILE_REQUIRED_DOCUMENTS: dict[str, tuple[DocumentTemplate, ...]] = {
    "high_street_mainstream": (),
    "specialist_self_employed": (
        DocumentTemplate(
            "business_bank_statements_12m",
            "Business bank statements (last 12 months)",
            "Specialist self-employed lenders often require deeper cash-flow verification.",
        ),
        DocumentTemplate(
            "management_accounts_ytd",
            "Year-to-date management accounts",
            "Used to evidence current trading trajectory between filed accounts.",
        ),
    ),
    "buy_to_let_specialist": (
        DocumentTemplate(
            "rental_stress_assessment_pack",
            "Rental stress assessment pack",
            "Specialist BTL lenders assess DSCR/ICR with detailed rental assumptions.",
        ),
    ),
    "adverse_credit_specialist": (
        DocumentTemplate(
            "credit_issue_timeline",
            "Credit issue timeline and remediation narrative",
            "Underwriter requires chronology and evidence of issue resolution.",
        ),
    ),
}

LENDER_PROFILE_CONDITIONAL_DOCUMENTS: dict[str, tuple[DocumentTemplate, ...]] = {
    "high_street_mainstream": (),
    "specialist_self_employed": (
        DocumentTemplate(
            "accountant_reference",
            "Accountant reference letter (detailed)",
            "Frequently requested for nuanced profit extraction or recent trading changes.",
        ),
    ),
    "buy_to_let_specialist": (
        DocumentTemplate(
            "landlord_experience_statement",
            "Landlord experience statement",
            "Specialist BTL underwriting may request landlord track-record context.",
        ),
    ),
    "adverse_credit_specialist": (
        DocumentTemplate(
            "credit_report_copy",
            "Tri-bureau credit report pack",
            "Specialist adverse lenders often request full bureau detail upfront.",
        ),
    ),
}

LENDER_PROFILE_NOTES: dict[str, tuple[str, ...]] = {
    "high_street_mainstream": (
        "High-street lenders are usually stricter on document freshness and standard affordability ratios.",
    ),
    "specialist_self_employed": (
        "Specialist lenders may accept wider income evidence, but expect fuller financial narratives.",
    ),
    "buy_to_let_specialist": (
        "BTL specialist lenders place strong emphasis on rental coverage and portfolio-level risk.",
    ),
    "adverse_credit_specialist": (
        "Adverse-credit specialists focus on recency, severity, and remediation of prior credit events.",
    ),
}


def _extend_unique(target: list[dict[str, str]], templates: Iterable[DocumentTemplate]) -> None:
    existing_codes = {item["code"] for item in target}
    for template in templates:
        if template.code in existing_codes:
            continue
        target.append(
            {
                "code": template.code,
                "title": template.title,
                "reason": template.reason,
            }
        )
        existing_codes.add(template.code)


def build_mortgage_document_checklist(
    *,
    mortgage_type: str,
    employment_profile: str,
    include_adverse_credit_pack: bool,
    lender_profile: str = "high_street_mainstream",
) -> dict[str, object]:
    if mortgage_type not in MORTGAGE_TYPE_METADATA:
        raise ValueError("unsupported_mortgage_type")
    if employment_profile not in EMPLOYMENT_PROFILE_METADATA:
        raise ValueError("unsupported_employment_profile")
    if lender_profile not in LENDER_PROFILE_METADATA:
        raise ValueError("unsupported_lender_profile")

    required_documents: list[dict[str, str]] = []
    conditional_documents: list[dict[str, str]] = []
    _extend_unique(required_documents, BASE_REQUIRED_DOCUMENTS)
    _extend_unique(required_documents, EMPLOYMENT_REQUIRED_DOCUMENTS.get(employment_profile, ()))
    _extend_unique(required_documents, MORTGAGE_TYPE_REQUIRED_DOCUMENTS.get(mortgage_type, ()))
    _extend_unique(required_documents, LENDER_PROFILE_REQUIRED_DOCUMENTS.get(lender_profile, ()))
    _extend_unique(conditional_documents, CONDITIONAL_DOCUMENTS)
    _extend_unique(conditional_documents, LENDER_PROFILE_CONDITIONAL_DOCUMENTS.get(lender_profile, ()))

    if include_adverse_credit_pack and mortgage_type != "adverse_credit":
        _extend_unique(
            conditional_documents,
            (
                DocumentTemplate(
                    "credit_issue_explanation",
                    "Written explanation of historic credit issues",
                    "Helps lenders place historic arrears/defaults into context.",
                ),
            ),
        )

    lender_notes = [
        "Most lenders in England expect 2 years of income history for self-employed applicants; 3 years is often stronger.",
        "Document freshness matters: many lenders require statements issued within the last 30-90 days.",
        "Mortgage advisers may add lender-specific extras after initial DIP/AIP checks.",
    ]
    lender_notes.extend(LENDER_PROFILE_NOTES.get(lender_profile, ()))
    next_steps = [
        "Prepare all required documents in PDF format and ensure names/dates match your application.",
        "Run a decision-in-principle (DIP) check before full application to reduce decline risk.",
        "After checklist completion, run affordability and submission readiness review with the agent.",
    ]

    metadata = MORTGAGE_TYPE_METADATA[mortgage_type]
    return {
        "jurisdiction": "England",
        "mortgage_type": mortgage_type,
        "mortgage_label": metadata["label"],
        "mortgage_description": metadata["description"],
        "lender_profile": lender_profile,
        "lender_profile_label": LENDER_PROFILE_METADATA[lender_profile]["label"],
        "employment_profile": employment_profile,
        "required_documents": required_documents,
        "conditional_documents": conditional_documents,
        "lender_notes": lender_notes,
        "next_steps": next_steps,
    }


DOCUMENT_CODE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "photo_id": ("passport", "driving_licence", "driving-license", "photo_id", "id_card"),
    "proof_of_address": ("proof_of_address", "utility_bill", "council_tax", "bank_statement_address"),
    "bank_statements_6m": ("bank_statement", "current_account", "statement"),
    "deposit_source_evidence": ("deposit", "source_of_funds", "gift_letter", "savings_statement"),
    "credit_commitments": ("credit_commitment", "loan_statement", "credit_card_statement"),
    "sa302_2y": ("sa302", "tax_calculation"),
    "tax_year_overviews_2y": ("tax_year_overview", "hmrc_overview"),
    "company_accounts_2y": ("company_accounts", "statutory_accounts"),
    "dividend_vouchers": ("dividend", "director_payslip"),
    "current_contract": ("contract", "engagement_letter"),
    "invoice_history_6m": ("invoice", "remittance"),
    "payslips_3m": ("payslip",),
    "p60_latest": ("p60",),
    "mixed_income_pack": ("mixed_income", "income_pack"),
    "deposit_gift_letter": ("gift_letter", "gifted_deposit"),
    "sale_memorandum": ("sale_memorandum", "memorandum_of_sale"),
    "existing_mortgage_statement": ("mortgage_statement",),
    "expected_rental_income": ("rental_income", "ast", "tenancy_agreement", "rent_valuation"),
    "property_portfolio_schedule": ("portfolio", "property_schedule"),
    "consent_to_let_or_btl_offer": ("consent_to_let", "btl_offer"),
    "housing_association_pack": ("housing_association", "shared_ownership", "lease_pack"),
    "right_to_buy_notice": ("right_to_buy", "section_125"),
    "reservation_form": ("reservation_form", "developer_reservation"),
    "planning_permission": ("planning_permission", "building_regulations"),
    "build_cost_schedule": ("build_cost", "contractor_quote", "cost_schedule"),
    "repayment_vehicle_evidence": ("repayment_vehicle", "endowment", "isa_statement"),
    "credit_issue_explanation": ("credit_explanation", "adverse_credit"),
    "guarantor_income_pack": ("guarantor", "guarantor_income"),
    "jbsp_declaration": ("jbsp", "sole_proprietor_declaration", "occupier_waiver"),
    "offset_account_statements": ("offset", "savings_statement"),
    "credit_report_copy": ("credit_report", "experian", "equifax", "transunion"),
    "accountant_reference": ("accountant_reference", "accountant_letter"),
    "proof_of_residency_status": ("visa", "residency", "brp", "settled_status"),
    "business_bank_statements_12m": ("business_statement", "business_bank_statement"),
    "management_accounts_ytd": ("management_accounts", "ytd_accounts"),
    "rental_stress_assessment_pack": ("rental_stress", "icr", "dscr"),
    "credit_issue_timeline": ("credit_timeline", "arrears_explanation"),
    "landlord_experience_statement": ("landlord_experience",),
}

PERIOD_FRESHNESS_DAYS_BY_CODE: dict[str, int] = {
    "proof_of_address": 120,
    "bank_statements_6m": 210,
    "invoice_history_6m": 210,
    "payslips_3m": 120,
    "existing_mortgage_statement": 120,
    "offset_account_statements": 120,
    "business_bank_statements_12m": 400,
    "management_accounts_ytd": 400,
}

UPLOAD_STALENESS_DAYS_BY_CODE: dict[str, int] = {
    "proof_of_address": 120,
    "bank_statements_6m": 120,
    "invoice_history_6m": 120,
    "payslips_3m": 90,
    "existing_mortgage_statement": 120,
    "offset_account_statements": 120,
}

NAME_VALIDATION_CODES: set[str] = {
    "photo_id",
    "proof_of_address",
    "payslips_3m",
    "p60_latest",
    "sa302_2y",
    "tax_year_overviews_2y",
}

MONTH_TOKEN_TO_NUMBER: dict[str, int] = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

DOCUMENT_NAME_GENERIC_TOKENS: set[str] = {
    "scan",
    "statement",
    "statements",
    "bank",
    "utility",
    "bill",
    "proof",
    "address",
    "passport",
    "license",
    "licence",
    "driving",
    "photo",
    "id",
    "tax",
    "overview",
    "hmrc",
    "latest",
    "final",
    "signed",
    "copy",
    "document",
    "docs",
    "mortgage",
    "report",
    "income",
    "evidence",
    "deposit",
    "source",
    "funds",
    "credit",
    "commitment",
    "commitments",
    "company",
    "accounts",
    "invoice",
    "payslip",
    "p60",
    "current",
    "account",
    "business",
    "rental",
    "valuation",
    "agreement",
    "tenancy",
    "schedule",
    "portfolio",
    "offer",
    "consent",
    "letter",
}
DOCUMENT_NAME_GENERIC_TOKENS.update(MONTH_TOKEN_TO_NUMBER.keys())

YEAR_MONTH_PATTERN = re.compile(r"(20\d{2})[_\-]?(0[1-9]|1[0-2])")
YEAR_PATTERN = re.compile(r"\b(20\d{2})\b")
NAME_TOKEN_PATTERN = re.compile(r"[a-z]{3,}")

MORTGAGE_COMPLIANCE_DISCLAIMER = (
    "This readiness output is for document preparation support only and is not regulated mortgage advice. "
    "A qualified UK mortgage adviser must review affordability, suitability, and lender policy alignment "
    "before any broker/lender submission."
)

MONTHLY_REFRESH_TRACKED_CODES: dict[str, dict[str, object]] = {
    "photo_id": {
        "reminder_type": "id_validity_check",
        "title": "Monthly ID validity check",
        "cadence_days": 30,
        "suggested_action": "Confirm passport/driving licence is valid and not expiring within the next 6 months.",
    },
    "proof_of_address": {
        "reminder_type": "statement_refresh",
        "title": "Proof of address refresh",
        "cadence_days": 30,
        "suggested_action": "Upload a more recent proof-of-address document issued in the current month.",
    },
    "bank_statements_6m": {
        "reminder_type": "statement_refresh",
        "title": "Bank statement refresh",
        "cadence_days": 30,
        "suggested_action": "Upload the latest monthly bank statement to keep affordability evidence current.",
    },
    "business_bank_statements_12m": {
        "reminder_type": "statement_refresh",
        "title": "Business bank statement refresh",
        "cadence_days": 30,
        "suggested_action": "Upload the latest monthly business bank statement.",
    },
    "payslips_3m": {
        "reminder_type": "statement_refresh",
        "title": "Payslip refresh",
        "cadence_days": 30,
        "suggested_action": "Upload the latest payslip(s) so the income pack remains current.",
    },
    "existing_mortgage_statement": {
        "reminder_type": "statement_refresh",
        "title": "Mortgage statement refresh",
        "cadence_days": 30,
        "suggested_action": "Upload the latest mortgage statement from your current lender.",
    },
    "offset_account_statements": {
        "reminder_type": "statement_refresh",
        "title": "Offset account statement refresh",
        "cadence_days": 30,
        "suggested_action": "Upload the latest offset-linked account statement.",
    },
}


def _normalize_filename(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_\.]+", "", normalized)
    return normalized


def detect_document_evidence_from_filenames(
    filenames: Iterable[str],
) -> tuple[set[str], dict[str, list[str]]]:
    detected_codes: set[str] = set()
    evidence_map: dict[str, list[str]] = {}
    for raw_name in filenames:
        name = _normalize_filename(raw_name)
        if not name:
            continue
        for code, keywords in DOCUMENT_CODE_KEYWORDS.items():
            if any(keyword in name for keyword in keywords):
                detected_codes.add(code)
                if code not in evidence_map:
                    evidence_map[code] = []
                if raw_name not in evidence_map[code]:
                    evidence_map[code].append(raw_name)
    return detected_codes, evidence_map


def detect_document_codes_from_filenames(filenames: Iterable[str]) -> set[str]:
    detected_codes, _ = detect_document_evidence_from_filenames(filenames)
    return detected_codes


def _coerce_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _coerce_date(value: object) -> datetime.date | None:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _coerce_datetime(value: object) -> datetime.datetime | None:
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return datetime.datetime.combine(value, datetime.time.min)
    if isinstance(value, str):
        iso_value = value.strip()
        if iso_value.endswith("Z"):
            iso_value = iso_value.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(iso_value)
        except ValueError:
            return None
    return None


def _extract_period_date_from_filename(normalized_filename: str) -> datetime.date | None:
    year_month_match = YEAR_MONTH_PATTERN.search(normalized_filename)
    if year_month_match:
        year = int(year_month_match.group(1))
        month = int(year_month_match.group(2))
        return datetime.date(year, month, 1)

    tokens = [token for token in re.split(r"[_\.]+", normalized_filename) if token]
    for idx, token in enumerate(tokens):
        month = MONTH_TOKEN_TO_NUMBER.get(token)
        if month is None:
            continue
        for offset in (-1, 1):
            neighbor_idx = idx + offset
            if neighbor_idx < 0 or neighbor_idx >= len(tokens):
                continue
            neighbor = tokens[neighbor_idx]
            if neighbor.isdigit() and len(neighbor) == 4 and neighbor.startswith("20"):
                return datetime.date(int(neighbor), month, 1)

    year_match = YEAR_PATTERN.search(normalized_filename)
    if year_match:
        return datetime.date(int(year_match.group(1)), 12, 1)
    return None


def _extract_name_tokens(value: str) -> set[str]:
    return {
        token
        for token in NAME_TOKEN_PATTERN.findall(value.lower())
        if token not in DOCUMENT_NAME_GENERIC_TOKENS and len(token) >= 3
    }


def _resolve_max_period_age_days(detected_codes: set[str]) -> int | None:
    thresholds = [PERIOD_FRESHNESS_DAYS_BY_CODE[code] for code in detected_codes if code in PERIOD_FRESHNESS_DAYS_BY_CODE]
    if not thresholds:
        return None
    return min(thresholds)


def _resolve_upload_staleness_days(detected_codes: set[str]) -> int:
    thresholds = [UPLOAD_STALENESS_DAYS_BY_CODE[code] for code in detected_codes if code in UPLOAD_STALENESS_DAYS_BY_CODE]
    if not thresholds:
        return 180
    return min(thresholds)


def build_mortgage_evidence_quality_checks(
    *,
    uploaded_documents: Iterable[dict[str, object]],
    applicant_first_name: str | None = None,
    applicant_last_name: str | None = None,
    today: datetime.date | None = None,
) -> dict[str, object]:
    reference_date = today or datetime.date.today()
    applicant_tokens = _extract_name_tokens(
        " ".join(part for part in (applicant_first_name, applicant_last_name) if isinstance(part, str))
    )

    issues: list[dict[str, object]] = []

    for raw_document in uploaded_documents:
        if not isinstance(raw_document, dict):
            continue
        raw_filename = raw_document.get("filename")
        if not isinstance(raw_filename, str) or not raw_filename.strip():
            continue
        filename = raw_filename.strip()
        normalized_filename = _normalize_filename(filename)
        detected_codes = detect_document_codes_from_filenames([filename])
        primary_code = sorted(detected_codes)[0] if detected_codes else None
        extracted_data = raw_document.get("extracted_data")
        if not isinstance(extracted_data, dict):
            extracted_data = {}

        status_value = str(raw_document.get("status", "")).strip().lower()
        ocr_confidence = _coerce_float(extracted_data.get("ocr_confidence"))
        needs_review = extracted_data.get("needs_review") is True
        review_reason_value = extracted_data.get("review_reason")
        review_reason = review_reason_value.strip() if isinstance(review_reason_value, str) else ""

        if status_value == "failed":
            issues.append(
                {
                    "check_type": "unreadable_ocr",
                    "severity": "critical",
                    "document_filename": filename,
                    "document_code": primary_code,
                    "message": "OCR extraction failed for this document.",
                    "suggested_action": "Re-upload a clearer scan or provide a native PDF copy.",
                }
            )
        elif needs_review or (ocr_confidence is not None and ocr_confidence < 0.6):
            severity = "critical" if ocr_confidence is not None and ocr_confidence < 0.45 else "warning"
            reason_suffix = f" Reason: {review_reason}" if review_reason else ""
            confidence_suffix = (
                f" OCR confidence {ocr_confidence:.2f} is below threshold." if ocr_confidence is not None else ""
            )
            issues.append(
                {
                    "check_type": "unreadable_ocr",
                    "severity": severity,
                    "document_filename": filename,
                    "document_code": primary_code,
                    "message": f"Document OCR quality is low.{confidence_suffix}{reason_suffix}".strip(),
                    "suggested_action": "Review OCR fields and replace with a higher-quality scan if needed.",
                }
            )

        uploaded_at = _coerce_datetime(raw_document.get("uploaded_at"))
        if uploaded_at is not None:
            upload_age_days = (reference_date - uploaded_at.date()).days
            staleness_limit_days = _resolve_upload_staleness_days(detected_codes)
            if upload_age_days > staleness_limit_days:
                severity = "critical" if staleness_limit_days <= 120 else "warning"
                issues.append(
                    {
                        "check_type": "staleness",
                        "severity": severity,
                        "document_filename": filename,
                        "document_code": primary_code,
                        "message": (
                            f"Document was uploaded {upload_age_days} days ago and may be stale for current "
                            "underwriting."
                        ),
                        "suggested_action": "Refresh this evidence with a newly issued document.",
                    }
                )

        period_date = _coerce_date(extracted_data.get("transaction_date")) or _extract_period_date_from_filename(
            normalized_filename
        )
        period_limit_days = _resolve_max_period_age_days(detected_codes)
        if period_date is not None and period_limit_days is not None:
            period_age_days = (reference_date - period_date).days
            if period_age_days > period_limit_days:
                severity = (
                    "critical"
                    if any(code in {"proof_of_address", "bank_statements_6m", "payslips_3m"} for code in detected_codes)
                    else "warning"
                )
                issues.append(
                    {
                        "check_type": "period_mismatch",
                        "severity": severity,
                        "document_filename": filename,
                        "document_code": primary_code,
                        "message": (
                            f"Document period appears {period_age_days} days old, exceeding expected window "
                            f"({period_limit_days} days)."
                        ),
                        "suggested_action": "Upload a document covering the required recent period.",
                    }
                )

        if applicant_tokens and detected_codes.intersection(NAME_VALIDATION_CODES):
            filename_name_tokens = _extract_name_tokens(normalized_filename)
            if len(filename_name_tokens) >= 2 and filename_name_tokens.isdisjoint(applicant_tokens):
                issues.append(
                    {
                        "check_type": "name_mismatch",
                        "severity": "warning",
                        "document_filename": filename,
                        "document_code": primary_code,
                        "message": (
                            "Document filename appears to include a different person name than the profile name "
                            "on this application."
                        ),
                        "suggested_action": "Verify this file belongs to the applicant and replace if mismatched.",
                    }
                )

    severity_rank = {"critical": 0, "warning": 1, "info": 2}
    issues.sort(
        key=lambda issue: (
            severity_rank.get(str(issue.get("severity", "info")), 3),
            str(issue.get("document_filename", "")).lower(),
            str(issue.get("check_type", "")).lower(),
        )
    )
    critical_count = sum(1 for issue in issues if issue.get("severity") == "critical")
    warning_count = sum(1 for issue in issues if issue.get("severity") == "warning")
    info_count = sum(1 for issue in issues if issue.get("severity") == "info")
    return {
        "evidence_quality_summary": {
            "total_issues": len(issues),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "info_count": info_count,
            "has_blockers": critical_count > 0,
        },
        "evidence_quality_issues": issues,
    }


def build_mortgage_refresh_reminders(
    *,
    uploaded_documents: Iterable[dict[str, object]],
    today: datetime.date | None = None,
) -> dict[str, object]:
    reference_date = today or datetime.date.today()
    reminders_by_code: dict[str, dict[str, object]] = {}

    for raw_document in uploaded_documents:
        if not isinstance(raw_document, dict):
            continue
        raw_filename = raw_document.get("filename")
        if not isinstance(raw_filename, str) or not raw_filename.strip():
            continue
        filename = raw_filename.strip()
        normalized_filename = _normalize_filename(filename)
        detected_codes = detect_document_codes_from_filenames([filename])
        if not detected_codes:
            continue

        extracted_data = raw_document.get("extracted_data")
        if not isinstance(extracted_data, dict):
            extracted_data = {}
        upload_datetime = _coerce_datetime(raw_document.get("uploaded_at"))
        period_date = _coerce_date(extracted_data.get("transaction_date")) or _extract_period_date_from_filename(
            normalized_filename
        )
        anchor_date_candidates: list[datetime.date] = []
        if upload_datetime is not None:
            anchor_date_candidates.append(upload_datetime.date())
        if period_date is not None:
            anchor_date_candidates.append(period_date)
        anchor_date = max(anchor_date_candidates) if anchor_date_candidates else reference_date

        for code in detected_codes:
            metadata = MONTHLY_REFRESH_TRACKED_CODES.get(code)
            if metadata is None:
                continue
            cadence_days = int(metadata["cadence_days"])
            due_date = anchor_date + datetime.timedelta(days=cadence_days)
            existing = reminders_by_code.get(code)
            if existing is not None and isinstance(existing.get("due_date"), datetime.date):
                existing_due_date = existing["due_date"]
                if isinstance(existing_due_date, datetime.date) and due_date < existing_due_date:
                    continue

            reminders_by_code[code] = {
                "reminder_type": str(metadata["reminder_type"]),
                "document_code": code,
                "title": str(metadata["title"]),
                "cadence_days": cadence_days,
                "due_date": due_date,
                "document_filename": filename,
                "suggested_action": str(metadata["suggested_action"]),
            }

    reminders: list[dict[str, object]] = []
    for code in sorted(reminders_by_code):
        item = reminders_by_code[code]
        due_date = item["due_date"]
        if not isinstance(due_date, datetime.date):
            continue
        days_until_due = (due_date - reference_date).days
        status = "due_now" if days_until_due <= 0 else "upcoming"
        if status == "due_now":
            message = "Monthly refresh is due now for this evidence item."
        else:
            message = f"Next monthly refresh due in {days_until_due} day(s)."
        reminders.append(
            {
                "reminder_type": item["reminder_type"],
                "document_code": item["document_code"],
                "title": item["title"],
                "cadence_days": item["cadence_days"],
                "due_date": due_date,
                "status": status,
                "document_filename": item["document_filename"],
                "message": message,
                "suggested_action": item["suggested_action"],
            }
        )

    reminders.sort(
        key=lambda reminder: (
            0 if reminder["status"] == "due_now" else 1,
            reminder["due_date"],
            str(reminder["title"]),
        )
    )

    due_now_count = sum(1 for reminder in reminders if reminder["status"] == "due_now")
    upcoming_count = len(reminders) - due_now_count
    next_due_date = reminders[0]["due_date"] if reminders else None

    return {
        "refresh_reminder_summary": {
            "total_reminders": len(reminders),
            "due_now_count": due_now_count,
            "upcoming_count": upcoming_count,
            "has_due_now": due_now_count > 0,
            "next_due_date": next_due_date,
        },
        "refresh_reminders": reminders,
    }


def build_mortgage_submission_gate(
    *,
    readiness_status: str,
    evidence_quality_summary: dict[str, object] | None,
    advisor_review_confirmed: bool,
) -> dict[str, object]:
    blockers: list[str] = []
    if readiness_status != "ready_for_broker_review":
        blockers.append(
            "Document readiness is not yet at 'ready_for_broker_review' level."
        )
    has_quality_blockers = False
    if isinstance(evidence_quality_summary, dict):
        has_quality_blockers = bool(evidence_quality_summary.get("has_blockers"))
    if has_quality_blockers:
        blockers.append("Critical evidence-quality issues must be resolved first.")
    if not advisor_review_confirmed:
        blockers.append("Advisor review confirmation is required before broker submission.")

    return {
        "compliance_disclaimer": MORTGAGE_COMPLIANCE_DISCLAIMER,
        "advisor_review_required": True,
        "advisor_review_confirmed": advisor_review_confirmed,
        "broker_submission_allowed": len(blockers) == 0,
        "broker_submission_blockers": blockers,
    }


def _documents_by_match_state(
    *,
    documents: list[dict[str, str]],
    detected_codes: set[str],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    matched: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    for document in documents:
        if document["code"] in detected_codes:
            matched.append(document)
        else:
            missing.append(document)
    return matched, missing


def build_mortgage_readiness_assessment(
    *,
    checklist: dict[str, object],
    uploaded_filenames: Iterable[str],
) -> dict[str, object]:
    filenames = [filename for filename in uploaded_filenames if filename]
    detected_codes = detect_document_codes_from_filenames(filenames)
    required_documents = list(checklist["required_documents"])
    conditional_documents = list(checklist["conditional_documents"])
    matched_required, missing_required = _documents_by_match_state(
        documents=required_documents,
        detected_codes=detected_codes,
    )
    _, missing_conditional = _documents_by_match_state(
        documents=conditional_documents,
        detected_codes=detected_codes,
    )
    total_required = len(required_documents)
    total_conditional = len(conditional_documents)
    required_completion = round((len(matched_required) / total_required) * 100, 1) if total_required > 0 else 100.0
    total_target = total_required + total_conditional
    overall_completion = (
        round(((total_target - len(missing_required) - len(missing_conditional)) / total_target) * 100, 1)
        if total_target > 0
        else 100.0
    )

    if required_completion == 100.0 and overall_completion >= 70.0:
        readiness_status = "ready_for_broker_review"
    elif required_completion >= 70.0:
        readiness_status = "almost_ready"
    else:
        readiness_status = "not_ready"

    next_actions = [f"Upload: {item['title']}" for item in missing_required[:5]]
    if not next_actions:
        next_actions = [
            "All required documents detected. Validate freshness (typically last 30-90 days) before broker submission."
        ]

    readiness_summary = (
        f"Detected {len(matched_required)} of {total_required} required documents "
        f"({required_completion}%). Readiness status: {readiness_status}."
    )

    result = dict(checklist)
    result.update(
        {
            "uploaded_document_count": len(filenames),
            "detected_document_codes": sorted(detected_codes),
            "matched_required_documents": matched_required,
            "missing_required_documents": missing_required,
            "missing_conditional_documents": missing_conditional,
            "required_completion_percent": required_completion,
            "overall_completion_percent": overall_completion,
            "readiness_status": readiness_status,
            "readiness_summary": readiness_summary,
            "next_actions": next_actions,
        }
    )
    return result


def _build_document_evidence_items(
    *,
    documents: list[dict[str, str]],
    evidence_map: dict[str, list[str]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for document in documents:
        matched_filenames = list(evidence_map.get(document["code"], []))
        items.append(
            {
                "code": document["code"],
                "title": document["title"],
                "reason": document["reason"],
                "match_status": "matched" if matched_filenames else "missing",
                "matched_filenames": matched_filenames,
            }
        )
    return items


def build_mortgage_pack_index(
    *,
    checklist: dict[str, object],
    uploaded_filenames: Iterable[str],
) -> dict[str, object]:
    filenames = [filename for filename in uploaded_filenames if filename]
    readiness = build_mortgage_readiness_assessment(
        checklist=checklist,
        uploaded_filenames=filenames,
    )
    detected_codes, evidence_map = detect_document_evidence_from_filenames(filenames)
    required_documents = list(checklist["required_documents"])
    conditional_documents = list(checklist["conditional_documents"])
    required_evidence = _build_document_evidence_items(
        documents=required_documents,
        evidence_map=evidence_map,
    )
    conditional_evidence = _build_document_evidence_items(
        documents=conditional_documents,
        evidence_map=evidence_map,
    )

    result = dict(checklist)
    result.update(
        {
            "uploaded_document_count": len(filenames),
            "detected_document_codes": sorted(detected_codes),
            "readiness_status": readiness["readiness_status"],
            "required_completion_percent": readiness["required_completion_percent"],
            "overall_completion_percent": readiness["overall_completion_percent"],
            "readiness_summary": readiness["readiness_summary"],
            "next_actions": readiness["next_actions"],
            "matched_required_documents": readiness["matched_required_documents"],
            "missing_required_documents": readiness["missing_required_documents"],
            "missing_conditional_documents": readiness["missing_conditional_documents"],
            "required_document_evidence": required_evidence,
            "conditional_document_evidence": conditional_evidence,
        }
    )
    return result


def build_mortgage_readiness_matrix(
    *,
    employment_profile: str,
    include_adverse_credit_pack: bool,
    lender_profile: str,
    uploaded_filenames: Iterable[str],
    mortgage_types: Iterable[str] | None = None,
) -> dict[str, object]:
    if employment_profile not in EMPLOYMENT_PROFILE_METADATA:
        raise ValueError("unsupported_employment_profile")
    if lender_profile not in LENDER_PROFILE_METADATA:
        raise ValueError("unsupported_lender_profile")

    selected_mortgage_types = list(mortgage_types or MORTGAGE_TYPE_METADATA.keys())
    for mortgage_type in selected_mortgage_types:
        if mortgage_type not in MORTGAGE_TYPE_METADATA:
            raise ValueError("unsupported_mortgage_type")

    filenames = [filename for filename in uploaded_filenames if filename]
    items: list[dict[str, object]] = []
    ready_count = 0
    almost_ready_count = 0
    not_ready_count = 0
    sum_required_completion = 0.0
    sum_overall_completion = 0.0

    for mortgage_type in selected_mortgage_types:
        checklist = build_mortgage_document_checklist(
            mortgage_type=mortgage_type,
            employment_profile=employment_profile,
            include_adverse_credit_pack=include_adverse_credit_pack,
            lender_profile=lender_profile,
        )
        readiness = build_mortgage_readiness_assessment(
            checklist=checklist,
            uploaded_filenames=filenames,
        )
        readiness_status = str(readiness["readiness_status"])
        if readiness_status == "ready_for_broker_review":
            ready_count += 1
        elif readiness_status == "almost_ready":
            almost_ready_count += 1
        else:
            not_ready_count += 1

        required_completion = float(readiness["required_completion_percent"])
        overall_completion = float(readiness["overall_completion_percent"])
        sum_required_completion += required_completion
        sum_overall_completion += overall_completion
        missing_required_documents = list(readiness["missing_required_documents"])

        items.append(
            {
                "mortgage_type": mortgage_type,
                "mortgage_label": checklist["mortgage_label"],
                "required_completion_percent": required_completion,
                "overall_completion_percent": overall_completion,
                "readiness_status": readiness_status,
                "missing_required_count": len(missing_required_documents),
                "missing_required_documents": missing_required_documents,
                "next_actions": list(readiness["next_actions"]),
            }
        )

    items.sort(
        key=lambda item: (
            float(item["required_completion_percent"]),
            float(item["overall_completion_percent"]),
            -int(item["missing_required_count"]),
        ),
        reverse=True,
    )

    total_types = len(items)
    average_required_completion = round(sum_required_completion / total_types, 1) if total_types else 0.0
    average_overall_completion = round(sum_overall_completion / total_types, 1) if total_types else 0.0

    overall_status: Literal["not_ready", "almost_ready", "ready_for_broker_review"]
    if ready_count == total_types and total_types > 0:
        overall_status = "ready_for_broker_review"
    elif ready_count > 0 or almost_ready_count > 0:
        overall_status = "almost_ready"
    else:
        overall_status = "not_ready"

    return {
        "jurisdiction": "England",
        "employment_profile": employment_profile,
        "lender_profile": lender_profile,
        "lender_profile_label": LENDER_PROFILE_METADATA[lender_profile]["label"],
        "include_adverse_credit_pack": include_adverse_credit_pack,
        "uploaded_document_count": len(filenames),
        "total_mortgage_types": total_types,
        "ready_for_broker_review_count": ready_count,
        "almost_ready_count": almost_ready_count,
        "not_ready_count": not_ready_count,
        "average_required_completion_percent": average_required_completion,
        "average_overall_completion_percent": average_overall_completion,
        "overall_status": overall_status,
        "items": items,
    }
