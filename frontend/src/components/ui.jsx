import React from 'react';

const toneMap = {
  slate: 'bg-slate-100 text-slate-600 border-slate-200',
  emerald: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  amber: 'bg-amber-50 text-amber-700 border-amber-200',
  rose: 'bg-rose-50 text-rose-700 border-rose-200',
  indigo: 'bg-indigo-50 text-indigo-700 border-indigo-200',
  sky: 'bg-sky-50 text-sky-700 border-sky-200',
};

export function Badge({ children, tone = 'slate', dot = false, className = '' }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold leading-5 ${toneMap[tone] || toneMap.slate} ${className}`}
    >
      {dot && <span className="h-1.5 w-1.5 rounded-full bg-current opacity-70" />}
      {children}
    </span>
  );
}

export function Card({ children, className = '', padded = true }) {
  return (
    <div className={`rounded-xl border border-slate-200 bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] ${padded ? 'p-5' : ''} ${className}`}>
      {children}
    </div>
  );
}

export function SectionHead({ title, sub, right }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h2 className="text-[15px] font-semibold tracking-tight text-slate-900">{title}</h2>
        {sub && <p className="mt-0.5 text-xs text-slate-500">{sub}</p>}
      </div>
      {right && <div className="flex flex-wrap items-center gap-2">{right}</div>}
    </div>
  );
}

const btn = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700 border-transparent',
  success: 'bg-emerald-600 text-white hover:bg-emerald-700 border-transparent',
  secondary: 'bg-white text-slate-700 hover:bg-slate-50 border-slate-300',
  ghost: 'bg-transparent text-slate-600 hover:bg-slate-100 border-transparent',
  danger: 'bg-white text-rose-600 hover:bg-rose-50 border-rose-200',
};

export function Btn({ variant = 'secondary', size = 'md', className = '', children, ...props }) {
  const sz = size === 'sm' ? 'h-8 px-2.5 text-xs' : 'h-9 px-3.5 text-[13px]';
  return (
    <button
      {...props}
      className={`inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-lg border font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${btn[variant]} ${sz} ${className}`}
    >
      {children}
    </button>
  );
}

export function Field({ label, hint, children, className = '' }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1 flex items-baseline justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</span>
        {hint && <span className="text-[10px] text-slate-400">{hint}</span>}
      </span>
      {children}
    </label>
  );
}

const inputCls =
  'w-full rounded-lg border border-slate-300 bg-white px-2.5 py-1.5 text-[13px] text-slate-900 outline-none transition-colors placeholder:text-slate-400 focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100';

export function Input({ className = '', ...props }) {
  return <input {...props} className={`${inputCls} ${className}`} />;
}

export function Select({ className = '', children, ...props }) {
  return (
    <select {...props} className={`${inputCls} cursor-pointer ${className}`}>
      {children}
    </select>
  );
}

export function Stat({ label, value, sub, tone = 'slate' }) {
  const accent = {
    slate: 'text-slate-900',
    emerald: 'text-emerald-700',
    amber: 'text-amber-700',
    rose: 'text-rose-700',
    indigo: 'text-indigo-700',
  }[tone];
  return (
    <div className="rounded-xl border border-slate-200 bg-white px-4 py-3">
      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">{label}</p>
      <p className={`mt-1 font-mono text-lg font-semibold tabular-nums ${accent}`}>{value}</p>
      {sub && <p className="mt-0.5 text-[11px] text-slate-400">{sub}</p>}
    </div>
  );
}

export function Empty({ title, sub, action }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-slate-300 bg-slate-50/60 px-6 py-14 text-center">
      <p className="text-sm font-semibold text-slate-700">{title}</p>
      {sub && <p className="max-w-sm text-xs text-slate-500">{sub}</p>}
      {action}
    </div>
  );
}

export function Table({ children, className = '' }) {
  return (
    <div className={`overflow-x-auto rounded-xl border border-slate-200 bg-white ${className}`}>
      <table className="w-full border-collapse text-left text-[13px]">{children}</table>
    </div>
  );
}

export function TH({ children, right = false, className = '' }) {
  return (
    <th
      className={`whitespace-nowrap border-b border-slate-200 bg-slate-50 px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 ${right ? 'text-right' : ''} ${className}`}
    >
      {children}
    </th>
  );
}

export function TD({ children, right = false, mono = false, className = '' }) {
  return (
    <td
      className={`border-b border-slate-100 px-3 py-2.5 align-middle text-slate-700 ${right ? 'text-right' : ''} ${mono ? 'font-mono tabular-nums' : ''} ${className}`}
    >
      {children}
    </td>
  );
}

export function Tabs({ items, value, onChange }) {
  return (
    <div className="flex flex-wrap items-center gap-1 rounded-lg border border-slate-200 bg-slate-50 p-1">
      {items.map((it) => (
        <button
          key={it.value}
          onClick={() => onChange(it.value)}
          className={`cursor-pointer rounded-md px-3 py-1.5 text-xs font-semibold transition-colors ${
            value === it.value ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-200' : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          {it.label}
        </button>
      ))}
    </div>
  );
}

export function Row({ label, value, strong = false, tone = '' }) {
  return (
    <div className={`flex items-baseline justify-between gap-4 px-3 py-1.5 ${strong ? 'font-semibold text-slate-900' : 'text-slate-600'}`}>
      <span className="text-[13px]">{label}</span>
      <span className={`font-mono text-[13px] tabular-nums ${tone}`}>{value}</span>
    </div>
  );
}
