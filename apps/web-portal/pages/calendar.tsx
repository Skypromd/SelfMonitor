import { CalendarDays, Plus } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import styles from '../styles/Home.module.css';

const CALENDAR_SERVICE_URL =
  process.env.NEXT_PUBLIC_CALENDAR_SERVICE_URL || 'http://localhost:8015';

type CalendarEvent = {
  id: string;
  user_id: string;
  event_title: string;
  event_date: string;
  notes?: string;
  created_at: string;
};

type CalendarPageProps = { token: string };

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

function isoToDisplay(date: string) {
  return new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}

function daysUntil(date: string) {
  const d = new Date(date);
  const now = new Date();
  now.setHours(0, 0, 0, 0);
  d.setHours(0, 0, 0, 0);
  return Math.round((d.getTime() - now.getTime()) / 86_400_000);
}

function urgencyColor(days: number) {
  if (days < 0) return '#6b7280';
  if (days <= 7) return '#f87171';
  if (days <= 30) return '#fbbf24';
  return '#34d399';
}

export default function CalendarPage({ token }: CalendarPageProps) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formMsg, setFormMsg] = useState('');
  const [title, setTitle] = useState('');
  const [eventDate, setEventDate] = useState('');
  const [notes, setNotes] = useState('');

  // Calendar view state
  const now = new Date();
  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth()); // 0-indexed

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };

  const fetchEvents = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      // Fetch 6 months window
      const start = new Date(viewYear, viewMonth - 1, 1).toISOString().slice(0, 10);
      const end = new Date(viewYear, viewMonth + 2, 0).toISOString().slice(0, 10);
      const res = await fetch(
        `${CALENDAR_SERVICE_URL}/events?start_date=${start}&end_date=${end}`,
        { headers }
      );
      if (res.ok) {
        setEvents(await res.json());
      } else if (res.status === 401) {
        setError('Authentication required.');
      } else {
        setError(`Service error: ${res.status}`);
      }
    } catch {
      setError('Unable to reach calendar service.');
    } finally {
      setLoading(false);
    }
  }, [token, viewMonth, viewYear]);

  useEffect(() => { fetchEvents(); }, [fetchEvents]);

  // Seed common tax deadline suggestions
  const seedDeadlines = [
    { title: 'Self Assessment Tax Return Deadline', date: `${viewYear}-01-31` },
    { title: 'Tax Payment on Account (1st)', date: `${viewYear}-01-31` },
    { title: 'Tax Payment on Account (2nd)', date: `${viewYear}-07-31` },
    { title: 'P60 Deadline', date: `${viewYear}-05-31` },
    { title: 'VAT Return (Q1)', date: `${viewYear}-05-07` },
    { title: 'VAT Return (Q2)', date: `${viewYear}-08-07` },
    { title: 'VAT Return (Q3)', date: `${viewYear}-11-07` },
    { title: 'VAT Return (Q4)', date: `${viewYear + 1}-02-07` },
  ];

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormMsg('');
    try {
      // Decode user_id from JWT
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      const user_id = payload.sub || 'me';
      const body = { user_id, event_title: title, event_date: eventDate, notes: notes || undefined };
      const res = await fetch(`${CALENDAR_SERVICE_URL}/events`, {
        method: 'POST', headers, body: JSON.stringify(body),
      });
      if (res.ok) {
        setFormMsg('Event added!');
        setTitle(''); setEventDate(''); setNotes('');
        setShowForm(false);
        fetchEvents();
      } else {
        const d = await res.json().catch(() => ({}));
        setFormMsg(`Error: ${d.detail || res.statusText}`);
      }
    } catch {
      setFormMsg('Network error — calendar service may not be running.');
    } finally {
      setSubmitting(false);
    }
  };

  const seedEvent = async (t: string, d: string) => {
    try {
      const payload = JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      const user_id = payload.sub || 'me';
      await fetch(`${CALENDAR_SERVICE_URL}/events`, {
        method: 'POST', headers,
        body: JSON.stringify({ user_id, event_title: t, event_date: d }),
      });
      fetchEvents();
    } catch { /* ignore */ }
  };

  // Mini calendar grid
  const firstDay = new Date(viewYear, viewMonth, 1).getDay();
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
  const eventDates = new Set(events.map((e) => e.event_date.slice(0, 10)));

  const prevMonth = () => {
    if (viewMonth === 0) { setViewMonth(11); setViewYear((y) => y - 1); }
    else setViewMonth((m) => m - 1);
  };
  const nextMonth = () => {
    if (viewMonth === 11) { setViewMonth(0); setViewYear((y) => y + 1); }
    else setViewMonth((m) => m + 1);
  };

  const upcoming = [...events]
    .filter((e) => daysUntil(e.event_date) >= 0)
    .sort((a, b) => a.event_date.localeCompare(b.event_date))
    .slice(0, 8);

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1 className={styles.title}>Calendar</h1>
        <button className={styles.btn} onClick={() => setShowForm(!showForm)}>
          <Plus size={16} style={{ marginRight: 6 }} /> Add Event
        </button>
      </div>

      {/* Add Event Form */}
      {showForm && (
        <div className={styles.card} style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ marginBottom: '1rem' }}>New Event</h3>
          <form onSubmit={handleCreate}>
            <div className={styles.grid}>
              <div>
                <label className={styles.label}>Title *</label>
                <input className={styles.input} value={title}
                  onChange={(e) => setTitle(e.target.value)} required placeholder="e.g. VAT return due" />
              </div>
              <div>
                <label className={styles.label}>Date *</label>
                <input type="date" className={styles.input} value={eventDate}
                  onChange={(e) => setEventDate(e.target.value)} required />
              </div>
            </div>
            <div style={{ marginTop: '0.75rem' }}>
              <label className={styles.label}>Notes</label>
              <input className={styles.input} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Optional" />
            </div>
            {formMsg && <p style={{ color: formMsg.startsWith('Error') ? '#f87171' : '#34d399', marginTop: 8 }}>{formMsg}</p>}
            <div style={{ display: 'flex', gap: 8, marginTop: '1rem' }}>
              <button type="submit" className={styles.btn} disabled={submitting}>
                {submitting ? 'Saving…' : 'Add Event'}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                style={{ padding: '0.5rem 1rem', borderRadius: 8, border: '1px solid var(--lp-border)', background: 'none', color: 'var(--lp-text)', cursor: 'pointer' }}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
        {/* Left: Mini calendar + upcoming */}
        <div>
          {/* Mini calendar */}
          <div className={styles.card} style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              <button onClick={prevMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--lp-text)', fontSize: '1.2rem' }}>‹</button>
              <strong style={{ color: 'var(--lp-text)' }}>{MONTHS[viewMonth]} {viewYear}</strong>
              <button onClick={nextMonth} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--lp-text)', fontSize: '1.2rem' }}>›</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 2, textAlign: 'center' }}>
              {['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'].map((d) => (
                <div key={d} style={{ fontSize: '0.72rem', color: 'var(--lp-text-muted)', padding: '0.2rem 0' }}>{d}</div>
              ))}
              {Array.from({ length: firstDay }).map((_, i) => <div key={`e${i}`} />)}
              {Array.from({ length: daysInMonth }, (_, i) => i + 1).map((day) => {
                const iso = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                const hasEvent = eventDates.has(iso);
                const isToday = iso === new Date().toISOString().slice(0, 10);
                return (
                  <div key={day} style={{
                    borderRadius: '50%', width: 28, height: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto',
                    fontSize: '0.82rem', cursor: 'default',
                    background: isToday ? 'var(--lp-accent-teal)' : hasEvent ? 'rgba(99,102,241,0.2)' : 'transparent',
                    color: isToday ? '#fff' : hasEvent ? '#a5b4fc' : 'var(--lp-text)',
                    fontWeight: isToday || hasEvent ? 700 : 400,
                  }}>{day}</div>
                );
              })}
            </div>
          </div>

          {/* Upcoming events */}
          <div className={styles.card}>
            <h3 style={{ marginBottom: '0.75rem', color: 'var(--lp-text)' }}>Upcoming</h3>
            {loading ? (
              <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.9rem' }}>Loading…</p>
            ) : error ? (
              <p className={styles.error} style={{ fontSize: '0.85rem' }}>{error}</p>
            ) : upcoming.length === 0 ? (
              <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.85rem' }}>No upcoming events. Add tax deadlines below.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
                {upcoming.map((ev) => {
                  const days = daysUntil(ev.event_date);
                  return (
                    <li key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0.5rem 0', borderBottom: '1px solid var(--lp-border)' }}>
                      <div>
                        <div style={{ fontWeight: 500, fontSize: '0.88rem' }}>{ev.event_title}</div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--lp-text-muted)' }}>{isoToDisplay(ev.event_date)}</div>
                      </div>
                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: urgencyColor(days), whiteSpace: 'nowrap', marginLeft: 8 }}>
                        {days === 0 ? 'Today' : days === 1 ? 'Tomorrow' : `${days}d`}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>

        {/* Right: Quick-add tax deadlines + all events */}
        <div>
          <div className={styles.card} style={{ marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.75rem' }}>
              <CalendarDays size={18} style={{ color: 'var(--lp-accent-teal)' }} />
              <h3 style={{ margin: 0, fontSize: '1rem' }}>HMRC Key Deadlines {viewYear}</h3>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {seedDeadlines.map((d) => (
                <div key={d.title} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'var(--lp-bg-surface)', borderRadius: 8, padding: '0.5rem 0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.85rem', fontWeight: 500 }}>{d.title}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--lp-text-muted)' }}>{isoToDisplay(d.date)}</div>
                  </div>
                  <button onClick={() => seedEvent(d.title, d.date)}
                    style={{ background: 'none', border: '1px solid var(--lp-accent-teal)', color: 'var(--lp-accent-teal)', borderRadius: 6, padding: '0.2rem 0.6rem', fontSize: '0.75rem', cursor: 'pointer' }}>
                    Add
                  </button>
                </div>
              ))}
            </div>
          </div>

          <div className={styles.card}>
            <h3 style={{ marginBottom: '0.75rem' }}>All Events ({events.length})</h3>
            {events.length === 0 ? (
              <p style={{ color: 'var(--lp-text-muted)', fontSize: '0.85rem' }}>No events in the current window.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, margin: 0, maxHeight: 320, overflowY: 'auto' }}>
                {[...events].sort((a, b) => a.event_date.localeCompare(b.event_date)).map((ev) => (
                  <li key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', padding: '0.5rem 0', borderBottom: '1px solid var(--lp-border)' }}>
                    <div>
                      <div style={{ fontWeight: 500, fontSize: '0.88rem' }}>{ev.event_title}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--lp-text-muted)' }}>{isoToDisplay(ev.event_date)}</div>
                      {ev.notes && <div style={{ fontSize: '0.75rem', color: 'var(--lp-text-muted)', marginTop: 2 }}>{ev.notes}</div>}
                    </div>
                    <span style={{ fontSize: '0.75rem', color: urgencyColor(daysUntil(ev.event_date)), fontWeight: 600, marginLeft: 8 }}>
                      {daysUntil(ev.event_date) < 0 ? 'Past' : `${daysUntil(ev.event_date)}d`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
