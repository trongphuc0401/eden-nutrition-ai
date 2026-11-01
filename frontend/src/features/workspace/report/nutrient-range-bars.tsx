import { Icon } from "@/components/ui/icon";
import type { NutrientRow, RangeStatus } from "@/lib/report-detail";

const STATUS: Record<RangeStatus, { label: string; text: string; dot: string; icon: "check" | "alert" }> = {
  in: { label: "Trong khoảng", text: "text-green-text", dot: "bg-green-text", icon: "check" },
  slightly_high: { label: "Cao nhẹ", text: "text-yellow-text", dot: "bg-yellow", icon: "alert" },
  high: { label: "Vượt khoảng", text: "text-coral-strong", dot: "bg-coral-strong", icon: "alert" },
  low: { label: "Thấp hơn khoảng", text: "text-yellow-text", dot: "bg-yellow", icon: "alert" },
  unknown: { label: "Chưa có khoảng tham chiếu", text: "text-muted", dot: "bg-subtle", icon: "alert" },
};

function format(value: number) {
  return value.toLocaleString("vi-VN", { maximumFractionDigits: 1 });
}

/** Axis end: leaves room past the larger of the value and the range so both are always visible. */
function axisMax(row: NutrientRow) {
  const reference = row.max ?? (row.min !== null ? row.min * 2 : 0);
  return Math.max(row.value ?? 0, reference, row.min ?? 0) * 1.25 || 1;
}

export function NutrientRangeBars({ rows }: { rows: NutrientRow[] }) {
  return (
    <section aria-labelledby="nutrient-ranges" className="rounded-xl border border-line p-4 sm:p-5">
      <div className="flex flex-wrap items-end justify-between gap-2 border-b border-line pb-3">
        <h3 id="nutrient-ranges" className="font-semibold text-strong">Cân đối dinh dưỡng trên 1 ly</h3>
        <p className="flex items-center gap-3 text-xs text-muted">
          <span className="flex items-center gap-1.5"><span className="h-2.5 w-6 rounded-full border border-green-line bg-green-soft" aria-hidden />Khoảng khuyến nghị</span>
          <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-strong" aria-hidden />Ly này</span>
        </p>
      </div>
      <ul>
        {rows.map((row) => {
          const status = STATUS[row.status];
          const end = axisMax(row);
          const lo = ((row.min ?? 0) / end) * 100;
          const hi = ((row.max ?? end) / end) * 100;
          const dot = row.value !== null ? Math.min((row.value / end) * 100, 100) : null;
          return (
            <li key={row.key} className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 gap-y-2 border-b border-line py-3 last:border-0 sm:grid-cols-[9rem_minmax(0,1fr)_9.5rem]">
              <span className="text-sm font-medium text-strong">{row.label}</span>
              <div className="col-span-2 row-start-2 sm:col-span-1 sm:row-start-auto">
                <div className="relative h-3 rounded-full bg-neutral-soft" aria-hidden>
                  {(row.min !== null || row.max !== null) && (
                    <span className="absolute inset-y-0 rounded-full border border-green-line bg-green-soft" style={{ left: `${lo}%`, width: `${Math.max(hi - lo, 1)}%` }} />
                  )}
                  {dot !== null && <span className={`absolute top-1/2 size-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full ring-2 ring-card ${status.dot}`} style={{ left: `${dot}%` }} />}
                </div>
                <p className="mt-1 text-xs text-subtle">
                  {row.min !== null && row.max !== null ? `${format(row.min)}–${format(row.max)} ${row.unit}`
                    : row.min !== null ? `≥ ${format(row.min)} ${row.unit}`
                    : row.max !== null ? `≤ ${format(row.max)} ${row.unit}` : "Chưa có khoảng tham chiếu"}
                  {row.basis && <span className="hidden md:inline"> · {row.basis}</span>}
                </p>
              </div>
              <div className="col-start-2 row-start-1 text-right sm:col-start-auto sm:row-start-auto">
                <strong className="block text-sm text-strong">{row.value !== null ? `${format(row.value)} ${row.unit}` : "Chưa đủ dữ liệu"}</strong>
                {row.value !== null && row.status !== "unknown" && (
                  <span className={`inline-flex items-center gap-1 text-xs font-semibold ${status.text}`}><Icon name={status.icon} className="size-3.5" />{status.label}</span>
                )}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
