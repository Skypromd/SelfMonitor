import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function EulaPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>End User License Agreement (EULA)</h1>
        <p className={styles.description}>License terms for web and mobile use of SelfMonitor.</p>

        <section className={styles.subContainer}>
          <h2>1. License</h2>
          <p>
            SelfMonitor grants you a limited, non-exclusive, non-transferable, revocable right to access and use the
            software for authorized internal business operations.
          </p>

          <h2>2. Prohibited actions</h2>
          <p>
            You may not copy, mirror, scrape, resell, sublicense, decompile, reverse engineer, or create competing
            derivative products from SelfMonitor software, APIs, or export templates.
          </p>

          <h2>3. Mobile and API security controls</h2>
          <p>
            You agree not to bypass mobile attestation checks, anti-automation controls, export fingerprinting, or any
            security safeguards designed to protect platform integrity.
          </p>

          <h2>4. Intellectual property and trademarks</h2>
          <p>
            SelfMonitor branding, logos, designs, and proprietary implementation details remain the exclusive property
            of SelfMonitor.
          </p>

          <h2>5. Termination and remedies</h2>
          <p>
            Violations may result in immediate termination of access and legal enforcement, including injunctive relief
            and damages.
          </p>

          <h2>6. Documents</h2>
          <p>
            See <Link className={styles.link} href="/terms">Terms of Service</Link> and the repository{' '}
            <code>LICENSE</code> for full proprietary terms.
          </p>
        </section>
      </main>
    </div>
  );
}
