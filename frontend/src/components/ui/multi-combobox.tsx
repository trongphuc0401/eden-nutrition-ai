"use client";

import { useId, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Icon } from "./icon";

export type ComboOption = { value: string; label: string; hint?: string };

const fold = (text: string) => text.normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/gi, "d").toLowerCase().trim();

type Props = {
  label: string; help?: string; placeholder: string; options: ComboOption[]; values: string[]; onChange: (values: string[]) => void;
  status?: "loading" | "ready" | "error"; onRetry?: () => void; emptyText?: string;
};

/** Searchable multi-select (ARIA combobox + listbox). Options come from the API; typing filters them, accent-insensitive. */
export function MultiCombobox({ label, help, placeholder, options, values, onChange, status = "ready", onRetry, emptyText = "Không có kết quả phù hợp." }: Props) {
  const id = useId();
  const listId = `${id}-list`, helpId = `${id}-help`;
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const results = useMemo(() => {
    const term = fold(query);
    const available = options.filter((option) => !values.includes(option.value) && (!term || fold(option.label).includes(term)));
    if (!term) return available.slice(0, 50);
    // A word that starts with the query ranks first: "oi" puts "Ổi" before "Bưởi".
    const startsWord = (option: ComboOption) => fold(option.label).split(/[\s-]+/).some((word) => word.startsWith(term));
    return [...available.filter(startsWord), ...available.filter((option) => !startsWord(option))].slice(0, 50);
  }, [options, values, query]);
  const labelOf = (value: string) => options.find((option) => option.value === value)?.label ?? value;

  const choose = (option: ComboOption) => { onChange([...values, option.value]); setQuery(""); setActive(0); inputRef.current?.focus(); };
  const remove = (value: string) => { onChange(values.filter((item) => item !== value)); inputRef.current?.focus(); };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") { event.preventDefault(); setOpen(true); setActive((index) => Math.min(index + 1, results.length - 1)); }
    else if (event.key === "ArrowUp") { event.preventDefault(); setActive((index) => Math.max(index - 1, 0)); }
    else if (event.key === "Enter" && open && results[active]) { event.preventDefault(); choose(results[active]); }
    else if (event.key === "Escape" && open) { event.preventDefault(); event.stopPropagation(); setOpen(false); }
    else if (event.key === "Backspace" && !query && values.length) remove(values[values.length - 1]);
  };

  return (
    <div className="relative" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false); }}>
      <label htmlFor={id} className="block text-sm font-semibold text-strong">{label}</label>
      {help && <p id={helpId} className="mt-1 text-xs text-muted">{help}</p>}
      <div className="field mt-2 flex min-h-12 flex-wrap items-center gap-1.5 py-2 focus-within:border-brand" onClick={() => inputRef.current?.focus()}>
        {values.map((value) => (
          <span key={value} className="inline-flex items-center gap-1 rounded-lg bg-orange-soft py-1 pl-2.5 pr-1 text-sm text-action">
            {labelOf(value)}
            <button type="button" onClick={(event) => { event.stopPropagation(); remove(value); }} aria-label={`Bỏ ${labelOf(value)}`} className="grid size-5 place-items-center rounded hover:bg-white/70">
              <Icon name="close" className="size-3.5" />
            </button>
          </span>
        ))}
        <span className="flex min-w-36 flex-1 items-center gap-2">
          <Icon name="search" className="size-4 text-subtle" />
          <input ref={inputRef} id={id} role="combobox" aria-expanded={open} aria-controls={listId} aria-autocomplete="list" aria-describedby={help ? helpId : undefined}
            aria-activedescendant={open && results[active] ? `${id}-opt-${active}` : undefined}
            className="min-w-0 flex-1 bg-transparent py-1 outline-none placeholder:text-subtle" placeholder={values.length ? "Thêm…" : placeholder} value={query}
            onChange={(event) => { setQuery(event.target.value); setOpen(true); setActive(0); }} onFocus={() => setOpen(true)} onKeyDown={onKeyDown} />
        </span>
      </div>
      {open && (
        <div className="absolute inset-x-0 z-30 mt-1 overflow-hidden rounded-control border border-line bg-card shadow-card">
          {status === "loading" && <p className="px-3 py-3 text-sm text-muted" role="status">Đang tải danh sách…</p>}
          {status === "error" && (
            <p className="flex items-center justify-between gap-2 px-3 py-3 text-sm text-coral-strong" role="alert">
              Không tải được danh sách.
              {onRetry && <button type="button" onMouseDown={(event) => event.preventDefault()} onClick={onRetry} className="font-semibold underline">Thử lại</button>}
            </p>
          )}
          {status === "ready" && (
            <ul id={listId} role="listbox" aria-label={label} aria-multiselectable="true" className="max-h-60 overflow-y-auto py-1">
              {results.map((option, index) => (
                <li key={option.value} id={`${id}-opt-${index}`} role="option" aria-selected={false}
                  onMouseDown={(event) => event.preventDefault()} onClick={() => choose(option)} onMouseEnter={() => setActive(index)}
                  className={`flex cursor-pointer items-center justify-between gap-3 px-3 py-2 text-sm ${index === active ? "bg-orange-soft text-ink" : "text-ink"}`}>
                  <span>{option.label}</span>
                  {option.hint && <span className="truncate text-xs text-muted">{option.hint}</span>}
                </li>
              ))}
              {results.length === 0 && <li className="px-3 py-3 text-sm text-muted">{query ? `Không tìm thấy “${query}”.` : emptyText}</li>}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
