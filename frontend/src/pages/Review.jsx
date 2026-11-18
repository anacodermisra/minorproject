import React, { useEffect, useMemo, useState } from 'react';
import axios from 'axios';
import {
  ArrowLeft,
  Check,
  AlertTriangle,
  XCircle,
  Save,
  CheckCircle2,
  Trash2,
  Plus,
  ShieldCheck,
  Receipt,
} from 'lucide-react';
import { Badge, Btn, Card, Empty, Field, Input, SectionHead, Select, TD, TH } from '../components/ui.jsx';
import { dt, inr, num, statusTone } from '../lib/format.js';

const blankLine = () => ({
  description: '',
  hsn_sac: '',
  quantity: 1,
  unit_price: 0,
  discount_amount: 0,
  total_amount: 0,
});

const checkIcon = (s) =>
  s === 'PASS' ? Check : s === 'WARNING' ? AlertTriangle : XCircle;

export default function Review({ docId, onBack, onChanged }) {
  const [doc, setDoc] = useState(null);
  const [form, setForm] = useState(null);
  const [items, setItems] = useState([]);
  const [proposal, setProposal] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState('');
  const [note, setNote] = useState(null);
  const [dirty, setDirty] = useState(false);

  const load = async () => {
    setLoading(true);
    setNote(null);
    try {
      const res = await axios.get(`/api/documents/${docId}`);
      const d = res.data;
      setDoc(d);
      setProposal(d.proposal);
      setReport(d.validation_report);
      setForm({
        invoice_number: d.invoice?.invoice_number || '',
        invoice_date: d.invoice?.invoice_date || '',
        due_date: d.invoice?.due_date || '',
        vendor_name: d.invoice?.vendor_name || '',
        vendor_gstin: d.invoice?.vendor_gstin || '',
        buyer_name: d.invoice?.buyer_name || '',
        buyer_gstin: d.invoice?.buyer_gstin || '',
        invoice_type: d.invoice?.invoice_type || 'PURCHASE',
        total_tax: d.invoice?.total_tax ?? 0,
        grand_total: d.invoice?.grand_total ?? 0,
      });
      setItems(
        (d.invoice?.line_items || []).map((li) => ({
          description: li.description || '',
          hsn_sac: li.hsn_sac || '',
          quantity: li.quantity ?? 1,
          unit_price: li.unit_price ?? 0,
          discount_amount: li.discount_amount ?? 0,
          total_amount: li.total_amount ?? 0,
        }))
      );
      setDirty(false);
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (docId) load();
  }, [docId]);

  const set = (k) => (e) => {
    setForm((f) => ({ ...f, [k]: e.target.value }));
    setDirty(true);
  };

  const setItem = (idx, k, value) => {
    setItems((list) => {
      const next = [...list];
      const row = { ...next[idx], [k]: value };
      if (['quantity', 'unit_price', 'discount_amount'].includes(k)) {
        const q = Number(k === 'quantity' ? value : row.quantity) || 0;
        const up = Number(k === 'unit_price' ? value : row.unit_price) || 0;
        const dc = Number(k === 'discount_amount' ? value : row.discount_amount) || 0;
        row.total_amount = Math.max(0, q * up - dc);
      }
      next[idx] = row;
      return next;
    });
    setDirty(true);
  };

  const subtotal = useMemo(
    () => items.reduce((a, it) => a + (Number(it.total_amount) || 0), 0),
    [items]
  );
  const tax = Number(form?.total_tax || 0);
  const computedGrand = subtotal + tax;

  const blocking = report?.has_blocking_failures;
  const failing = (report?.checks || []).filter((c) => c.status === 'FAIL');
  const warnings = (report?.checks || []).filter((c) => c.status === 'WARNING');
  const passed = (report?.checks || []).filter((c) => c.status === 'PASS');
  const posted = doc?.status === 'POSTED';

  const save = async ({ silent = false } = {}) => {
    setBusy('save');
    setNote(null);
    try {
      const payload = {
        ...form,
        total_tax: Number(form.total_tax) || 0,
        grand_total: computedGrand,
        line_items: items.map((it) => ({
          description: it.description || 'Item',
          hsn_sac: it.hsn_sac || null,
          quantity: Number(it.quantity) || 0,
          unit_price: Number(it.unit_price) || 0,
          discount_amount: Number(it.discount_amount) || 0,
          total_amount: Number(it.total_amount) || 0,
        })),
      };
      const res = await axios.put(`/api/documents/${docId}/invoice`, payload);
      setProposal(res.data.proposal);
      setReport(res.data.validation_report);
      setDirty(false);
      await onChanged?.();
      if (!silent) setNote({ tone: 'emerald', text: 'Saved. The entry and the checks were regenerated from the corrected values.' });
      return res.data;
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
      return null;
    } finally {
      setBusy('');
    }
  };

  const approve = async () => {
    setBusy('post');
    setNote(null);
    try {
      const saved = await save({ silent: true });
      if (!saved) return;
      if (saved.validation_report?.has_blocking_failures) {
        setNote({ tone: 'rose', text: 'This invoice still fails a blocking check. Fix the highlighted fields before posting.' });
        return;
      }
      await axios.post('/api/journal/post', saved.proposal);
      await onChanged?.();
      setNote({ tone: 'emerald', text: `Posted to the ledger as ${saved.proposal.invoice_number}.` });
      await load();
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
    } finally {
      setBusy('');
    }
  };

  const remove = async () => {
    if (!window.confirm('Delete this invoice and any journal entry posted from it?')) return;
    setBusy('delete');
    try {
      await axios.delete(`/api/documents/${docId}`);
      await onChanged?.();
      onBack?.();
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
      setBusy('');
    }
  };

  if (loading) {
    return (
      <Card>
        <p className="py-10 text-center text-xs text-slate-500">Reading the extracted document…</p>
      </Card>
    );
  }

  if (!form) {
    return (
      <Empty
        title="This document could not be opened"
        sub={note?.text || 'It may have been deleted.'}
        action={
          <Btn className="mt-2" onClick={onBack}>
            Back to invoices
          </Btn>
        }
      />
    );
  }

  const summaryTone = blocking ? 'rose' : warnings.length ? 'amber' : 'emerald';

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <button
            onClick={onBack}
            className="mb-1 inline-flex cursor-pointer items-center gap-1 text-[11px] font-semibold text-slate-500 hover:text-slate-800"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Invoices
          </button>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">
            {form.invoice_number || doc?.filename || 'Untitled invoice'}
          </h1>
          <p className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-slate-500">
            <span>{doc?.filename}</span>
            <Badge tone={statusTone(doc?.status)}>{(doc?.status || '').replace('_', ' ').toLowerCase()}</Badge>
            <Badge tone={form.invoice_type === 'SALES' ? 'indigo' : 'sky'}>
              {form.invoice_type === 'SALES' ? 'Sales invoice' : 'Purchase bill'}
            </Badge>
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {posted && <Badge tone="emerald" dot>Already posted to ledger</Badge>}
          <Btn variant="danger" onClick={remove} disabled={!!busy}>
            <Trash2 className="h-3.5 w-3.5" /> Delete
          </Btn>
          <Btn variant="secondary" onClick={() => save()} disabled={!!busy || !dirty}>
            <Save className="h-3.5 w-3.5" /> {busy === 'save' ? 'Saving…' : dirty ? 'Save changes' : 'Saved'}
          </Btn>
          <Btn variant="success" onClick={approve} disabled={!!busy || posted}>
            <CheckCircle2 className="h-3.5 w-3.5" />
            {busy === 'post' ? 'Posting…' : posted ? 'Posted' : 'Approve & post'}
          </Btn>
        </div>
      </div>

      {note && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs font-medium ${
            note.tone === 'rose'
              ? 'border-rose-200 bg-rose-50 text-rose-700'
              : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}
        >
          {note.text}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <div className="space-y-4">
          <Card>
            <SectionHead
              title="Extracted details"
              sub="Correct anything the reader got wrong. Saving re-runs the arithmetic checks and rebuilds the journal."
            />

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <Field label="Invoice number">
                <Input value={form.invoice_number} onChange={set('invoice_number')} className="font-mono" />
              </Field>
              <Field label="Book">
                <Select value={form.invoice_type} onChange={set('invoice_type')}>
                  <option value="PURCHASE">Purchase bill (inward)</option>
                  <option value="SALES">Sales invoice (outward)</option>
                </Select>
              </Field>
              <Field label="Invoice date">
                <Input type="date" value={form.invoice_date || ''} onChange={set('invoice_date')} />
              </Field>
              <Field label="Due date">
                <Input type="date" value={form.due_date || ''} onChange={set('due_date')} />
              </Field>
              <Field label="Supplier / seller">
                <Input value={form.vendor_name} onChange={set('vendor_name')} />
              </Field>
              <Field label="Supplier GSTIN">
                <Input value={form.vendor_gstin} onChange={set('vendor_gstin')} className="font-mono uppercase" />
              </Field>
              <Field label="Buyer / customer">
                <Input value={form.buyer_name} onChange={set('buyer_name')} />
              </Field>
              <Field label="Buyer GSTIN">
                <Input value={form.buyer_gstin} onChange={set('buyer_gstin')} className="font-mono uppercase" />
              </Field>
            </div>
          </Card>

          <Card padded={false}>
            <div className="flex flex-wrap items-center justify-between gap-2 px-5 pt-4">
              <SectionHead
                title="Line items"
                sub="Quantity × rate − discount. The total recalculates as you type."
              />
              <Btn
                size="sm"
                variant="secondary"
                onClick={() => {
                  setItems((l) => [...l, blankLine()]);
                  setDirty(true);
                }}
              >
                <Plus className="h-3.5 w-3.5" /> Add line
              </Btn>
            </div>

            <div className="mt-1 overflow-x-auto">
              <table className="w-full border-collapse text-left text-[13px]">
                <thead>
                  <tr>
                    <TH className="min-w-[200px]">Description</TH>
                    <TH>HSN/SAC</TH>
                    <TH right>Qty</TH>
                    <TH right>Rate</TH>
                    <TH right>Discount</TH>
                    <TH right>Amount</TH>
                    <TH />
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={i} className="align-top">
                      <TD>
                        <Input
                          value={it.description}
                          onChange={(e) => setItem(i, 'description', e.target.value)}
                          placeholder="Item or service"
                        />
                      </TD>
                      <TD>
                        <Input
                          value={it.hsn_sac}
                          onChange={(e) => setItem(i, 'hsn_sac', e.target.value)}
                          className="w-24 font-mono"
                        />
                      </TD>
                      <TD right>
                        <Input
                          type="number"
                          step="any"
                          value={it.quantity}
                          onChange={(e) => setItem(i, 'quantity', e.target.value)}
                          className="w-20 text-right font-mono"
                        />
                      </TD>
                      <TD right>
                        <Input
                          type="number"
                          step="any"
                          value={it.unit_price}
                          onChange={(e) => setItem(i, 'unit_price', e.target.value)}
                          className="w-28 text-right font-mono"
                        />
                      </TD>
                      <TD right>
                        <Input
                          type="number"
                          step="any"
                          value={it.discount_amount}
                          onChange={(e) => setItem(i, 'discount_amount', e.target.value)}
                          className="w-24 text-right font-mono"
                        />
                      </TD>
                      <TD right mono className="pt-4 font-semibold text-slate-900">
                        {num(it.total_amount)}
                      </TD>
                      <TD right>
                        <Btn
                          size="sm"
                          variant="ghost"
                          onClick={() => {
                            setItems((l) => l.filter((_, x) => x !== i));
                            setDirty(true);
                          }}
                          title="Remove line"
                        >
                          <XCircle className="h-3.5 w-3.5 text-slate-400" />
                        </Btn>
                      </TD>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="grid grid-cols-1 gap-3 border-t border-slate-200 bg-slate-50/60 px-5 py-4 sm:grid-cols-4">
              <div className="sm:col-span-2" />
              <div className="space-y-1.5 text-[13px]">
                <div className="flex items-center justify-between gap-6 text-slate-600">
                  <span>Subtotal</span>
                  <span className="font-mono tabular-nums text-slate-900">{inr(subtotal)}</span>
                </div>
                <div className="flex items-center justify-between gap-6 text-slate-600">
                  <span>GST / tax</span>
                  <span className="font-mono tabular-nums text-slate-900">{inr(tax)}</span>
                </div>
                <div className="flex items-center justify-between gap-6 border-t border-slate-200 pt-1.5 font-semibold text-slate-900">
                  <span>Grand total</span>
                  <span className="font-mono tabular-nums">{inr(computedGrand)}</span>
                </div>
              </div>
              <Field label="Total tax (override)">
                <Input
                  type="number"
                  step="any"
                  value={form.total_tax}
                  onChange={set('total_tax')}
                  className="text-right font-mono"
                />
                <span className="mt-1 block text-[10px] text-slate-400">
                  Grand total is recomputed as subtotal + tax.
                </span>
              </Field>
            </div>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <SectionHead
              title="Checks"
              sub={report?.summary_message || 'Arithmetic, GST and double-entry checks.'}
              right={
                <Badge tone={summaryTone} dot>
                  {blocking ? `${failing.length} blocking` : warnings.length ? `${warnings.length} warning` : 'All passed'}
                </Badge>
              }
            />
            <div className="flex gap-2 pb-3">
              <Badge tone="emerald">{passed.length} passed</Badge>
              <Badge tone="amber">{warnings.length} warnings</Badge>
              <Badge tone="rose">{failing.length} failed</Badge>
            </div>
            <div className="max-h-[320px] space-y-1.5 overflow-y-auto pr-1">
              {(report?.checks || []).map((c, i) => {
                const Icon = checkIcon(c.status);
                return (
                  <div key={i} className="rounded-lg border border-slate-200 bg-white px-2.5 py-2">
                    <div className="flex items-start gap-2">
                      <Icon
                        className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${
                          c.status === 'PASS' ? 'text-emerald-600' : c.status === 'WARNING' ? 'text-amber-600' : 'text-rose-600'
                        }`}
                      />
                      <div className="min-w-0">
                        <p className="text-[12px] font-semibold text-slate-800">{c.check_name}</p>
                        <p className="text-[11px] leading-snug text-slate-500">{c.explanation}</p>
                        {c.status !== 'PASS' && c.difference && (
                          <p className="mt-0.5 font-mono text-[10px] text-slate-400">
                            expected {c.expected_value} · actual {c.actual_value} · diff {c.difference}
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
              {!report?.checks?.length && (
                <p className="py-6 text-center text-xs text-slate-400">No checks returned for this document.</p>
              )}
            </div>
          </Card>

          <Card padded={false}>
            <div className="px-5 pt-4">
              <SectionHead
                title="Ledger entry to be posted"
                sub="Every debit has a matching credit. This is what the reports will read."
                right={
                  <Badge tone={proposal?.is_balanced ? 'emerald' : 'rose'}>
                    {proposal?.is_balanced ? 'Balanced' : 'Out of balance'}
                  </Badge>
                }
              />
            </div>
            <div className="overflow-x-auto">
              <table className="w-full border-collapse text-left text-[13px]">
                <thead>
                  <tr>
                    <TH>Account</TH>
                    <TH right>Debit</TH>
                    <TH right>Credit</TH>
                  </tr>
                </thead>
                <tbody>
                  {(proposal?.lines || []).map((l, i) => (
                    <tr key={i}>
                      <TD>
                        <div className="flex items-center gap-2">
                          <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-[10px] text-slate-500">
                            {l.account_code}
                          </span>
                          <span className="text-[12px] text-slate-700">{l.account_name}</span>
                        </div>
                      </TD>
                      <TD right mono>
                        {l.entry_type === 'DEBIT' ? num(l.amount) : '—'}
                      </TD>
                      <TD right mono>
                        {l.entry_type === 'CREDIT' ? num(l.amount) : '—'}
                      </TD>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr>
                    <TD className="bg-slate-50 font-semibold text-slate-900">Totals</TD>
                    <TD right mono className="bg-slate-50 font-semibold text-slate-900">
                      {num(proposal?.total_debits)}
                    </TD>
                    <TD right mono className="bg-slate-50 font-semibold text-slate-900">
                      {num(proposal?.total_credits)}
                    </TD>
                  </tr>
                </tfoot>
              </table>
            </div>
            <div className="space-y-1.5 border-t border-slate-200 px-5 py-3">
              {proposal?.reasoning && (
                <p className="flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-500">
                  <Receipt className="mt-0.5 h-3 w-3 shrink-0" /> {proposal.reasoning}
                </p>
              )}
              {(proposal?.applied_rules || []).slice(0, 3).map((r, i) => (
                <p key={i} className="flex items-start gap-1.5 text-[11px] leading-relaxed text-slate-400">
                  <ShieldCheck className="mt-0.5 h-3 w-3 shrink-0" /> {r}
                </p>
              ))}
            </div>
          </Card>

          <p className="px-1 text-[11px] leading-relaxed text-slate-400">
            Posted on {proposal?.entry_date ? dt(proposal.entry_date) : '—'} · {proposal?.financial_year || '—'} ·{' '}
            {(proposal?.transaction_type || '').replaceAll('_', ' ').toLowerCase()}
          </p>
        </div>
      </div>
    </div>
  );
}
