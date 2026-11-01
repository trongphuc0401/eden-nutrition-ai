"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { Icon } from "@/components/ui/icon";
import type { ChatModel } from "@/lib/chat-api";

type Props = {
  models: ChatModel[];
  value: string;
  onChange: (model: string) => void;
  /** locked while an answer is streaming, so one answer never mixes two models */
  disabled?: boolean;
  /** false when the backend answers from data templates only */
  aiEnabled: boolean;
};

/** Model dropdown beside the chat input. Opens upward because the prompt box sits at the bottom of the workspace. */
export function ModelPicker({ models, value, onChange, disabled, aiEnabled }: Props) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const itemRefs = useRef<(HTMLButtonElement | null)[]>([]);
  const current = models.find((item) => item.id === value) ?? models[0];

  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", outside);
    const selected = Math.max(0, models.findIndex((item) => item.id === value));
    itemRefs.current[selected]?.focus({ preventScroll: true });
    return () => document.removeEventListener("mousedown", outside);
  }, [open, models, value]);

  const close = () => { setOpen(false); buttonRef.current?.focus(); };
  const choose = (id: string) => { onChange(id); close(); };

  const menuKeys = (event: KeyboardEvent<HTMLDivElement>) => {
    const items = itemRefs.current.filter(Boolean) as HTMLButtonElement[];
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    if (event.key === "Escape") { event.preventDefault(); close(); }
    else if (event.key === "ArrowDown") { event.preventDefault(); items[(index + 1) % items.length]?.focus(); }
    else if (event.key === "ArrowUp") { event.preventDefault(); items[(index - 1 + items.length) % items.length]?.focus(); }
    else if (event.key === "Home") { event.preventDefault(); items[0]?.focus(); }
    else if (event.key === "End") { event.preventDefault(); items[items.length - 1]?.focus(); }
    else if (event.key === "Tab") setOpen(false);
  };

  if (!current) return null;

  return (
    <div ref={rootRef} className="relative ml-auto">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        onKeyDown={(event) => { if (event.key === "ArrowUp" || event.key === "ArrowDown") { event.preventDefault(); setOpen(true); } }}
        disabled={disabled}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={`Model AI: ${current.label}. Đổi model`}
        className="flex min-h-8 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-muted transition hover:bg-orange-soft hover:text-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand disabled:cursor-not-allowed disabled:opacity-60"
      >
        <Icon name="sparkles" className="size-3.5 text-action" />
        <span>{current.label}</span>
        <span className="rounded-full bg-green-soft px-1.5 py-px text-[10px] font-semibold text-green-text">Miễn phí</span>
        <Icon name="chevronDown" className={`size-3.5 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>
      {open && (
        <div role="menu" aria-label="Chọn model AI" onKeyDown={menuKeys}
          className="absolute bottom-full right-0 z-50 mb-2 w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-line bg-card p-1.5 shadow-card">
          <p className="px-3 pb-1.5 pt-1 text-xs font-semibold text-subtle">Model miễn phí</p>
          {models.map((item, index) => {
            const selected = item.id === current.id;
            return (
              <button
                key={item.id}
                ref={(node) => { itemRefs.current[index] = node; }}
                type="button"
                role="menuitemradio"
                aria-checked={selected}
                onClick={() => choose(item.id)}
                className={`flex w-full items-start gap-2.5 rounded-xl px-3 py-2 text-left transition hover:bg-orange-soft focus-visible:bg-orange-soft focus-visible:outline-none ${selected ? "bg-orange-soft/60" : ""}`}
              >
                <span className="min-w-0 flex-1">
                  <span className="block text-sm font-medium text-ink">{item.label}</span>
                  <span className="block text-xs text-muted">{item.description}</span>
                </span>
                {selected && <Icon name="check" className="mt-0.5 size-4 shrink-0 text-action" />}
              </button>
            );
          })}
          {!aiEnabled && (
            <p className="mx-1 mt-1 rounded-xl bg-yellow-soft px-3 py-2 text-xs text-yellow-text">
              Máy chủ đang trả lời theo dữ liệu có sẵn, chưa dùng AI. Lựa chọn sẽ áp dụng khi bật chế độ AI.
            </p>
          )}
        </div>
      )}
    </div>
  );
}
