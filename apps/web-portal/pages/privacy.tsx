import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function PrivacyPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main} style={{ maxWidth: 800 }}>
        <h1 className={styles.title}>Privacy Policy</h1>
        <p className={styles.description}>
          How MyNetTax collects, uses, stores, and protects your personal data.
        </p>

        <section className={styles.subContainer}>
          <h2>1. Who We Are</h2>
          <p>
            MyNetTax Ltd (&quot;MyNetTax&quot;, &quot;we&quot;, &quot;us&quot;, or
            &quot;our&quot;) is a company registered in England and Wales. We are the data
            controller responsible for your personal data processed through the MyNetTax
            platform, including our web portal, mobile applications, and APIs.
          </p>
          <p>
            Our Data Protection Officer (DPO) can be contacted at:{' '}
            <strong>dpo@mynettax.co.uk</strong>
          </p>
          <p>
            We are committed to protecting your personal data in compliance with the UK General
            Data Protection Regulation (UK GDPR), the Data Protection Act 2018, and all applicable
            UK data protection legislation.
          </p>

          <h2>2. What Data We Collect</h2>

          <h3>2.1. Account Data</h3>
          <p>When you register and use MyNetTax, we collect:</p>
          <ul>
            <li>Full name</li>
            <li>Email address</li>
            <li>Password (stored as a cryptographic hash; we never store plaintext passwords)</li>
            <li>Phone number (if provided for 2FA)</li>
            <li>Business name and type (sole trader, freelancer, etc.)</li>
            <li>Unique Taxpayer Reference (UTR) and National Insurance Number (NINO)</li>
          </ul>

          <h3>2.2. Financial Data</h3>
          <p>To provide our core services, we process:</p>
          <ul>
            <li>Income and expense records</li>
            <li>Invoices (created, sent, and received)</li>
            <li>Tax calculations and Self Assessment returns</li>
            <li>MTD for ITSA quarterly update data</li>
            <li>Profit and loss statements</li>
            <li>Mortgage readiness reports and financial health indicators</li>
          </ul>

          <h3>2.3. Bank Data (via Open Banking)</h3>
          <p>
            If you choose to connect your bank account, we receive read-only access to your
            transaction data through our authorised Open Banking provider, SaltEdge. This includes:
          </p>
          <ul>
            <li>Transaction descriptions, amounts, dates, and categories</li>
            <li>Account balances</li>
            <li>Account holder name and account identifiers</li>
          </ul>
          <p>
            We <strong>cannot</strong> initiate payments, transfer funds, or modify your bank
            accounts. Access is strictly read-only and is only triggered when you manually press
            the Sync button.
          </p>

          <h3>2.4. HMRC Data</h3>
          <p>When you use our HMRC integration features, we process:</p>
          <ul>
            <li>Tax calculations and liability summaries</li>
            <li>Self Assessment submission data</li>
            <li>MTD quarterly update records</li>
            <li>HMRC obligation periods and deadlines</li>
            <li>National Insurance Number (NINO) for HMRC authentication</li>
          </ul>

          <h3>2.5. Device and Fraud Prevention Data</h3>
          <p>
            As required by HMRC&apos;s fraud prevention policy for third-party software, we
            collect the following device data when you interact with HMRC services through
            MyNetTax:
          </p>
          <ul>
            <li>IP address</li>
            <li>Operating system and version</li>
            <li>Browser type and version</li>
            <li>Device identifiers</li>
            <li>Screen resolution and timezone</li>
          </ul>
          <p>
            This data is transmitted to HMRC as part of mandatory fraud prevention headers and is
            required by law for all software that connects to HMRC APIs.
          </p>

          <h3>2.6. Usage Data</h3>
          <p>We collect data about how you interact with the Service, including:</p>
          <ul>
            <li>Pages visited and features used</li>
            <li>Actions performed (e.g., invoices created, reports generated)</li>
            <li>Session duration and frequency of use</li>
            <li>Error logs and performance data</li>
            <li>Referring pages and exit pages</li>
          </ul>

          <h2>3. Legal Basis for Processing (GDPR Article 6)</h2>
          <p>
            We process your personal data on the following legal bases under Article 6 of the
            UK GDPR:
          </p>

          <h3>3.1. Contract Performance (Article 6(1)(b))</h3>
          <p>
            Processing necessary to perform the contract between you and MyNetTax, including
            providing the core Service features: account management, invoicing, tax calculations,
            bank synchronisation, HMRC submissions, and financial reporting.
          </p>

          <h3>3.2. Legal Obligation (Article 6(1)(c))</h3>
          <p>Processing required to comply with legal obligations, including:</p>
          <ul>
            <li>
              HMRC fraud prevention requirements (transmission of device data with API requests)
            </li>
            <li>Anti-money laundering (AML) and counter-terrorism financing regulations</li>
            <li>Tax record retention requirements (minimum seven years)</li>
            <li>Responding to lawful requests from regulatory authorities</li>
          </ul>

          <h3>3.3. Legitimate Interest (Article 6(1)(f))</h3>
          <p>
            Processing necessary for our legitimate interests, provided these do not override your
            fundamental rights. This includes:
          </p>
          <ul>
            <li>Service improvement and development of new features</li>
            <li>Security monitoring, fraud prevention, and abuse detection</li>
            <li>Analytics and performance optimisation</li>
            <li>Customer support and communication about your account</li>
          </ul>

          <h3>3.4. Consent (Article 6(1)(a))</h3>
          <p>
            Where we rely on your consent, including:
          </p>
          <ul>
            <li>Marketing communications (email newsletters, product updates)</li>
            <li>
              Non-essential cookies (analytics and preference cookies — see our{' '}
              <Link className={styles.link} href="/cookies">Cookie Policy</Link>)
            </li>
            <li>Optional data sharing with partner services</li>
          </ul>
          <p>
            You may withdraw consent at any time without affecting the lawfulness of processing
            carried out before withdrawal.
          </p>

          <h2>4. How We Use Your Data</h2>
          <p>We use your personal data to:</p>
          <ul>
            <li>Provide, maintain, and improve the MyNetTax platform;</li>
            <li>Process and display your financial data, transactions, and reports;</li>
            <li>Prepare and submit tax returns and MTD updates to HMRC on your behalf;</li>
            <li>Synchronise bank transactions when you initiate a sync;</li>
            <li>Generate mortgage readiness reports and financial health indicators;</li>
            <li>Process subscription payments via Stripe;</li>
            <li>Provide customer support and respond to your enquiries;</li>
            <li>Send transactional notifications (e.g., tax deadline reminders, submission confirmations);</li>
            <li>Detect and prevent fraud, abuse, and security threats;</li>
            <li>Comply with legal and regulatory obligations; and</li>
            <li>Conduct anonymised, aggregated analytics to improve the Service.</li>
          </ul>

          <h2>5. Data Sharing</h2>
          <p>
            We do not sell, rent, or trade your personal data to third parties. We share your
            data only in the following circumstances:
          </p>

          <h3>5.1. HMRC</h3>
          <p>
            When you explicitly confirm a tax submission, we transmit the relevant tax data and
            required fraud prevention headers to HMRC via their official APIs. No data is sent to
            HMRC without your active confirmation.
          </p>

          <h3>5.2. SaltEdge (Open Banking Provider)</h3>
          <p>
            If you connect your bank account, SaltEdge acts as our authorised Account Information
            Service Provider (AISP) under FCA regulation. SaltEdge accesses your bank data on a
            read-only basis to relay transaction information to MyNetTax. SaltEdge is bound by
            its own data protection obligations and FCA requirements.
          </p>

          <h3>5.3. Stripe (Payment Processing)</h3>
          <p>
            Subscription payments are processed by Stripe. We share your name, email, and payment
            details with Stripe solely for the purpose of processing transactions. We do not
            store full credit or debit card numbers on our servers. Stripe is PCI DSS Level 1
            certified.
          </p>

          <h3>5.4. Legal and Regulatory Requirements</h3>
          <p>
            We may disclose your data if required to do so by law, regulation, court order, or
            governmental request, or if disclosure is necessary to protect our rights, property,
            or safety, or the rights, property, or safety of others.
          </p>

          <h3>5.5. Business Transfers</h3>
          <p>
            In the event of a merger, acquisition, or sale of all or a portion of our assets,
            your data may be transferred as part of that transaction. We will notify you via email
            and/or a prominent notice on the Service before your data is transferred and becomes
            subject to a different privacy policy.
          </p>

          <h2>6. Data Storage and Security</h2>
          <p>
            6.1. Your data is stored on servers located in the United Kingdom. We use
            industry-standard security measures including:
          </p>
          <ul>
            <li>Encryption at rest (AES-256) and in transit (TLS 1.2+);</li>
            <li>Secure password hashing using modern cryptographic algorithms;</li>
            <li>Role-based access controls and the principle of least privilege;</li>
            <li>Regular security audits and vulnerability assessments;</li>
            <li>DDoS protection and intrusion detection systems; and</li>
            <li>Automated backup and disaster recovery procedures.</li>
          </ul>
          <p>
            6.2. While we implement robust security measures, no method of electronic storage or
            transmission is 100% secure. We cannot guarantee absolute security but are committed
            to protecting your data to the highest commercially reasonable standard.
          </p>

          <h2>7. Data Retention</h2>
          <p>
            7.1. <strong>Active accounts:</strong> We retain your data for as long as your account
            is active and as needed to provide the Service.
          </p>
          <p>
            7.2. <strong>Deleted accounts:</strong> When you delete your account, we will delete
            or anonymise your personal data within 30 days, except where retention is required by
            law.
          </p>
          <p>
            7.3. <strong>Tax records:</strong> In accordance with HMRC requirements, we are
            legally required to retain tax-related records for a minimum of seven (7) years from
            the end of the relevant tax year. This includes Self Assessment submissions, MTD
            quarterly updates, and supporting transaction data.
          </p>
          <p>
            7.4. <strong>Payment records:</strong> Billing and transaction records are retained
            for six (6) years in accordance with UK accounting and tax obligations.
          </p>
          <p>
            7.5. <strong>Usage and analytics data:</strong> Anonymised usage data may be retained
            indefinitely for statistical analysis and service improvement.
          </p>

          <h2>8. Your Rights Under GDPR</h2>
          <p>
            Under the UK GDPR, you have the following rights regarding your personal data:
          </p>
          <ul>
            <li>
              <strong>Right of Access (Article 15):</strong> You have the right to request a copy
              of the personal data we hold about you.
            </li>
            <li>
              <strong>Right to Rectification (Article 16):</strong> You have the right to request
              correction of inaccurate or incomplete personal data.
            </li>
            <li>
              <strong>Right to Erasure (Article 17):</strong> You have the right to request
              deletion of your personal data, subject to legal retention obligations (e.g.,
              seven-year tax record retention).
            </li>
            <li>
              <strong>Right to Data Portability (Article 20):</strong> You have the right to
              receive your personal data in a structured, commonly used, machine-readable format
              and to transmit it to another controller.
            </li>
            <li>
              <strong>Right to Object (Article 21):</strong> You have the right to object to
              processing based on legitimate interests, including profiling and direct marketing.
            </li>
            <li>
              <strong>Right to Restrict Processing (Article 18):</strong> You have the right to
              request restriction of processing in certain circumstances.
            </li>
            <li>
              <strong>Right to Withdraw Consent:</strong> Where processing is based on consent,
              you may withdraw consent at any time without affecting the lawfulness of processing
              carried out before withdrawal.
            </li>
          </ul>
          <p>
            To exercise any of these rights, please contact our Data Protection Officer at{' '}
            <strong>dpo@mynettax.co.uk</strong>. We will respond to your request within one
            calendar month, as required by the UK GDPR. In complex cases, we may extend this
            period by a further two months, and we will inform you of any such extension.
          </p>

          <h2>9. Cookies</h2>
          <p>
            We use cookies and similar technologies to provide, secure, and improve the Service.
            For detailed information about the cookies we use and how to manage them, please refer
            to our <Link className={styles.link} href="/cookies">Cookie Policy</Link>.
          </p>

          <h2>10. International Data Transfers</h2>
          <p>
            Your data is primarily stored and processed within the United Kingdom. In the limited
            circumstances where data may be transferred outside the UK (e.g., for specific
            third-party integrations), we ensure appropriate safeguards are in place, including
            UK adequacy decisions, Standard Contractual Clauses (SCCs), or other lawful transfer
            mechanisms as approved by the Information Commissioner&apos;s Office (ICO).
          </p>

          <h2>11. Children</h2>
          <p>
            The MyNetTax Service is not intended for individuals under the age of 18. We do
            not knowingly collect personal data from children. If we become aware that we have
            collected data from a person under 18, we will take steps to delete that data promptly.
            If you believe a child has provided us with personal data, please contact us at{' '}
            <strong>dpo@mynettax.co.uk</strong>.
          </p>

          <h2>12. Automated Decision-Making</h2>
          <p>
            MyNetTax uses automated processing for tax calculations, expense categorisation,
            and financial analysis. These automated processes assist with data presentation but
            do not make legally binding decisions on your behalf. All submissions to HMRC require
            your explicit manual confirmation. You have the right to request human review of any
            automated decision that significantly affects you.
          </p>

          <h2>13. Changes to This Policy</h2>
          <p>
            We may update this Privacy Policy from time to time to reflect changes in our
            practices, technology, legal requirements, or other factors. Material changes will be
            communicated to you via email or a prominent notice within the Service at least 30
            days before the changes take effect. We encourage you to review this page periodically.
          </p>

          <h2>14. Complaints and the ICO</h2>
          <p>
            If you are not satisfied with how we handle your personal data or respond to your
            rights requests, you have the right to lodge a complaint with the Information
            Commissioner&apos;s Office (ICO), the UK&apos;s supervisory authority for data
            protection:
          </p>
          <ul>
            <li><strong>Website:</strong> ico.org.uk</li>
            <li><strong>Helpline:</strong> 0303 123 1113</li>
            <li>
              <strong>Address:</strong> Information Commissioner&apos;s Office, Wycliffe House,
              Water Lane, Wilmslow, Cheshire, SK9 5AF
            </li>
          </ul>
          <p>
            We would appreciate the opportunity to address your concerns before you contact the
            ICO. Please reach out to us first at <strong>dpo@mynettax.co.uk</strong>.
          </p>

          <h2>15. Contact Us</h2>
          <p>
            If you have any questions about this Privacy Policy or our data practices, please
            contact us:
          </p>
          <ul>
            <li><strong>Data Protection Officer:</strong> dpo@mynettax.co.uk</li>
            <li><strong>General Support:</strong> support@mynettax.co.uk</li>
            <li><strong>Address:</strong> MyNetTax Ltd, London, England</li>
          </ul>

          <p style={{ marginTop: '2rem', fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>
            Last updated: April 2026
          </p>
        </section>
      </main>
    </div>
  );
}
