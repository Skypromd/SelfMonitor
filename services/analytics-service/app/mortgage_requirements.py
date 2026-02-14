from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
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


def _normalize_filename(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[^a-z0-9_\.]+", "", normalized)
    return normalized


def detect_document_codes_from_filenames(filenames: Iterable[str]) -> set[str]:
    detected_codes: set[str] = set()
    for raw_name in filenames:
        name = _normalize_filename(raw_name)
        if not name:
            continue
        for code, keywords in DOCUMENT_CODE_KEYWORDS.items():
            if any(keyword in name for keyword in keywords):
                detected_codes.add(code)
    return detected_codes


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
