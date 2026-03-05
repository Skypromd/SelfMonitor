import Head from 'next/head';
import { useState, useEffect, useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';

// ── Types ──────────────────────────────────────────────────────────────────────
type Role = 'user' | 'assistant' | 'system';
type MessageStatus = 'sent' | 'sending' | 'error';
type TabId = 'chat' | 'ticket' | 'status';

interface ChatMessage {
  id:      string;
  role:    Role;
  content: string;
  ts:      Date;
  intent?: string;
  status?: MessageStatus;
}

interface TicketForm {
  user_email: string;
  category:   string;
  priority:   string;
  subject:    string;
  message:    string;
}

// ── Config ─────────────────────────────────────────────────────────────────────
const WS_URL  = process.env.NEXT_PUBLIC_SUPPORT_WS_URL  || 'ws://localhost:8020';
const API_URL = process.env.NEXT_PUBLIC_SUPPORT_API_URL || 'http://localhost:8020';

function genId() {
  return Math.random().toString(36).slice(2, 10);
}

function genSessionId() {
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

function fmtTime(date: Date) {
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

// ── Status indicator ──────────────────────────────────────────────────────────
const SERVICES = [
  { name: 'Authentication',    status: 'operational' },
  { name: 'Bank Sync',         status: 'operational' },
  { name: 'Invoice Generator', status: 'operational' },
  { name: 'HMRC MTD API',      status: 'degraded'    },
  { name: 'AI Assistant',      status: 'operational' },
];

// ── Main page ──────────────────────────────────────────────────────────────────
export default function SupportPortal() {
  const [tab,   setTab]   = useState<TabId>('chat');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input,  setInput]  = useState('');
  const [wsState, setWsState] = useState<'connecting' | 'open' | 'closed'>('connecting');
  const [sessionId] = useState(genSessionId);
  const [isTyping, setIsTyping] = useState(false);
  const [userEmail, setUserEmail] = useState('');

  // Ticket form
  const [ticket, setTicket] = useState<TicketForm>({
    user_email: '', category: 'technical', priority: 'medium', subject: '', message: '',
  });
  const [ticketState, setTicketState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');

  const wsRef      = useRef<WebSocket | null>(null);
  const bottomRef  = useRef<HTMLDivElement | null>(null);
  const inputRef   = useRef<HTMLTextAreaElement | null>(null);

  // ── WebSocket ────────────────────────────────────────────────────────────────
  const connect = useCallback(() => {
    setWsState('connecting');
    const ws = new WebSocket(`${WS_URL}/ws/chat/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsState('open');
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.role === 'assistant') {
          setIsTyping(false);
          setMessages(prev => [...prev, {
            id:     genId(),
            role:   'assistant',
            content: data.content,
            ts:     new Date(),
            intent: data.intent,
          }]);
        }
      } catch { /* ignore */ }
    };

    ws.onerror = () => {
      setWsState('closed');
      setIsTyping(false);
    };

    ws.onclose = () => {
      setWsState('closed');
      setIsTyping(false);
    };
  }, [sessionId]);

  useEffect(() => {
    connect();
    return () => { wsRef.current?.close(); };
  }, [connect]);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // ── Send message ─────────────────────────────────────────────────────────────
  function sendMessage(text?: string) {
    const content = (text ?? input).trim();
    if (!content || wsState !== 'open') return;

    setMessages(prev => [...prev, {
      id: genId(), role: 'user', content, ts: new Date(), status: 'sent',
    }]);
    setInput('');
    setIsTyping(true);

    wsRef.current?.send(JSON.stringify({ content, user_email: userEmail || undefined }));
    inputRef.current?.focus();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  // ── Submit ticket ─────────────────────────────────────────────────────────────
  async function submitTicket(e: React.FormEvent) {
    e.preventDefault();
    setTicketState('sending');
    try {
      const res = await fetch(`${API_URL}/tickets`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(ticket),
      });
      if (!res.ok) throw new Error(await res.text());
      setTicketState('sent');
      setTicket({ user_email: '', category: 'technical', priority: 'medium', subject: '', message: '' });
    } catch {
      setTicketState('error');
    }
  }

  // ── Quick suggestions ─────────────────────────────────────────────────────────
  const SUGGESTIONS = [
    'How do I connect my bank?',
    'What are the pricing plans?',
    'How does HMRC submission work?',
    'I forgot my password',
    'How do I export my data?',
  ];

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <>
      <Head>
        <title>SelfMonitor Support</title>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <div style={s.shell}>
        {/* ── Header ── */}
        <header style={s.header}>
          <div style={s.headerBrand}>
            <span style={s.logo}>SM</span>
            <span style={s.brandText}>SelfMonitor <span style={{ color: 'var(--muted)', fontWeight: 400 }}>Support</span></span>
          </div>
          <div style={s.headerRight}>
            <span style={{ ...s.dot, background: wsState === 'open' ? 'var(--success)' : wsState === 'connecting' ? 'var(--warn)' : 'var(--danger)' }} />
            <span style={s.wsLabel}>
              {wsState === 'open' ? 'Connected' : wsState === 'connecting' ? 'Connecting…' : 'Offline'}
            </span>
            {wsState === 'closed' && (
              <button style={s.reconnectBtn} onClick={connect}>Reconnect</button>
            )}
          </div>
        </header>

        {/* ── Tabs ── */}
        <nav style={s.tabs}>
          {(['chat', 'ticket', 'status'] as TabId[]).map(t => (
            <button
              key={t}
              style={{ ...s.tab, ...(tab === t ? s.tabActive : {}) }}
              onClick={() => setTab(t)}
            >
              {t === 'chat'   ? '💬 AI Chat' :
               t === 'ticket' ? '🎫 Submit Ticket' :
                                '🟢 System Status'}
            </button>
          ))}
        </nav>

        {/* ── Chat tab ── */}
        {tab === 'chat' && (
          <div style={s.chatShell}>
            {/* Email bar */}
            <div style={s.emailBar}>
              <label style={s.emailLabel}>Your email (optional)</label>
              <input
                style={s.emailInput}
                type="email"
                placeholder="you@example.com"
                value={userEmail}
                onChange={e => setUserEmail(e.target.value)}
              />
            </div>

            {/* Messages */}
            <div style={s.messages}>
              {messages.length === 0 && wsState === 'connecting' && (
                <div style={s.emptyState}>Connecting to AI Support Agent…</div>
              )}

              {messages.map(msg => (
                <div key={msg.id} style={{ ...s.msgRow, justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
                  {msg.role === 'assistant' && (
                    <div style={s.avatar}>🤖</div>
                  )}
                  <div style={{
                    ...s.bubble,
                    ...(msg.role === 'user' ? s.bubbleUser : s.bubbleBot),
                  }}>
                    {msg.role === 'assistant' ? (
                      <div className="md">
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    ) : (
                      <span>{msg.content}</span>
                    )}
                    <span style={s.ts}>{fmtTime(msg.ts)}</span>
                  </div>
                  {msg.role === 'user' && (
                    <div style={s.avatarUser}>👤</div>
                  )}
                </div>
              ))}

              {isTyping && (
                <div style={{ ...s.msgRow, justifyContent: 'flex-start' }}>
                  <div style={s.avatar}>🤖</div>
                  <div style={{ ...s.bubble, ...s.bubbleBot }}>
                    <span style={s.typingDots}><span />  <span />  <span /></span>
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>

            {/* Suggestions */}
            {messages.length < 2 && (
              <div style={s.suggestions}>
                {SUGGESTIONS.map(s_ => (
                  <button key={s_} style={s.suggBtn} onClick={() => sendMessage(s_)}>{s_}</button>
                ))}
              </div>
            )}

            {/* Input */}
            <div style={s.inputRow}>
              <textarea
                ref={inputRef}
                style={s.textarea}
                rows={2}
                placeholder="Type a message… (Enter to send, Shift+Enter for new line)"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={onKeyDown}
                disabled={wsState !== 'open'}
              />
              <button
                style={{ ...s.sendBtn, opacity: (!input.trim() || wsState !== 'open') ? .4 : 1 }}
                onClick={() => sendMessage()}
                disabled={!input.trim() || wsState !== 'open'}
              >
                ➤
              </button>
            </div>
          </div>
        )}

        {/* ── Ticket tab ── */}
        {tab === 'ticket' && (
          <div style={s.panel}>
            <h2 style={s.panelTitle}>Submit a Support Ticket</h2>
            <p style={s.panelSub}>Our team will respond within your plan&rsquo;s SLA. Business plan: 4h&nbsp;•&nbsp;Pro: 8h&nbsp;•&nbsp;Others: 1 business day.</p>

            {ticketState === 'sent' ? (
              <div style={s.successBox}>
                ✅ <strong>Ticket submitted!</strong> We&rsquo;ll respond to your email shortly.
                <br />
                <button style={s.newTicketBtn} onClick={() => setTicketState('idle')}>Submit another</button>
              </div>
            ) : (
              <form onSubmit={submitTicket} style={s.ticketForm}>
                <div style={s.formRow}>
                  <label style={s.label}>Email *</label>
                  <input style={s.input} type="email" required value={ticket.user_email}
                    onChange={e => setTicket(p => ({ ...p, user_email: e.target.value }))} />
                </div>

                <div style={s.formRowDouble}>
                  <div style={{ flex: 1 }}>
                    <label style={s.label}>Category *</label>
                    <select style={s.select} value={ticket.category}
                      onChange={e => setTicket(p => ({ ...p, category: e.target.value }))}>
                      <option value="billing">Billing</option>
                      <option value="technical">Technical Issue</option>
                      <option value="account">Account</option>
                      <option value="feature">Feature Request</option>
                      <option value="other">Other</option>
                    </select>
                  </div>
                  <div style={{ flex: 1 }}>
                    <label style={s.label}>Priority *</label>
                    <select style={s.select} value={ticket.priority}
                      onChange={e => setTicket(p => ({ ...p, priority: e.target.value }))}>
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                    </select>
                  </div>
                </div>

                <div style={s.formRow}>
                  <label style={s.label}>Subject *</label>
                  <input style={s.input} type="text" required maxLength={120} value={ticket.subject}
                    onChange={e => setTicket(p => ({ ...p, subject: e.target.value }))} />
                </div>

                <div style={s.formRow}>
                  <label style={s.label}>Message *</label>
                  <textarea style={{ ...s.input, ...s.msgArea }} required rows={6} value={ticket.message}
                    onChange={e => setTicket(p => ({ ...p, message: e.target.value }))} />
                </div>

                {ticketState === 'error' && (
                  <p style={{ color: 'var(--danger)', fontSize: '.9rem' }}>
                    Something went wrong. Please try again or email support@selfmonitor.app.
                  </p>
                )}

                <button style={s.submitBtn} type="submit" disabled={ticketState === 'sending'}>
                  {ticketState === 'sending' ? 'Submitting…' : 'Submit Ticket'}
                </button>
              </form>
            )}
          </div>
        )}

        {/* ── Status tab ── */}
        {tab === 'status' && (
          <div style={s.panel}>
            <h2 style={s.panelTitle}>System Status</h2>
            <p style={s.panelSub}>Current status of all SelfMonitor services.</p>
            <div style={s.statusGrid}>
              {SERVICES.map(svc => (
                <div key={svc.name} style={s.statusRow}>
                  <span style={s.svcName}>{svc.name}</span>
                  <span style={{
                    ...s.badge,
                    background: svc.status === 'operational' ? '#14532d'
                               : svc.status === 'degraded'   ? '#78350f'
                               : '#7f1d1d',
                    color: svc.status === 'operational' ? 'var(--success)'
                          : svc.status === 'degraded'   ? 'var(--warn)'
                          : 'var(--danger)',
                  }}>
                    {svc.status === 'operational' ? '✓ Operational'
                   : svc.status === 'degraded'    ? '⚠ Degraded'
                   : '✗ Down'}
                  </span>
                </div>
              ))}
            </div>
            <p style={s.uptime}>Overall uptime (30 days): <strong style={{ color: 'var(--success)' }}>99.94%</strong></p>
          </div>
        )}

        <footer style={s.footer}>
          © 2026 SelfMonitor Ltd · <a href="mailto:support@selfmonitor.app">support@selfmonitor.app</a> · <a href="http://localhost:3000">Main App</a>
        </footer>
      </div>
    </>
  );
}

// ── Inline styles ─────────────────────────────────────────────────────────────
const s: Record<string, React.CSSProperties> = {
  shell:       { display: 'flex', flexDirection: 'column', minHeight: '100vh', maxWidth: 800, margin: '0 auto', padding: '0 1rem' },
  header:      { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem 0', borderBottom: '1px solid var(--border)' },
  headerBrand: { display: 'flex', alignItems: 'center', gap: '.75rem' },
  logo:        { background: 'var(--accent)', color: '#fff', fontWeight: 700, fontSize: '.9rem', padding: '.35rem .55rem', borderRadius: 8 },
  brandText:   { fontWeight: 700, fontSize: '1.1rem' },
  headerRight: { display: 'flex', alignItems: 'center', gap: '.5rem' },
  dot:         { width: 9, height: 9, borderRadius: '50%', display: 'inline-block' },
  wsLabel:     { fontSize: '.85rem', color: 'var(--muted)' },
  reconnectBtn:{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', padding: '.25rem .6rem', borderRadius: 6, fontSize: '.8rem' },

  tabs:        { display: 'flex', gap: '.5rem', padding: '1rem 0 0' },
  tab:         { flex: 1, padding: '.55rem .5rem', background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--muted)', borderRadius: 8, fontSize: '.9rem', transition: 'all .15s' },
  tabActive:   { background: 'var(--accent)', border: '1px solid var(--accent)', color: '#fff', fontWeight: 600 },

  chatShell:   { display: 'flex', flexDirection: 'column', flex: 1, gap: '.75rem', paddingTop: '.75rem' },
  emailBar:    { display: 'flex', alignItems: 'center', gap: .75, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '.5rem .85rem' },
  emailLabel:  { fontSize: '.82rem', color: 'var(--muted)', whiteSpace: 'nowrap' },
  emailInput:  { flex: 1, background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: '.9rem' },

  messages:    { flex: 1, minHeight: 320, maxHeight: '55vh', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '.75rem', paddingRight: '.25rem' },
  emptyState:  { margin: 'auto', color: 'var(--muted)', fontSize: '.9rem' },
  msgRow:      { display: 'flex', alignItems: 'flex-end', gap: '.5rem' },
  avatar:      { fontSize: '1.3rem', flexShrink: 0 },
  avatarUser:  { fontSize: '1.3rem', flexShrink: 0 },
  bubble:      { maxWidth: '75%', padding: '.65rem .9rem', borderRadius: 14, fontSize: '.92rem', lineHeight: 1.6, position: 'relative' },
  bubbleBot:   { background: 'var(--surface)', border: '1px solid var(--border)', borderBottomLeftRadius: 4 },
  bubbleUser:  { background: 'var(--accent)', color: '#fff', borderBottomRightRadius: 4 },
  ts:          { display: 'block', fontSize: '.7rem', color: 'rgba(255,255,255,.45)', textAlign: 'right', marginTop: '.3rem' },

  typingDots:  { display: 'inline-flex', gap: 4, alignItems: 'center' },

  suggestions: { display: 'flex', flexWrap: 'wrap', gap: '.4rem' },
  suggBtn:     { background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '.35rem .75rem', borderRadius: 20, fontSize: '.82rem', cursor: 'pointer' },

  inputRow:    { display: 'flex', gap: '.5rem', paddingBottom: '.5rem' },
  textarea:    { flex: 1, background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 10, padding: '.65rem .85rem', fontSize: '.93rem', resize: 'none', outline: 'none' },
  sendBtn:     { background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: 10, padding: '0 1.1rem', fontSize: '1.3rem', transition: 'opacity .15s' },

  panel:       { paddingTop: '1.5rem', flex: 1 },
  panelTitle:  { fontSize: '1.25rem', fontWeight: 700, marginBottom: '.5rem' },
  panelSub:    { color: 'var(--muted)', fontSize: '.9rem', marginBottom: '1.5rem' },

  ticketForm:  { display: 'flex', flexDirection: 'column', gap: '1rem' },
  formRow:     { display: 'flex', flexDirection: 'column', gap: '.4rem' },
  formRowDouble:{ display: 'flex', gap: '1rem' },
  label:       { fontSize: '.85rem', color: 'var(--muted)', fontWeight: 500 },
  input:       { background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '.55rem .9rem', fontSize: '.92rem', outline: 'none' },
  select:      { background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 8, padding: '.55rem .9rem', fontSize: '.92rem', outline: 'none', width: '100%' },
  msgArea:     { fontFamily: 'inherit', resize: 'vertical' },
  submitBtn:   { background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: 10, padding: '.7rem 1.8rem', fontSize: '1rem', fontWeight: 600, alignSelf: 'flex-start', transition: 'opacity .15s' },
  successBox:  { background: '#14532d', border: '1px solid var(--success)', borderRadius: 12, padding: '1.2rem 1.5rem', lineHeight: 1.7 },
  newTicketBtn:{ background: 'transparent', border: '1px solid var(--success)', color: 'var(--success)', borderRadius: 8, padding: '.4rem 1rem', marginTop: '.75rem', fontSize: '.9rem' },

  statusGrid:  { display: 'flex', flexDirection: 'column', gap: '.5rem' },
  statusRow:   { display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 10, padding: '.65rem 1rem' },
  svcName:     { fontWeight: 500 },
  badge:       { padding: '.25rem .65rem', borderRadius: 20, fontSize: '.82rem', fontWeight: 600 },
  uptime:      { marginTop: '1.25rem', color: 'var(--muted)', fontSize: '.9rem' },

  footer:      { padding: '1.5rem 0 1rem', color: 'var(--muted)', fontSize: '.82rem', textAlign: 'center', borderTop: '1px solid var(--border)', marginTop: 'auto' },
};
