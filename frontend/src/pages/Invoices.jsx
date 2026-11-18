import React, { useMemo, useRef, useState } from 'react';
import axios from 'axios';
import { Search, Upload, RefreshCw, Trash2, ChevronRight, FileText } from 'lucide-react';
import { Badge, Btn, Empty, Input, Select, Table, TD, TH } from '../components/ui.jsx';
import { dt, inr, paymentTone, statusTone, typeLabel } from '../lib/format.js';

export default function Invoices({ documents, loading, onRefresh, onOpen }) {
  const [q, setQ] = useState('');
  const [type, setType] = useState('ALL');
  const [pay, setPay] = useState('ALL');
  const [status, setStatus] = useState('ALL');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);
  const fileRef = useRef(null);

  const rows = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return documents.filter((d) => {
      if (type !== 'ALL' && (d.invoice_type || 'PURCHASE') !== type) return false;
      if (pay !== 'ALL' && (d.payment_status || 'UNPAID') !== pay) return false;
      if (status !== 'ALL' && d.status !== status) return false;
      if (!needle) return true;
      return [d.invoice_number, d.vendor_name, d.buyer_name, d.filename]
        .filter(Boolean)
        .some((v) => String(v).toLowerCase().includes(needle));
    });
  }, [documents, q, type, pay, status]);

  const total = rows.reduce((a, d) => a + Number(d.grand_total || 0), 0);

  const doUpload = async (files) => {
    if (!files?.length) return;
    setBusy(true);
    setNote(null);
    try {
      if (files.length > 1) {
        const fd = new FormData();
        for (const f of files) fd.append('files', f);
        const up = await axios.post('/api/documents/upload-batch', fd);
        await axios.post('/api/documents/batch-process');
        setNote({ tone: 'emerald', text: `${up.data.count} invoices uploaded and processed. Review them before approving.` });
      } else {
        const fd = new FormData();
        fd.append('file', files[0]);
        const up = await axios.post('/api/documents/upload', fd);
        await axios.post(`/api/documents/${up.data.document_id}/process`);
        setNote({ tone: 'emerald', text: `${files[0].name} extracted. Check the fields, then approve.` });
      }
      await onRefresh();
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message || 'Upload failed.' });
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const resetAll = async () => {
    if (!window.confirm('Delete every invoice, journal entry and audit record? This cannot be undone.')) return;
    setBusy(true);
    setNote(null);
    try {
      await axios.post('/api/documents/reset-data');
      setNote({ tone: 'emerald', text: 'All test data cleared. The workspace is empty and ready for fresh uploads.' });
      await onRefresh();
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-slate-900">Invoices &amp; bills</h1>
          <p className="mt-0.5 text-xs text-slate-500">
            Upload supplier bills or raised sales invoices. Extracted data stays reviewable until you approve it.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept=".pdf,.png,.jpg,.jpeg"
            multiple
            className="hidden"
            onChange={(e) => doUpload([...e.target.files])}
          />
          <Btn variant="secondary" onClick={onRefresh} disabled={busy || loading}>
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Btn>
          <Btn variant="danger" onClick={resetAll} disabled={busy}>
            <Trash2 className="h-3.5 w-3.5" /> Clear test data
          </Btn>
          <Btn variant="primary" onClick={() => fileRef.current?.click()} disabled={busy}>
            <Upload className="h-3.5 w-3.5" /> {busy ? 'Processing…' : 'Upload invoices'}
          </Btn>
        </div>
      </div>

      {note && (
        <div
          className={`rounded-lg border px-3 py-2 text-xs font-medium ${
            note.tone === 'rose' ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700'
          }`}
        >
          {note.text}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[220px] flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <Input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search invoice number or party…"
            className="pl-8"
          />
        </div>
        <Select value={type} onChange={(e) => setType(e.target.value)} className="w-auto">
          <option value="ALL">Purchases &amp; sales</option>
          <option value="PURCHASE">Purchases only</option>
          <option value="SALES">Sales only</option>
        </Select>
        <Select value={pay} onChange={(e) => setPay(e.target.value)} className="w-auto">
          <option value="ALL">Any payment status</option>
          <option value="UNPAID">Unpaid</option>
          <option value="PARTIALLY_PAID">Partially paid</option>
          <option value="PAID">Paid</option>
        </Select>
        <Select value={status} onChange={(e) => setStatus(e.target.value)} className="w-auto">
          <option value="ALL">Any pipeline status</option>
          <option value="REVIEW_REQUIRED">Needs review</option>
          <option value="PROCESSED">Processed, unposted</option>
          <option value="POSTED">Posted to ledger</option>
        </Select>
      </div>

      {rows.length === 0 ? (
        <Empty
          title={documents.length ? 'No invoice matches these filters' : 'No invoices yet'}
          sub={
            documents.length
              ? 'Clear the search or widen the filters.'
              : 'Upload one or several PDFs. Digital files are read from their text layer; scans go through OCR and arrive flagged for review.'
          }
          action={
            !documents.length && (
              <Btn variant="primary" className="mt-2" onClick={() => fileRef.current?.click()}>
                <Upload className="h-3.5 w-3.5" /> Upload invoices
              </Btn>
            )
          }
        />
      ) : (
        <>
          <Table>
            <thead>
              <tr>
                <TH>Date</TH>
                <TH>Invoice #</TH>
                <TH>Party</TH>
                <TH>Book</TH>
                <TH>Payment</TH>
                <TH right>Grand total</TH>
                <TH>Status</TH>
                <TH right> </TH>
              </tr>
            </thead>
            <tbody>
              {rows.map((d) => (
                <tr key={d.id} className="transition-colors hover:bg-slate-50">
                  <TD mono>{dt(d.invoice_date || d.uploaded_at)}</TD>
                  <TD>
                    <button
                      onClick={() => onOpen(d.id)}
                      className="cursor-pointer font-medium text-slate-900 underline-offset-2 hover:text-indigo-700 hover:underline"
                    >
                      {d.invoice_number || d.filename}
                    </button>
                  </TD>
                  <TD>
                    <div className="max-w-[240px] truncate">
                      {(d.invoice_type === 'SALES' ? d.buyer_name : d.vendor_name) || d.buyer_name || d.vendor_name || '—'}
                    </div>
                    <div className="text-[11px] text-slate-400">{d.filename}</div>
                  </TD>
                  <TD>{typeLabel(d.invoice_type)}</TD>
                  <TD>
                    <Badge tone={paymentTone(d.payment_status)}>{(d.payment_status || 'UNPAID').replace('_', ' ').toLowerCase()}</Badge>
                  </TD>
                  <TD right mono>{inr(d.grand_total)}</TD>
                  <TD>
                    <Badge tone={statusTone(d.status)}>{(d.status || '').replace('_', ' ').toLowerCase()}</Badge>
                  </TD>
                  <TD right>
                    <Btn size="sm" variant="ghost" onClick={() => onOpen(d.id)}>
                      Open <ChevronRight className="h-3.5 w-3.5" />
                    </Btn>
                  </TD>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr>
                <TD className="bg-slate-50 font-semibold text-slate-900" colSpan={5}>
                  {rows.length} of {documents.length} invoices
                </TD>
                <TD right mono className="bg-slate-50 font-semibold text-slate-900">{inr(total)}</TD>
                <TD className="bg-slate-50" colSpan={2} />
              </tr>
            </tfoot>
          </Table>
          <p className="flex items-center gap-1.5 text-[11px] text-slate-400">
            <FileText className="h-3.5 w-3.5" /> Every figure above comes from the posted journal, not from the PDF text.
          </p>
        </>
      )}
    </div>
  );
}
