# Product Requirements Document (PRD): MVP UK Launch

**Version:** 0.1 (Draft)
**Owner:** Product Lead

## 1. Introduction

This document outlines the requirements for the Minimum Viable Product (MVP) of our automated accounting and tax preparation platform for UK-based freelancers and self-employed individuals.

**Vision:** To simplify financial management for the self-employed by automating transaction categorization, receipt management, and tax estimation.

## 2. Goals & Objectives

### Business Goals
-   Validate the core value proposition with a small group of test users.
-   Establish a baseline for OCR accuracy and transaction categorization.
-   Achieve an end-to-end user flow from onboarding to a simple tax data export.

### User Problems to Solve
-   "I find it hard to keep track of my business expenses."
-   "I'm not sure which expenses are tax-deductible."
-   "I waste a lot of time manually organizing my receipts and transactions at the end of the tax year."

## 3. Scope & Features

The MVP will focus on the following core user journey:

1.  **Onboarding:** User registers and creates an account (`auth-service`).
2.  **Bank Connection:** User connects their UK bank account via an Open Banking provider (`banking-connector`, `consent-service`).
3.  **Transaction Sync:** The system imports and de-duplicates transactions from the connected bank (`transactions-service`).
4.  **Document Upload:** User uploads a receipt/invoice for an expense (`documents-service`).
5.  **Data Extraction (PoC):** The system performs OCR on the uploaded document to extract key details (vendor, amount, date).
6.  **Simple Export:** User can export their processed transactions as a CSV file, ready for their accountant.

## 4. User Stories

| ID | As a... | I want to... | So that I can... | Services Involved |
|----|---|---|---|---|
| US-01 | New User | Register for an account using my email and a password | Securely access the application | `auth-service` |
| US-02 | Registered User | Connect my bank account through a secure portal | Automatically import my transactions | `banking-connector`, `consent-service` |
| US-03 | Connected User | See a list of all my imported bank transactions | Get an overview of my financial activity | `transactions-service` |
| US-04 | Connected User | Upload a photo of a receipt | Keep a digital record of my expenses | `documents-service` |
| US-05 | Connected User | Have the system automatically read the details from my uploaded receipt | Save time on manual data entry | `documents-service`, `analytics-service` (future) |
| US-06 | Connected User | Export a list of my transactions for a specific period to a CSV file | Easily share my financial data with my accountant | `transactions-service` |


## 5. Non-Functional Requirements

-   **Security:** All user data must be encrypted at rest and in transit. The `consent-service` must provide an audit trail.
-   **Data Residency:** All user data must be stored within the UK.
-   **Performance:** The bank connection and transaction import should complete within a reasonable timeframe (TBD).

## 6. Out of Scope for MVP

-   Automated tax submission to HMRC.
-   Multi-language support.
-   Advanced financial advice (`advice-service`).
-   ML-based automatic transaction categorization (categorization will be manual or based on simple rules).
