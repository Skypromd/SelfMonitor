import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function TermsPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main} style={{ maxWidth: 800 }}>
        <h1 className={styles.title}>Terms of Service</h1>
        <p className={styles.description}>
          These terms govern your use of the MyNetTax platform and services.
        </p>

        <section className={styles.subContainer}>
          <h2>1. Introduction and Acceptance</h2>
          <p>
            These Terms of Service (&quot;Terms&quot;) constitute a legally binding agreement between
            you (&quot;User&quot;, &quot;you&quot;, or &quot;your&quot;) and MyNetTax Ltd, a company registered in
            England and Wales (&quot;MyNetTax&quot;, &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;). By creating an
            account, accessing, or using the MyNetTax platform (including the web portal at
            mynettax.co.uk, mobile applications, and APIs), you agree to be bound by these Terms.
          </p>
          <p>
            If you do not agree to these Terms, you must not access or use the Service.
            We recommend that you also read our{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>,{' '}
            <Link className={styles.link} href="/cookies">Cookie Policy</Link>, and{' '}
            <Link className={styles.link} href="/eula">End User License Agreement</Link>.
          </p>

          <h2>2. Service Description</h2>
          <p>
            MyNetTax is a financial management platform designed for self-employed individuals,
            freelancers, and sole traders in the United Kingdom. The Service provides the following
            features:
          </p>
          <ul>
            <li>
              <strong>Tax Filing and HMRC Submissions:</strong> Tools to calculate, prepare, and
              submit Self Assessment tax returns and Making Tax Digital (MTD) for Income Tax
              Self Assessment (ITSA) quarterly updates to HM Revenue &amp; Customs (HMRC).
            </li>
            <li>
              <strong>Invoicing:</strong> Creation, management, and tracking of professional invoices
              for your clients.
            </li>
            <li>
              <strong>Mortgage Readiness:</strong> Financial health indicators and reports designed
              to help self-employed individuals prepare mortgage applications.
            </li>
            <li>
              <strong>Bank Synchronisation:</strong> Read-only connection to your bank accounts via
              Open Banking (through our authorised provider, SaltEdge) to import transactions.
            </li>
            <li>
              <strong>AI Assistant:</strong> An artificial intelligence assistant that provides
              general guidance on tax categories, expense classification, and financial queries.
            </li>
            <li>
              <strong>Financial Reporting and Analytics:</strong> Dashboards, profit and loss
              statements, and business intelligence tools.
            </li>
            <li>
              <strong>Document Management:</strong> Secure storage and organisation of receipts,
              invoices, and financial documents.
            </li>
          </ul>

          <h2>3. Eligibility</h2>
          <p>To use MyNetTax, you must:</p>
          <ul>
            <li>Be at least 18 years of age;</li>
            <li>Be a resident of the United Kingdom;</li>
            <li>
              Be self-employed, a sole trader, a freelancer, or otherwise have a legitimate need
              for self-employment financial management tools;
            </li>
            <li>Have the legal capacity to enter into a binding contract; and</li>
            <li>
              Not be prohibited from using the Service under any applicable law or regulation.
            </li>
          </ul>
          <p>
            By registering, you represent and warrant that all information you provide is accurate,
            current, and complete.
          </p>

          <h2>4. Account Registration and Security</h2>
          <p>
            4.1. You must register for an account to access the Service. You agree to provide
            accurate and complete registration information and to keep this information up to date.
          </p>
          <p>
            4.2. You are responsible for maintaining the confidentiality of your account credentials,
            including your password and any two-factor authentication (2FA) codes. We strongly
            recommend enabling 2FA on your account.
          </p>
          <p>
            4.3. You are responsible for all activities that occur under your account. You must
            notify us immediately at security@mynettax.co.uk if you become aware of any
            unauthorised use of your account or any other breach of security.
          </p>
          <p>
            4.4. MyNetTax shall not be liable for any loss or damage arising from your failure
            to comply with these security obligations.
          </p>

          <h2>5. Subscription Plans and Billing</h2>
          <p>
            5.1. MyNetTax offers the following subscription tiers:
          </p>
          <ul>
            <li>
              <strong>Free:</strong> Basic access with limited features, suitable for getting
              started.
            </li>
            <li>
              <strong>Starter:</strong> Core features including invoicing, basic tax calculations,
              and limited bank sync.
            </li>
            <li>
              <strong>Growth:</strong> Enhanced features including full MTD support, expanded bank
              sync, and AI assistant access.
            </li>
            <li>
              <strong>Pro:</strong> Full platform access including advanced analytics, mortgage
              readiness reports, and priority support.
            </li>
            <li>
              <strong>Business:</strong> All Pro features plus dedicated account management, custom
              integrations, and enhanced API access.
            </li>
          </ul>
          <p>
            5.2. Paid subscriptions are billed monthly or annually in advance via our payment
            processor, Stripe. All prices are quoted in pounds sterling (GBP) and are inclusive
            of VAT where applicable.
          </p>
          <p>
            5.3. You may upgrade or downgrade your subscription at any time. Upgrades take effect
            immediately with pro-rata billing. Downgrades take effect at the end of the current
            billing period.
          </p>
          <p>
            5.4. We reserve the right to change subscription prices with at least 30 days&apos;
            notice. Continued use after a price change constitutes acceptance.
          </p>
          <p>
            5.5. Refunds are handled in accordance with the Consumer Rights Act 2015. If you
            cancel within 14 days of your initial purchase (cooling-off period), you are entitled
            to a full refund.
          </p>

          <h2>6. Bank Synchronisation</h2>
          <p>
            6.1. Bank synchronisation is initiated only when you explicitly press the
            &quot;Sync&quot; button within the application. MyNetTax does not perform automatic
            or background bank synchronisation.
          </p>
          <p>
            6.2. Bank sync frequency limits apply per subscription tier. Daily sync limits are
            specified in your plan details and are subject to change.
          </p>
          <p>
            6.3. Bank connections are facilitated through SaltEdge, an FCA-authorised Account
            Information Service Provider (AISP). MyNetTax receives read-only access to your
            transaction data. We cannot initiate payments, transfers, or modify your bank accounts
            in any way.
          </p>
          <p>
            6.4. You may disconnect your bank account at any time through your account settings.
            Upon disconnection, no further transaction data will be retrieved.
          </p>

          <h2>7. HMRC Submissions</h2>
          <p>
            7.1. MyNetTax can prepare and submit tax returns and MTD quarterly updates to HMRC
            on your behalf, using HMRC&apos;s official APIs.
          </p>
          <p>
            7.2. <strong>No submission to HMRC will be made without your explicit confirmation.</strong>{' '}
            Before any submission, you will be presented with a summary of the data to be submitted
            and must actively confirm your intent to proceed.
          </p>
          <p>
            7.3. You remain solely responsible for the accuracy and completeness of all information
            submitted to HMRC. MyNetTax provides tools to assist with calculations and
            preparation, but you are the legal taxpayer and bear ultimate responsibility for your
            tax affairs.
          </p>
          <p>
            7.4. MyNetTax collects device information (IP address, operating system, browser
            details) as required by HMRC&apos;s fraud prevention headers. This data is transmitted
            to HMRC as part of each API request in compliance with HMRC requirements.
          </p>

          <h2>8. Mortgage Readiness</h2>
          <p>
            8.1. The mortgage readiness feature provides informational reports and financial health
            indicators based on your data within MyNetTax.
          </p>
          <p>
            8.2. <strong>Mortgage readiness reports are for informational purposes only and do not
            constitute financial advice, mortgage advice, or a recommendation to apply for any
            financial product.</strong> MyNetTax is not authorised by the Financial Conduct
            Authority (FCA) to provide regulated mortgage advice.
          </p>
          <p>
            8.3. You should seek independent, qualified financial advice before making any
            decisions regarding mortgage applications.
          </p>

          <h2>9. AI Assistant</h2>
          <p>
            9.1. The MyNetTax AI assistant provides general guidance on expense categorisation,
            tax questions, and financial queries based on publicly available information and your
            account data.
          </p>
          <p>
            9.2. <strong>The AI assistant does not provide professional tax advice, legal advice,
            or regulated financial advice.</strong> AI-generated responses may contain errors or
            inaccuracies. You should not rely solely on AI output for important financial or tax
            decisions.
          </p>
          <p>
            9.3. For complex tax matters, disputes with HMRC, or specialised financial planning,
            we recommend consulting a qualified accountant, tax adviser, or financial adviser.
          </p>

          <h2>10. Data Accuracy</h2>
          <p>
            10.1. You are solely responsible for the accuracy, completeness, and legality of all
            data you enter into or submit through the Service, including but not limited to
            income figures, expense records, tax calculations, and invoices.
          </p>
          <p>
            10.2. While MyNetTax implements validation checks and automated calculations, these
            tools are provided as aids and do not guarantee the correctness of your data. You must
            review all outputs before relying on them or submitting them to third parties.
          </p>

          <h2>11. Acceptable Use</h2>
          <p>You agree not to:</p>
          <ul>
            <li>Use the Service for any unlawful purpose or in violation of any applicable law;</li>
            <li>Submit false, misleading, or fraudulent information;</li>
            <li>Attempt to gain unauthorised access to any part of the Service or its systems;</li>
            <li>
              Interfere with or disrupt the Service, servers, or networks connected to the Service;
            </li>
            <li>Use automated means to access the Service except through our published APIs;</li>
            <li>Reverse engineer, decompile, or disassemble any part of the Service;</li>
            <li>Resell, sublicense, or redistribute access to the Service; or</li>
            <li>Use the Service to facilitate money laundering, tax evasion, or fraud.</li>
          </ul>

          <h2>12. Intellectual Property</h2>
          <p>
            12.1. All intellectual property rights in the Service, including but not limited to
            software, designs, text, graphics, logos, icons, and trademarks, are owned by or
            licensed to MyNetTax and are protected by copyright, trademark, and other
            intellectual property laws of England and Wales and international treaties.
          </p>
          <p>
            12.2. You retain ownership of any data you input into the Service. By using the
            Service, you grant MyNetTax a limited, non-exclusive licence to process your data
            solely for the purpose of providing the Service to you.
          </p>
          <p>
            12.3. Nothing in these Terms grants you any right, title, or interest in the Service
            except for the limited right to use it in accordance with these Terms.
          </p>

          <h2>13. Limitation of Liability</h2>
          <p>
            13.1. To the maximum extent permitted by law, MyNetTax shall not be liable for any
            indirect, incidental, special, consequential, or punitive damages, including but not
            limited to loss of profits, data, business, or goodwill, arising out of or in
            connection with your use of the Service.
          </p>
          <p>
            13.2. MyNetTax&apos;s total aggregate liability for all claims arising out of or
            relating to these Terms or the Service shall not exceed the greater of (a) the amount
            you have paid to MyNetTax in the twelve (12) months preceding the claim, or (b) one
            hundred pounds sterling (£100).
          </p>
          <p>
            13.3. Nothing in these Terms excludes or limits liability for (a) death or personal
            injury caused by negligence, (b) fraud or fraudulent misrepresentation, or (c) any
            other liability that cannot be excluded or limited by English law.
          </p>
          <p>
            13.4. MyNetTax does not warrant that the Service will be uninterrupted,
            error-free, or free of harmful components. The Service is provided on an
            &quot;as is&quot; and &quot;as available&quot; basis.
          </p>

          <h2>14. Indemnification</h2>
          <p>
            You agree to indemnify and hold harmless MyNetTax, its directors, officers,
            employees, and agents from and against any claims, losses, damages, liabilities,
            costs, and expenses (including reasonable legal fees) arising out of or relating to
            your breach of these Terms, your use of the Service, or your violation of any
            applicable law or third-party rights.
          </p>

          <h2>15. Termination</h2>
          <p>
            15.1. You may terminate your account at any time by contacting us at
            support@mynettax.co.uk or through your account settings.
          </p>
          <p>
            15.2. MyNetTax may suspend or terminate your access to the Service immediately,
            without prior notice, if you breach these Terms, engage in fraudulent activity,
            violate applicable law, or if required by a legal obligation or regulatory authority.
          </p>
          <p>
            15.3. Upon termination, your right to use the Service will cease immediately. We will
            retain your data in accordance with our{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link> and applicable
            legal requirements, including a minimum of seven (7) years for tax records as required
            by HMRC.
          </p>
          <p>
            15.4. Sections of these Terms that by their nature should survive termination
            (including Intellectual Property, Limitation of Liability, Indemnification, and
            Governing Law) shall continue in full force and effect.
          </p>

          <h2>16. Modifications to the Service and Terms</h2>
          <p>
            16.1. MyNetTax reserves the right to modify, suspend, or discontinue any part of
            the Service at any time, with or without notice.
          </p>
          <p>
            16.2. We may update these Terms from time to time. Material changes will be notified
            to you via email or through a prominent notice within the Service at least 30 days
            before the changes take effect. Your continued use of the Service after the effective
            date constitutes acceptance of the updated Terms.
          </p>

          <h2>17. Third-Party Services</h2>
          <p>
            The Service integrates with third-party services including HMRC, SaltEdge (Open
            Banking), and Stripe (payment processing). Your use of these third-party services is
            subject to their respective terms and conditions. MyNetTax is not responsible for
            the availability, accuracy, or conduct of third-party services.
          </p>

          <h2>18. Dispute Resolution</h2>
          <p>
            18.1. If you have a complaint or dispute, please contact us first at
            support@mynettax.co.uk. We will make reasonable efforts to resolve any dispute
            informally within 30 days.
          </p>
          <p>
            18.2. If a dispute cannot be resolved informally, it may be referred to mediation
            or alternative dispute resolution. UK consumers may also contact the relevant
            ombudsman service or the European Commission&apos;s online dispute resolution
            platform where applicable.
          </p>

          <h2>19. Governing Law and Jurisdiction</h2>
          <p>
            19.1. These Terms shall be governed by and construed in accordance with the laws of
            England and Wales.
          </p>
          <p>
            19.2. Any disputes arising out of or in connection with these Terms shall be subject
            to the exclusive jurisdiction of the courts of England and Wales, without prejudice
            to any mandatory consumer protection provisions that may apply in your jurisdiction.
          </p>

          <h2>20. Severability</h2>
          <p>
            If any provision of these Terms is found to be invalid or unenforceable by a court of
            competent jurisdiction, the remaining provisions shall continue in full force and effect.
          </p>

          <h2>21. Entire Agreement</h2>
          <p>
            These Terms, together with our{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>,{' '}
            <Link className={styles.link} href="/cookies">Cookie Policy</Link>, and{' '}
            <Link className={styles.link} href="/eula">End User License Agreement</Link>,
            constitute the entire agreement between you and MyNetTax regarding your use of
            the Service.
          </p>

          <h2>22. Contact Information</h2>
          <p>
            If you have any questions about these Terms, please contact us:
          </p>
          <ul>
            <li><strong>Email:</strong> legal@mynettax.co.uk</li>
            <li><strong>Support:</strong> support@mynettax.co.uk</li>
            <li><strong>Address:</strong> MyNetTax Ltd, London, England</li>
            <li><strong>Company Registration:</strong> Registered in England and Wales</li>
          </ul>

          <p style={{ marginTop: '2rem', fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>
            Last updated: April 2026
          </p>
        </section>
      </main>
    </div>
  );
}
