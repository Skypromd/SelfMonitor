# HMRC Reports Catalog (Draft - Needs HMRC Confirmation)

## Purpose
This document lists report types and submission artifacts needed for UK Self-Assessment
for sole traders. It is a draft and must be verified against HMRC guidance.

## Scope (Draft)
### Self-Assessment core
- SA100 (Self Assessment tax return)
- SA103S/SA103F (Self-employment short/full)
- Class 2 & Class 4 NIC calculation
- Payments on account

### MTD ITSA (if applicable)
- Quarterly updates
- EOPS (End of Period Statement)
- Final Declaration

## Internal user-facing reports (Product)
These are the reports shown in the app to help the user prepare:
- Monthly summary (income/expenses, categories)
- Quarterly summary (if required)
- Profit & Loss (P&L)
- Tax-year summary
- Mortgage readiness (PDF)
- Evidence pack (receipts, invoices, ledger)

## Submission artifacts (Draft)
For HMRC submission, the system should produce:
- SA103 category totals
- Tax-year totals with adjustments
- NIC calculations
- Declaration confirmation

## Frequency rules (Draft)
- Monthly close for user workflow.
- Quarterly updates if turnover exceeds HMRC threshold.
- Annual final submission.

## Known gaps (Needs HMRC confirmation)
- Exact thresholds for quarterly reporting.
- Exact SA103S vs SA103F conditions.
- Mandatory fields and validation rules per HMRC API.
- MTD ITSA specific payload requirements.

## Next steps
1. Confirm HMRC official requirements and thresholds.
2. Replace draft rules with confirmed guidance.
3. Map each report to API endpoints and schemas.
