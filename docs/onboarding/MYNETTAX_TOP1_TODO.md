# MyNetTax Top-1 TODO

## North Star

**MyNetTax gets UK self-employed workers HMRC-ready in minutes, with CIS refunds tracked, evidence packaged, and guidance delivered in their language.**

This TODO turns the current MyNetTax codebase into a focused product that can compete with Sage by winning on readiness, CIS, language support, evidence, mobile UX, and self-employed mortgage readiness.

## Ground Rules

- [ ] Use **MyNetTax** as the customer-facing brand everywhere.
- [ ] Keep `SelfMonitor` only as a repository/internal legacy name unless the repository is renamed later.
- [ ] Never describe HMRC submission as unattended auto-submit.
- [ ] Use: **prepare → preview → confirm → submit**.
- [ ] Keep bank sync button-only unless the business rule is explicitly changed.
- [ ] Make every blocker actionable: each problem must open the exact fix screen.
- [ ] Treat language support as a trust feature, not just UI translation.
- [ ] Treat CIS as a lead differentiator, not a secondary report.

## Domain And Brand

### P0.0 Brand Cleanup

- [ ] Replace customer-facing `SelfMonitor` with `MyNetTax` in web landing pages.
- [ ] Replace customer-facing `SelfMonitor` with `MyNetTax` in pricing copy.
- [ ] Replace customer-facing `SelfMonitor` with `MyNetTax` in testimonials or demo copy.
- [ ] Replace customer-facing `SelfMonitor` with `MyNetTax` in billing emails.
- [x] Replace customer-facing `SelfMonitor` with `MyNetTax` in invoice PDFs and payment emails.
- [ ] Replace app-store placeholder links using `selfmonitor` package/URLs with MyNetTax placeholders.
- [ ] Update service metadata only where it is visible to customers or API docs.
- [ ] Keep internal namespace changes scoped; do not rename code packages unless needed.
- [ ] Add a brand glossary: `MyNetTax`, `SelfMate`, `Practolog`, `CIS Refund Tracker`.
- [ ] Audit all public docs for conflicting product naming.

### Domain Architecture

- [ ] Set `mynettax.app` as the primary product domain.
- [ ] Set `app.mynettax.app` as the client web app host.
- [ ] Set `api.mynettax.app` as the API gateway host.
- [ ] Set `pay.mynettax.app` as payment-link host.
- [ ] Choose admin host: `admin.mynettax.app` or `practolog.mynettax.app`.
- [ ] Set `mynettax.co.uk` as UK trust and SEO domain.
- [ ] Redirect `mynettax.com` to `mynettax.app`.
- [ ] Update CORS origins for production domains.
- [ ] Update trusted host settings for production domains.
- [ ] Update OAuth redirect URLs for HMRC, banking provider, Stripe, and mobile deep links.
- [ ] Update legal pages to use MyNetTax domains.
- [ ] Add canonical URLs for SEO pages.
- [ ] Add redirects from legacy `selfmonitor.*` references if those domains are used anywhere.

## P0 Foundation

### P0.1 Readiness Engine

- [ ] Define canonical readiness statuses: `ready`, `needs_attention`, `blocked`.
- [ ] Define financial object statuses: `unreviewed`, `needs_receipt`, `needs_split`, `needs_business_pct`, `verified`, `unverified`, `ready`.
- [ ] Add readiness blocker types for unreviewed transactions.
- [ ] Add readiness blocker types for missing receipts.
- [ ] Add readiness blocker types for missing category.
- [ ] Add readiness blocker types for missing split.
- [ ] Add readiness blocker types for missing business-use percentage.
- [ ] Add readiness blocker types for stale bank sync.
- [ ] Add readiness blocker types for CIS unverified credits.
- [ ] Add readiness blocker types for missing CIS statement.
- [ ] Add readiness blocker types for CIS bank mismatch.
- [ ] Add readiness blocker types for HMRC fraud client context missing.
- [ ] Add readiness blocker types for missing MTD obligation data.
- [ ] Add readiness blocker types for VAT eligibility or VAT return prep where Pro+ applies.
- [ ] Add a backend response contract for quarter readiness.
- [ ] Add stable blocker IDs for deep-linking.
- [ ] Add blocker severity: `info`, `attention`, `blocking`.
- [ ] Add blocker impact: readiness points or estimated completion gain.
- [ ] Add blocker action metadata: label, route, payload, estimated time.
- [ ] Add test fixtures for readiness with mixed blockers.
- [ ] Add API tests for readiness blocker generation.

### P0.2 Transaction Inbox Zero

- [ ] Make Transaction Inbox the main financial workbench.
- [x] Add filters by readiness status.
- [ ] Add filters by tax period.
- [x] Add filters by transaction type: income, expense, CIS, receipt draft.
- [ ] Add “fastest readiness gain” sorting.
- [ ] Add “needs receipt” queue.
- [ ] Add “needs category” queue.
- [ ] Add “needs business %” queue.
- [ ] Add “needs split” queue.
- [ ] Add “possible CIS income” queue.
- [x] Add quick action: mark personal.
- [x] Add quick action: mark business.
- [x] Add quick action: set business-use percentage.
- [ ] Add quick action: attach receipt.
- [ ] Add quick action: split transaction.
- [ ] Add quick action: create recurring rule.
- [ ] Add quick action: ignore receipt draft candidate.
- [x] Add bulk review mode.
- [x] Add weekly Inbox Zero metric.
- [ ] Add empty state that celebrates completion without sounding childish.
- [ ] Add keyboard/mobile-friendly review flow.
- [ ] Add tests for transaction status transitions.

### P0.3 Quarter Readiness Console

- [ ] Create quarter readiness screen.
- [ ] Show status: Ready / Needs attention / Blocked.
- [ ] Show current tax quarter and due date.
- [ ] Show MTD obligation status.
- [ ] Show readiness score.
- [ ] Show blocker groups.
- [ ] Show “Fix in 5 minutes” button.
- [ ] Generate Today list from top blockers.
- [ ] Show estimated time per task.
- [ ] Show improvement impact per task.
- [ ] Show missing bank sync warning.
- [ ] Show missing receipts count.
- [ ] Show unreviewed transaction count.
- [ ] Show missing category/split/business % count.
- [ ] Show CIS verified/unverified summary.
- [ ] Show direct/guided/simulation HMRC mode status.
- [ ] Show HMRC operational readiness where relevant.
- [ ] Add mobile version of readiness console.
- [ ] Add empty state for fully ready quarter.
- [ ] Add tests for readiness score and blocker display.

### P0.4 Preview, Confirm, Submit

- [ ] Build MTD quarterly draft preview.
- [ ] Show turnover.
- [ ] Show expenses.
- [ ] Show profit.
- [ ] Show estimated tax due.
- [ ] Show tax reserve suggestion.
- [ ] Show category summary.
- [ ] Show CIS credits summary.
- [ ] Show verified CIS credits.
- [ ] Show unverified CIS credits.
- [ ] Show missing evidence warning.
- [ ] Show direct vs guided/simulation mode.
- [x] Require "true and complete" acknowledgement before submit.
- [ ] Require extra acknowledgement if CIS credits are unverified.
- [ ] Wire existing confirmation-token flow into tax submit UX.
- [ ] Generate and store preview fingerprint.
- [ ] Store confirmed timestamp.
- [ ] Store submit receipt reference.
- [ ] Store submission history.
- [ ] Show retrying state for transient HMRC failures.
- [ ] Show clear error messages for OAuth, 429, 5xx and timeout.
- [ ] Show direct-to-simulation fallback notice if fallback is enabled.
- [ ] Add audit events for preview, confirmation and submit.
- [ ] Add tests for confirmation and duplicate submit prevention.

### P0.5 Reliability And Trust UX

- [ ] Standardize user-facing API error copy.
- [ ] Add retry indicators for HMRC submit.
- [ ] Add retry indicators for bank sync.
- [ ] Add retry indicators for OCR processing.
- [ ] Add transparent fallback messaging.
- [ ] Add operational readiness surface for HMRC.
- [ ] Add “last successful sync” display.
- [ ] Add “last successful submission” display.
- [ ] Add audit trail access for user-visible actions.
- [ ] Add security copy that is specific and verifiable.

## P1-A MTD ITSA

### Obligations First

- [x] Add "Your Deadlines" screen.
- [x] Show period start.
- [x] Show period end.
- [x] Show due date.
- [x] Show obligation status: Open / Fulfilled / Overdue.
- [x] Show days until deadline.
- [x] Link each deadline to quarter readiness.
- [ ] Add reminders for 14, 7, 3 and 1 day windows.
- [ ] Suppress reminders when already submitted.
- [ ] Add urgent pending reminder 24h before deadline.
- [ ] Add mobile push copy for deadlines.
- [ ] Add email copy for deadlines.

### Category Mapping

- [ ] Define plain-language self-employed categories.
- [ ] Map UI categories to HMRC/SA/MTD fields.
- [ ] Add “why this category” explanation.
- [ ] Add guidance warning for suspicious categories.
- [ ] Add “not advice” copy where needed.
- [ ] Add category mapping tests.
- [ ] Add export of digital record categories.

### Tax Reserve

- [x] Calculate profit-to-date.
- [x] Calculate estimated tax reserve.
- [x] Include CIS deductions in reserve estimate.
- [ ] Add weekly reserve suggestion.
- [ ] Add confidence level: low / medium / high.
- [ ] Explain reserve changes: profit up, expenses down, quarter changed, CIS credited.
- [x] Add reserve widget to dashboard.
- [ ] Add reserve widget to quarter preview.

### 7-Minute Quarterly Wizard

- [x] Step 1: Sync bank.
- [x] Step 2: Fix Inbox blockers.
- [x] Step 3: Review receipts and CIS.
- [x] Step 4: Preview quarterly update.
- [x] Step 5: Confirm.
- [x] Step 6: Submit or save guided package.
- [x] Show estimated time on each step.
- [x] Show blockers per step.
- [x] Allow resume later.
- [x] Add completion celebration with receipt reference.

## P1-B CIS Wedge

### CIS Control Center

- [x] Make CIS Refund Tracker visible in primary navigation.
- [ ] Add homepage section for CIS subcontractors.
- [x] Show UK tax month x contractor table.
- [ ] Show statuses: Matched, Mismatch, Missing statement, Unverified, Not CIS.
- [x] Add filter: only problems.
- [x] Add filter: unverified credits.
- [x] Add filter: missing statements.
- [ ] Add contractor grouping.
- [ ] Add refund estimate summary.
- [ ] Add total verified deductions.
- [ ] Add total unverified deductions.
- [ ] Add next action per row.

### CIS Statement Ingest

- [x] Add upload flow for CIS statement PDF/photo.
- [x] Parse contractor name.
- [x] Parse period start and end.
- [x] Parse gross total.
- [x] Parse materials total.
- [x] Parse CIS deducted total.
- [x] Parse net paid total.
- [ ] Link statement to contractor and tax month.
- [x] Show OCR confidence.
- [x] Require review when confidence is low.
- [x] Store document reference on CIS record.
- [ ] Add tests for statement parsing edge cases.

### CIS Bank Reconciliation

- [ ] Auto-match statement net paid to bank transactions.
- [ ] Show why a match succeeded.
- [ ] Show why a mismatch happened.
- [ ] Add manual matching UI.
- [ ] Support multiple bank transaction matches.
- [ ] Mark reconciliation status `matched`.
- [ ] Mark reconciliation status `needs_review`.
- [ ] Mark reconciliation status `missing_bank_transaction`.
- [ ] Add tolerance rules for rounding.
- [ ] Add tests for matching and mismatch.

### CIS Gating And Evidence

- [ ] Show CIS disclosure in quarterly preview.
- [ ] Allow unverified credits with explicit acknowledgement.
- [x] Watermark unverified CIS in evidence pack.
- [ ] Generate "what to upload to become verified" report.
- [ ] Add accountant-facing CIS evidence summary.
- [x] Add share token for accountant evidence pack.
- [ ] Add audit events for CIS classification.
- [ ] Add audit events for statement upload.
- [ ] Add audit events for shared evidence download.

### CIS Reminders

- [x] Keep 72h hard throttle.
- [x] Keep 2 per 7 days soft throttle.
- [ ] Add reminder copy for requesting statement from contractor/client.
- [ ] Add snooze 7, 14, 30 days.
- [ ] Add reminder sent log.
- [ ] Add mobile push reminder.
- [ ] Add email reminder.

## P1-C Language Advantage

### Localization Coverage

- [ ] Confirm priority languages: EN, PL, RO, UK, RU, ES, IT, PT, TR, BN.
- [x] Remove raw translation keys from visible UI.
- [ ] Localize onboarding.
- [ ] Localize dashboard.
- [ ] Localize Transaction Inbox.
- [ ] Localize Quarter Readiness.
- [ ] Localize CIS Control Center.
- [ ] Localize receipt review.
- [ ] Localize MTD preview.
- [ ] Localize confirmation and warning copy.
- [ ] Localize error messages.
- [ ] Localize emails and push notifications.
- [ ] Add translation completeness checks.

### Multilingual Tax Guidance

- [ ] Write plain-language MTD explanation per language.
- [ ] Write plain-language CIS explanation per language.
- [ ] Write plain-language VAT explanation per language.
- [ ] Preserve key HMRC/legal terms in English where needed.
- [ ] Add “guidance, not advice” translation per language.
- [ ] Add language-specific onboarding examples.

### AI And Voice

- [ ] Allow assistant questions in supported languages.
- [ ] Add mode for “explain this blocker”.
- [ ] Add mode for “explain this category”.
- [ ] Add mode for “what do I need before submitting?”.
- [ ] Add voice expense capture in supported languages.
- [ ] Convert voice expense to draft transaction.
- [ ] Add review before saving voice-created transaction.
- [ ] Add tests for multilingual expense intent parsing.

### SEO By Language

- [ ] Create `mynettax.co.uk/mtd-income-tax`.
- [ ] Create `mynettax.co.uk/cis-refund-tracker`.
- [ ] Create `mynettax.co.uk/self-employed-tax`.
- [ ] Create `mynettax.co.uk/mortgage-readiness`.
- [ ] Create Polish landing pages for MTD/CIS/self-employed tax.
- [ ] Create Romanian landing pages for MTD/CIS/self-employed tax.
- [ ] Create Ukrainian landing pages for MTD/CIS/self-employed tax.
- [ ] Add hreflang and canonical tags.
- [ ] Add localized CTAs into app registration.

## P1-D Sage Parity And Differentiation

### Must Not Fall Behind

- [ ] Bank connection must be simple and reliable.
- [ ] Bank sync must show imported count.
- [ ] Bank sync must show last sync time.
- [x] Bank sync must show tier limits.
- [x] Bank sync must show next available sync.
- [ ] Receipt scan must be faster than manual entry.
- [ ] Invoices must remain easy to create and send.
- [x] Export CSV/PDF must be easy to find.
- [ ] VAT Pro+ flow must be clearly positioned.
- [x] MTD obligations must be accurate.
- [ ] HMRC fraud context must be handled correctly.
- [ ] Pricing must be clear and credible.
- [ ] Legal pages must be production-ready.

### Where MyNetTax Must Win

- [x] CIS refund tracking must be more user-friendly than Sage CIS workflows.
- [x] Quarter readiness must feel easier than accounting dashboards.
- [ ] Language support must be visible before signup.
- [ ] Mobile receipt and voice flows must feel native and fast.
- [x] Evidence pack must feel professional enough for accountants.
- [x] Mortgage readiness must connect tax records to life goals.
- [ ] AI must answer around the user’s actual blockers, not generic tax questions only.

## P2 Evidence Pack And Accountant Layer

- [ ] Build quarter evidence pack PDF.
- [x] Build quarter evidence pack ZIP.
- [ ] Include transaction summary.
- [ ] Include category summary.
- [ ] Include receipts list.
- [ ] Include missing receipts list.
- [x] Include CIS records.
- [ ] Include CIS statements list.
- [x] Include unverified CIS watermark.
- [ ] Include readiness summary.
- [ ] Include MTD preview fingerprint.
- [ ] Include submission receipt reference.
- [ ] Include audit trail.
- [x] Add accountant share token.
- [x] Add token expiry.
- [ ] Add shared download audit event.
- [x] Add Growth/Pro/Business gating for pack features.

## P2 Mobile Wow

- [ ] Make Receipt Scan a primary mobile action.
- [ ] Make Bank Sync a primary mobile action.
- [ ] Make Quarter Readiness a primary mobile card.
- [ ] Make CIS missing statement prompt mobile-friendly.
- [ ] Add offline-safe draft capture for expenses.
- [ ] Add haptics only where useful.
- [ ] Add push actions that deep-link to exact blocker.
- [ ] Add biometric lock copy with MyNetTax branding.
- [ ] Add app-store screenshots around MTD, CIS, receipts and languages.

## P3 Mortgage Growth Loop

- [x] Connect tax estimate to mortgage readiness.
- [x] Connect bank history to mortgage readiness.
- [x] Connect evidence pack to broker bundle.
- [x] Add multilingual mortgage readiness explanation.
- [x] Add broker bundle CTA.
- [ ] Add `.co.uk` SEO page for self-employed mortgage readiness.
- [x] Add "Road to mortgage" dashboard card.
- [ ] Add monthly mortgage progress digest.
- [ ] Add partner broker marketplace backlog.

## VAT Backlog

- [ ] Keep VAT positioned as Pro+.
- [ ] Do not make VAT the lead wedge before P0/P1 are polished.
- [ ] Add VAT obligations page when MTD/CIS readiness is stable.
- [ ] Add VAT prepare/preview/confirm/submit flow.
- [ ] Add non-VAT to VAT migration path.
- [ ] Add VAT evidence pack extension.

## Go-To-Market

### Website

- [ ] Rebuild homepage around MyNetTax, not SelfMonitor.
- [ ] Above the fold: MTD readiness + CIS refunds + language support.
- [ ] Add Sage comparison page without aggressive claims.
- [ ] Add CIS subcontractor landing page.
- [ ] Add MTD ITSA landing page.
- [ ] Add multilingual community landing pages.
- [ ] Add mortgage readiness landing page.
- [ ] Add pricing page aligned with current tiers.
- [ ] Add trust badges only if verifiable.

### Pricing And Packaging

- [ ] Free: manual entry, dashboard, basic tax calculator.
- [ ] Starter: CIS tracker, guided MTD, one bank sync tier.
- [ ] Growth: more history, evidence pack basics, accountant share.
- [ ] Pro: direct HMRC/fraud context, VAT, richer evidence pack.
- [ ] Business: higher limits, team/accountant workflows.
- [ ] Make CIS value visible in every paid tier.
- [ ] Make direct HMRC limitations clear by plan.
- [ ] Avoid overpromising “HMRC recognised” unless officially true.

### SEO Topics

- [ ] “MTD for Income Tax self-employed”.
- [ ] “CIS refund tracker”.
- [ ] “CIS statement missing”.
- [ ] “Self-employed tax app UK”.
- [ ] “Polish self-employed tax UK”.
- [ ] “Romanian self-employed tax UK”.
- [ ] “Ukrainian self-employed tax UK”.
- [ ] “Self-employed mortgage readiness UK”.
- [ ] “CIS deductions evidence”.
- [ ] “Quarterly tax update app”.

## Compliance And Release

- [ ] Verify HMRC wording across site.
- [ ] Verify fraud prevention headers and client context flow.
- [ ] Verify direct submission only available on correct plans.
- [ ] Verify guided MTD fallback for lower tiers.
- [ ] Verify VAT Pro+ gating.
- [ ] Verify CIS evidence pack access by tier.
- [ ] Verify audit events for sensitive actions.
- [ ] Verify no secrets in public repo.
- [ ] Verify production CORS.
- [ ] Verify firewall and internal ports.
- [ ] Verify data retention language.
- [ ] Verify GDPR/ICO-ready pages.
- [ ] Verify App Store privacy copy.
- [ ] Verify Play Store data safety copy.

## Product Metrics

- [ ] Weekly Inbox Zero completion rate.
- [ ] Quarter readiness completion rate.
- [ ] Average blockers per user.
- [ ] Median time to ready quarter.
- [ ] Receipt OCR success rate.
- [ ] Receipt match rate.
- [ ] CIS statements uploaded per active CIS user.
- [ ] CIS verified credits percentage.
- [ ] CIS evidence pack downloads.
- [ ] MTD preview-to-confirm conversion.
- [ ] Confirm-to-submit completion.
- [ ] HMRC submit success rate.
- [ ] Direct-to-simulation fallback count.
- [ ] Language selected at signup.
- [ ] Non-English activation rate.
- [ ] Mortgage bundle downloads.
- [ ] Paid conversion by wedge: CIS, MTD, mortgage, language.

## Immediate Sprint: First 14 Days

- [ ] Audit visible brand strings.
- [ ] Replace visible SelfMonitor with MyNetTax.
- [ ] Replace “auto-submission” with guided MTD wording.
- [ ] Define production domain map.
- [ ] Update env examples for domains.
- [ ] Make CIS Refund Tracker visible in navigation.
- [ ] Add CIS section to homepage.
- [ ] Draft Quarter Readiness API contract.
- [ ] Draft readiness blocker schema.
- [ ] Draft Today list prioritization rules.
- [ ] Draft MyNetTax homepage messaging.
- [ ] Draft `.co.uk` SEO page structure.

## Next 30 Days

- [ ] Build Quarter Readiness Console MVP.
- [ ] Build Today list MVP.
- [ ] Upgrade Transaction Inbox filters.
- [ ] Add fastest-readiness sorting.
- [ ] Add CIS Control Center polish.
- [ ] Add statement upload review flow.
- [ ] Add MTD preview/confirm UX wiring.
- [ ] Add tax reserve widget.
- [ ] Add localized onboarding baseline.
- [ ] Add initial `.co.uk` MTD and CIS pages.

## Next 60 Days

- [ ] Build Evidence Pack v1.
- [ ] Add accountant share token UX.
- [ ] Add mobile CIS and readiness polish.
- [ ] Add multilingual AI blocker explanation.
- [ ] Add voice expense draft flow.
- [ ] Add mortgage broker bundle CTA.
- [ ] Add Sage comparison landing.
- [ ] Add language community SEO pages.
- [ ] Add product metrics dashboard.
- [ ] Prepare launch checklist for `mynettax.app`.

## Definition Of Top-1 Candidate

- [ ] User can connect/sync bank and understand limits.
- [ ] User can reach Inbox Zero.
- [ ] User can see quarter readiness in one screen.
- [ ] User can fix top blockers in under 5 minutes.
- [ ] User can preview MTD update in plain language.
- [ ] User can explicitly confirm and submit or save guided package.
- [ ] CIS user can see refund tracker and evidence status.
- [ ] CIS user can upload statement and reconcile with bank.
- [ ] User can export evidence pack for accountant.
- [ ] User can use the product in their language.
- [ ] User can understand next mortgage-readiness step.
- [ ] Product copy is consistent as MyNetTax.
- [ ] Production domains are aligned.
- [ ] Sage comparison is clear: MyNetTax wins on self-employed readiness, CIS, language, mobile and mortgage path.
