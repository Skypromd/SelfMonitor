import { Copy, Gift, TrendingUp, Users } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const REFERRAL_SERVICE_URL =
  process.env.NEXT_PUBLIC_REFERRAL_SERVICE_URL || '/api/referrals';

type ReferralCode = {
  id: string;
  code: string;
  campaign_type: string;
  reward_amount: number;
  max_uses: number;
  is_active: boolean;
  created_at: string;
  expires_at?: string;
};

type ReferralStats = {
  total_referrals: number;
  active_referrals: number;
  total_earned: number;
  pending_rewards: number;
  conversions_this_month: number;
};

type LeaderboardEntry = {
  user_id: string;
  rank: number;
  referrals: number;
  earned: number;
};

type ReferralsPageProps = { token: string };

export default function ReferralsPage({ token }: ReferralsPageProps) {
  const [stats, setStats] = useState<ReferralStats | null>(null);
  const [codes, setCodes] = useState<ReferralCode[]>([]);
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState('');
  const [creating, setCreating] = useState(false);
  const [createMsg, setCreateMsg] = useState('');
  const [validateCode, setValidateCode] = useState('');
  const [validateMsg, setValidateMsg] = useState('');
  const [validating, setValidating] = useState(false);

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [statsRes, lbRes] = await Promise.all([
        fetch(`${REFERRAL_SERVICE_URL}/stats`, { headers }),
        fetch(`${REFERRAL_SERVICE_URL}/leaderboard`, { headers }),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (lbRes.ok) {
        const data = await lbRes.json();
        setLeaderboard(Array.isArray(data) ? data : data.leaderboard || []);
      }
    } catch {
      setError('Unable to reach referral service.');
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const copyCode = async (code: string) => {
    await navigator.clipboard.writeText(code).catch(() => {});
    setCopied(code);
    setTimeout(() => setCopied(''), 2000);
  };

  const createCode = async () => {
    setCreating(true);
    setCreateMsg('');
    try {
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      const user_id = payload.sub || 'me';
      const res = await fetch(`${REFERRAL_SERVICE_URL}/referral-codes`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ user_id, campaign_type: 'standard', reward_amount: 25, max_uses: 50 }),
      });
      if (res.ok) {
        const code: ReferralCode = await res.json();
        setCodes((prev) => [code, ...prev]);
        setCreateMsg(`Code created: ${code.code}`);
        fetchAll();
      } else {
        const d = await res.json().catch(() => ({}));
        setCreateMsg(`Error: ${d.detail || res.statusText}`);
      }
    } catch {
      setCreateMsg('Network error — referral service may not be running.');
    } finally {
      setCreating(false);
    }
  };

  const validate = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidating(true);
    setValidateMsg('');
    try {
      const res = await fetch(`${REFERRAL_SERVICE_URL}/validate-referral`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ code: validateCode }),
      });
      const data = await res.json();
      if (res.ok) {
        setValidateMsg(`✓ Valid referral code! Reward: £${data.reward_amount ?? '—'}`);
      } else {
        setValidateMsg(`✗ ${data.detail || 'Invalid code'}`);
      }
    } catch {
      setValidateMsg('Network error.');
    } finally {
      setValidating(false);
    }
  };

  const fmt = (v: number) => `£${v.toFixed(2)}`;

  if (loading) return <div className={styles.pageContainer}><p style={{ color: 'var(--lp-text-muted)' }}>Loading referrals…</p></div>;

  return (
    <div className={styles.pageContainer}>
      <div className={styles.header}>
        <h1 className={styles.title}>Referral Programme</h1>
        <button className={styles.btn} onClick={createCode} disabled={creating}>
          <Gift size={16} style={{ marginRight: 6 }} /> {creating ? 'Generating…' : 'Generate Code'}
        </button>
      </div>

      {error && <p className={styles.error}>{error}</p>}
      {createMsg && <p style={{ color: createMsg.startsWith('Error') || createMsg.startsWith('Network') ? '#f87171' : '#34d399', marginBottom: '1rem' }}>{createMsg}</p>}

      {/* Stats */}
      {stats && (
        <div className={styles.grid} style={{ marginBottom: '1.5rem' }}>
          {[
            { label: 'Total Referrals', value: stats.total_referrals, icon: <Users size={20} /> },
            { label: 'Active Referrals', value: stats.active_referrals, icon: <TrendingUp size={20} /> },
            { label: 'Total Earned', value: fmt(stats.total_earned), icon: <Gift size={20} /> },
            { label: 'Pending Rewards', value: fmt(stats.pending_rewards), icon: <Copy size={20} /> },
            { label: 'Conversions This Month', value: stats.conversions_this_month, icon: <TrendingUp size={20} /> },
          ].map((c) => (
            <div key={c.label} className={styles.card}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: 'var(--lp-text-muted)' }}>
                {c.icon} <span style={{ fontSize: '0.82rem' }}>{c.label}</span>
              </div>
              <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>{c.value}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Referral Codes */}
        <div>
          <div className={styles.card}>
            <h3 style={{ marginBottom: '1rem' }}>Your Referral Codes</h3>
            {codes.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--lp-text-muted)' }}>
                <Gift size={36} style={{ marginBottom: 8, opacity: 0.4 }} />
                <p style={{ fontSize: '0.88rem' }}>No codes yet. Generate your first referral code.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {codes.map((rc) => (
                  <div key={rc.id} style={{ background: 'var(--lp-bg-surface)', borderRadius: 10, padding: '0.75rem 1rem', border: '1px solid var(--lp-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <code style={{ fontSize: '1.1rem', fontWeight: 700, letterSpacing: 2, color: 'var(--lp-accent-teal)' }}>{rc.code}</code>
                      <button
                        onClick={() => copyCode(rc.code)}
                        style={{ background: 'none', border: '1px solid var(--lp-border)', borderRadius: 6, padding: '0.25rem 0.6rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.8rem', color: copied === rc.code ? '#34d399' : 'var(--lp-text-muted)' }}
                      >
                        <Copy size={13} /> {copied === rc.code ? 'Copied!' : 'Copy'}
                      </button>
                    </div>
                    <div style={{ fontSize: '0.78rem', color: 'var(--lp-text-muted)', marginTop: 4 }}>
                      Reward: {fmt(rc.reward_amount)} · Max: {rc.max_uses} uses · {rc.campaign_type}
                    </div>
                    {rc.expires_at && (
                      <div style={{ fontSize: '0.75rem', color: '#fbbf24', marginTop: 2 }}>
                        Expires: {new Date(rc.expires_at).toLocaleDateString('en-GB')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Validate a code */}
          <div className={styles.card} style={{ marginTop: '1.25rem' }}>
            <h3 style={{ marginBottom: '0.75rem' }}>Validate a Code</h3>
            <form onSubmit={validate} style={{ display: 'flex', gap: 8 }}>
              <input
                className={styles.input}
                value={validateCode}
                onChange={(e) => setValidateCode(e.target.value.toUpperCase())}
                placeholder="Enter referral code"
                style={{ flex: 1, letterSpacing: 1 }}
                required
              />
              <button type="submit" className={styles.btn} disabled={validating}>
                {validating ? '…' : 'Check'}
              </button>
            </form>
            {validateMsg && (
              <p style={{ marginTop: 8, fontSize: '0.88rem', color: validateMsg.startsWith('✓') ? '#34d399' : '#f87171' }}>
                {validateMsg}
              </p>
            )}
          </div>
        </div>

        {/* Leaderboard */}
        <div className={styles.card}>
          <h3 style={{ marginBottom: '1rem' }}>🏆 Referral Leaderboard</h3>
          {leaderboard.length === 0 ? (
            <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.88rem' }}>No leaderboard data yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {leaderboard.slice(0, 10).map((entry, i) => (
                <div key={entry.user_id || i} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  padding: '0.55rem 0.75rem', borderRadius: 8,
                  background: i < 3 ? `rgba(13,148,136,${0.12 - i * 0.03})` : 'var(--lp-bg-surface)',
                  border: '1px solid var(--lp-border)',
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ width: 24, textAlign: 'center', fontWeight: 700, color: i === 0 ? '#fbbf24' : i === 1 ? '#94a3b8' : i === 2 ? '#cd7f32' : 'var(--lp-text-muted)', fontSize: '0.9rem' }}>
                      {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                    </span>
                    <span style={{ fontSize: '0.85rem', fontFamily: 'monospace', color: 'var(--lp-text)' }}>
                      {typeof entry.user_id === 'string' ? entry.user_id.slice(0, 12) + '…' : '—'}
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.88rem', fontWeight: 600 }}>{entry.referrals ?? '—'} referrals</div>
                    <div style={{ fontSize: '0.75rem', color: '#34d399' }}>{fmt(entry.earned ?? 0)}</div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* How it works */}
          <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(13,148,136,0.06)', borderRadius: 10, border: '1px solid rgba(13,148,136,0.2)' }}>
            <p style={{ fontWeight: 600, marginBottom: '0.5rem', fontSize: '0.9rem' }}>How it works</p>
            {[
              '1. Generate your unique referral code above',
              '2. Share it with friends, colleagues, or clients',
              '3. When they sign up and start a paid plan, you earn £25',
              '4. Rewards stack — no limit on how much you can earn',
            ].map((s) => (
              <p key={s} style={{ fontSize: '0.82rem', color: 'var(--lp-text-muted)', marginBottom: 4 }}>{s}</p>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
