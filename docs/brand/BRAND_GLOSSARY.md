# MyNetTax Brand Glossary

This glossary defines canonical product names for all customer-facing and partner-facing copy.

## Product Names

| Term | Usage |
|------|-------|
| **MyNetTax** | Primary product brand. Use everywhere customers see the product name. |
| **SelfMate** | AI assistant feature within MyNetTax. Use in AI-related features, chat UI, and marketing. |
| **Practolog** | Operator/accountant portal. Use for the admin subdomain and practitioner-facing UI only. |
| **CIS Refund Tracker** | Feature name for the Construction Industry Scheme refund tracking module. Always capitalised as shown. |

## Domain Architecture

| Domain | Purpose |
|--------|---------|
| `mynettax.app` | Primary product domain |
| `app.mynettax.app` | Client-facing web app |
| `api.mynettax.app` | API gateway |
| `pay.mynettax.app` | Payment link host |
| `practolog.mynettax.app` | Operator/accountant portal |
| `mynettax.co.uk` | UK trust and SEO domain |

## Repository / Internal Names

- Repository: `SelfMonitor` (internal legacy name — do not use in customer-facing copy)
- Internal Python packages: keep existing namespaces (`selfmonitor.*`) unless renaming adds clear value

## Copy Rules

- Never describe HMRC submission as "auto-submit" or "automated submission". Use: **prepare → preview → confirm → submit**
- Bank sync is button-only. Never imply background or automatic sync.
- Mortgage readiness is informational only. Always include: "This is guidance, not financial advice."
- AI assistant answers are general guidance only. Always include: "This is not professional tax or legal advice."
- All feature explanations must be available in: EN, PL, RO, UK, RU, ES, IT, PT, TR, BN

## App Store References

| Store | Package / Bundle ID |
|-------|---------------------|
| Google Play | `com.mynettax.app` |
| Apple App Store | `com.mynettax.app` |
