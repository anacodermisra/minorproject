import React, { useState } from 'react';
import axios from 'axios';
import { Landmark, Check, ShieldCheck } from 'lucide-react';
import { Btn, Field, Input, Select } from '../components/ui.jsx';
import { BUSINESS_TYPES } from '../lib/format.js';

export default function Onboarding({ tenant, onDone }) {
  const [form, setForm] = useState({
    name: tenant?.name || '',
    gstin: tenant?.gstin || '',
    business_type: tenant?.business_type || 'IT_SERVICES',
    currency: tenant?.currency || 'INR',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) {
      setError('Enter the legal name of the business.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const res = await axios.put('/api/tenant/profile', form);
      onDone(res.data.tenant);
    } catch (err) {
      setError(err.response?.data?.detail || err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <div className="hidden w-[42%] flex-col justify-between border-r border-slate-200 bg-white p-10 lg:flex">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-slate-900 text-white">
            <Landmark className="h-4.5 w-4.5" />
          </div>
          <span className="text-sm font-bold tracking-tight text-slate-900">Invoice to Books</span>
        </div>

        <div className="max-w-sm">
          <h1 className="text-2xl font-bold leading-tight tracking-tight text-slate-900">
            Set up the books for this company once. Every invoice after that is classified automatically.
          </h1>
          <p className="mt-3 text-sm leading-relaxed text-slate-500">
            The business type decides the accounting treatment. A stationery retailer capitalises purchases as trading stock;
            a consultancy expenses them. Choosing it here keeps the ledger consistent, instead of toggling a rule per invoice.
          </p>
          <ul className="mt-8 space-y-3 text-sm text-slate-600">
            {[
              'Double-entry posting generated per invoice',
              'GST split into CGST, SGST and IGST',
              'Purchase and sales registers kept separately',
              'Trial balance, trading account and balance sheet from the same postings',
            ].map((t) => (
              <li key={t} className="flex items-start gap-2">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>{t}</span>
              </li>
            ))}
          </ul>
        </div>

        <p className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <ShieldCheck className="h-3.5 w-3.5" /> All checks run in the background. You only see what needs attention.
        </p>
      </div>

      <div className="flex flex-1 items-center justify-center px-5 py-10">
        <form onSubmit={submit} className="w-full max-w-md">
          <div className="mb-6 lg:hidden">
            <h1 className="text-lg font-bold text-slate-900">Invoice to Books</h1>
            <p className="text-xs text-slate-500">Company setup</p>
          </div>

          <h2 className="text-lg font-semibold tracking-tight text-slate-900">Company profile</h2>
          <p className="mb-6 mt-1 text-xs text-slate-500">This is stored against every entry you post later.</p>

          <div className="space-y-4">
            <Field label="Legal name">
              <Input value={form.name} onChange={set('name')} placeholder="Modern Tech Solutions Pvt Ltd" autoFocus />
            </Field>

            <div className="grid grid-cols-2 gap-3">
              <Field label="GSTIN">
                <Input value={form.gstin} onChange={set('gstin')} placeholder="07BBBBB1111B1Z2" className="font-mono" />
              </Field>
              <Field label="Currency">
                <Select value={form.currency} onChange={set('currency')}>
                  <option value="INR">INR — Indian Rupee</option>
                  <option value="USD">USD — US Dollar</option>
                  <option value="EUR">EUR — Euro</option>
                </Select>
              </Field>
            </div>

            <div>
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Business type</p>
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
            </div>
          </div>

          {error && <p className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs font-medium text-rose-700">{error}</p>}

          <Btn type="submit" variant="primary" disabled={saving} className="mt-6 w-full">
            {saving ? 'Saving…' : 'Enter workspace'}
          </Btn>
          <p className="mt-3 text-center text-[11px] text-slate-400">
            You can change these details later from Company profile.
          </p>
        </form>
      </div>
    </div>
  );
}
