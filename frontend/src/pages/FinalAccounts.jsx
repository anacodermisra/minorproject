import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { RefreshCw, Scale, CalendarDays, History } from 'lucide-react';
import {
  Badge,
  Btn,
  Card,
  Empty,
  Input,
  Select,
  Stat,
  Table,
  TD,
  TH,
  Tabs,
} from '../components/ui.jsx';
import { dt, inr, num } from '../lib/format.js';

const VIEWS = [
  { value: 'tb', label: 'Trial balance' },
  { value: 'trading', label: 'Trading account' },
  { value: 'pl', label: 'Profit & loss' },
  { value: 'bs', label: 'Balance sheet' },
  { value: 'monthly', label: '12-month analytics' },
  { value: 'audit', label: 'Audit trail' },
];

function ReportShell({ title, sub, right, children }) {
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-200 px-5 py-4">
        <div>
          <h2 className="text-[15px] font-semibold tracking-tight text-slate-900">{title}</h2>
          {sub && <p className="mt-0.5 text-[11px] text-slate-500">{sub}</p>}
        </div>
        {right}
      </div>
      {children}
    </Card>
  );
}

function TrialBalance({ tb }) {
  if (!tb) return null;
  return (
    <ReportShell
      title="Trial balance"
      sub={`All ledger accounts as at ${dt(tb.as_of_date)} · ${tb.financial_year || 'all years'}`}
      right={
        <Badge tone={tb.is_balanced ? 'emerald' : 'rose'} dot>
          {tb.is_balanced ? 'Debits equal credits' : 'Out of balance'}
        </Badge>
      }
    >
      <Table className="rounded-none border-0">
        <thead>
          <tr>
            <TH>Code</TH>
            <TH>Account</TH>
            <TH>Group</TH>
            <TH right>Total debit</TH>
            <TH right>Total credit</TH>
            <TH right>Closing balance</TH>
          </tr>
        </thead>
        <tbody>
          {tb.rows.map((r) => (
            <tr key={r.account_code} className="hover:bg-slate-50">
              <TD mono className="text-[11px] text-slate-500">{r.account_code}</TD>
              <TD className="font-medium text-slate-900">{r.account_name}</TD>
              <TD>
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">{r.category}</span>
              </TD>
              <TD right mono>{num(r.total_debits)}</TD>
              <TD right mono>{num(r.total_credits)}</TD>
              <TD right mono className="font-semibold text-slate-900">
                {num(r.closing_balance)} <span className="text-[10px] font-normal text-slate-400">{r.balance_type}</span>
              </TD>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <TD className="bg-slate-50 font-semibold text-slate-900" colSpan={3}>
              {tb.rows.length} accounts
            </TD>
            <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(tb.total_debit_balance)}</TD>
            <TD right mono className="bg-slate-50 font-semibold text-slate-900">{num(tb.total_credit_balance)}</TD>
            <TD className="bg-slate-50" />
          </tr>
        </tfoot>
      </Table>
    </ReportShell>
  );
}

function TradingAndPnl({ data }) {
  if (!data) return null;
  const t = data.trading_account || {};
  const p = data.profit_and_loss_account || {};

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <ReportShell
        title="Trading account"
        sub={`Gross profit for the period ending ${dt(data.as_of_date)}`}
        right={<Badge tone={t.is_gross_profit ? 'emerald' : 'rose'}>{t.is_gross_profit ? 'Gross profit' : 'Gross loss'}</Badge>}
      >
        <div className="divide-y divide-slate-100">
          <div className="flex items-center justify-between px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">Net sales / revenue</span>
            <span className="font-mono tabular-nums text-slate-900">{num(t.sales_revenue)}</span>
          </div>
          <div className="flex items-center justify-between px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">Less: cost of goods sold</span>
            <span className="font-mono tabular-nums text-slate-900">({num(t.cost_of_goods_sold)})</span>
          </div>
          <div className="flex items-center justify-between bg-slate-50 px-5 py-3">
            <span className="text-[13px] font-semibold text-slate-900">Gross profit carried to P&amp;L</span>
            <span className={`font-mono text-[15px] font-semibold tabular-nums ${t.is_gross_profit ? 'text-emerald-700' : 'text-rose-700'}`}>
              {inr(t.gross_profit)}
            </span>
          </div>
        </div>
        <p className="px-5 py-3 text-[11px] leading-relaxed text-slate-400">
          Sales come from the sales register. Cost of goods sold comes from the purchases of trading goods, so stock and
          purchases are not double counted.
        </p>
      </ReportShell>

      <ReportShell
        title="Profit & loss account"
        sub={`Net result for the period ending ${dt(data.as_of_date)}`}
        right={<Badge tone={p.is_net_profit ? 'emerald' : 'rose'}>{p.is_net_profit ? 'Net profit' : 'Net loss'}</Badge>}
      >
        <div className="divide-y divide-slate-100">
          <div className="flex items-center justify-between px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">Gross profit brought forward</span>
            <span className="font-mono tabular-nums text-slate-900">{num(p.gross_profit_bf)}</span>
          </div>
          <div className="flex items-center justify-between px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">Other income</span>
            <span className="font-mono tabular-nums text-slate-900">{num(p.other_income)}</span>
          </div>
          <div className="flex items-center justify-between px-5 py-2.5 text-[13px]">
            <span className="text-slate-600">Less: indirect expenses</span>
            <span className="font-mono tabular-nums text-slate-900">({num(p.total_indirect_expenses)})</span>
          </div>
          <div className="flex items-center justify-between bg-slate-50 px-5 py-3">
            <span className="text-[13px] font-semibold text-slate-900">Net profit transferred to capital</span>
            <span className={`font-mono text-[15px] font-semibold tabular-nums ${p.is_net_profit ? 'text-emerald-700' : 'text-rose-700'}`}>
              {inr(p.net_profit)}
            </span>
          </div>
        </div>
        <div className="px-5 py-3">
          {(p.indirect_expenses || []).length ? (
            <div className="space-y-1">
              {(p.indirect_expenses || []).map((e) => (
                <div key={e.code || e.name} className="flex items-center justify-between text-[11px] text-slate-500">
                  <span>{e.name}</span>
                  <span className="font-mono tabular-nums">{num(e.amount)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-slate-400">No indirect expenses posted in this period.</p>
          )}
        </div>
      </ReportShell>
    </div>
  );
}

function BalanceSheet({ bs }) {
  if (!bs) return null;
  const Section = ({ title, rows, total, totalLabel, tone }) => (
    <div>
      <div className="flex items-center justify-between border-b border-slate-200 px-5 py-2">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500">{title}</span>
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">{totalLabel || 'Amount'}</span>
      </div>
      <div className="divide-y divide-slate-50 px-5">
        {rows.length === 0 && <p className="py-3 text-[11px] text-slate-400">Nothing in this section.</p>}
        {rows.map((r) => (
          <div key={r.code} className="flex items-center justify-between py-2 text-[13px]">
            <span className="text-slate-600">
              <span className="mr-2 font-mono text-[10px] text-slate-400">{r.code}</span>
              {r.name}
            </span>
            <span className="font-mono tabular-nums text-slate-900">{num(r.amount)}</span>
          </div>
        ))}
        {rows.length > 0 && (
          <div className="flex items-center justify-between border-t border-slate-200 py-2.5">
            <span className="text-[13px] font-semibold text-slate-900">Total {title.toLowerCase()}</span>
            <span className={`font-mono text-[13px] font-semibold tabular-nums ${tone}`}>{inr(total)}</span>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <ReportShell
      title="Balance sheet"
      sub={`Position as at ${dt(bs.as_of_date)} · ${bs.financial_year || 'all years'}`}
      right={<Badge tone={bs.is_balanced ? 'emerald' : 'rose'} dot>{bs.is_balanced ? 'Balanced' : 'Does not balance'}</Badge>}
    >
      <div className="grid grid-cols-1 divide-y divide-slate-200 lg:grid-cols-2 lg:divide-x lg:divide-y-0">
        <Section title="Assets" rows={bs.assets || []} total={bs.total_assets} tone="text-slate-900" />
        <div>
          <Section title="Liabilities" rows={bs.liabilities || []} total={bs.total_liabilities} tone="text-slate-900" />
          <div className="border-t border-slate-200 px-5">
            <div className="flex items-center justify-between py-2 text-[13px]">
              <span className="text-slate-600">Owner's equity</span>
              <span className="font-mono tabular-nums text-slate-900">{num(bs.total_equity)}</span>
            </div>
            <div className="flex items-center justify-between py-2 text-[13px]">
              <span className="text-slate-600">Retained earnings (current year result)</span>
              <span className="font-mono tabular-nums text-slate-900">{num(bs.retained_earnings)}</span>
            </div>
            <div className="flex items-center justify-between border-t border-slate-200 py-2.5">
              <span className="text-[13px] font-semibold text-slate-900">Total liabilities &amp; equity</span>
              <span className="font-mono text-[13px] font-semibold tabular-nums text-slate-900">
                {inr(bs.total_liabilities_and_equity)}
              </span>
            </div>
          </div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 border-t border-slate-200 bg-slate-50/60 px-5 py-3">
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-slate-500">Total assets</span>
          <span className="font-mono font-semibold tabular-nums text-slate-900">{inr(bs.total_assets)}</span>
        </div>
        <div className="flex items-center justify-between text-[12px]">
          <span className="text-slate-500">Total liabilities &amp; equity</span>
          <span className="font-mono font-semibold tabular-nums text-slate-900">{inr(bs.total_liabilities_and_equity)}</span>
        </div>
      </div>
      {(bs.equity || []).length > 0 && (
        <p className="px-5 py-2 text-[11px] text-slate-400">
          Equity accounts: {(bs.equity || []).map((e) => e.name).join(', ')}
        </p>
      )}
    </ReportShell>
  );
}

function Monthly({ data }) {
  if (!data) return null;
  const months = data.months || [];
  const max = Math.max(1, ...months.map((m) => Math.max(Number(m.revenue || 0), Number(m.expenses || 0))));
  const revenue = months.reduce((a, m) => a + Number(m.revenue || 0), 0);
  const expenses = months.reduce((a, m) => a + Number(m.expenses || 0), 0);
  const tax = months.reduce((a, m) => a + Number(m.output_tax || 0), 0);
  const itc = months.reduce((a, m) => a + Number(m.itc_claimed || 0), 0);

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Revenue for the year" value={inr(revenue)} sub="posted sales" tone="emerald" />
        <Stat label="Expenses for the year" value={inr(expenses)} sub="direct and indirect" tone="rose" />
        <Stat label="Net result" value={inr(revenue - expenses)} sub="before owner drawings" tone={revenue - expenses >= 0 ? 'emerald' : 'rose'} />
        <Stat label="Output GST / ITC" value={`${inr(tax)} / ${inr(itc)}`} sub="liability vs credit available" />
      </div>

      <ReportShell
        title={`Month by month · ${data.financial_year || ''}`}
        sub="Revenue against expenses, from the journal. Bars are scaled to the highest month."
      >
        <div className="space-y-2 px-5 py-4">
          {months.map((m) => {
            const revW = (Number(m.revenue || 0) / max) * 100;
            const expW = (Number(m.expenses || 0) / max) * 100;
            return (
              <div key={`${m.year}-${m.month_number}`} className="grid grid-cols-[52px_minmax(0,1fr)_120px] items-center gap-3">
                <span className={`text-[11px] font-semibold ${m.transaction_count ? 'text-slate-700' : 'text-slate-300'}`}>
                  {m.month_short}
                </span>
                <div className="space-y-1">
                  <div className="h-2.5 overflow-hidden rounded-sm bg-slate-100">
                    <div className="h-full rounded-sm bg-emerald-500/80" style={{ width: `${revW}%` }} />
                  </div>
                  <div className="h-2.5 overflow-hidden rounded-sm bg-slate-100">
                    <div className="h-full rounded-sm bg-rose-400/80" style={{ width: `${expW}%` }} />
                  </div>
                </div>
                <div className="text-right">
                  <p className={`font-mono text-[11px] tabular-nums ${m.net_profit >= 0 ? 'text-emerald-700' : 'text-rose-700'}`}>
                    {num(m.net_profit)}
                  </p>
                  <p className="text-[10px] text-slate-400">
                    {m.transaction_count} entr{m.transaction_count === 1 ? 'y' : 'ies'}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
        <div className="flex items-center gap-4 border-t border-slate-200 px-5 py-2.5">
          <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="h-2 w-2 rounded-sm bg-emerald-500/80" /> Revenue
          </span>
          <span className="flex items-center gap-1.5 text-[11px] text-slate-500">
            <span className="h-2 w-2 rounded-sm bg-rose-400/80" /> Expenses
          </span>
        </div>
      </ReportShell>

      <ReportShell title="Cash and tax by month" sub="Receipts, payments and GST position month by month.">
        <Table className="rounded-none border-0">
          <thead>
            <tr>
              <TH>Month</TH>
              <TH right>Revenue</TH>
              <TH right>Expenses</TH>
              <TH right>Net profit</TH>
              <TH right>Cash in</TH>
              <TH right>Cash out</TH>
              <TH right>Net cash</TH>
              <TH right>Output GST</TH>
              <TH right>ITC claimed</TH>
            </tr>
          </thead>
          <tbody>
            {months.map((m) => (
              <tr key={`${m.year}-${m.month_number}`} className={m.transaction_count ? 'hover:bg-slate-50' : 'text-slate-400'}>
                <TD className="font-medium">{m.month_short} {m.year}</TD>
                <TD right mono>{num(m.revenue)}</TD>
                <TD right mono>{num(m.expenses)}</TD>
                <TD right mono className={m.net_profit >= 0 ? 'text-emerald-700' : 'text-rose-700'}>{num(m.net_profit)}</TD>
                <TD right mono>{num(m.cash_inflow)}</TD>
                <TD right mono>{num(m.cash_outflow)}</TD>
                <TD right mono>{num(m.net_cash_flow)}</TD>
                <TD right mono>{num(m.output_tax)}</TD>
                <TD right mono>{num(m.itc_claimed)}</TD>
              </tr>
            ))}
          </tbody>
        </Table>
      </ReportShell>
    </div>
  );
}

const ACTION_LABEL = {
  UPLOAD: 'Uploaded',
  PROCESS: 'Processed',
  UPDATE: 'Edited',
  POST: 'Posted',
  DELETE: 'Deleted',
  SETTLE: 'Settled',
  RESET: 'Reset data',
};

function Audit({ logs }) {
  if (!logs?.length) {
    return <Empty title="No audit records yet" sub="Uploads, edits, postings and settlements are logged here with who did them and when." />;
  }
  return (
    <ReportShell title="Audit trail" sub="Every state change, newest first.">
      <div className="divide-y divide-slate-100">
        {logs.map((l) => (
          <div key={l.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-2.5">
            <div className="flex items-start gap-2">
              <History className="mt-0.5 h-3.5 w-3.5 shrink-0 text-slate-400" />
              <div>
                <p className="text-[12px] font-semibold text-slate-800">
                  <span className="mr-2 rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] uppercase text-slate-500">
                    {ACTION_LABEL[l.action] || l.action}
                  </span>
                  {l.entity_name} <span className="font-normal text-slate-400">· {String(l.entity_id || '').slice(0, 8)}</span>
                </p>
                {l.details && <p className="mt-0.5 text-[11px] text-slate-500">{typeof l.details === 'string' ? l.details : JSON.stringify(l.details)}</p>}
              </div>
            </div>
            <div className="text-right">
              <p className="text-[11px] font-medium text-slate-600">{l.performed_by}</p>
              <p className="font-mono text-[10px] text-slate-400">
                {l.timestamp ? new Date(l.timestamp).toLocaleString('en-GB') : ''}
              </p>
            </div>
          </div>
        ))}
      </div>
    </ReportShell>
  );
}

export default function FinalAccounts({ financialYears, fy, onFy, asOf, onAsOf }) {
  const [view, setView] = useState('tb');
  const [tb, setTb] = useState(null);
  const [tp, setTp] = useState(null);
  const [bs, setBs] = useState(null);
  const [monthly, setMonthly] = useState(null);
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    const params = { as_of_date: asOf, financial_year: fy };
    try {
      const [a, b, c] = await Promise.all([
        axios.get('/api/reports/trial-balance', { params }),
        axios.get('/api/reports/trading-and-pnl', { params }),
        axios.get('/api/reports/balance-sheet', { params }),
      ]);
      setTb(a.data);
      setTp(b.data);
      setBs(c.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const loadMonthly = async () => {
    try {
      const r = await axios.get('/api/reports/monthly-analytics', { params: { financial_year: fy } });
      setMonthly(r.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  const loadAudit = async () => {
    try {
      const r = await axios.get('/api/reports/audit-logs');
      setLogs(r.data);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    }
  };

  useEffect(() => {
    load();
  }, [fy, asOf]);

  useEffect(() => {
    if (view === 'monthly') loadMonthly();
    if (view === 'audit') loadAudit();
  }, [view, fy]);

  const refresh = () => {
    load();
    if (view === 'monthly') loadMonthly();
    if (view === 'audit') loadAudit();
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Final accounts</h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Trial balance, trading account, profit &amp; loss and balance sheet, all tied to the same posted journal.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2 py-1">
            <CalendarDays className="h-3.5 w-3.5 text-slate-400" />
            <Select value={fy} onChange={(e) => onFy(e.target.value)} className="h-7 w-auto border-0 py-0 pl-0 pr-6 text-[12px] shadow-none focus:ring-0">
              {(financialYears.length ? financialYears : [fy]).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </Select>
          </label>
          <label className="flex items-center gap-1.5 rounded-lg border border-slate-300 bg-white px-2 py-1">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">As at</span>
            <Input
              type="date"
              value={asOf}
              onChange={(e) => onAsOf(e.target.value)}
              className="h-7 w-[130px] border-0 py-0 pl-0 text-[12px] shadow-none focus:ring-0"
            />
          </label>
          <Btn variant="secondary" onClick={refresh} disabled={loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Btn>
        </div>
      </div>

      {error && <div className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</div>}

      {tb && (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Stat
            label="Trial balance"
            value={tb.is_balanced ? 'Balanced' : 'Out'}
            sub={`${inr(tb.total_debit_balance)} on each side`}
            tone={tb.is_balanced ? 'emerald' : 'rose'}
          />
          <Stat
            label="Gross profit"
            value={inr(tp?.trading_account?.gross_profit)}
            sub={tp?.trading_account?.is_gross_profit ? 'sales less COGS' : 'gross loss'}
            tone={tp?.trading_account?.is_gross_profit ? 'emerald' : 'rose'}
          />
          <Stat
            label="Net profit"
            value={inr(tp?.profit_and_loss_account?.net_profit)}
            sub="after indirect expenses"
            tone={(tp?.profit_and_loss_account?.net_profit || 0) >= 0 ? 'emerald' : 'rose'}
          />
          <Stat
            label="Balance sheet"
            value={bs?.is_balanced ? 'Balanced' : 'Out'}
            sub={inr(bs?.total_assets)}
            tone={bs?.is_balanced ? 'emerald' : 'rose'}
          />
        </div>
      )}

      <Tabs items={VIEWS} value={view} onChange={setView} />

      {loading && !tb ? (
        <Card>
          <p className="py-10 text-center text-xs text-slate-500">Closing the books…</p>
        </Card>
      ) : view === 'tb' ? (
        tb ? <TrialBalance tb={tb} /> : <Empty title="Trial balance unavailable" />
      ) : view === 'trading' || view === 'pl' ? (
        tp ? <TradingAndPnl data={tp} /> : <Empty title="Trading and P&L unavailable" />
      ) : view === 'bs' ? (
        bs ? <BalanceSheet bs={bs} /> : <Empty title="Balance sheet unavailable" />
      ) : view === 'monthly' ? (
        monthly ? <Monthly data={monthly} /> : <Card><p className="py-10 text-center text-xs text-slate-500">Loading monthly analytics…</p></Card>
      ) : (
        <Audit logs={logs} />
      )}

      <p className="flex items-center gap-1.5 px-1 text-[11px] text-slate-400">
        <Scale className="h-3.5 w-3.5" /> Every figure is derived from journal lines. If the trial balance does not balance, the badge at the top of the workspace turns amber and names the failing check.
      </p>
    </div>
  );
}
