import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function TermsPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>Terms of Service</h1>
        <p className={styles.description}>SelfMonitor platform terms for all users and organizations.</p>

        <section className={styles.subContainer}>
          <h2>1. Service scope</h2>
          <p>
            SelfMonitor provides software tools for compliance, invoicing, analytics, and account security workflows.
            The service is provided on a best-effort basis and may evolve over time.
          </p>

          <h2>2. Acceptable use</h2>
          <p>
            You may not use the service for unlawful activities, abuse, credential stuffing, reverse engineering, or
            attempts to bypass technical or contractual protections.
          </p>

          <h2>3. Intellectual property</h2>
          <p>
            Product code, architecture, UX, trademarks, and documentation are proprietary to SelfMonitor and protected
            by copyright and trademark law. Unauthorized cloning or distribution is prohibited.
          </p>

          <h2>4. Account and security obligations</h2>
          <p>
            You are responsible for keeping credentials secure, enabling recommended protections (2FA), and reporting
            suspicious account activity promptly.
          </p>

          <h2>5. Data and compliance</h2>
          <p>
            You are responsible for the legal correctness of submissions and exports generated from your account.
            SelfMonitor provides supporting tools but does not replace regulated legal advice.
          </p>

          <h2>6. Termination</h2>
          <p>
            SelfMonitor may suspend or terminate access for abuse, fraud signals, legal requirements, or material
            breach of these terms.
          </p>

          <h2>7. Legal references</h2>
          <p>
            See the <Link className={styles.link} href="/eula">EULA</Link> and repository{' '}
            <code>LICENSE</code> for proprietary licensing terms.
          </p>
        </section>
      </main>
    </div>
  );
}
