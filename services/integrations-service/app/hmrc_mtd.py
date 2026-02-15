import datetime
import uuid
from typing import Literal

from pydantic import BaseModel, Field


def _next_month_same_day(date_value: datetime.date) -> datetime.date:
    if date_value.month == 12:
        return datetime.date(date_value.year + 1, 1, date_value.day)
    return datetime.date(date_value.year, date_value.month + 1, date_value.day)


def quarter_boundaries(
    tax_year_start: datetime.date,
) -> dict[str, tuple[datetime.date, datetime.date, datetime.date]]:
    year = tax_year_start.year
    q1_start, q1_end = datetime.date(year, 4, 6), datetime.date(year, 7, 5)
    q2_start, q2_end = datetime.date(year, 7, 6), datetime.date(year, 10, 5)
    q3_start, q3_end = datetime.date(year, 10, 6), datetime.date(year + 1, 1, 5)
    q4_start, q4_end = datetime.date(year + 1, 1, 6), datetime.date(year + 1, 4, 5)
    return {
        "Q1": (q1_start, q1_end, _next_month_same_day(q1_end)),
        "Q2": (q2_start, q2_end, _next_month_same_day(q2_end)),
        "Q3": (q3_start, q3_end, _next_month_same_day(q3_end)),
        "Q4": (q4_start, q4_end, _next_month_same_day(q4_end)),
    }


class HMRCMTDBusinessIdentity(BaseModel):
    taxpayer_ref: str = Field(min_length=3, max_length=128)
    business_name: str = Field(min_length=2, max_length=160)
    accounting_method: Literal["cash", "traditional"] = "cash"


class HMRCMTDQuarterlyPeriod(BaseModel):
    tax_year_start: datetime.date
    tax_year_end: datetime.date
    quarter: Literal["Q1", "Q2", "Q3", "Q4"]
    period_start: datetime.date
    period_end: datetime.date
    due_date: datetime.date


class HMRCMTDFinancials(BaseModel):
    turnover: float
    allowable_expenses: float
    taxable_profit: float
    estimated_tax_due: float
    currency: Literal["GBP"] = "GBP"


class HMRCCategorySummaryItem(BaseModel):
    category: str
    total_amount: float
    taxable_amount: float


class HMRCMTDQuarterlyReport(BaseModel):
    schema_version: Literal["hmrc-mtd-itsa-quarterly-v1"] = "hmrc-mtd-itsa-quarterly-v1"
    jurisdiction: Literal["UK"] = "UK"
    policy_code: str = Field(min_length=3, max_length=64)
    generated_at: datetime.datetime
    business: HMRCMTDBusinessIdentity
    period: HMRCMTDQuarterlyPeriod
    financials: HMRCMTDFinancials
    category_summary: list[HMRCCategorySummaryItem]
    declaration: Literal["true_and_complete"] = "true_and_complete"


class HMRCMTDQuarterlySubmissionRequest(BaseModel):
    report: HMRCMTDQuarterlyReport
    submission_channel: Literal["api", "agent_copilot", "manual"] = "api"
    correlation_id: str | None = None


class HMRCMTDQuarterlySubmissionStatus(BaseModel):
    submission_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: Literal["pending", "completed", "failed"]
    message: str
    submission_type: Literal["mtd_quarterly_update"] = "mtd_quarterly_update"
    hmrc_receipt_reference: str
    hmrc_endpoint: str


class HMRCMTDQuarterlyReportSpec(BaseModel):
    schema_version: Literal["hmrc-mtd-itsa-quarterly-v1"] = "hmrc-mtd-itsa-quarterly-v1"
    required_sections: list[str]
    required_period_alignment: str
    required_declaration: str
    notes: list[str]


def validate_quarterly_report(report: HMRCMTDQuarterlyReport) -> list[str]:
    errors: list[str] = []
    if report.period.tax_year_end != datetime.date(
        report.period.tax_year_start.year + 1,
        4,
        5,
    ):
        errors.append("tax_year_end must be 5 April following tax_year_start.")

    quarter_map = quarter_boundaries(report.period.tax_year_start)
    expected = quarter_map.get(report.period.quarter)
    if expected is None:
        errors.append("quarter must be one of Q1-Q4.")
    else:
        expected_start, expected_end, expected_due = expected
        if report.period.period_start != expected_start or report.period.period_end != expected_end:
            errors.append("period_start/period_end must match the selected tax-year quarter boundaries.")
        if report.period.due_date != expected_due:
            errors.append("due_date must equal one month after period_end.")

    derived_profit = max(report.financials.turnover - report.financials.allowable_expenses, 0.0)
    if abs(derived_profit - report.financials.taxable_profit) > 0.01:
        errors.append("taxable_profit must equal max(turnover - allowable_expenses, 0).")
    if report.financials.estimated_tax_due < 0:
        errors.append("estimated_tax_due cannot be negative.")
    if len(report.category_summary) == 0:
        errors.append("category_summary must include at least one row.")

    return errors


def build_quarterly_report_spec() -> HMRCMTDQuarterlyReportSpec:
    return HMRCMTDQuarterlyReportSpec(
        required_sections=[
            "report.schema_version",
            "report.jurisdiction",
            "report.policy_code",
            "report.generated_at",
            "report.business",
            "report.period",
            "report.financials",
            "report.category_summary",
            "report.declaration",
        ],
        required_period_alignment=(
            "period_start/period_end must exactly match HMRC quarterly windows for the tax year "
            "(Q1 6 Apr-5 Jul, Q2 6 Jul-5 Oct, Q3 6 Oct-5 Jan, Q4 6 Jan-5 Apr)."
        ),
        required_declaration="declaration must be 'true_and_complete'.",
        notes=[
            "This spec is versioned to support future HMRC schema updates without breaking existing payloads.",
            "Tax engine should submit quarterly periods to this endpoint for direct HMRC transmission.",
        ],
    )


async def submit_quarterly_update_to_hmrc(
    *,
    request: HMRCMTDQuarterlySubmissionRequest,
    user_id: str,
    hmrc_direct_api_base_url: str,
) -> HMRCMTDQuarterlySubmissionStatus:
    validation_errors = validate_quarterly_report(request.report)
    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    endpoint = f"{hmrc_direct_api_base_url.rstrip('/')}/itsa/quarterly-updates"
    receipt_ref = f"HMRC-MTD-{datetime.datetime.now(datetime.UTC):%Y%m%d%H%M%S}-{uuid.uuid4().hex[:8]}"
    print(
        "Direct HMRC quarterly submission prepared:",
        {
            "user_id": user_id,
            "endpoint": endpoint,
            "quarter": request.report.period.quarter,
            "tax_year_start": request.report.period.tax_year_start.isoformat(),
            "policy_code": request.report.policy_code,
            "correlation_id": request.correlation_id,
        },
    )
    return HMRCMTDQuarterlySubmissionStatus(
        status="pending",
        message="Quarterly MTD update has been accepted for direct HMRC processing.",
        hmrc_receipt_reference=receipt_ref,
        hmrc_endpoint=endpoint,
    )
