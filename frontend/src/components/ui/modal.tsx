"use client";

import { useEffect, useRef, type ReactNode } from "react";

const FOCUSABLE = "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

const placements = {
  center: "grid place-items-end sm:place-items-center sm:p-4",
  left: "flex justify-start",
  right: "flex justify-end",
};

const panels = {
  center: "w-full max-w-2xl rounded-t-[28px] sm:rounded-[28px] max-h-[92dvh] overflow-y-auto",
  left: "h-full w-80 max-w-[85vw] overflow-y-auto",
  right: "h-full w-96 max-w-[90vw] overflow-y-auto",
};

/** Accessible overlay: traps focus, closes on Esc or backdrop click, restores focus on close. */
export function Modal({ open, onClose, labelledBy, label, placement = "center", children, panelClassName = "" }: {
  open: boolean; onClose: () => void; labelledBy?: string; label?: string; placement?: keyof typeof placements; children: ReactNode; panelClassName?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef(onClose);
  useEffect(() => { closeRef.current = onClose; }, [onClose]);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const panel = panelRef.current;
    (panel?.querySelector<HTMLElement>("[data-autofocus]") ?? panel?.querySelector<HTMLElement>(FOCUSABLE) ?? panel)?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.stopPropagation(); closeRef.current(); return; }
      if (event.key !== "Tab" || !panel) return;
      const items = [...panel.querySelectorAll<HTMLElement>(FOCUSABLE)];
      if (!items.length) return;
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("keydown", onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = overflow; previous?.focus?.(); };
  }, [open]);

  if (!open) return null;
  return (
    <div className={`fixed inset-0 z-40 bg-ink/35 backdrop-blur-sm ${placements[placement]}`} onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div ref={panelRef} role="dialog" aria-modal="true" aria-labelledby={labelledBy} aria-label={label} tabIndex={-1}
        className={`border border-line bg-card shadow-card outline-none ${panels[placement]} ${panelClassName}`}>
        {children}
      </div>
    </div>
  );
}
