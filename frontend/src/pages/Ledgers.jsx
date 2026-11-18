import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { RefreshCw, Search, BookOpen, ChevronDown, ChevronRight, HandCoins, Users } from 'lucide-react';
import {
  Badge,
  Btn,
  Card,
  Empty,
  Field,
  Input,
  Select,
  Stat,
  Table,
  TD,
  TH,
  Tabs,
} from '../components/ui.jsx';
import { dt, inr, num, paymentTone, today } from '../lib/format.js';

const CATEGORY_LABEL = {
  ASSET: 'Assets',
  LIABILITY: 'Liabilities',
  EQUITY: 'Equity',
  REVENUE: 'Revenue',
  EXPENSE: 'Expenses',
};

function Folio({ code, onSettled }) {
  const [folio, setFolio] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!code) return;
    setLoading(true);
    setError('');
    axios
      .get(`/api/reports/ledger-folio/${code}`)
      .then((r) => setFolio(r.data))
      .catch((e) => setError(e.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [code, onSettled]);

  if (loading) {
    return (
      <Card>
        <p className="py-8 text-center text-xs text-slate-500">Opening folio…</p>
      </Card>
    );
  }
  if (error) {
    return (
      <Card>
        <p className="py-8 text-center text-xs text-rose-600">{error}</p>
      </Card>
    );
  }
  if (!folio) return null;

  const dr = (folio.transactions || []).reduce((a, t) => a + Number(t.debit || 0), 0);
  const cr = (folio.transactions || []).reduce((a, t) => a + Number(t.credit || 0), 0);

  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[11px] text-slate-500">{folio.account_code}</span>
            <h2 className="text-[15px] font-semibold text-slate-900">{folio.account_name}</h2>
          </div>
          <p className="mt-0.5 text-[11px] text-slate-500">
            {CATEGORY_LABEL[folio.category] || folio.category} · normal balance {folio.normal_balance.toLowerCase()} ·{' '}
            {folio.financial_year || 'all years'}
          </p>
        </div>
        <div className="text-right">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Closing balance</p>
          <p className="font-mono text-lg font-semibold tabular-nums text-slate-900">
            {inr(folio.closing_balance)} <span className="text-xs font-medium text-slate-400">{folio.closing_balance_type}</span>
          </p>
        </div>
      </div>

      {!folio.transactions?.length ? (
        <p className="px-5 py-10 text-center text-xs text-slate-500">No postings in this account yet.</p>
      ) : (
        <Table className="rounded-none border-0">
          <thead>
            <tr>
              <TH>Date</TH>
              <TH>Particulars</TH>
              <TH>Voucher</TH>
              <TH right>Debit</TH>
              <TH right>Credit</TH>
              <TH right>Balance</TH>
            </tr>
          </thead>
          <tbody>
            {folio.transactions.map((t) => (
              <tr key={t.id} className="hover:bg-slate-50">
                <TD mono>{dt(t.date)}</TD>
                <TD className="max-w-[340px]">
                  <div className="truncate">{t.particulars || '—'}</div>
                  {t.invoice_number && <div className="font-mono text-[10px] text-slate-400">{t.invoice_number}</div>}
                </TD>
                <TD mono className="text-[11px] text-slate-400">{t.entry_id?.slice(0, 8)}</TD>
                <TD right mono>{t.debit ? num(t.debit) : '—'}</TD>
                <TD right mono>{t.credit ? num(t.credit) : '—'}</TD>
                <TD right mono className="font-semibold text-slate-900">
                  {num(t.running_balance)} <span className="text-[10px] font-normal text-slate-400">{t.balance_type}</span>
                </TD>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <TD className="bg-slate-50 font-semibold text-slate-900" colSpan={3}>
                {folio.total_transactions} postings
              </TD>
              <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(dr)}</TD>
              <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(cr)}</TD>
              <TD className="bg-slate-50" />
            </tr>
          </tfoot>
        </Table>
      )}
    </Card>
  );
}

function SettleForm({ invoice, onDone, onCancel }) {
  const [amount, setAmount] = useState(String(invoice.balance_due ?? ''));
  const [account, setAccount] = useState('1020');
  const [ref, setRef] = useState('');
  const [date, setDate] = useState(today());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await axios.post(`/api/invoices/${invoice.id}/settle`, {
        amount: Number(amount),
        payment_account_code: account,
        payment_reference: ref || undefined,
        payment_date: date,
      });
      await onDone();
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-2 rounded-lg border border-indigo-200 bg-indigo-50/50 px-3 py-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Field label="Amount">
          <Input type="number" step="any" value={amount} onChange={(e) => setAmount(e.target.value)} className="text-right font-mono" />
        </Field>
        <Field label="Paid from / into">
          <Select value={account} onChange={(e) => setAccount(e.target.value)}>
            <option value="1020">Bank</option>
            <option value="1010">Cash</option>
          </Select>
        </Field>
        <Field label="Reference">
          <Input value={ref} onChange={(e) => setRef(e.target.value)} placeholder="UTR / cheque no." />
        </Field>
        <Field label="Date">
          <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
      </div>
      {error && <p className="mt-2 text-[11px] font-medium text-rose-700">{error}</p>}
      <div className="mt-2 flex items-center justify-end gap-2">
        <Btn size="sm" variant="ghost" type="button" onClick={onCancel}>
          Cancel
        </Btn>
        <Btn size="sm" variant="success" type="submit" disabled={busy}>
          {busy ? 'Posting…' : 'Record settlement'}
        </Btn>
      </div>
    </form>
  );
}

function PartyCard({ party, kind, onSettled }) {
  const [open, setOpen] = useState(false);
  const [settling, setSettling] = useState(null);
  const isPayable = kind === 'payable';
  const received = isPayable ? party.total_paid : party.total_received;

  return (
    <Card padded={false}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full cursor-pointer flex-wrap items-center justify-between gap-3 px-4 py-3 text-left hover:bg-slate-50"
      >
        <div className="flex items-start gap-2">
          {open ? <ChevronDown className="mt-0.5 h-4 w-4 text-slate-400" /> : <ChevronRight className="mt-0.5 h-4 w-4 text-slate-400" />}
          <div>
            <p className="text-[13px] font-semibold text-slate-900">{party.party_name}</p>
            <p className="text-[11px] text-slate-500">
              {party.gstin || 'GSTIN not recorded'} · {party.invoices?.length || 0} invoice(s)
            </p>
          </div>
        </div>
        <div className="flex items-center gap-5 text-right">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{isPayable ? 'Billed' : 'Raised'}</p>
            <p className="font-mono text-[12px] tabular-nums text-slate-700">{num(party.total_billed)}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{isPayable ? 'Paid' : 'Received'}</p>
            <p className="font-mono text-[12px] tabular-nums text-slate-700">{num(received)}</p>
          </div>
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">Outstanding</p>
            <p className={`font-mono text-[13px] font-semibold tabular-nums ${party.balance_due > 0 ? 'text-rose-700' : 'text-emerald-700'}`}>
              {num(party.balance_due)}
            </p>
          </div>
        </div>
      </button>

      {open && (
        <div className="border-t border-slate-200 px-4 py-3">
          <div className="space-y-2">
            {(party.invoices || []).map((inv) => (
              <div key={inv.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[11px] text-slate-400">{dt(inv.invoice_date)}</span>
                    <span className="text-[12px] font-semibold text-slate-900">{inv.invoice_number}</span>
                    <Badge tone={paymentTone(inv.payment_status)}>{(inv.payment_status || '').replace('_', ' ').toLowerCase()}</Badge>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-[11px] text-slate-500">total {num(inv.grand_total)}</span>
                    <span className="font-mono text-[12px] font-semibold text-slate-900">due {num(inv.balance_due)}</span>
                    {inv.balance_due > 0 && (
                      <Btn
                        size="sm"
                        variant="secondary"
                        onClick={() => setSettling(settling === inv.id ? null : inv.id)}
                      >
                        <HandCoins className="h-3.5 w-3.5" /> Settle
                      </Btn>
                    )}
                  </div>
                </div>
                {settling === inv.id && (
                  <SettleForm
                    invoice={inv}
                    onCancel={() => setSettling(null)}
                    onDone={async () => {
                      setSettling(null);
                      await onSettled();
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
}

export default function Ledgers() {
  const [tab, setTab] = useState('folios');
  const [accounts, setAccounts] = useState([]);
  const [sub, setSub] = useState(null);
  const [selected, setSelected] = useState('2010');
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('ALL');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tick, setTick] = useState(0);

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const [a, s] = await Promise.all([
        axios.get('/api/accounts'),
        axios.get('/api/reports/subsidiary-ledger'),
      ]);
      setAccounts(a.data);
      setSub(s.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    const n = q.trim().toLowerCase();
    return accounts.filter((a) => {
      if (category !== 'ALL' && a.category !== category) return false;
      if (!n) return true;
      return `${a.code} ${a.name}`.toLowerCase().includes(n);
    });
  }, [accounts, q, category]);

  const grouped = useMemo(() => {
    const map = {};
    for (const a of filtered) (map[a.category] ||= []).push(a);
    return map;
  }, [filtered]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Ledgers</h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Every account has a folio. Parties carry their own subsidiary ledger so outstanding balances can be settled invoice by invoice.
          </p>
        </div>
        <Btn variant="secondary" onClick={load} disabled={loading}>
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </Btn>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Payables outstanding" value={inr(sub?.total_payables_outstanding)} sub={`${sub?.payables_vendors?.length || 0} suppliers`} tone="rose" />
        <Stat label="Receivables outstanding" value={inr(sub?.total_receivables_outstanding)} sub={`${sub?.receivables_customers?.length || 0} customers`} tone="emerald" />
        <Stat label="Ledger accounts" value={String(accounts.length)} sub="chart of accounts" />
        <Stat label="Party ledgers" value={String((sub?.payables_vendors?.length || 0) + (sub?.receivables_customers?.length || 0))} sub="with open balances" />
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</div>}

      <Tabs
        items={[
          { value: 'folios', label: 'Account folios' },
          { value: 'parties', label: 'Party ledgers & settlement' },
        ]}
        value={tab}
        onChange={setTab}
      />

      {tab === 'folios' ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[300px_minmax(0,1fr)]">
          <Card padded={false} className="self-start">
            <div className="space-y-2 border-b border-slate-200 p-3">
              <div className="relative">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
                <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Find account" className="pl-8" />
              </div>
              <Select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="ALL">All categories</option>
                {Object.entries(CATEGORY_LABEL).map(([k, v]) => (
                  <option key={k} value={k}>{v}</option>
                ))}
              </Select>
            </div>
            <div className="max-h-[520px] overflow-y-auto p-2">
              {Object.keys(grouped).length === 0 && (
                <p className="px-2 py-6 text-center text-xs text-slate-400">No account matches.</p>
              )}
              {Object.entries(grouped).map(([cat, list]) => (
                <div key={cat} className="mb-2">
                  <p className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    {CATEGORY_LABEL[cat] || cat}
                  </p>
                  {list.map((a) => (
                    <button
                      key={a.code}
                      onClick={() => setSelected(a.code)}
                      className={`flex w-full cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 text-left text-[12px] transition-colors ${
                        selected === a.code ? 'bg-indigo-50 font-semibold text-indigo-800' : 'text-slate-700 hover:bg-slate-50'
                      }`}
                    >
                      <span className="font-mono text-[10px] text-slate-400">{a.code}</span>
                      <span className="truncate">{a.name}</span>
                    </button>
                  ))}
                </div>
              ))}
            </div>
          </Card>

          <div>
            {selected ? (
              <Folio code={selected} onSettled={tick} />
            ) : (
              <Empty title="Choose an account" sub="Its transactions, running balance and closing balance appear here." />
            )}
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-rose-600" />
              <h2 className="text-[13px] font-bold uppercase tracking-wider text-slate-600">Sundry creditors — purchases</h2>
            </div>
            {!sub?.payables_vendors?.length ? (
              <Empty title="No supplier balances" sub="Posted purchase bills appear here." />
            ) : (
              sub.payables_vendors.map((p) => (
                <PartyCard key={p.party_name} party={p} kind="payable" onSettled={() => { load(); setTick((t) => t + 1); }} />
              ))
            )}
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <BookOpen className="h-4 w-4 text-emerald-600" />
              <h2 className="text-[13px] font-bold uppercase tracking-wider text-slate-600">Sundry debtors — sales</h2>
            </div>
            {!sub?.receivables_customers?.length ? (
              <Empty title="No customer balances" sub="Posted sales invoices appear here." />
            ) : (
              sub.receivables_customers.map((p) => (
                <PartyCard key={p.party_name} party={p} kind="receivable" onSettled={() => { load(); setTick((t) => t + 1); }} />
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
