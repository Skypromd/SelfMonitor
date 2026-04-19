import { Bot, Send, User } from 'lucide-react';
import { useRouter } from 'next/router';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties } from 'react';
import styles from '../styles/Home.module.css';


const AI_AGENT_URL       = process.env.NEXT_PUBLIC_AI_AGENT_SERVICE_URL    || '/api/agent';
const ORCHESTRATOR_URL   = process.env.NEXT_PUBLIC_ORCHESTRATOR_SERVICE_URL || '/api/orchestrator';

type Role = 'user' | 'assistant';

type Message = {
  id: string;
  role: Role;
  content: string;
  timestamp: Date;
  warnings?: string[];
  agentsUsed?: string[];
  confidence?: number;
};

type AssistantPageProps = { token: string };

type AdvisorFocus = 'general' | 'mortgage' | 'tax';

const QUICK_PROMPTS = [
  'Prepare my tax return for this year',
  'How much tax do I owe?',
  'Check my receipts and unmatched items',
  'Analyse my income and expenses',
  'What are my HMRC deadlines?',
  'What expenses can I claim as self-employed?',
];

export default function AssistantPage({ token }: AssistantPageProps) {
  const router = useRouter();
  const [advisorFocus, setAdvisorFocus] = useState<AdvisorFocus>('general');
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '0',
      role: 'assistant',
      content: "Hi! I'm your MyNetTax AI assistant. I can help with tax questions, expense planning, invoicing, and financial advice for self-employed individuals. What can I help you with today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  const headers = useMemo(
    () => ({
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    }),
    [token],
  );

  // Check agent status on mount
  useEffect(() => {
    fetch(`${AI_AGENT_URL}/status`, { headers })
      .then((r) => r.json())
      .then((d) => setAgentStatus(d?.status || 'online'))
      .catch(() => setAgentStatus(null));
  }, [headers]);

  useEffect(() => {
    const q = router.query?.mode;
    if (q === 'mortgage') setMortgageMode(true);
  }, [router.query?.mode]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    const userMsg: Message = { id: crypto.randomUUID(), role: 'user', content: text.trim(), timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    const chatContext = {
      user_type: 'self_employed',
      currency: 'GBP',
      region: 'UK',
      ...(advisorFocus === 'mortgage' ? { advisor_mode: 'mortgage' as const } : {}),
      ...(advisorFocus === 'tax' ? { advisor_mode: 'tax' as const } : {}),
    };

    try {
      let res: Response;
      if (advisorFocus === 'mortgage' || advisorFocus === 'tax') {
        res = await fetch(`${AI_AGENT_URL}/chat`, {
          method: 'POST',
          headers,
          body: JSON.stringify({
            message: text.trim(),
            session_id: sessionId,
            language: 'en',
            context: chatContext,
          }),
        });
      } else {
        res = await fetch(`${ORCHESTRATOR_URL}/orchestrate`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ message: text.trim(), session_id: sessionId, language: 'en' }),
        });
        if (!res.ok && (res.status === 503 || res.status === 502 || res.status === 404)) {
          res = await fetch(`${AI_AGENT_URL}/chat`, {
            method: 'POST',
            headers,
            body: JSON.stringify({
              message: text.trim(),
              session_id: sessionId,
              language: 'en',
              context: chatContext,
            }),
          });
        }
      }

      if (res.ok) {
        const data = await res.json();
        const reply: Message = {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: data.response || data.message || JSON.stringify(data),
          timestamp: new Date(),
          warnings: data.warnings ?? [],
          agentsUsed: data.agents_used ?? [],
          confidence: data.confidence,
        };
        setMessages((prev) => [...prev, reply]);
      } else if (res.status === 503 || res.status === 500) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: "I'm having trouble connecting right now. Please try again shortly.",
            timestamp: new Date(),
          },
        ]);
      } else {
        const err = await res.json().catch(() => ({}));
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            role: 'assistant',
            content: `Error: ${(err as any).detail || res.statusText}`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: 'Unable to reach the AI service. Please ensure the backend is running.',
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const formatTime = (d: Date) =>
    d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });

  return (
    <div className={styles.pageContainerFull} style={{ display: 'flex', gap: '1.5rem', height: 'calc(100vh - 120px)' }}>
      {/* Sidebar */}
      <div style={{ width: 260, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div className={styles.card}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.5rem' }}>
            <Bot size={20} style={{ color: 'var(--lp-accent-teal)' }} />
            <strong style={{ fontSize: '0.95rem' }}>AI Assistant</strong>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: agentStatus === 'online' ? '#34d399' : '#f87171', display: 'inline-block' }} />
            <span style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)' }}>
              {agentStatus === 'online' ? 'Online' : agentStatus ? `Status: ${agentStatus}` : 'Connecting…'}
            </span>
          </div>
          <label style={{ display: 'block', marginTop: 12, fontSize: '0.78rem', color: 'var(--lp-text-muted)' }}>
            <span style={{ display: 'block', marginBottom: 4, fontWeight: 600 }}>Focus</span>
            <select
              value={advisorFocus}
              onChange={(e) => setAdvisorFocus(e.target.value as AdvisorFocus)}
              style={{
                width: '100%',
                padding: '6px 8px',
                borderRadius: 8,
                border: '1px solid var(--lp-border)',
                background: 'var(--lp-bg-surface)',
                color: 'var(--lp-text)',
                fontSize: '0.78rem',
              }}
            >
              <option value="general">General</option>
              <option value="tax">UK tax (informational — not advice)</option>
              <option value="mortgage">Mortgage readiness (informational)</option>
            </select>
          </label>
        </div>

        <div className={styles.card}>
          <p style={{ fontSize: '0.8rem', color: 'var(--lp-text-muted)', marginBottom: '0.75rem', fontWeight: 600 }}>QUICK PROMPTS</p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => sendMessage(p)}
                disabled={loading}
                style={{
                  textAlign: 'left',
                  padding: '0.45rem 0.7rem',
                  background: 'var(--lp-bg-surface)',
                  border: '1px solid var(--lp-border)',
                  borderRadius: 8,
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  color: 'var(--lp-text)',
                  transition: 'border-color 0.15s',
                } as CSSProperties}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Messages */}
        <div className={styles.card} style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: '1.25rem' }}>
          {messages.map((msg) => (
            <div
              key={msg.id}
              style={{
                display: 'flex', gap: 10,
                flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                alignItems: 'flex-start',
              }}
            >
              <div style={{
                width: 32, height: 32, borderRadius: '50%', flexShrink: 0,
                background: msg.role === 'assistant' ? 'rgba(13,148,136,0.15)' : 'rgba(99,102,241,0.15)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                {msg.role === 'assistant'
                  ? <Bot size={16} style={{ color: 'var(--lp-accent-teal)' }} />
                  : <User size={16} style={{ color: '#818cf8' }} />}
              </div>
              <div style={{ maxWidth: '72%' }}>
                <div style={{
                  background: msg.role === 'user' ? 'rgba(99,102,241,0.12)' : 'var(--lp-bg-surface)',
                  border: '1px solid var(--lp-border)', borderRadius: 12,
                  padding: '0.6rem 0.9rem',
                  borderTopRightRadius: msg.role === 'user' ? 4 : 12,
                  borderTopLeftRadius: msg.role === 'assistant' ? 4 : 12,
                }}>
                  <p style={{ margin: 0, fontSize: '0.9rem', lineHeight: 1.55, whiteSpace: 'pre-wrap', color: 'var(--lp-text)' }}>
                    {msg.content}
                  </p>
                </div>
                {msg.role === 'assistant' && msg.warnings && msg.warnings.length > 0 && (
                  <div style={{ marginTop: 6 }}>
                    {msg.warnings.map((w, i) => (
                      <div key={i} style={{ fontSize: '0.78rem', color: '#b45309', background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)', borderRadius: 6, padding: '4px 8px', marginTop: 3 }}>
                        ⚠️ {w}
                      </div>
                    ))}
                  </div>
                )}
                {msg.role === 'assistant' && msg.agentsUsed && msg.agentsUsed.length > 0 && (
                  <div style={{ marginTop: 4, display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {msg.agentsUsed.map(a => (
                      <span key={a} style={{ fontSize: '0.68rem', background: 'rgba(13,148,136,0.1)', color: 'var(--lp-accent-teal)', border: '1px solid rgba(13,148,136,0.2)', borderRadius: 999, padding: '1px 7px' }}>
                        {a}
                      </span>
                    ))}
                  </div>
                )}
                <div style={{ fontSize: '0.72rem', color: 'var(--lp-text-muted)', marginTop: 3, textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                  {formatTime(msg.timestamp)}
                </div>
              </div>
            </div>
          ))}
          {loading && (
            <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
              <div style={{ width: 32, height: 32, borderRadius: '50%', background: 'rgba(13,148,136,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <Bot size={16} style={{ color: 'var(--lp-accent-teal)' }} />
              </div>
              <div style={{ background: 'var(--lp-bg-surface)', border: '1px solid var(--lp-border)', borderRadius: 12, borderTopLeftRadius: 4, padding: '0.6rem 1rem' }}>
                <div style={{ display: 'flex', gap: 4, alignItems: 'center', height: 20 }}>
                  {[0, 1, 2].map((i) => (
                    <span key={i} style={{
                      width: 7, height: 7, borderRadius: '50%', background: 'var(--lp-accent-teal)',
                      opacity: 0.6, animation: `pulse 1.2s ease-in-out ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {/* Input */}
        <form onSubmit={handleSubmit} style={{ marginTop: '0.75rem', display: 'flex', gap: 8 }}>
          <input
            className={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about tax, invoices, expenses…"
            disabled={loading}
            style={{ flex: 1 }}
          />
          <button
            type="submit"
            className={styles.btn}
            disabled={!input.trim() || loading}
            style={{ display: 'flex', alignItems: 'center', gap: 6, whiteSpace: 'nowrap' }}
          >
            <Send size={15} /> Send
          </button>
        </form>

        <style jsx>{`
          @keyframes pulse {
            0%, 80%, 100% { transform: scale(0.6); opacity: 0.3; }
            40% { transform: scale(1); opacity: 1; }
          }
        `}</style>
      </div>
    </div>
  );
}
