from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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
) -> dict[str, object]:
    if mortgage_type not in MORTGAGE_TYPE_METADATA:
        raise ValueError("unsupported_mortgage_type")
    if employment_profile not in EMPLOYMENT_PROFILE_METADATA:
        raise ValueError("unsupported_employment_profile")

    required_documents: list[dict[str, str]] = []
    conditional_documents: list[dict[str, str]] = []
    _extend_unique(required_documents, BASE_REQUIRED_DOCUMENTS)
    _extend_unique(required_documents, EMPLOYMENT_REQUIRED_DOCUMENTS.get(employment_profile, ()))
    _extend_unique(required_documents, MORTGAGE_TYPE_REQUIRED_DOCUMENTS.get(mortgage_type, ()))
    _extend_unique(conditional_documents, CONDITIONAL_DOCUMENTS)

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
        "employment_profile": employment_profile,
        "required_documents": required_documents,
        "conditional_documents": conditional_documents,
        "lender_notes": lender_notes,
        "next_steps": next_steps,
    }
