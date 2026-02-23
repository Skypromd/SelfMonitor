# Partner Data Contract v1 (Transactions Ingestion)

## Purpose
This contract defines how partner systems send transaction data into our platform
to power UK Self-Assessment workflows (SA100/SA103).

## Endpoint (internal)
```
POST /transactions/ingest/partner
Content-Type: application/json
Authorization: Bearer <token>
```

## Idempotency and de-duplication
- `provider_transaction_id` is treated as the stable unique id per account.
- Ingestion skips duplicates for the same `account_id`.
- Optional `batch_id` can be used for higher-level traceability.

## Required fields
- `schema_version`: must be `"1.0"`
- `source_system`: partner system name
- `user_reference`: partner user identifier
- `account_id`: internal account UUID
- `transactions`: array of transaction objects (see schema)

## Optional fields
- `tax_year` (e.g. `2023-04-06/2024-04-05`)
- `metadata`
- Per-transaction fields: `category`, `tax_category`, `business_use_percent`, `tags`

## Category guidance
If `tax_category` is provided, it overrides automatic mapping.
Recommended `tax_category` values (SA103 style):
- turnover
- other_business_income
- cost_of_goods
- premises
- repairs
- travel
- vehicle
- wages
- subcontractors
- legal_professional
- advertising
- office
- bank_charges
- other_expenses
- capital_allowances
- disallowable

## Example payload
```json
{
  "schema_version": "1.0",
  "source_system": "partner-app",
  "batch_id": "5b7f6b3a-2a1b-4c2f-84f4-2a30b5f0c1d2",
  "user_reference": "partner-user-42",
  "account_id": "d6f2cfb2-1c09-43d6-9b39-7d0a16c2e591",
  "tax_year": "2023-04-06/2024-04-05",
  "transactions": [
    {
      "provider_transaction_id": "txn-123",
      "date": "2024-01-03",
      "description": "Amazon Web Services",
      "amount": -125.5,
      "currency": "GBP",
      "tax_category": "office",
      "business_use_percent": 100
    },
    {
      "provider_transaction_id": "txn-124",
      "date": "2024-01-08",
      "description": "Client invoice #8821",
      "amount": 2400,
      "currency": "GBP",
      "tax_category": "turnover"
    }
  ]
}
```
