import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function CookiesPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main} style={{ maxWidth: 800 }}>
        <h1 className={styles.title}>Cookie Policy</h1>
        <p className={styles.description}>
          How MyNetTax uses cookies and similar technologies.
        </p>

        <section className={styles.subContainer}>
          <h2>1. What Are Cookies</h2>
          <p>
            Cookies are small text files that are placed on your device (computer, tablet, or
            mobile phone) when you visit a website. They are widely used to make websites work
            efficiently, provide information to website owners, and enhance the user experience.
          </p>
          <p>
            Cookies may be &quot;session cookies&quot; (which are deleted when you close your
            browser) or &quot;persistent cookies&quot; (which remain on your device for a set
            period or until you delete them).
          </p>
          <p>
            This Cookie Policy explains what cookies we use on the MyNetTax platform, why we
            use them, and how you can manage your preferences. This policy should be read
            alongside our <Link className={styles.link} href="/privacy">Privacy Policy</Link>.
          </p>

          <h2>2. Cookies We Use</h2>

          <h3>2.1. Essential Cookies (Required)</h3>
          <p>
            These cookies are strictly necessary for the operation of the MyNetTax platform.
            Without them, the Service cannot function properly. They cannot be disabled.
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Cookie</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Purpose</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>auth_token</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Authenticates your session after login</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Session / 7 days</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>session_id</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Maintains your session state across pages</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Session</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>csrf_token</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Prevents cross-site request forgery attacks</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Session</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>cookie_consent</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Records your cookie consent preferences</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>1 year</td>
              </tr>
            </tbody>
          </table>

          <h3>2.2. Analytics Cookies (Optional)</h3>
          <p>
            These cookies help us understand how visitors interact with the MyNetTax platform
            by collecting information about page views, feature usage, and navigation patterns.
            All analytics data is aggregated and anonymised where possible.
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Cookie</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Purpose</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>_sm_analytics</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Tracks page views and feature usage</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>1 year</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>_sm_session_track</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Measures session duration and engagement</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>30 minutes</td>
              </tr>
            </tbody>
          </table>

          <h3>2.3. Preference Cookies (Optional)</h3>
          <p>
            These cookies remember your settings and preferences to provide a more personalised
            experience.
          </p>
          <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: '1rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Cookie</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Purpose</th>
                <th style={{ textAlign: 'left', padding: '0.5rem 0', color: 'var(--lp-text-muted)', fontSize: '0.8rem' }}>Duration</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>locale</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Stores your preferred language setting</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>1 year</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>theme</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Stores your preferred display theme (dark/light)</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>1 year</td>
              </tr>
              <tr style={{ borderBottom: '1px solid var(--lp-border)' }}>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>dashboard_layout</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>Remembers your dashboard widget arrangement</td>
                <td style={{ padding: '0.5rem 0', fontSize: '0.85rem' }}>1 year</td>
              </tr>
            </tbody>
          </table>

          <h2>3. Third-Party Cookies</h2>
          <p>
            Some cookies are placed by third-party services that appear on our pages. We do not
            control these cookies and recommend reviewing the privacy policies of these third
            parties.
          </p>

          <h3>3.1. Stripe</h3>
          <p>
            Stripe, our payment processor, may set cookies when you interact with payment forms
            on our platform. These cookies are used for fraud detection and secure payment
            processing. For more information, visit{' '}
            <strong>stripe.com/privacy</strong>.
          </p>

          <h3>3.2. Analytics Providers</h3>
          <p>
            If you consent to analytics cookies, our analytics provider may set cookies to help
            us measure and improve the Service. These cookies collect anonymised data about your
            usage patterns.
          </p>

          <h2>4. How to Manage Cookies</h2>
          <p>
            You can manage your cookie preferences in the following ways:
          </p>

          <h3>4.1. Cookie Consent Banner</h3>
          <p>
            When you first visit MyNetTax, you will see a cookie consent banner allowing you
            to accept or reject optional cookies. You can change your preferences at any time
            through your account settings.
          </p>

          <h3>4.2. Browser Settings</h3>
          <p>
            Most web browsers allow you to control cookies through their settings. You can
            typically:
          </p>
          <ul>
            <li>View what cookies are stored on your device;</li>
            <li>Delete individual cookies or all cookies;</li>
            <li>Block cookies from specific or all websites; and</li>
            <li>Set your browser to notify you when a cookie is being set.</li>
          </ul>
          <p>
            Please note that blocking essential cookies will prevent the MyNetTax platform from
            functioning correctly. You may not be able to log in or use core features.
          </p>

          <h3>4.3. How to Manage Cookies in Common Browsers</h3>
          <ul>
            <li><strong>Google Chrome:</strong> Settings &gt; Privacy and Security &gt; Cookies and other site data</li>
            <li><strong>Mozilla Firefox:</strong> Settings &gt; Privacy &amp; Security &gt; Cookies and Site Data</li>
            <li><strong>Safari:</strong> Preferences &gt; Privacy &gt; Manage Website Data</li>
            <li><strong>Microsoft Edge:</strong> Settings &gt; Cookies and site permissions</li>
          </ul>

          <h2>5. Cookie Consent</h2>
          <p>
            In accordance with UK privacy regulations (the Privacy and Electronic Communications
            Regulations 2003, as amended), we obtain your consent before setting any non-essential
            cookies.
          </p>
          <p>
            Essential cookies are set without consent as they are strictly necessary for the
            Service to function. We will never set analytics or preference cookies without your
            explicit opt-in.
          </p>
          <p>
            You can withdraw your consent at any time by updating your preferences in your
            account settings or by clearing your cookies through your browser.
          </p>

          <h2>6. Do Not Track</h2>
          <p>
            Some browsers offer a &quot;Do Not Track&quot; (DNT) signal. MyNetTax currently
            respects DNT signals by treating them as equivalent to opting out of analytics cookies.
          </p>

          <h2>7. Changes to This Cookie Policy</h2>
          <p>
            We may update this Cookie Policy from time to time. Changes will be posted on this
            page with an updated &quot;Last updated&quot; date. If we make material changes to
            how we use cookies, we will notify you through the Service or by email.
          </p>

          <h2>8. Further Information</h2>
          <p>
            For more information about cookies and how to manage them, you can visit{' '}
            <strong>allaboutcookies.org</strong> or{' '}
            <strong>ico.org.uk/for-the-public/online/cookies</strong>.
          </p>

          <h2>9. Contact Us</h2>
          <p>
            If you have any questions about this Cookie Policy, please contact us:
          </p>
          <ul>
            <li><strong>Data Protection Officer:</strong> dpo@mynettax.co.uk</li>
            <li><strong>General Support:</strong> support@mynettax.co.uk</li>
            <li><strong>Address:</strong> MyNetTax Ltd, London, England</li>
          </ul>
          <p>
            For more information about our data practices, please refer to our{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>.
          </p>

          <p style={{ marginTop: '2rem', fontSize: '0.85rem', color: 'var(--lp-text-muted)' }}>
            Last updated: April 2026
          </p>
        </section>
      </main>
    </div>
  );
}
