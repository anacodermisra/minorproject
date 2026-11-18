import React, { useState } from 'react';
import axios from 'axios';
import { Check, Building2, Save } from 'lucide-react';
import { Badge, Btn, Card, Field, Input, SectionHead, Select, Stat } from '../components/ui.jsx';
import { BUSINESS_TYPES } from '../lib/format.js';

export default function CompanyProfile({ tenant, onSaved }) {
  const [form, setForm] = useState({
    name: tenant?.name || '',
    gstin: tenant?.gstin || '',
    business_type: tenant?.business_type || 'IT_SERVICES',
    currency: tenant?.currency || 'INR',
  });
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState(null);

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const save = async (e) => {
    e?.preventDefault();
    setBusy(true);
    setNote(null);
    try {
      const res = await axios.put('/api/tenant/profile', form);
      onSaved?.(res.data.tenant);
      setNote({ tone: 'emerald', text: 'Company profile saved. New invoices will be classified under this business type.' });
    } catch (err) {
      setNote({ tone: 'rose', text: err.response?.data?.detail || err.message });
    } finally {
      setBusy(false);
    }
  };

  const current = BUSINESS_TYPES.find((b) => b.value === form.business_type);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold tracking-tight text-slate-900">Company profile</h1>
        <p className="mt-0.5 text-xs text-slate-500">
          The business type set here decides how purchases and expenses are classified for every invoice.
        </p>
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

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="Legal name" value={tenant?.name || '—'} sub={tenant?.gstin || 'GSTIN not set'} />
        <Stat label="Business type" value={current?.title || form.business_type} sub="drives classification" />
        <Stat label="Currency" value={form.currency} sub="presentation currency" />
        <Stat label="Workspace ID" value={String(tenant?.id || '').slice(0, 8)} sub="single-company ledger" />
      </div>

      <form onSubmit={save} className="grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]">
        <Card>
          <SectionHead title="Registered details" sub="Printed on statements and used to validate GSTINs." right={<Badge tone="slate"><Building2 className="h-3 w-3" /> Company</Badge>} />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Legal name" className="sm:col-span-2">
              <Input value={form.name} onChange={set('name')} placeholder="Registered company name" />
            </Field>
            <Field label="GSTIN">
              <Input value={form.gstin} onChange={set('gstin')} className="font-mono uppercase" />
            </Field>
            <Field label="Currency">
              <Select value={form.currency} onChange={set('currency')}>
                <option value="INR">INR — Indian Rupee</option>
                <option value="USD">USD — US Dollar</option>
                <option value="EUR">EUR — Euro</option>
              </Select>
            </Field>
          </div>
          <div className="mt-4 flex justify-end">
            <Btn type="submit" variant="primary" disabled={busy}>
              <Save className="h-3.5 w-3.5" /> {busy ? 'Saving…' : 'Save profile'}
            </Btn>
          </div>
        </Card>

        <Card>
          <SectionHead title="Business type" sub="Pick one. It is a company-level policy, not a per-invoice toggle." />
          <div className="space-y-2">
            {BUSINESS_TYPES.map((b) => {
              const active = form.business_type === b.value;
              return (
                <button
                  type="button"
                  key={b.value}
                  onClick={() => setForm((f) => ({ ...f, business_type: b.value }))}
                  className={`w-full cursor-pointer rounded-lg border px-3 py-2.5 text-left transition-colors ${
                    active ? 'border-indigo-300 bg-indigo-50/60 ring-1 ring-indigo-200' : 'border-slate-200 bg-white hover:border-slate-300'
                  }`}
                >
                  <span className="flex items-center justify-between">
                    <span className="text-[13px] font-semibold text-slate-900">{b.title}</span>
                    <span
                      className={`flex h-4 w-4 items-center justify-center rounded-full border ${
                        active ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-slate-300 bg-white'
                      }`}
                    >
                      {active && <Check className="h-3 w-3" />}
                    </span>
                  </span>
                  <span className="mt-0.5 block text-[11px] leading-relaxed text-slate-500">{b.hint}</span>
                </button>
              );
            })}
          </div>
          <div className="mt-4 flex justify-end">
            <Btn type="submit" variant="primary" disabled={busy}>
              <Save className="h-3.5 w-3.5" /> {busy ? 'Saving…' : 'Save business type'}
            </Btn>
          </div>
        </Card>
      </form>
    </div>
  );
}
