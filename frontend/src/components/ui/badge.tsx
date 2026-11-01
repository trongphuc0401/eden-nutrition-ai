import type { ReactNode } from "react";

export type BadgeTone = "good" | "warn" | "alert" | "neutral" | "brand";

const tones: Record<BadgeTone, string> = {
  good: "bg-green-soft text-green-text",
  warn: "bg-yellow-soft text-yellow-text",
  alert: "bg-coral-soft text-coral-strong",
  neutral: "bg-neutral-soft text-muted",
  brand: "bg-orange-soft text-action",
};

export function Badge({ tone = "neutral", children, className = "" }: { tone?: BadgeTone; children: ReactNode; className?: string }) {
  return <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold ${tones[tone]} ${className}`}>{children}</span>;
}
