# CSV Import (Transactions)

## Purpose
Fallback ingestion method when a bank connection is not available.

## Endpoint
```
POST /transactions/import/csv
Content-Type: multipart/form-data
```

## Required form fields
- `account_id` (UUID)
- `file` (CSV file, UTF-8)

## Supported headers
Required:
- `date` (YYYY-MM-DD recommended)
- `description`
- `amount` (positive income, negative expense)
- `currency` (ISO 4217, e.g. GBP)

Optional:
- `provider_transaction_id`
- `category`
- `tax_category`
- `business_use_percent`

## Example
```
date,description,amount,currency,tax_category,business_use_percent
2023-10-01,Coffee,-3.50,GBP,other_expenses,100
2023-10-02,Invoice 1001,2500,GBP,turnover,100
```

## Notes
- Duplicate rows are skipped if the same provider transaction id is seen.
- If no provider id is supplied, a deterministic id is generated from row data.
