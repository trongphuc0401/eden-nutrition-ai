import { referenceShare, type NutrientRow } from "@/lib/report-detail";

const SIZE = 280;
/** Side room for axis labels such as "Năng lượng 98%". */
const PAD_X = 56;
const CENTER = SIZE / 2;
const RADIUS = 92;
/** Outer ring = 150 % of the reference; values above are clipped to the ring. */
const SCALE_MAX = 150;
const SHORT: Record<string, string> = { calories: "Năng lượng", carbohydrate: "Carb", protein: "Đạm", fat: "Béo", fiber: "Xơ", sugar: "Đường", sodium: "Natri" };

function polar(index: number, count: number, r: number) {
  const angle = (Math.PI * 2 * index) / count - Math.PI / 2;
  return [CENTER + r * Math.cos(angle), CENTER + r * Math.sin(angle)] as const;
}

function point(index: number, count: number, share: number) {
  return polar(index, count, (Math.min(share, SCALE_MAX) / SCALE_MAX) * RADIUS);
}

export function BalanceRadar({ rows }: { rows: NutrientRow[] }) {
  const axes = rows.map((row) => ({ row, share: referenceShare(row) })).filter((item): item is { row: NutrientRow; share: number } => item.share !== null);
  if (axes.length < 3) return null;
  const polygon = (share: (i: number) => number) => axes.map((_, i) => point(i, axes.length, share(i)).join(",")).join(" ");
  const summary = axes.map(({ row, share }) => `${row.label} ${share}%`).join(", ");

  return (
    <section aria-labelledby="balance-radar" className="rounded-xl border border-line p-4 sm:p-5">
      <h3 id="balance-radar" className="font-semibold text-strong">Cân bằng tổng thể</h3>
      <p className="mt-1 text-xs text-muted">% so với mốc khuyến nghị: mức trần, hoặc mức tối thiểu với chất chỉ có ngưỡng dưới.</p>
      <svg viewBox={`${-PAD_X} 0 ${SIZE + PAD_X * 2} ${SIZE}`} className="mx-auto mt-2 w-full max-w-96" role="img" aria-label={`Biểu đồ cân bằng: ${summary}`}>
        {[50, 100, 150].map((ring) => (
          <polygon key={ring} points={polygon(() => ring)} fill="none" stroke="var(--color-line)" strokeWidth={ring === 100 ? 1.5 : 1} strokeDasharray={ring === 100 ? "4 3" : undefined} />
        ))}
        {axes.map((_, i) => {
          const [x, y] = point(i, axes.length, SCALE_MAX);
          return <line key={i} x1={CENTER} y1={CENTER} x2={x} y2={y} stroke="var(--color-line)" />;
        })}
        <polygon points={polygon((i) => axes[i].share)} fill="rgb(249 115 22 / 18%)" stroke="var(--color-brand)" strokeWidth={2} strokeLinejoin="round" />
        {axes.map(({ share }, i) => {
          const [x, y] = point(i, axes.length, share);
          return <circle key={i} cx={x} cy={y} r={3.5} fill="var(--color-action)" />;
        })}
        {axes.map(({ row, share }, i) => {
          const [x, y] = polar(i, axes.length, RADIUS + 14);
          const anchor = Math.abs(x - CENTER) < 8 ? "middle" : x > CENTER ? "start" : "end";
          return (
            <text key={row.key} x={x} y={y} textAnchor={anchor} dominantBaseline="middle" fontSize={11} fill="var(--color-muted)">
              {SHORT[row.key] ?? row.label}<tspan fontWeight={600} fill="var(--color-strong)"> {share}%</tspan>
            </text>
          );
        })}
      </svg>
      <p className="mt-1 flex justify-center gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="h-0.5 w-4 bg-brand" aria-hidden />Ly này</span>
        <span className="flex items-center gap-1.5"><span className="w-4 border-t border-dashed border-subtle" aria-hidden />Mốc 100%</span>
      </p>
    </section>
  );
}
