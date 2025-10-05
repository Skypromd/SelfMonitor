# Data Protection Impact Assessment (DPIA) Template

**Project/System Name:** [Your Project Name]
**Date:** [Date]
**DPO (Data Protection Officer):** [DPO Name]

## Step 1: Identify the need for a DPIA

-   **Describe the nature of the processing:** What are you planning to do with personal data?
    > (Example: The project involves processing personal financial data obtained via Open Banking APIs. This includes transaction history, account details, and personal identifiers. The data will be used to provide automated accounting and tax estimation services.)

-   **Why is this processing necessary?**
    > (Example: To deliver the core functionality of the product, which is to simplify financial management for freelancers.)

## Step 2: Describe the processing

-   **Nature of the data:** What types of personal data are involved? (e.g., financial, identity, contact). Is any special category data involved?
-   **Data sources:** Where will the data come from? (e.g., directly from the user, from Open Banking providers).
-   **Data lifecycle:** How will data be collected, stored, used, shared, and deleted?
    -   **Collection:** `auth-service` (email), `banking-connector` (financial data).
    -   **Storage:** AWS RDS (PostgreSQL) in `eu-west-2` region. `documents-service` uses AWS S3.
    -   **Retention:** How long will data be kept? (e.g., 7 years for tax purposes).
    -   **Deletion:** How will data be securely deleted upon user request or after the retention period?

## Step 3: Consultation process

-   Have you consulted with the DPO?
-   Have you consulted with data subjects or their representatives?

## Step 4: Assess necessity and proportionality

-   What is the lawful basis for processing? (e.g., Consent, Contract).
    > `consent-service` is used to obtain and manage explicit consent for Open Banking data access.

## Step 5: Identify and assess risks

| Risk Description | Likelihood (Low/Med/High) | Impact (Low/Med/High) | Existing Controls | Residual Risk |
|---|---|---|---|---|
| Unauthorised access to financial data due to a data breach. | Med | High | - Data encrypted at rest (AWS KMS) and in transit (TLS 1.2+)<br>- Short-lived access tokens for Open Banking<br>- Strict access control policies (IAM) | Low |
| Incorrect tax calculation due to data processing error. | Med | Med | - Unit and integration tests for `tax-engine`<br>- Clear disclaimers that advice is non-regulated. | Low |
| Failure to correctly revoke consent and delete data. | Low | High | - `consent-service` provides an immutable audit log (`compliance-service`).<br>- Automated DSAR and data deletion workflows. | Low |

## Step 6: Identify measures to reduce risk

-   Based on the risks identified, what additional measures will be implemented?
    -   Regular third-party penetration testing.
    -   Implementation of a formal incident response plan.
    -   Staff training on data protection principles.

## Step 7: Sign off and record outcomes

**DPO Assessment & Signature:**
...

**Project Lead Signature:**
...
