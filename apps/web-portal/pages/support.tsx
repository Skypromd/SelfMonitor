import Head from 'next/head';
import { useState, type FormEvent } from 'react';
import styles from '../styles/Home.module.css';

type SupportPageProps = {
  token: string;
};

type TicketPriority = 'low' | 'medium' | 'high';
type TicketCategory = 'billing' | 'technical' | 'account' | 'feature' | 'other';
type SubmitState = 'idle' | 'loading' | 'success' | 'error';

const FAQ_ITEMS = [
  {
    q: 'How do I connect my bank account?',
    a: 'Go to Dashboard → Bank Connections, click "Add Bank", and follow the secure Open Banking flow. Supported banks include Barclays, HSBC, Lloyds, Monzo, Starling, and 40+ more.',
  },
  {
    q: 'How do I cancel my subscription?',
    a: 'Go to Billing → Your Plan → Cancel Subscription. You keep access until the end of your billing period. No hidden fees.',
  },
  {
    q: 'Is my financial data secure?',
    a: 'Yes. All data is encrypted with AES-256 at rest and in transit. We store data in UK data centres and are fully GDPR compliant. We never sell your data.',
  },
  {
    q: 'How does HMRC auto-submission work?',
    a: 'On the Pro and Business plans, SelfMonitor can submit your Self Assessment tax return directly to HMRC via the MTD API. You review and approve before anything is sent.',
  },
  {
    q: 'Can I export my data?',
    a: 'Yes — go to Reports and click "Export CSV / PDF". You can also export invoices to Xero and QuickBooks from the Invoices page.',
  },
  {
    q: 'What happens when my free trial ends?',
    a: "After 14 days your account switches to the Free plan automatically. No charge is made unless you enter payment details. You can upgrade anytime from the Billing page.",
  },
  {
    q: 'How do I invite a team member? (Business plan)',
    a: 'Go to Profile → Team Members → Invite. The invited person receives an email with a secure sign-up link. You control their permissions.',
  },
  {
    q: 'I found a bug — how do I report it?',
    a: "Use the form below, select category 'Technical Issue', and set priority to 'High'. Screenshots are very helpful — paste a description of what you expected vs what happened.",
  },
];

export default function SupportPage({ token }: SupportPageProps) {
  // ── Feedback (star rating) ─────────────────────────────────────────────────
  const [rating, setRating] = useState(0);
  const [hoverRating, setHoverRating] = useState(0);
  const [feedbackMsg, setFeedbackMsg] = useState('');
  const [feedbackState, setFeedbackState] = useState<SubmitState>('idle');

  // ── Support ticket ─────────────────────────────────────────────────────────
  const [subject, setSubject] = useState('');
  const [category, setCategory] = useState<TicketCategory>('technical');
  const [priority, setPriority] = useState<TicketPriority>('medium');
  const [ticketMsg, setTicketMsg] = useState('');
  const [ticketState, setTicketState] = useState<SubmitState>('idle');

  // ── FAQ accordion ──────────────────────────────────────────────────────────
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleFeedback = async (e: FormEvent) => {
    e.preventDefault();
    if (!rating) return;
    setFeedbackState('loading');
    // Simulate API — replace with real endpoint when backend is ready
    await new Promise((resolve) => setTimeout(resolve, 800));
    setFeedbackState('success');
    setRating(0);
    setFeedbackMsg('');
  };

  const handleTicket = async (e: FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !ticketMsg.trim()) return;
    setTicketState('loading');
    // Simulate API — replace with real endpoint when backend is ready
    await new Promise((resolve) => setTimeout(resolve, 900));
    setTicketState('success');
    setSubject('');
    setTicketMsg('');
    setCategory('technical');
    setPriority('medium');
  };

  const priorityColor: Record<TicketPriority, string> = {
    low: '#34d399',
    medium: '#f59e0b',
    high: '#f87171',
  };

  return (
    <>
      <Head>
        <title>Support &amp; Feedback — SelfMonitor</title>
      </Head>
      <div className={styles.dashboard}>
        <div className={styles.pageHeader}>
          <p className={styles.pageEyebrow}>Help Centre</p>
          <h1 className={styles.pageTitle}>💬 Support &amp; Feedback</h1>
          <p className={styles.pageLead}>
            We read every message. Average response time: <strong style={{ color: '#14b8a6' }}>under 4 hours</strong> on business days.
          </p>
        </div>

        {/* ── AI Chat banner ─────────────────────────────────────────────── */}
        <div style={{
          background: 'linear-gradient(135deg, #1e293b 0%, #0f2040 100%)',
          border: '1px solid #334155',
          borderRadius: 16,
          padding: '1.5rem 2rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '1rem',
          flexWrap: 'wrap',
          marginBottom: '2rem',
        }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '.6rem', marginBottom: '.4rem' }}>
              <span style={{ fontSize: '1.5rem' }}>🤖</span>
              <strong style={{ fontSize: '1.1rem', color: '#f1f5f9' }}>AI Support Agent — available 24/7</strong>
            </div>
            <p style={{ color: '#94a3b8', fontSize: '.9rem', margin: 0 }}>
              Get instant answers: bank connections, billing, HMRC, invoices and more. Escalates to a human if needed.
            </p>
          </div>
          <a
            href="http://localhost:3001"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              background: '#6366f1',
              color: '#fff',
              padding: '.7rem 1.6rem',
              borderRadius: 12,
              fontWeight: 700,
              fontSize: '.95rem',
              textDecoration: 'none',
              whiteSpace: 'nowrap',
              flexShrink: 0,
            }}
          >
            Chat now ↗
          </a>
        </div>

        {/* ── Contact cards ─────────────────────────────────────────────── */}
        <div className={styles.supportContactGrid}>
          <div className={styles.supportContactCard}>
            <span className={styles.supportContactIcon}>📧</span>
            <div>
              <strong className={styles.supportContactTitle}>Email</strong>
              <p className={styles.supportContactSub}>
                <a href="mailto:support@selfmonitor.app" className={styles.supportLink}>
                  support@selfmonitor.app
                </a>
              </p>
            </div>
          </div>
          <div className={styles.supportContactCard}>
            <span className={styles.supportContactIcon}>📖</span>
            <div>
              <strong className={styles.supportContactTitle}>Help Docs</strong>
              <p className={styles.supportContactSub}>
                <a href="https://selfmonitor.app/help" target="_blank" rel="noreferrer" className={styles.supportLink}>
                  selfmonitor.app/help
                </a>
              </p>
            </div>
          </div>
          <div className={styles.supportContactCard}>
            <span className={styles.supportContactIcon}>💬</span>
            <div>
              <strong className={styles.supportContactTitle}>Live Chat</strong>
              <p className={styles.supportContactSub} style={{ color: '#f59e0b' }}>
                Coming soon — Pro &amp; Business plans
              </p>
            </div>
          </div>
          <div className={styles.supportContactCard}>
            <span className={styles.supportContactIcon}>📞</span>
            <div>
              <strong className={styles.supportContactTitle}>Phone</strong>
              <p className={styles.supportContactSub} style={{ color: '#64748b' }}>
                Business plan · Mon–Fri 9–5 GMT
              </p>
            </div>
          </div>
        </div>

        {/* ── Feedback (star rating) ────────────────────────────────────── */}
        <div className={styles.subContainer}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>⭐ Rate Your Experience</h2>
            <p className={styles.sectionSubtitle}>
              Quick 30-second feedback helps us prioritise improvements.
            </p>
          </div>

          {feedbackState === 'success' ? (
            <div className={styles.supportSuccessBanner}>
              ✅ Thank you for your feedback! It helps us build a better product.
            </div>
          ) : (
            <form onSubmit={handleFeedback} className={styles.feedbackForm}>
              <div className={styles.starRow}>
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    className={styles.starBtn}
                    style={{
                      color: (hoverRating || rating) >= star ? '#f59e0b' : '#334155',
                      fontSize: '2rem',
                    }}
                    onClick={() => setRating(star)}
                    onMouseEnter={() => setHoverRating(star)}
                    onMouseLeave={() => setHoverRating(0)}
                    aria-label={`Rate ${star} star${star !== 1 ? 's' : ''}`}
                  >
                    ★
                  </button>
                ))}
                {rating > 0 && (
                  <span className={styles.ratingLabel}>
                    {['', 'Poor', 'Below average', 'Average', 'Good', 'Excellent'][rating]}
                  </span>
                )}
              </div>

              <textarea
                className={styles.supportTextarea}
                placeholder="Tell us more (optional) — what's working well, what could be better?"
                rows={4}
                value={feedbackMsg}
                onChange={(e) => setFeedbackMsg(e.target.value)}
              />

              <button
                className={styles.button}
                type="submit"
                disabled={!rating || feedbackState === 'loading'}
              >
                {feedbackState === 'loading' ? 'Sending...' : 'Submit Feedback'}
              </button>
            </form>
          )}
        </div>

        {/* ── Support ticket ────────────────────────────────────────────── */}
        <div className={styles.subContainer}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>🎫 Submit a Support Ticket</h2>
            <p className={styles.sectionSubtitle}>
              Describe your issue in detail. We'll reply to <strong style={{ color: '#f1f5f9' }}>your account email</strong>.
            </p>
          </div>

          {ticketState === 'success' ? (
            <div className={styles.supportSuccessBanner}>
              ✅ Ticket submitted! You'll receive a confirmation email shortly. Reference: #SM-{Math.floor(Math.random() * 90000) + 10000}
            </div>
          ) : (
            <form onSubmit={handleTicket} className={styles.ticketForm}>
              <div className={styles.ticketFieldRow}>
                <label className={styles.filterField}>
                  <span>Category</span>
                  <select
                    className={styles.categorySelect}
                    value={category}
                    onChange={(e) => setCategory(e.target.value as TicketCategory)}
                  >
                    <option value="billing">💳 Billing / Subscription</option>
                    <option value="technical">🔧 Technical Issue</option>
                    <option value="account">👤 Account / Login</option>
                    <option value="feature">💡 Feature Request</option>
                    <option value="other">❓ Other</option>
                  </select>
                </label>

                <label className={styles.filterField}>
                  <span>Priority</span>
                  <select
                    className={styles.categorySelect}
                    value={priority}
                    onChange={(e) => setPriority(e.target.value as TicketPriority)}
                    style={{ color: priorityColor[priority] }}
                  >
                    <option value="low">🟢 Low — general question</option>
                    <option value="medium">🟡 Medium — affecting my work</option>
                    <option value="high">🔴 High — blocking me completely</option>
                  </select>
                </label>
              </div>

              <input
                className={styles.input}
                placeholder="Subject — e.g. 'Bank connection failing since yesterday'"
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                required
              />

              <textarea
                className={styles.supportTextarea}
                placeholder="Describe the issue in detail. Include: what you were trying to do, what happened, any error messages, and steps to reproduce if possible."
                rows={6}
                value={ticketMsg}
                onChange={(e) => setTicketMsg(e.target.value)}
                required
              />

              <div className={styles.ticketFormFooter}>
                <p className={styles.ticketEta}>
                  Expected response:{' '}
                  <strong style={{ color: priorityColor[priority] }}>
                    {priority === 'high' ? 'within 2 hours' : priority === 'medium' ? 'within 4 hours' : 'within 1 business day'}
                  </strong>
                </p>
                <button
                  className={styles.button}
                  type="submit"
                  disabled={!subject.trim() || !ticketMsg.trim() || ticketState === 'loading'}
                >
                  {ticketState === 'loading' ? 'Submitting...' : '🎫 Submit Ticket'}
                </button>
              </div>
            </form>
          )}
        </div>

        {/* ── FAQ ───────────────────────────────────────────────────────── */}
        <div className={styles.subContainer}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>❓ Frequently Asked Questions</h2>
            <p className={styles.sectionSubtitle}>{FAQ_ITEMS.length} most common questions — click to expand.</p>
          </div>
          <div className={styles.faqList}>
            {FAQ_ITEMS.map((item, idx) => (
              <div key={idx} className={styles.faqItem}>
                <button
                  className={styles.faqQuestion}
                  onClick={() => setOpenFaq(openFaq === idx ? null : idx)}
                  type="button"
                >
                  <span>{item.q}</span>
                  <span className={styles.faqChevron} style={{ transform: openFaq === idx ? 'rotate(180deg)' : 'none' }}>
                    ▾
                  </span>
                </button>
                {openFaq === idx && (
                  <div className={styles.faqAnswer}>{item.a}</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* ── Status strip ─────────────────────────────────────────────── */}
        <div className={styles.supportStatusStrip}>
          <span>🟢 All systems operational</span>
          <span>·</span>
          <span>Uptime this month: 99.94%</span>
          <span>·</span>
          <a href="https://status.selfmonitor.app" target="_blank" rel="noreferrer" className={styles.supportLink}>
            Status page →
          </a>
        </div>
      </div>
    </>
  );
}
