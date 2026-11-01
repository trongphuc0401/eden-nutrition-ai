"use client";

import { useId, type ReactNode } from "react";

/** Label + control pair with a real htmlFor/id link; children receive the generated id. */
export function Field({ label, help, children }: { label: string; help?: string; children: (id: string, helpId?: string) => ReactNode }) {
  const id = useId();
  const helpId = help ? `${id}-help` : undefined;
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold text-strong">{label}</label>
      {children(id, helpId)}
      {help && <p id={helpId} className="mt-2 text-xs leading-5 text-muted">{help}</p>}
    </div>
  );
}

export function NumberField({ label, value, onChange, min, max, help }: { label: string; value: number; onChange: (value: number) => void; min?: number; max?: number; help?: string }) {
  return <Field label={label} help={help}>{(id, helpId) => <input id={id} aria-describedby={helpId} className="field" type="number" inputMode="numeric" min={min} max={max} value={value || ""} onChange={(event) => onChange(Number(event.target.value))} />}</Field>;
}

export function SelectField({ label, value, options, onChange, help, placeholder = "Chọn…" }: { label: string; value: string; options: { value: string; label: string }[]; onChange: (value: string) => void; help?: string; placeholder?: string }) {
  return <Field label={label} help={help}>{(id, helpId) => <select id={id} aria-describedby={helpId} className="field" value={value} onChange={(event) => onChange(event.target.value)}>{!value && <option value="" disabled>{placeholder}</option>}{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select>}</Field>;
}
