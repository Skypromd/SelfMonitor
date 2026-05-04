"""
UK self-employed category definitions with HMRC / SA103 / MTD field mappings.

This module is the single source of truth for all UI-facing category labels,
their corresponding HMRC self-assessment box references, MTD submission fields,
plain-language explanations, and any guidance warnings.

Import this in any service or frontend data-generation route.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Category:
    key: str
    """Internal slug used in the database and API."""

    label: str
    """Short plain-English label shown in the UI."""

    description: str
    """One-sentence plain-language explanation for the user."""

    hmrc_sa_box: str | None
    """SA103 box reference (e.g. 'Box 9 – Allowable business expenses')."""

    mtd_field: str | None
    """MTD ITSA submission field name (camelCase as per HMRC API)."""

    is_income: bool = False
    """True if this category represents taxable income."""

    not_advice_copy: str | None = None
    """Disclaimer to show alongside this category where FCA/HMRC guidance applies."""

    suspicious_warning: str | None = None
    """Warning shown if this category is applied to a transaction that looks unusual."""


# ---------------------------------------------------------------------------
# Income categories
# ---------------------------------------------------------------------------

INCOME_CATEGORIES: list[Category] = [
    Category(
        key="income",
        label="Self-employment income",
        description="Money received for goods or services you provided as a self-employed person.",
        hmrc_sa_box="Box 9 – Turnover",
        mtd_field="turnover",
        is_income=True,
        not_advice_copy=(
            "If you are unsure whether a receipt is taxable, consult an accountant or HMRC guidance."
        ),
    ),
    Category(
        key="cis_income",
        label="CIS income (gross)",
        description=(
            "Gross payment from a contractor under the Construction Industry Scheme. "
            "Tax deducted at source (CIS deduction) is tracked separately."
        ),
        hmrc_sa_box="Box 9 – Turnover (CIS gross)",
        mtd_field="turnover",
        is_income=True,
        not_advice_copy=(
            "CIS deductions already withheld by your contractor reduce your tax bill at year-end. "
            "Do not deduct them again as an expense."
        ),
    ),
    Category(
        key="rental_income",
        label="Rental income",
        description="Income from letting out property you own.",
        hmrc_sa_box="SA105 – UK property income",
        mtd_field="otherIncome",
        is_income=True,
        not_advice_copy=(
            "Rental income is reported on a separate SA105 property schedule, "
            "not on your main self-employment SA103F."
        ),
        suspicious_warning=(
            "Rental income mixed with business trading income may require separate property pages. "
            "Consider speaking to an accountant."
        ),
    ),
    Category(
        key="other_income",
        label="Other income",
        description="Any taxable money received that does not fit another category.",
        hmrc_sa_box="Box 10 – Any other income",
        mtd_field="otherIncome",
        is_income=True,
        not_advice_copy=(
            "Use this sparingly. If a receipt recurs, it likely fits a more specific category."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Expense categories (allowable deductions)
# ---------------------------------------------------------------------------

EXPENSE_CATEGORIES: list[Category] = [
    Category(
        key="office_supplies",
        label="Office supplies",
        description="Paper, printer ink, postage, and similar consumables used purely for business.",
        hmrc_sa_box="Box 20 – Office costs",
        mtd_field="officeAndAdminCosts",
    ),
    Category(
        key="software",
        label="Software & subscriptions",
        description="Business software, SaaS tools, and trade or professional subscriptions.",
        hmrc_sa_box="Box 20 – Office costs",
        mtd_field="officeAndAdminCosts",
        suspicious_warning=(
            "Personal streaming or gaming subscriptions are not allowable. "
            "Only include tools used wholly for your business."
        ),
    ),
    Category(
        key="utilities",
        label="Utilities (business use)",
        description=(
            "Business phone, broadband, and utility bills — or the business-use portion "
            "if shared with personal use."
        ),
        hmrc_sa_box="Box 20 – Office costs",
        mtd_field="officeAndAdminCosts",
        not_advice_copy=(
            "If you work from home, you can claim a proportion of household bills. "
            "HMRC's simplified flat-rate or actual-cost method both apply — keep records."
        ),
    ),
    Category(
        key="travel",
        label="Business travel",
        description="Train, bus, taxi, or car mileage for journeys that are wholly for business.",
        hmrc_sa_box="Box 17 – Car, van and travel expenses",
        mtd_field="travelCosts",
        not_advice_copy=(
            "Ordinary commuting from home to a permanent workplace is not allowable. "
            "Use HMRC's approved mileage rates (45p/mile up to 10,000 miles) for car journeys."
        ),
        suspicious_warning=(
            "Large travel amounts relative to your sector may attract HMRC attention. "
            "Keep a log of every business journey."
        ),
    ),
    Category(
        key="transport",
        label="Local transport",
        description="Short local journeys by taxi, bus, or Tube that are wholly for business.",
        hmrc_sa_box="Box 17 – Car, van and travel expenses",
        mtd_field="travelCosts",
    ),
    Category(
        key="advertising",
        label="Advertising & marketing",
        description="Website hosting, social media ads, printed materials, and other promotion costs.",
        hmrc_sa_box="Box 21 – Advertising and business entertainment costs",
        mtd_field="advertisingCosts",
        suspicious_warning=(
            "Client entertainment (meals, events) is generally not tax-deductible unless "
            "wholly and exclusively for business. Use 'Professional services' if in doubt."
        ),
    ),
    Category(
        key="professional_services",
        label="Professional services",
        description=(
            "Accountancy, legal, bookkeeping, and other professional fees paid to run your business."
        ),
        hmrc_sa_box="Box 22 – Accountancy, legal and other professional fees",
        mtd_field="professionalFees",
    ),
    Category(
        key="insurance",
        label="Business insurance",
        description="Public liability, professional indemnity, and other business-related insurance.",
        hmrc_sa_box="Box 19 – Insurance",
        mtd_field="adminCosts",
    ),
    Category(
        key="equipment",
        label="Equipment & tools",
        description=(
            "Tools, machinery, or equipment bought for business use. "
            "Capital items (long-life assets) may qualify for the Annual Investment Allowance."
        ),
        hmrc_sa_box="Box 27 – Capital allowances (AIA)",
        mtd_field="capitalAllowances",
        not_advice_copy=(
            "Items costing less than £1,000 and lasting under two years are usually classed as revenue "
            "expenses. Items lasting longer may need to be capitalised — ask your accountant."
        ),
    ),
    Category(
        key="rent",
        label="Business premises / rent",
        description="Rent for a studio, workshop, or office used exclusively for your business.",
        hmrc_sa_box="Box 18 – Rent, rates, power and insurance costs",
        mtd_field="premisesCosts",
        not_advice_copy=(
            "Home-office use: claim only the portion used exclusively for business. "
            "Renting your home to your business is complex — seek professional advice."
        ),
        suspicious_warning=(
            "Rent payments to a connected party (e.g., your own company or spouse) "
            "may be challenged by HMRC unless at a market rate with a written agreement."
        ),
    ),
    Category(
        key="food_and_drink",
        label="Food & drink (business only)",
        description=(
            "Meals consumed during overnight business travel away from your normal work area. "
            "Day-to-day lunch is not allowable."
        ),
        hmrc_sa_box="Box 21 – Advertising and business entertainment costs",
        mtd_field="advertisingCosts",
        not_advice_copy=(
            "HMRC allows subsistence costs for genuine overnight business travel. "
            "Day-to-day meals are a personal expense."
        ),
        suspicious_warning=(
            "Regular food and drink claims are a common HMRC enquiry trigger. "
            "Only overnight-trip subsistence is generally allowable."
        ),
    ),
    Category(
        key="entertainment",
        label="Client entertainment",
        description=(
            "Hospitality, events, or gifts for clients. "
            "Most client entertainment is NOT tax-deductible."
        ),
        hmrc_sa_box="Box 21 – Advertising and business entertainment costs (disallowable portion)",
        mtd_field="advertisingCosts",
        not_advice_copy=(
            "HMRC does not allow a deduction for entertaining clients or customers. "
            "Staff entertainment (up to £150/head/year) may qualify — check HMRC EIM21690."
        ),
        suspicious_warning=(
            "Client entertainment is almost never an allowable deduction. "
            "Please verify this is not personal expenditure before submitting."
        ),
    ),
    Category(
        key="groceries",
        label="Groceries",
        description="Supermarket food and household items.",
        hmrc_sa_box=None,
        mtd_field=None,
        not_advice_copy=(
            "Groceries are a personal expense and are NOT deductible against business profits."
        ),
        suspicious_warning=(
            "Groceries should not appear as a business expense unless you run a catering "
            "or hospitality business. Please review this transaction."
        ),
    ),
    Category(
        key="subscriptions",
        label="Subscriptions",
        description="Regular subscription payments — could be personal or business.",
        hmrc_sa_box="Box 20 – Office costs (business subscriptions only)",
        mtd_field="officeAndAdminCosts",
        not_advice_copy=(
            "Only claim subscriptions that are wholly and exclusively for your business. "
            "Personal subscriptions (Netflix, Spotify, etc.) are not allowable."
        ),
        suspicious_warning=(
            "Please confirm this subscription is used wholly for business, not personal use."
        ),
    ),
    Category(
        key="other",
        label="Other expense",
        description="A business expense that does not fit any other category.",
        hmrc_sa_box="Box 24 – Other business expenses",
        mtd_field="otherExpenses",
        not_advice_copy=(
            "Use 'Other expense' only when no specific category applies. "
            "HMRC may query a large or unexplained 'other expenses' total."
        ),
    ),
]

# ---------------------------------------------------------------------------
# Non-deductible / personal
# ---------------------------------------------------------------------------

PERSONAL_CATEGORIES: list[Category] = [
    Category(
        key="personal",
        label="Personal (not deductible)",
        description="A personal expense that has no business element and cannot be claimed.",
        hmrc_sa_box=None,
        mtd_field=None,
    ),
]

# ---------------------------------------------------------------------------
# Convenience lookups
# ---------------------------------------------------------------------------

ALL_CATEGORIES: list[Category] = INCOME_CATEGORIES + EXPENSE_CATEGORIES + PERSONAL_CATEGORIES

_BY_KEY: dict[str, Category] = {c.key: c for c in ALL_CATEGORIES}


def get_category(key: str) -> Category | None:
    """Look up a Category by its slug key. Returns None if not found."""
    return _BY_KEY.get(key)


def get_hmrc_field(key: str) -> str | None:
    """Return the MTD ITSA submission field name for a category key."""
    cat = _BY_KEY.get(key)
    return cat.mtd_field if cat else None


def get_sa_box(key: str) -> str | None:
    """Return the SA103 box reference for a category key."""
    cat = _BY_KEY.get(key)
    return cat.hmrc_sa_box if cat else None


def export_digital_record_categories() -> list[dict]:
    """
    Export all categories in a structured format suitable for digital record-keeping.
    Returns a list of dicts compatible with HMRC MTD digital records requirements.
    """
    return [
        {
            "key": c.key,
            "label": c.label,
            "description": c.description,
            "hmrc_sa_box": c.hmrc_sa_box,
            "mtd_field": c.mtd_field,
            "is_income": c.is_income,
        }
        for c in ALL_CATEGORIES
    ]
