import React, { useCallback, useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  Landmark,
  FileText,
  ClipboardCheck,
  BookOpen,
  Layers,
  PieChart,
  Building2,
  ShieldCheck,
  AlertTriangle,
  ArrowLeft,
  RefreshCw,
} from 'lucide-react';
import { Badge, Btn } from './components/ui.jsx';
import { inr, today } from './lib/format.js';
import Onboarding from './pages/Onboarding.jsx';
import Invoices from './pages/Invoices.jsx';
import Review from './pages/Review.jsx';
import DayBooks from './pages/DayBooks.jsx';
import Ledgers from './pages/Ledgers.jsx';
import FinalAccounts from './pages/FinalAccounts.jsx';
import CompanyProfile from './pages/CompanyProfile.jsx';

const SETUP_KEY = 'itb.company-setup.v1';

const NAV = [
  { key: 'invoices', label: 'Invoices', icon: FileText, group: 'Workspace' },
  { key: 'review', label: 'Review', icon: ClipboardCheck, group: 'Workspace' },
  { key: 'books', label: 'Day books', icon: BookOpen, group: 'Books' },
  { key: 'ledgers', label: 'Ledgers', icon: Layers, group: 'Books' },
  { key: 'final', label: 'Final accounts', icon: PieChart, group: 'Reports' },
  { key: 'company', label: 'Company profile', icon: Building2, group: 'Settings' },
];

const TITLES = {
  invoices: ['Invoices & bills', 'Upload, verify and approve. Nothing reaches the ledger until you approve it.'],
  review: ['Invoice review', 'Correct the extraction, then save or approve and post.'],
  books: ['Day books', 'Purchase, sales, cash & bank and journal proper.'],
  ledgers: ['Ledgers', 'Account folios and party ledgers with settlement.'],
  final: ['Final accounts', 'Trial balance through to the balance sheet.'],
  company: ['Company profile', 'Identity and accounting policy.'],
};

export default function App() {
  const [tenant, setTenant] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [financialYears, setFinancialYears] = useState([]);
  const [fy, setFy] = useState('FY 2026-27');
  const [asOf, setAsOf] = useState(today());
  const [tb, setTb] = useState(null);
  const [booting, setBooting] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [setupDone, setSetupDone] = useState(() => localStorage.getItem(SETUP_KEY) === '1');
  const [route, setRoute] = useState(() => window.location.hash.replace(/^#\/?/, '') || 'invoices');

  const [view, docId] = useMemo(() => {
    const [v, id] = route.split('/');
    return [v || 'invoices', id || null];
  }, [route]);

  const go = (key, id) => {
    window.location.hash = `#/${key}${id ? `/${id}` : ''}`;
  };

  useEffect(() => {
    const onHash = () => setRoute(window.location.hash.replace(/^#\/?/, '') || 'invoices');
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const loadCore = useCallback(async () => {
    const [t, d, y, b] = await Promise.allSettled([
      axios.get('/api/tenant'),
      axios.get('/api/documents'),
      axios.get('/api/financial-years'),
      axios.get('/api/reports/trial-balance', { params: { as_of_date: asOf, financial_year: fy } }),
    ]);
    if (t.status === 'fulfilled') setTenant(t.value.data);
    if (d.status === 'fulfilled') setDocuments(d.value.data || []);
    if (y.status === 'fulfilled') {
      const list = y.value.data.available_financial_years || [];
      setFinancialYears(list);
      const current = y.value.data.current_financial_year;
      if (current && !list.includes(fy)) setFy(current);
    }
    if (b.status === 'fulfilled') setTb(b.value.data);
  }, [asOf, fy]);

  useEffect(() => {
    let alive = true;
    (async () => {
      await loadCore();
      if (alive) setBooting(false);
    })();
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    if (!booting) loadCore();
  }, [fy, asOf]);

  const refreshDocs = async () => {
    setRefreshing(true);
    try {
      const [d, b] = await Promise.all([
        axios.get('/api/documents'),
        axios.get('/api/reports/trial-balance', { params: { as_of_date: asOf, financial_year: fy } }),
      ]);
      setDocuments(d.data || []);
      setTb(b.data);
    } finally {
      setRefreshing(false);
    }
  };

  const pendingReview = documents.filter((d) => d.status === 'REVIEW_REQUIRED').length;
  const unposted = documents.filter((d) => d.status === 'PROCESSED').length;
  const bookIssues = !tb?.is_balanced;

  const badge = bookIssues
    ? { tone: 'rose', icon: AlertTriangle, label: 'Books out of balance', sub: 'Trial balance does not agree' }
    : pendingReview
    ? { tone: 'amber', icon: AlertTriangle, label: `${pendingReview} invoice${pendingReview > 1 ? 's' : ''} to check`, sub: `${unposted} processed and ready to post` }
    : { tone: 'emerald', icon: ShieldCheck, label: 'Verified & Balanced', sub: 'All checks passed in the background' };

  if (!setupDone) {
    if (booting) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-slate-50">
          <p className="text-xs text-slate-500">Opening the workspace…</p>
        </div>
      );
    }
    return (
      <Onboarding
        tenant={tenant}
        onDone={(t) => {
          setTenant(t);
          localStorage.setItem(SETUP_KEY, '1');
          setSetupDone(true);
          loadCore();
        }}
      />
    );
  }

  const BadgeIcon = badge.icon;
  const [title, subtitle] = TITLES[view] || TITLES.invoices;

  const navButton = (item, compact = false) => {
    const Icon = item.icon;
    const active = view === item.key;
    const count = item.key === 'review' ? pendingReview : 0;
    return (
      <button
        key={item.key}
        onClick={() => go(item.key, item.key === 'review' && docId ? docId : undefined)}
        className={
          compact
            ? `inline-flex shrink-0 cursor-pointer items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[12px] font-semibold transition-colors ${
                active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'
              }`
            : `flex w-full cursor-pointer items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-colors ${
                active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
              }`
        }
      >
        <Icon className={compact ? 'h-3.5 w-3.5' : 'h-4 w-4'} />
        <span className={compact ? '' : 'flex-1 text-left'}>{item.label}</span>
        {count > 0 && (
          <span
            className={`rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
              active ? 'bg-white/20 text-white' : 'bg-amber-100 text-amber-700'
            }`}
          >
            {count}
          </span>
        )}
      </button>
    );
  };

  const grouped = NAV.reduce((acc, item) => {
    (acc[item.group] ||= []).push(item);
    return acc;
  }, {});

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="flex">
        <aside className="sticky top-0 hidden h-screen w-[236px] shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
          <div className="flex items-center gap-2.5 px-4 py-4">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Landmark className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-[13px] font-bold tracking-tight text-slate-900">Invoice to Books</p>
              <p className="text-[10px] text-slate-400">Accounting workspace</p>
            </div>
          </div>

          <div className="mx-3 mb-3 rounded-lg border border-slate-200 bg-slate-50/80 px-2.5 py-2">
            <p className="truncate text-[12px] font-semibold text-slate-800">{tenant?.name || 'Loading company…'}</p>
            <p className="truncate font-mono text-[10px] text-slate-400">{tenant?.gstin || 'GSTIN pending'}</p>
            <p className="mt-1 text-[10px] font-medium text-slate-500">
              {(tenant?.business_type || '').replaceAll('_', ' ').toLowerCase() || '—'}
            </p>
          </div>

          <nav className="flex-1 space-y-4 overflow-y-auto px-3 pb-4">
            {Object.entries(grouped).map(([group, items]) => (
              <div key={group}>
                <p className="px-2.5 pb-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">{group}</p>
                <div className="space-y-0.5">{items.map((it) => navButton(it))}</div>
              </div>
            ))}
          </nav>

          <div className="border-t border-slate-200 px-4 py-3">
            <div className="flex items-center justify-between text-[11px] text-slate-500">
              <span>Posted value</span>
              <span className="font-mono font-semibold text-slate-900">{inr(tb?.total_debit_balance)}</span>
            </div>
            <div className="mt-1 flex items-center justify-between text-[11px] text-slate-500">
              <span>Documents</span>
              <span className="font-mono font-semibold text-slate-900">{documents.length}</span>
            </div>
            <button
              onClick={() => {
                localStorage.removeItem(SETUP_KEY);
                setSetupDone(false);
              }}
              className="mt-2 cursor-pointer text-[10px] text-slate-400 underline-offset-2 hover:text-slate-600 hover:underline"
            >
              Run company setup again
            </button>
          </div>
        </aside>

        <div className="min-w-0 flex-1">
          <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
              <div className="flex min-w-0 items-center gap-2">
                <button
                  onClick={() => go('invoices')}
                  className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white lg:hidden"
                  title="Invoice to Books"
                >
                  <Landmark className="h-4 w-4" />
                </button>
                <div className="min-w-0">
                  <h1 className="truncate text-[15px] font-semibold tracking-tight text-slate-900">{title}</h1>
                  <p className="hidden truncate text-[11px] text-slate-500 sm:block">{subtitle}</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <div
                  className={`flex items-center gap-2 rounded-lg border px-2.5 py-1.5 ${
                    badge.tone === 'emerald'
                      ? 'border-emerald-200 bg-emerald-50'
                      : badge.tone === 'amber'
                      ? 'border-amber-200 bg-amber-50'
                      : 'border-rose-200 bg-rose-50'
                  }`}
                  title={badge.sub}
                >
                  <BadgeIcon
                    className={`h-3.5 w-3.5 ${
                      badge.tone === 'emerald' ? 'text-emerald-600' : badge.tone === 'amber' ? 'text-amber-600' : 'text-rose-600'
                    }`}
                  />
                  <div className="leading-tight">
                    <p
                      className={`text-[11px] font-bold ${
                        badge.tone === 'emerald' ? 'text-emerald-800' : badge.tone === 'amber' ? 'text-amber-800' : 'text-rose-800'
                      }`}
                    >
                      {badge.label}
                    </p>
                    <p className="hidden text-[10px] text-slate-500 sm:block">{badge.sub}</p>
                  </div>
                </div>
                <Btn variant="secondary" size="sm" onClick={refreshDocs} disabled={refreshing} title="Refresh books">
                  <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                  <span className="hidden sm:inline">Refresh</span>
                </Btn>
              </div>
            </div>

            <div className="flex gap-1 overflow-x-auto border-t border-slate-100 px-3 py-2 lg:hidden">
              {NAV.map((it) => navButton(it, true))}
            </div>
          </header>

          <main className="mx-auto max-w-[1400px] px-4 py-5 sm:px-6">
            {booting ? (
              <div className="rounded-xl border border-slate-200 bg-white px-6 py-16 text-center">
                <p className="text-xs text-slate-500">Opening the books…</p>
              </div>
            ) : view === 'review' ? (
              docId ? (
                <Review docId={docId} onBack={() => go('invoices')} onChanged={refreshDocs} />
              ) : (
                <ReviewQueue documents={documents} onOpen={(id) => go('review', id)} onRefresh={refreshDocs} />
              )
            ) : view === 'books' ? (
              <DayBooks />
            ) : view === 'ledgers' ? (
              <Ledgers />
            ) : view === 'final' ? (
              <FinalAccounts financialYears={financialYears} fy={fy} onFy={setFy} asOf={asOf} onAsOf={setAsOf} />
            ) : view === 'company' ? (
              <CompanyProfile tenant={tenant} onSaved={(t) => { setTenant(t); loadCore(); }} />
            ) : (
              <Invoices
                documents={documents}
                loading={refreshing}
                onRefresh={refreshDocs}
                onOpen={(id) => go('review', id)}
              />
            )}
          </main>
        </div>
      </div>
    </div>
  );
}

function ReviewQueue({ documents, onOpen, onRefresh }) {
  const review = documents.filter((d) => d.status !== 'POSTED');
  const [busy, setBusy] = useState(false);

  const processAll = async () => {
    setBusy(true);
    try {
      await axios.post('/api/documents/batch-process');
      await onRefresh();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Review queue</h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Invoices that are extracted but not yet posted. Open one to check the fields and approve it.
          </p>
        </div>
        <Btn variant="secondary" onClick={processAll} disabled={busy}>
          {busy ? 'Processing…' : 'Process pending uploads'}
        </Btn>
      </div>

      {review.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-300 bg-white px-6 py-14 text-center">
          <p className="text-sm font-semibold text-slate-700">Nothing waiting</p>
          <p className="mt-1 text-xs text-slate-500">Every extracted invoice has been posted.</p>
        </div>
      ) : (
        <div className="divide-y divide-slate-100 overflow-hidden rounded-xl border border-slate-200 bg-white">
          {review.map((d) => (
            <button
              key={d.id}
              onClick={() => onOpen(d.id)}
              className="flex w-full cursor-pointer items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
            >
              <div className="min-w-0">
                <p className="truncate text-[13px] font-semibold text-slate-900">{d.invoice_number || d.filename}</p>
                <p className="truncate text-[11px] text-slate-500">
                  {d.buyer_name || d.vendor_name || '—'} · {d.filename}
                </p>
              </div>
              <div className="flex items-center gap-3">
                <Badge tone={d.status === 'REVIEW_REQUIRED' ? 'amber' : 'indigo'}>
                  {d.status.replace('_', ' ').toLowerCase()}
                </Badge>
                <span className="w-28 text-right font-mono text-[13px] font-semibold tabular-nums text-slate-900">
                  {inr(d.grand_total)}
                </span>
                <ArrowLeft className="h-4 w-4 rotate-180 text-slate-400" />
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
