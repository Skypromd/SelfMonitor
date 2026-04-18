import Link from 'next/link';
import styles from '../styles/Home.module.css';

export default function EulaPage() {
  return (
    <div className={styles.container}>
      <main className={styles.main} style={{ maxWidth: 800 }}>
        <h1 className={styles.title}>End User License Agreement</h1>
        <p className={styles.description}>
          License terms for web and mobile use of MyNetTax software.
        </p>

        <section className={styles.subContainer}>
          <h2>1. Introduction</h2>
          <p>
            This End User License Agreement (&quot;EULA&quot; or &quot;Agreement&quot;) is a legal
            agreement between you (&quot;User&quot;, &quot;you&quot;, or &quot;your&quot;) and
            MyNetTax Ltd, a company registered in England and Wales (&quot;MyNetTax&quot;,
            &quot;we&quot;, &quot;us&quot;, or &quot;our&quot;).
          </p>
          <p>
            This EULA governs your use of the MyNetTax software, including the web portal at
            mynettax.co.uk, the MyNetTax mobile application for iOS and Android (built with
            React Native and Expo), and any associated APIs, updates, patches, or supplements
            (collectively, the &quot;Software&quot;).
          </p>
          <p>
            By installing, accessing, or using the Software, you agree to be bound by this EULA.
            If you do not agree, you must not install, access, or use the Software. This EULA
            supplements our{' '}
            <Link className={styles.link} href="/terms">Terms of Service</Link> and{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>.
          </p>

          <h2>2. License Grant</h2>
          <p>
            2.1. Subject to your compliance with this EULA and our Terms of Service, MyNetTax
            grants you a limited, non-exclusive, non-transferable, non-sublicensable, revocable
            licence to:
          </p>
          <ul>
            <li>
              Access and use the MyNetTax web portal through a standard web browser for your
              personal or sole-trader business purposes;
            </li>
            <li>
              Download, install, and use the MyNetTax mobile application on devices that you
              own or control, solely for your personal or sole-trader business purposes; and
            </li>
            <li>
              Use the MyNetTax APIs in accordance with any published API documentation and
              rate limits.
            </li>
          </ul>
          <p>
            2.2. This licence is personal to you and is linked to your MyNetTax account. You
            may not share your licence or account access with any other person or entity.
          </p>
          <p>
            2.3. The licence granted herein does not constitute a sale of the Software or any
            portion thereof. MyNetTax retains all rights, title, and interest in and to the
            Software.
          </p>

          <h2>3. Mobile Application Terms</h2>
          <p>
            3.1. The MyNetTax mobile application is built using React Native and Expo (SDK 51,
            React Native 0.74.5) and is distributed through the Apple App Store and Google Play
            Store.
          </p>
          <p>
            3.2. Your use of the mobile application is also subject to the terms and conditions
            of the app store from which you downloaded it:
          </p>
          <ul>
            <li>
              <strong>Apple App Store:</strong> Apple&apos;s Licensed Application End User License
              Agreement (the &quot;Apple EULA&quot;) applies. In the event of a conflict between
              Apple&apos;s EULA and this EULA, Apple&apos;s terms shall prevail to the extent
              required by Apple.
            </li>
            <li>
              <strong>Google Play Store:</strong> Google Play&apos;s Terms of Service apply. In
              the event of a conflict between Google&apos;s terms and this EULA, Google&apos;s
              terms shall prevail to the extent required by Google.
            </li>
          </ul>
          <p>
            3.3. You acknowledge that this EULA is between you and MyNetTax only, not with
            Apple Inc. or Google LLC. MyNetTax, not Apple or Google, is solely responsible for
            the Software and its content.
          </p>
          <p>
            3.4. Apple and Google have no obligation to provide any maintenance or support
            services for the Software. MyNetTax is solely responsible for any product
            warranties, whether express or implied by law.
          </p>

          <h2>4. App Store and Google Play Compliance</h2>
          <p>
            4.1. The Software complies with the applicable terms and guidelines of the Apple App
            Store and Google Play Store, including but not limited to:
          </p>
          <ul>
            <li>Apple App Store Review Guidelines;</li>
            <li>Google Play Developer Program Policies;</li>
            <li>Platform-specific privacy and data handling requirements; and</li>
            <li>In-app purchase and subscription policies where applicable.</li>
          </ul>
          <p>
            4.2. In the event of any third-party claim that the Software infringes a third
            party&apos;s intellectual property rights, MyNetTax (not Apple or Google) shall
            be solely responsible for the investigation, defence, settlement, and discharge of
            such claim.
          </p>
          <p>
            4.3. You represent and warrant that (a) you are not located in a country subject to
            UK government embargo, and (b) you are not listed on any UK government list of
            prohibited or restricted parties.
          </p>
          <p>
            4.4. Apple and Google, and their subsidiaries, are third-party beneficiaries of this
            EULA. Upon your acceptance of this EULA, Apple and Google shall have the right (and
            will be deemed to have accepted the right) to enforce this EULA against you as a
            third-party beneficiary.
          </p>

          <h2>5. Updates and Modifications</h2>
          <p>
            5.1. MyNetTax may release updates, patches, bug fixes, or new versions of the
            Software from time to time. These updates may be delivered automatically through the
            relevant app store or web portal.
          </p>
          <p>
            5.2. We recommend that you keep the Software updated to the latest version to ensure
            you have access to the latest features, security patches, and bug fixes. Older
            versions of the Software may not be supported and may not function correctly.
          </p>
          <p>
            5.3. MyNetTax reserves the right to modify, enhance, or discontinue any features
            of the Software at any time. We will provide reasonable notice for material changes
            that affect core functionality.
          </p>
          <p>
            5.4. Continued use of the Software after an update constitutes acceptance of any
            changes included in that update.
          </p>

          <h2>6. Restrictions</h2>
          <p>
            6.1. You shall not, and shall not permit any third party to:
          </p>
          <ul>
            <li>
              <strong>Reverse engineer:</strong> Decompile, disassemble, reverse engineer, or
              attempt to derive the source code, algorithms, or data structures of the Software,
              except to the extent expressly permitted by applicable law (including the Computer
              Programs Directive as implemented in UK law);
            </li>
            <li>
              <strong>Modify:</strong> Modify, adapt, translate, or create derivative works based
              on the Software;
            </li>
            <li>
              <strong>Redistribute:</strong> Copy, distribute, publish, sell, lease, rent,
              sublicense, or otherwise transfer the Software or any rights therein to any third
              party;
            </li>
            <li>
              <strong>Circumvent protections:</strong> Remove, alter, or obscure any copyright
              notices, trademarks, or other proprietary notices in the Software, or bypass any
              technical protection measures, authentication mechanisms, or security features;
            </li>
            <li>
              <strong>Compete:</strong> Use the Software, or any information obtained from the
              Software, to build or support a competing product or service;
            </li>
            <li>
              <strong>Misuse:</strong> Use the Software for any unlawful, harmful, or
              unauthorised purpose, including but not limited to facilitating tax evasion, money
              laundering, or fraud;
            </li>
            <li>
              <strong>Automated access:</strong> Use bots, scrapers, crawlers, or other automated
              means to access the Software, except through our published APIs within documented
              rate limits; or
            </li>
            <li>
              <strong>Overload:</strong> Intentionally overload, stress test, or interfere with
              the Software&apos;s infrastructure.
            </li>
          </ul>
          <p>
            6.2. Notwithstanding the above, nothing in this EULA restricts your rights under
            the Copyright, Designs and Patents Act 1988 to decompile the Software to the extent
            necessary to achieve interoperability with independently created software, provided
            you have first requested the necessary information from MyNetTax and we have not
            made it available within a reasonable time.
          </p>

          <h2>7. Intellectual Property</h2>
          <p>
            7.1. The Software and all copies thereof are the intellectual property of and are
            owned by MyNetTax. The structure, organisation, and code of the Software are
            valuable trade secrets and confidential information of MyNetTax.
          </p>
          <p>
            7.2. The MyNetTax name, logo, and all related product names, design marks, and
            slogans are trademarks or service marks of MyNetTax. You are not authorised to
            use any such marks without our prior written permission.
          </p>
          <p>
            7.3. You retain all rights to the data you input into the Software. MyNetTax
            claims no intellectual property rights over your financial data, invoices, or other
            content you create using the Software.
          </p>

          <h2>8. Termination</h2>
          <p>
            8.1. This EULA is effective until terminated. Your rights under this EULA will
            terminate automatically without notice if you fail to comply with any of its terms.
          </p>
          <p>
            8.2. MyNetTax may terminate this EULA at any time by providing written notice to
            you, or immediately if you breach any provision of this EULA.
          </p>
          <p>
            8.3. Upon termination:
          </p>
          <ul>
            <li>
              All licences granted under this EULA shall immediately cease;
            </li>
            <li>
              You must stop using the Software and delete all copies from your devices;
            </li>
            <li>
              You may request an export of your data prior to account deletion, in accordance
              with your GDPR rights; and
            </li>
            <li>
              MyNetTax will retain data as required by law (see our{' '}
              <Link className={styles.link} href="/privacy">Privacy Policy</Link>).
            </li>
          </ul>
          <p>
            8.4. Sections relating to Intellectual Property, Disclaimer of Warranties, Limitation
            of Liability, Indemnification, and Governing Law shall survive termination.
          </p>

          <h2>9. Disclaimer of Warranties</h2>
          <p>
            9.1. To the maximum extent permitted by applicable law, the Software is provided
            &quot;AS IS&quot; and &quot;AS AVAILABLE&quot;, without warranty of any kind, whether
            express, implied, statutory, or otherwise.
          </p>
          <p>
            9.2. MyNetTax expressly disclaims all implied warranties, including but not limited
            to implied warranties of merchantability, fitness for a particular purpose, and
            non-infringement.
          </p>
          <p>
            9.3. Without limiting the foregoing, MyNetTax does not warrant that:
          </p>
          <ul>
            <li>The Software will be uninterrupted, timely, secure, or error-free;</li>
            <li>The results obtained from the Software will be accurate or reliable;</li>
            <li>
              The Software will be compatible with all devices, operating systems, or browsers;
            </li>
            <li>Any errors in the Software will be corrected; or</li>
            <li>
              The Software will meet your specific requirements or expectations.
            </li>
          </ul>
          <p>
            9.4. Nothing in this EULA excludes or limits any statutory rights that you have as a
            consumer under the Consumer Rights Act 2015, which provides that digital content must
            be of satisfactory quality, fit for purpose, and as described.
          </p>

          <h2>10. Limitation of Liability</h2>
          <p>
            10.1. To the maximum extent permitted by law, in no event shall MyNetTax, its
            directors, officers, employees, agents, or affiliates be liable for any indirect,
            incidental, special, consequential, or punitive damages, including but not limited
            to:
          </p>
          <ul>
            <li>Loss of profits, revenue, or business;</li>
            <li>Loss of data or data corruption;</li>
            <li>Loss of goodwill or reputation;</li>
            <li>
              Penalties, fines, or interest charged by HMRC or other authorities due to errors
              in data you submitted through the Software;
            </li>
            <li>Cost of procurement of substitute services; or</li>
            <li>
              Any other intangible losses arising out of or in connection with your use of or
              inability to use the Software.
            </li>
          </ul>
          <p>
            10.2. MyNetTax&apos;s total aggregate liability for all claims arising from this
            EULA shall not exceed the amount you have paid to MyNetTax in the twelve (12)
            months preceding the event giving rise to the claim, or one hundred pounds sterling
            (£100), whichever is greater.
          </p>
          <p>
            10.3. Nothing in this EULA excludes or limits liability for:
          </p>
          <ul>
            <li>Death or personal injury caused by negligence;</li>
            <li>Fraud or fraudulent misrepresentation;</li>
            <li>Breach of the terms implied by Section 12 of the Sale of Goods Act 1979; or</li>
            <li>Any other liability that cannot be excluded or limited by English law.</li>
          </ul>

          <h2>11. Indemnification</h2>
          <p>
            You agree to defend, indemnify, and hold harmless MyNetTax, its directors,
            officers, employees, and agents from and against any claims, damages, losses,
            liabilities, costs, and expenses (including reasonable legal fees) arising out of or
            relating to: (a) your use of the Software in violation of this EULA; (b) your
            violation of any applicable law or regulation; (c) your violation of any third-party
            rights; or (d) any data or content you submit through the Software.
          </p>

          <h2>12. Export Compliance</h2>
          <p>
            You agree to comply with all applicable UK and international export control laws and
            regulations. You shall not export, re-export, or transfer the Software to any country,
            entity, or person prohibited by applicable law.
          </p>

          <h2>13. Open Source Components</h2>
          <p>
            The Software may include open source software components, each of which has its own
            licence. The open source licence terms are available within the application or upon
            request. Nothing in this EULA limits your rights under, or grants you rights that
            supersede, the terms of any applicable open source licence.
          </p>

          <h2>14. Privacy and Data Protection</h2>
          <p>
            Your use of the Software is also governed by our{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>, which describes
            how we collect, use, store, and protect your personal data in compliance with the UK
            GDPR and the Data Protection Act 2018.
          </p>

          <h2>15. Governing Law and Jurisdiction</h2>
          <p>
            15.1. This EULA shall be governed by and construed in accordance with the laws of
            England and Wales.
          </p>
          <p>
            15.2. Any disputes arising out of or in connection with this EULA shall be subject to
            the exclusive jurisdiction of the courts of England and Wales, without prejudice to
            any mandatory consumer protection provisions that may apply in your jurisdiction.
          </p>

          <h2>16. Severability</h2>
          <p>
            If any provision of this EULA is held to be invalid, illegal, or unenforceable by a
            court of competent jurisdiction, the validity, legality, and enforceability of the
            remaining provisions shall not be affected or impaired.
          </p>

          <h2>17. Entire Agreement</h2>
          <p>
            This EULA, together with our{' '}
            <Link className={styles.link} href="/terms">Terms of Service</Link>,{' '}
            <Link className={styles.link} href="/privacy">Privacy Policy</Link>, and{' '}
            <Link className={styles.link} href="/cookies">Cookie Policy</Link>, constitutes the
            entire agreement between you and MyNetTax regarding the Software and supersedes
            all prior and contemporaneous agreements, proposals, or representations, written or
            oral, concerning its subject matter.
          </p>

          <h2>18. Contact Information</h2>
          <p>
            If you have any questions about this EULA, please contact us:
          </p>
          <ul>
            <li><strong>Email:</strong> legal@mynettax.co.uk</li>
            <li><strong>Support:</strong> support@mynettax.co.uk</li>
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
