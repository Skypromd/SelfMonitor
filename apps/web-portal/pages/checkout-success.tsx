import Head from 'next/head';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

export default function CheckoutSuccessPage() {
  const router = useRouter();
  const { plan, session_id, dev } = router.query;
  const [countdown, setCountdown] = useState(5);

  const planName = plan
    ? (plan as string).charAt(0).toUpperCase() + (plan as string).slice(1)
    : 'Starter';

  const isDevMode = dev === '1';

  // Auto-redirect to register after 5 seconds
  useEffect(() => {
    if (!router.isReady) return;
    const timer = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          router.push(`/register?plan=${plan || 'starter'}&payment=success`);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [router.isReady, plan, router]);

  return (
    <>
      <Head>
        <title>Payment Successful — MyNetTax</title>
      </Head>
      <div className={styles.container}>
        <main className={styles.main} style={{ maxWidth: 520, textAlign: 'center' }}>

          {/* Success icon */}
          <div style={{
            width: 80, height: 80, borderRadius: '50%',
            background: 'rgba(13,148,136,0.15)', border: '2px solid #0d9488',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '2.5rem', margin: '0 auto 1.5rem',
          }}>
            ✓
          </div>

          <h1 className={styles.title} style={{ fontSize: '1.75rem', marginBottom: '1rem' }}>
            {isDevMode ? 'Test Payment Confirmed' : 'Payment Successful!'}
          </h1>

          <p className={styles.description} style={{ marginBottom: '0.5rem' }}>
            Your <strong style={{ color: '#14b8a6' }}>{planName}</strong> plan is ready.
            {isDevMode && (
              <span style={{ color: '#f59e0b', display: 'block', fontSize: '0.8rem', marginTop: '0.25rem' }}>
                (Dev mode — no real charge)
              </span>
            )}
          </p>

          {/* Benefits reminder */}
          <div style={{
            width: '100%', padding: '1.25rem', borderRadius: 12,
            background: 'rgba(13,148,136,0.08)', border: '1px solid rgba(13,148,136,0.25)',
            margin: '1.5rem 0', textAlign: 'left', lineHeight: 2,
            color: '#94a3b8', fontSize: '0.875rem',
          }}>
            <div>✓ 14-day free trial starts when you register</div>
            <div>✓ No charge until your trial ends</div>
            <div>✓ Cancel anytime from your dashboard</div>
            <div>✓ HMRC 6-year secure report storage included</div>
          </div>

          {/* Auto-redirect countdown */}
          <p style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '1.5rem' }}>
            Redirecting to create your account in <strong style={{ color: '#14b8a6' }}>{countdown}s</strong>…
          </p>

          <Link
            href={`/register?plan=${plan || 'starter'}&payment=success`}
            className={styles.button}
            style={{ display: 'inline-block', textDecoration: 'none', padding: '0.875rem 2rem', borderRadius: 10 }}
          >
            Create My Account →
          </Link>

          {session_id && !isDevMode && (
            <p style={{ marginTop: '1.5rem', color: '#475569', fontSize: '0.75rem' }}>
              Ref: {session_id}
            </p>
          )}
        </main>
      </div>
    </>
  );
}
