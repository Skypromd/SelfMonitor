import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import styles from '../styles/Home.module.css';

export default function CheckoutCancelPage() {
  const router = useRouter();
  const { plan, product } = router.query;
  const productStr = Array.isArray(product) ? product[0] : product;
  const isConsult = productStr === 'accountant_cis_consult';

  const planName = plan
    ? (plan as string).charAt(0).toUpperCase() + (plan as string).slice(1)
    : 'Starter';

  return (
    <>
      <Head>
        <title>Payment Cancelled — MyNetTax</title>
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 520, textAlign: 'center' }}>

          {/* Cancel icon */}
          <div style={{
            width: 80, height: 80, borderRadius: '50%',
            background: 'rgba(239,68,68,0.1)', border: '2px solid rgba(239,68,68,0.4)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '2.5rem', margin: '0 auto 1.5rem',
          }}>
            ×
          </div>

          <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '1rem' }}>
            Payment Cancelled
          </h1>

          <p className={styles.description} style={{ marginBottom: '1.5rem' }}>
            {isConsult ? (
              <>
                Checkout for a <strong style={{ color: '#14b8a6' }}>CIS accountant review</strong> session was
                cancelled. You have not been charged.
              </>
            ) : (
              <>
                No worries — your <strong style={{ color: '#14b8a6' }}>{planName}</strong> subscription was not started.
                You have not been charged.
              </>
            )}
          </p>

          <div style={{
            width: '100%', padding: '1.25rem', borderRadius: 12,
            background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)',
            margin: '0 0 1.5rem', textAlign: 'left', color: '#94a3b8', fontSize: '0.875rem', lineHeight: 2,
          }}>
            {isConsult ? (
              <>
                <div>💡 You can restart checkout from My subscription</div>
                <div>💡 Questions? Use the contact link in the site footer</div>
              </>
            ) : (
              <>
                <div>💡 You can always start a free trial — no credit card required</div>
                <div>💡 Try the Free plan to explore MyNetTax at no cost</div>
                <div>💡 Upgrade whenever you&apos;re ready from your dashboard</div>
              </>
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%' }}>
            <Link
              href={isConsult ? '/my-subscription' : '/#pricing'}
              className={styles.button}
              style={{ display: 'block', textDecoration: 'none', padding: '0.875rem 2rem', borderRadius: 10 }}
            >
              {isConsult ? 'Back to My subscription' : 'View Plans Again'}
            </Link>
            {!isConsult ? (
              <Link
                href="/register?plan=free"
                style={{
                  display: 'block', textDecoration: 'none', padding: '0.875rem 2rem',
                  borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)',
                  color: '#94a3b8', fontSize: '0.875rem', textAlign: 'center',
                }}
              >
                Start with Free Plan instead
              </Link>
            ) : null}
          </div>

          <p style={{ marginTop: '1.5rem' }}>
            <Link href="/" style={{ color: '#475569', fontSize: '0.8rem' }}>← Back to homepage</Link>
          </p>
        </main>
      </div>
    </>
  );
}
