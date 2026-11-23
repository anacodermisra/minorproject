import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import { RefreshCw, Download, Search } from 'lucide-react';
import { Badge, Btn, Card, Empty, Input, Stat, Table, TD, TH, Tabs } from '../components/ui.jsx';
import { dt, inr, num, paymentTone } from '../lib/format.js';

const BOOKS = [
  { value: 'purchase_book', label: 'Purchase register' },
  { value: 'sales_book', label: 'Sales register' },
  { value: 'cash_bank_book', label: 'Cash & bank book' },
  { value: 'journal_proper', label: 'Journal proper' },
];

function RegisterBook({ rows, partyLabel }) {
  const [q, setQ] = useState('');
  const filtered = useMemo(() => {
    const n = q.trim().toLowerCase();
    if (!n) return rows;
    return rows.filter((r) =>
      [r.party_name, r.invoice_number, r.gstin].filter(Boolean).some((v) => String(v).toLowerCase().includes(n))
    );
  }, [rows, q]);

  const totals = filtered.reduce(
    (a, r) => ({
      subtotal: a.subtotal + Number(r.subtotal || 0),
      tax: a.tax + Number(r.tax || 0),
      grand: a.grand + Number(r.grand_total || 0),
    }),
    { subtotal: 0, tax: 0, grand: 0 }
  );

  if (!rows.length) {
    return <Empty title="No entries in this register yet" sub="Invoices posted under this book will appear here automatically." />;
  }

  return (
    <div className="space-y-3">
      <div className="relative max-w-xs">
        <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
        <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by party, number or GSTIN" className="pl-8" />
      </div>
      <Table>
        <thead>
          <tr>
            <TH>Date</TH>
            <TH>Invoice #</TH>
            <TH>{partyLabel}</TH>
            <TH>GSTIN</TH>
            <TH right>Taxable value</TH>
            <TH right>GST</TH>
            <TH right>Invoice total</TH>
            <TH>Payment</TH>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={r.id} className="hover:bg-slate-50">
              <TD mono>{dt(r.date)}</TD>
              <TD className="font-medium text-slate-900">{r.invoice_number}</TD>
              <TD>{r.party_name || '—'}</TD>
              <TD mono className="text-[11px] text-slate-500">{r.gstin || '—'}</TD>
              <TD right mono>{num(r.subtotal)}</TD>
              <TD right mono>{num(r.tax)}</TD>
              <TD right mono className="font-semibold text-slate-900">{num(r.grand_total)}</TD>
              <TD>
                <Badge tone={paymentTone(r.payment_status)}>{(r.payment_status || 'UNPAID').replace('_', ' ').toLowerCase()}</Badge>
              </TD>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <TD className="bg-slate-50 font-semibold text-slate-900" colSpan={4}>
              {filtered.length} entries
            </TD>
            <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(totals.subtotal)}</TD>
            <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(totals.tax)}</TD>
            <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(totals.grand)}</TD>
            <TD className="bg-slate-50" />
          </tr>
        </tfoot>
      </Table>
    </div>
  );
}

function CashBankBook({ rows }) {
  if (!rows.length) {
    return <Empty title="No cash or bank movements yet" sub="Settlements recorded against invoices appear here with a running balance." />;
  }
  const inflow = rows.reduce((a, r) => a + Number(r.receipt || 0), 0);
  const outflow = rows.reduce((a, r) => a + Number(r.payment || 0), 0);
  return (
    <Table>
      <thead>
        <tr>
          <TH>Date</TH>
          <TH>Account</TH>
          <TH>Voucher</TH>
          <TH>Particulars</TH>
          <TH right>Receipt</TH>
          <TH right>Payment</TH>
          <TH right>Balance</TH>
        </tr>
      </thead>
      <tbody>
        {rows.map((r) => (
          <tr key={r.id} className="hover:bg-slate-50">
            <TD mono>{dt(r.date)}</TD>
            <TD>
              <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">{r.account_code}</span>{' '}
              <span className="text-[12px]">{r.account_name}</span>
            </TD>
            <TD mono className="text-[11px] text-slate-500">{r.voucher_ref || '—'}</TD>
            <TD className="max-w-[320px] truncate">{r.particulars}</TD>
            <TD right mono className="text-emerald-700">{r.receipt ? num(r.receipt) : '—'}</TD>
            <TD right mono className="text-rose-700">{r.payment ? num(r.payment) : '—'}</TD>
            <TD right mono className="font-semibold text-slate-900">{num(r.running_balance)}</TD>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <TD className="bg-slate-50 font-semibold text-slate-900" colSpan={4}>
            Totals
          </TD>
          <TD right mono className="bg-slate-50 font-semibold text-emerald-700">{num(inflow)}</TD>
          <TD right mono className="bg-slate-50 font-semibold text-rose-700">{num(outflow)}</TD>
          <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(inflow - outflow)}</TD>
        </tr>
      </tfoot>
    </Table>
  );
}

function JournalProper({ rows, onReversed }) {
  const [reversingId, setReversingId] = useState(null);
  const [revError, setRevError] = useState('');

  const handleReverse = async (id, invNo) => {
    if (!window.confirm(`Are you sure you want to execute a Statutory Reversal for entry #${invNo || id.slice(0, 8)}? This will post an opposite contra entry to the ledger.`)) {
      return;
    }
    setReversingId(id);
    setRevError('');
    try {
      await axios.post(`/api/journal/reverse/${id}`, {
        reason: 'User requested contra reversal from Day Books workspace',
        reversed_by: 'AUDIT_CHECKER'
      });
      if (onReversed) onReversed();
    } catch (err) {
      alert(err.response?.data?.detail || err.message);
    } finally {
      setReversingId(null);
    }
  };

  if (!rows.length) {
    return <Empty title="No journal entries yet" sub="Manual adjustments, settlement entries, and statutory reversals are listed here with both sides of the entry." />;
  }
  return (
    <div className="space-y-2.5">
      {rows.map((r) => {
        const isReversal = (r.transaction_type || '').includes('REVERSAL');
        return (
          <Card key={r.id} padded={false}>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-200 px-4 py-2.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-[11px] text-slate-400">{dt(r.date)}</span>
                <span className="text-[13px] font-semibold text-slate-900">{r.invoice_number || 'Manual entry'}</span>
                <Badge tone={isReversal ? 'rose' : 'slate'}>{(r.transaction_type || '').replaceAll('_', ' ').toLowerCase()}</Badge>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-mono text-[11px] text-slate-400">{r.id.slice(0, 8)}</span>
                {!isReversal && (
                  <button
                    onClick={() => handleReverse(r.id, r.invoice_number)}
                    disabled={reversingId === r.id}
                    className="cursor-pointer rounded border border-rose-200 bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700 hover:bg-rose-100 disabled:opacity-50"
                    title="Execute statutory GAAP/Ind AS contra reversal"
                  >
                    {reversingId === r.id ? 'Reversing…' : 'Reverse entry'}
                  </button>
                )}
              </div>
            </div>
            {r.narration && <p className="px-4 pt-2 text-[11px] leading-relaxed text-slate-500">{r.narration}</p>}
            <div className="overflow-x-auto">
              <table className="mt-1 w-full border-collapse text-left text-[13px]">
                <thead>
                  <tr>
                    <TH>Account</TH>
                    <TH>Narration</TH>
                    <TH right>Debit</TH>
                    <TH right>Credit</TH>
                  </tr>
                </thead>
                <tbody>
                  {(r.lines || []).map((l, i) => (
                    <tr key={i}>
                      <TD>
                        <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                          {l.account_code}
                        </span>{' '}
                        <span className="text-[12px]">{l.account_name}</span>
                      </TD>
                      <TD className="max-w-[360px] truncate text-[11px] text-slate-500">{l.description || '—'}</TD>
                      <TD right mono>{l.debit ? num(l.debit) : '—'}</TD>
                      <TD right mono>{l.credit ? num(l.credit) : '—'}</TD>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export default function DayBooks() {
  const [book, setBook] = useState('purchase_book');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await axios.get('/api/reports/day-books');
      setData(res.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const purchaseTotal = (data?.purchase_book || []).reduce((a, r) => a + Number(r.grand_total || 0), 0);
  const salesTotal = (data?.sales_book || []).reduce((a, r) => a + Number(r.grand_total || 0), 0);
  const cashRows = data?.cash_bank_book || [];

  const exportCsv = () => {
    const rows =
      book === 'cash_bank_book'
        ? cashRows
        : book === 'journal_proper'
        ? (data?.journal_proper || [])
        : data?.[book] || [];
    if (!rows.length) return;
    const keys = book === 'journal_proper' ? ['id', 'date', 'invoice_number', 'transaction_type', 'narration'] : Object.keys(rows[0]);
    const csv = [keys.join(','), ...rows.map((r) => keys.map((k) => JSON.stringify(r[k] ?? '')).join(','))].join('\n');
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = `${book}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Day books &amp; registers</h1>
          <p className="mt-0.5 text-xs text-slate-500">
            The four statutory books of account, each generated from the posted journal — not typed separately.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Btn variant="secondary" onClick={load} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Btn>
          <Btn variant="secondary" onClick={exportCsv}>
            <Download className="h-3.5 w-3.5" /> Export CSV
          </Btn>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Purchase register" value={inr(purchaseTotal)} sub={`${(data?.purchase_book || []).length} bills`} />
        <Stat label="Sales register" value={inr(salesTotal)} sub={`${(data?.sales_book || []).length} invoice${(data?.sales_book || []).length === 1 ? '' : 's'}`} />
        <Stat label="Cash & bank entries" value={String(cashRows.length)} sub="receipts and payments" />
        <Stat label="Journal entries" value={String((data?.journal_proper || []).length)} sub="including settlements" />
      </div>

      {error && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</div>
      )}

      <Tabs items={BOOKS} value={book} onChange={setBook} />

      {loading && !data ? (
        <Card>
          <p className="py-10 text-center text-xs text-slate-500">Building the books…</p>
        </Card>
      ) : book === 'purchase_book' ? (
        <RegisterBook rows={data?.purchase_book || []} partyLabel="Supplier" />
      ) : book === 'sales_book' ? (
        <RegisterBook rows={data?.sales_book || []} partyLabel="Customer" />
      ) : book === 'cash_bank_book' ? (
        <CashBankBook rows={cashRows} />
      ) : (
        <JournalProper rows={data?.journal_proper || []} onReversed={load} />
      )}
    </div>
  );
}
