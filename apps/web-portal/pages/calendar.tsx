import { CalendarDays, Check, ChevronLeft, ChevronRight, Edit2, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import calStyles from '../styles/Calendar.module.css';

const CALENDAR_URL = process.env.NEXT_PUBLIC_CALENDAR_SERVICE_URL || '/api/calendar';

// ── Types ──────────────────────────────────────────────────────────
type Category = 'hmrc' | 'invoice' | 'meeting' | 'personal' | 'other';
type View = 'month' | 'week' | 'list';

type CalEvent = {
  id: string;
  user_id: string;
  event_title: string;
  event_date: string;
  event_time?: string | null;
  category: Category;
  is_completed: boolean;
  notes?: string | null;
  created_at: string;
};

type FormState = {
  event_title: string;
  event_date: string;
  event_time: string;
  category: Category;
  notes: string;
};

// ── Constants ──────────────────────────────────────────────────────
const DAYS_MON = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTHS_FULL = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];
const CATEGORIES: { id: Category; label: string; emoji: string }[] = [
  { id: 'hmrc',     label: 'HMRC',     emoji: '🔴' },
  { id: 'invoice',  label: 'Invoice',  emoji: '🟡' },
  { id: 'meeting',  label: 'Meeting',  emoji: '🟢' },
  { id: 'personal', label: 'Personal', emoji: '🔵' },
  { id: 'other',    label: 'Other',    emoji: '🟣' },
];
const CAT_COLOR: Record<Category, string> = {
  hmrc:     '#f87171',
  invoice:  '#fbbf24',
  meeting:  '#34d399',
  personal: '#60a5fa',
  other:    '#c084fc',
};
const EMPTY_FORM: FormState = {
  event_title: '', event_date: '', event_time: '', category: 'personal', notes: '',
};

// ── Helpers ────────────────────────────────────────────────────────
function todayIso() { return new Date().toISOString().slice(0, 10); }

function getUserId(token: string): string {
  try {
    return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))).sub ?? '';
  } catch { return ''; }
}

function fmtDate(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', {
    weekday: 'short', day: 'numeric', month: 'short',
  });
}

function daysUntil(iso: string) {
  const d = new Date(iso + 'T00:00:00');
  const t = new Date(); t.setHours(0, 0, 0, 0);
  return Math.round((d.getTime() - t.getTime()) / 86_400_000);
}

type GridCell = { iso: string; day: number; current: boolean };

function buildMonthGrid(year: number, month: number): GridCell[] {
  const firstJsDay = new Date(year, month, 1).getDay();
  const offset = (firstJsDay + 6) % 7; // Mon = 0
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const prevDays = new Date(year, month, 0).getDate();
  const cells: GridCell[] = [];

  for (let i = offset - 1; i >= 0; i--) {
    const d = prevDays - i;
    const m = month === 0 ? 11 : month - 1;
    const y = month === 0 ? year - 1 : year;
    cells.push({ iso: `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, day: d, current: false });
  }
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ iso: `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, day: d, current: true });
  }
  const rem = (7 - (cells.length % 7)) % 7;
  const nm = month === 11 ? 0 : month + 1;
  const ny = month === 11 ? year + 1 : year;
  for (let d = 1; d <= rem; d++) {
    cells.push({ iso: `${ny}-${String(nm + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`, day: d, current: false });
  }
  return cells;
}

function getWeekIsos(anchorIso: string): string[] {
  const d = new Date(anchorIso + 'T00:00:00');
  const offset = (d.getDay() + 6) % 7;
  d.setDate(d.getDate() - offset);
  return Array.from({ length: 7 }, (_, i) => {
    const dd = new Date(d); dd.setDate(d.getDate() + i);
    return dd.toISOString().slice(0, 10);
  });
}

function getHMRC(year: number) {
  return [
    { title: 'Self Assessment Tax Return', iso: `${year}-01-31` },
    { title: 'Payment on Account (1st)',    iso: `${year}-01-31` },
    { title: 'End of Tax Year',             iso: `${year}-04-05` },
    { title: 'VAT Return Q1',               iso: `${year}-05-07` },
    { title: 'P60 Issue Deadline',          iso: `${year}-05-31` },
    { title: 'Payment on Account (2nd)',    iso: `${year}-07-31` },
    { title: 'VAT Return Q2',               iso: `${year}-08-07` },
    { title: 'VAT Return Q3',               iso: `${year}-11-07` },
    { title: 'VAT Return Q4',               iso: `${year + 1}-02-07` },
  ].sort((a, b) => a.iso.localeCompare(b.iso));
}

// ── Component ──────────────────────────────────────────────────────
export default function CalendarPage({ token }: { token: string }) {
  const now = new Date();
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView]       = useState<View>('month');
  const [viewYear, setViewYear]   = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());
  const [selected, setSelected]   = useState(todayIso());
  const [modal, setModal] = useState<{ mode: 'create' | 'edit'; event?: CalEvent } | null>(null);
  const [form, setForm]   = useState<FormState>(EMPTY_FORM);
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [delId, setDelId] = useState<string | null>(null);

  const today = useMemo(() => todayIso(), []);
  const hdrs  = useMemo(() => ({ Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }), [token]);

  // ── Fetch ────────────────────────────────────────────────────────
  const fetch3Months = useCallback(async () => {
    setLoading(true);
    try {
      const start = new Date(viewYear, viewMonth - 1, 1).toISOString().slice(0, 10);
      const end   = new Date(viewYear, viewMonth + 2, 0).toISOString().slice(0, 10);
      const res   = await fetch(`${CALENDAR_URL}/events?start_date=${start}&end_date=${end}`, { headers: hdrs });
      if (res.ok) setEvents(await res.json());
    } catch { /* offline */ } finally { setLoading(false); }
  }, [hdrs, viewYear, viewMonth]);

  useEffect(() => { fetch3Months(); }, [fetch3Months]);

  // ── Derived ──────────────────────────────────────────────────────
  const byDate = useMemo(() => {
    const m: Record<string, CalEvent[]> = {};
    events.forEach(ev => { (m[ev.event_date.slice(0, 10)] ??= []).push(ev); });
    return m;
  }, [events]);

  const monthGrid = useMemo(() => buildMonthGrid(viewYear, viewMonth), [viewYear, viewMonth]);
  const weekIsos  = useMemo(() => getWeekIsos(selected), [selected]);

  const upcoming = useMemo(() => {
    const end14 = new Date(today); end14.setDate(end14.getDate() + 14);
    return events
      .filter(ev => ev.event_date >= today && ev.event_date <= end14.toISOString().slice(0, 10) && !ev.is_completed)
      .sort((a, b) => a.event_date.localeCompare(b.event_date))
      .slice(0, 8);
  }, [events, today]);

  const listGroups = useMemo(() => {
    const sorted = [...events].sort((a, b) => a.event_date.localeCompare(b.event_date));
    const m = new Map<string, CalEvent[]>();
    sorted.forEach(ev => { const d = ev.event_date.slice(0, 10); (m.get(d) ?? m.set(d, []).get(d)!).push(ev); });
    return [...m.entries()].map(([date, evs]) => ({ date, events: evs }));
  }, [events]);

  const hmrcDeadlines = useMemo(() => getHMRC(viewYear), [viewYear]);
  const selectedEvs   = byDate[selected] ?? [];

  // ── Navigation ───────────────────────────────────────────────────
  const prevMonth = () => { if (viewMonth === 0) { setViewMonth(11); setViewYear(y => y - 1); } else setViewMonth(m => m - 1); };
  const nextMonth = () => { if (viewMonth === 11) { setViewMonth(0); setViewYear(y => y + 1); } else setViewMonth(m => m + 1); };
  const goToday   = () => { setViewYear(now.getFullYear()); setViewMonth(now.getMonth()); setSelected(today); };

  // ── Modal helpers ────────────────────────────────────────────────
  const openCreate = (date?: string) => {
    setForm({ ...EMPTY_FORM, event_date: date ?? selected });
    setFormError('');
    setModal({ mode: 'create' });
  };
  const openEdit = (ev: CalEvent) => {
    setForm({ event_title: ev.event_title, event_date: ev.event_date.slice(0, 10),
              event_time: ev.event_time ?? '', category: ev.category, notes: ev.notes ?? '' });
    setFormError('');
    setModal({ mode: 'edit', event: ev });
  };

  // ── API actions ──────────────────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setSubmitting(true); setFormError('');
    try {
      if (modal?.mode === 'create') {
        const r = await fetch(`${CALENDAR_URL}/events`, {
          method: 'POST', headers: hdrs,
          body: JSON.stringify({ user_id: getUserId(token), event_title: form.event_title,
            event_date: form.event_date, event_time: form.event_time || null,
            category: form.category, notes: form.notes || null }),
        });
        if (!r.ok) { const d = await r.json().catch(() => ({})); setFormError(d.detail ?? 'Error'); return; }
      } else if (modal?.mode === 'edit' && modal.event) {
        const r = await fetch(`${CALENDAR_URL}/events/${modal.event.id}`, {
          method: 'PUT', headers: hdrs,
          body: JSON.stringify({ event_title: form.event_title, event_date: form.event_date,
            event_time: form.event_time || null, category: form.category, notes: form.notes || null }),
        });
        if (!r.ok) { const d = await r.json().catch(() => ({})); setFormError(d.detail ?? 'Error'); return; }
      }
      setModal(null); fetch3Months();
    } catch { setFormError('Network error'); } finally { setSubmitting(false); }
  };

  const handleDelete = async (id: string) => {
    await fetch(`${CALENDAR_URL}/events/${id}`, { method: 'DELETE', headers: hdrs }).catch(() => {});
    setDelId(null); fetch3Months();
  };

  const handleComplete = async (ev: CalEvent) => {
    await fetch(`${CALENDAR_URL}/events/${ev.id}/complete`, { method: 'PATCH', headers: hdrs }).catch(() => {});
    fetch3Months();
  };

  const seedHMRC = async (title: string, iso: string) => {
    await fetch(`${CALENDAR_URL}/events`, {
      method: 'POST', headers: hdrs,
      body: JSON.stringify({ user_id: getUserId(token), event_title: title, event_date: iso, category: 'hmrc' }),
    }).catch(() => {});
    fetch3Months();
  };

  // ── Render helpers ───────────────────────────────────────────────
  const renderChip = (ev: CalEvent) => (
    <div key={ev.id} className={calStyles.chip}
      style={{ background: `${CAT_COLOR[ev.category]}22`, color: CAT_COLOR[ev.category], opacity: ev.is_completed ? 0.4 : 1 }}
      onClick={e => { e.stopPropagation(); openEdit(ev); }}
      title={ev.event_title}>
      {ev.event_time ? `${ev.event_time} ` : ''}{ev.event_title}
    </div>
  );

  const renderItem = (ev: CalEvent, showDate?: boolean) => (
    <div key={ev.id} className={`${calStyles.eventItem} ${ev.is_completed ? calStyles.eventItemDone : ''}`}>
      <div className={calStyles.catDot} style={{ background: CAT_COLOR[ev.category] }} />
      <div className={calStyles.eventItemContent}>
        <div className={calStyles.eventItemTitle}>{ev.event_title}</div>
        <div className={calStyles.eventItemMeta}>
          {showDate ? fmtDate(ev.event_date) : ''}
          {showDate && ev.event_time ? ' · ' : ''}
          {ev.event_time ?? ''}
          {ev.notes ? ((showDate || ev.event_time) ? ' · ' : '') + ev.notes.slice(0, 38) : ''}
        </div>
      </div>
      <div className={calStyles.eventItemActions}>
        <button className={calStyles.iconBtn} onClick={() => handleComplete(ev)} title={ev.is_completed ? 'Unmark' : 'Done'}>
          <Check size={12} />
        </button>
        <button className={calStyles.iconBtn} onClick={() => openEdit(ev)} title="Edit">
          <Edit2 size={12} />
        </button>
        <button className={`${calStyles.iconBtn} ${calStyles.iconBtnDanger}`} onClick={() => setDelId(ev.id)} title="Delete">
          <Trash2 size={12} />
        </button>
      </div>
    </div>
  );

  // ── JSX ──────────────────────────────────────────────────────────
  return (
    <div className={calStyles.page}>

      {/* Header */}
      <div className={calStyles.header}>
        <h1 className={calStyles.title}>Calendar</h1>
        <div className={calStyles.headerActions}>
          <div className={calStyles.viewSwitcher}>
            {(['month', 'week', 'list'] as View[]).map(v => (
              <button key={v} onClick={() => setView(v)}
                className={`${calStyles.viewTab} ${view === v ? calStyles.viewTabActive : ''}`}>
                {v.charAt(0).toUpperCase() + v.slice(1)}
              </button>
            ))}
          </div>
          <button className={calStyles.addBtn} onClick={() => openCreate()}>
            <Plus size={15} /><span>Add Event</span>
          </button>
        </div>
      </div>

      {/* Month nav */}
      <div className={calStyles.monthNav}>
        <button className={calStyles.navBtn} onClick={prevMonth}><ChevronLeft size={16} /></button>
        <span className={calStyles.monthLabel}>{MONTHS_FULL[viewMonth]} {viewYear}</span>
        <button className={calStyles.navBtn} onClick={nextMonth}><ChevronRight size={16} /></button>
        <button className={calStyles.todayBtn} onClick={goToday}>Today</button>
      </div>

      {/* Main layout: view + side panel */}
      <div className={calStyles.calLayout}>
        <div>
          {/* ── Month view ─── */}
          {view === 'month' && (
            <div className={calStyles.monthGrid}>
              <div className={calStyles.weekHeader}>
                {DAYS_MON.map(d => <div key={d} className={calStyles.weekHeaderCell}>{d}</div>)}
              </div>
              <div className={calStyles.daysGrid}>
                {monthGrid.map((cell, idx) => {
                  const evs      = byDate[cell.iso] ?? [];
                  const isToday  = cell.iso === today;
                  const isSel    = cell.iso === selected;
                  const lastRow  = idx >= monthGrid.length - 7;
                  return (
                    <div key={cell.iso}
                      className={[
                        calStyles.dayCell,
                        !cell.current ? calStyles.dayCellOtherMonth : '',
                        isSel  ? calStyles.dayCellSelected  : '',
                        lastRow ? calStyles.dayCellLast : '',
                      ].filter(Boolean).join(' ')}
                      onClick={() => setSelected(cell.iso)}>
                      <div className={`${calStyles.dayNum} ${isToday ? calStyles.dayNumToday : ''}`}>{cell.day}</div>
                      <div className={calStyles.chips}>
                        {evs.slice(0, 3).map(ev => renderChip(ev))}
                        {evs.length > 3 && <span className={calStyles.chipMore}>+{evs.length - 3}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── Week view ─── */}
          {view === 'week' && (
            <div className={calStyles.weekGrid}>
              <div className={calStyles.weekColHeader}>
                {weekIsos.map(iso => {
                  const d = new Date(iso + 'T00:00:00');
                  return (
                    <div key={iso}
                      className={`${calStyles.weekColHead} ${iso === today ? calStyles.weekColHeadToday : ''}`}
                      onClick={() => setSelected(iso)}>
                      <div>{DAYS_MON[(d.getDay() + 6) % 7]}</div>
                      <div style={{ fontSize: '1.1rem', fontWeight: 700, marginTop: 2 }}>{d.getDate()}</div>
                    </div>
                  );
                })}
              </div>
              <div className={calStyles.weekColBody}>
                {weekIsos.map(iso => {
                  const evs = byDate[iso] ?? [];
                  return (
                    <div key={iso}
                      className={`${calStyles.weekDay} ${iso === selected ? calStyles.dayCellSelected : ''}`}
                      onClick={() => setSelected(iso)}>
                      {evs.length === 0
                        ? <div style={{ color: 'var(--lp-text-muted)', fontSize: '0.72rem', padding: '0.2rem', opacity: 0.5 }}>—</div>
                        : evs.map(ev => (
                          <div key={ev.id}
                            style={{ fontSize: '0.72rem', padding: '2px 5px', marginBottom: 3, borderRadius: 4,
                              background: `${CAT_COLOR[ev.category]}22`, color: CAT_COLOR[ev.category],
                              overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis',
                              cursor: 'pointer', opacity: ev.is_completed ? 0.4 : 1 }}
                            onClick={e => { e.stopPropagation(); openEdit(ev); }}>
                            {ev.event_time ? `${ev.event_time} ` : ''}{ev.event_title}
                          </div>
                        ))
                      }
                      <button style={{ fontSize: '0.68rem', color: 'var(--lp-text-muted)', background: 'none',
                        border: 'none', cursor: 'pointer', marginTop: 4, padding: '0.15rem 0.25rem', borderRadius: 4 }}
                        onClick={e => { e.stopPropagation(); openCreate(iso); }}>
                        + Add
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ── List view ─── */}
          {view === 'list' && (
            <div className={calStyles.listView}>
              {loading && <div className={calStyles.skeleton} />}
              {!loading && listGroups.length === 0 && (
                <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--lp-text-muted)' }}>
                  <CalendarDays size={40} style={{ marginBottom: 12, opacity: 0.25 }} />
                  <p style={{ marginBottom: '1rem' }}>No events in this period.</p>
                  <button className={calStyles.addBtn} style={{ margin: '0 auto' }} onClick={() => openCreate()}>
                    <Plus size={15} /><span>Add Event</span>
                  </button>
                </div>
              )}
              {listGroups.map(({ date, events: evs }) => (
                <div key={date} className={calStyles.listGroup}>
                  <div className={`${calStyles.listGroupDate} ${date === today ? calStyles.listGroupDateToday : ''}`}>
                    {date === today ? 'TODAY — ' : ''}{fmtDate(date)}
                  </div>
                  <div style={{ padding: '0.45rem 0.5rem' }}>{evs.map(ev => renderItem(ev, false))}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className={calStyles.sidePanel}>
          <div className={calStyles.sidePanelHeader}>
            <span className={calStyles.sidePanelDate}>
              {selected === today ? 'Today' : fmtDate(selected)}
            </span>
            <button className={calStyles.iconBtn} onClick={() => openCreate(selected)} title="Add event on this day">
              <Plus size={14} />
            </button>
          </div>
          <div className={calStyles.sidePanelBody}>
            {selectedEvs.length === 0
              ? (
                <p className={calStyles.sidePanelEmpty}>
                  No events ·{' '}
                  <button style={{ background: 'none', border: 'none', color: 'var(--lp-accent-teal)', cursor: 'pointer', fontSize: '0.85rem', padding: 0 }}
                    onClick={() => openCreate(selected)}>Add one</button>
                </p>
              )
              : selectedEvs.map(ev => renderItem(ev, false))
            }
          </div>

          {upcoming.length > 0 && (
            <>
              <div className={calStyles.sidePanelSection}>Next 14 days</div>
              <div style={{ padding: '0.45rem 0.65rem' }}>
                {upcoming.map(ev => renderItem(ev, true))}
              </div>
            </>
          )}
        </div>
      </div>

      {/* HMRC Deadlines */}
      <div className={calStyles.hmrcSection}>
        <div className={calStyles.hmrcHeader}>
          <CalendarDays size={16} style={{ color: 'var(--lp-accent-teal)' }} />
          <h3 className={calStyles.hmrcTitle}>HMRC Tax Deadlines {viewYear}</h3>
        </div>
        <div className={calStyles.hmrcList}>
          {hmrcDeadlines.map(dl => {
            const days  = daysUntil(dl.iso);
            const past  = days < 0;
            const soon  = !past && days <= 14;
            const mid   = !past && days > 14 && days <= 60;
            const added = events.some(ev => ev.event_title === dl.title && ev.event_date.slice(0, 10) === dl.iso);
            return (
              <div key={dl.title + dl.iso} className={calStyles.hmrcRow}>
                <span className={calStyles.hmrcStatus}>{past ? '✅' : soon ? '🔴' : mid ? '🟡' : '⬚'}</span>
                <div className={calStyles.hmrcInfo}>
                  <div className={calStyles.hmrcDeadlineName}>{dl.title}</div>
                  <div className={calStyles.hmrcDeadlineDate}>{fmtDate(dl.iso)}</div>
                </div>
                <span className={`${calStyles.hmrcBadge} ${past ? calStyles.badgeGray : soon ? calStyles.badgeRed : mid ? calStyles.badgeAmber : calStyles.badgeGreen}`}>
                  {past ? 'Done' : days === 0 ? 'Today!' : `${days}d`}
                </span>
                {!added && !past
                  ? <button className={calStyles.hmrcAddBtn} onClick={() => seedHMRC(dl.title, dl.iso)}>Add</button>
                  : added ? <span style={{ fontSize: '0.7rem', color: 'var(--lp-text-muted)' }}>Added ✓</span>
                  : null
                }
              </div>
            );
          })}
        </div>
      </div>

      {/* Event modal */}
      {modal && (
        <div className={calStyles.modalOverlay} onClick={() => setModal(null)}>
          <div className={calStyles.modal} onClick={e => e.stopPropagation()}>
            <h2 className={calStyles.modalTitle}>{modal.mode === 'create' ? 'New Event' : 'Edit Event'}</h2>
            <form onSubmit={handleSubmit}>
              <div className={calStyles.formField}>
                <label className={calStyles.label}>Title *</label>
                <input className={calStyles.input} required placeholder="e.g. VAT return due"
                  value={form.event_title}
                  onChange={e => setForm(f => ({ ...f, event_title: e.target.value }))} />
              </div>
              <div className={calStyles.formRow}>
                <div className={calStyles.formField}>
                  <label className={calStyles.label}>Date *</label>
                  <input type="date" className={calStyles.input} required
                    value={form.event_date}
                    onChange={e => setForm(f => ({ ...f, event_date: e.target.value }))} />
                </div>
                <div className={calStyles.formField}>
                  <label className={calStyles.label}>Time (optional)</label>
                  <input type="time" className={calStyles.input}
                    value={form.event_time}
                    onChange={e => setForm(f => ({ ...f, event_time: e.target.value }))} />
                </div>
              </div>
              <div className={calStyles.formField}>
                <label className={calStyles.label}>Category</label>
                <div className={calStyles.catGrid}>
                  {CATEGORIES.map(cat => (
                    <button type="button" key={cat.id}
                      className={calStyles.catBtn}
                      style={{
                        background: form.category === cat.id ? CAT_COLOR[cat.id] : 'var(--lp-bg-surface)',
                        borderColor: form.category === cat.id ? CAT_COLOR[cat.id] : `${CAT_COLOR[cat.id]}55`,
                        color: form.category === cat.id ? '#fff' : 'var(--lp-text-muted)',
                      }}
                      onClick={() => setForm(f => ({ ...f, category: cat.id }))}>
                      <div>{cat.emoji}</div>
                      <div>{cat.label}</div>
                    </button>
                  ))}
                </div>
              </div>
              <div className={calStyles.formField}>
                <label className={calStyles.label}>Notes</label>
                <input className={calStyles.input} placeholder="Optional"
                  value={form.notes}
                  onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
              {formError && <p style={{ color: '#f87171', fontSize: '0.85rem', marginBottom: '0.75rem' }}>{formError}</p>}
              <div className={calStyles.modalActions}>
                {modal.mode === 'edit' && (
                  <button type="button" className={calStyles.btnDanger}
                    onClick={() => { setDelId(modal.event!.id); setModal(null); }}>
                    Delete
                  </button>
                )}
                <button type="button" className={calStyles.btnSecondary} onClick={() => setModal(null)}>Cancel</button>
                <button type="submit" className={calStyles.btnPrimary} disabled={submitting}>
                  {submitting ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete confirm */}
      {delId && (
        <div className={calStyles.modalOverlay} onClick={() => setDelId(null)}>
          <div className={calStyles.modal} style={{ maxWidth: 360 }} onClick={e => e.stopPropagation()}>
            <h2 className={calStyles.modalTitle}>Delete Event?</h2>
            <p style={{ color: 'var(--lp-text-muted)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              This cannot be undone.
            </p>
            <div className={calStyles.modalActions}>
              <button className={calStyles.btnSecondary} onClick={() => setDelId(null)}>Cancel</button>
              <button className={calStyles.btnPrimary} style={{ background: '#ef4444' }} onClick={() => handleDelete(delId)}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
