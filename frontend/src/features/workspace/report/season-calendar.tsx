import { Badge, type BadgeTone } from "@/components/ui/badge";
import { seasonLabel, type ReportDetail, type SeasonStatus } from "@/lib/report-detail";

const MONTHS = Array.from({ length: 12 }, (_, i) => i + 1);
const SEASON_TONE: Record<SeasonStatus, BadgeTone> = {
  in_season: "good", year_round: "good", out_of_season: "warn", not_seasonal: "neutral", unknown: "neutral",
};

function format(value: number) {
  return value.toLocaleString("vi-VN", { maximumFractionDigits: 1 });
}

/** Months come from the ingredient_seasons reference table; rows without a calendar are listed in the table only. */
export function SeasonCalendar({ detail }: { detail: ReportDetail }) {
  const rows = detail.ingredients.filter((item) => item.season.months.length > 0);
  if (!rows.length) return null;
  return (
    <section aria-labelledby="season-calendar" className="rounded-xl border border-line p-4 sm:p-5">
      <h3 id="season-calendar" className="font-semibold text-strong">Lịch mùa vụ nguyên liệu tươi</h3>
      <p className="mt-1 text-xs text-muted">Tháng hiện tại (tháng {detail.month}) được đánh dấu màu cam.</p>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[30rem] border-separate border-spacing-y-1.5 text-sm">
          <thead>
            <tr>
              <th scope="col" className="w-32 text-left text-xs font-medium text-muted"><span className="sr-only">Nguyên liệu</span></th>
              {MONTHS.map((month) => (
                <th key={month} scope="col" className={`text-center text-xs font-medium ${month === detail.month ? "text-action" : "text-subtle"}`}>
                  <span className={month === detail.month ? "rounded-full bg-orange-soft px-1.5 py-0.5" : ""}>{month}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.name}>
                <th scope="row" className="pr-2 text-left font-medium text-strong">{item.name}</th>
                {MONTHS.map((month) => {
                  const inSeason = item.season.months.includes(month);
                  return (
                    <td key={month} className="text-center">
                      <span className={`mx-auto block h-5 w-4 rounded-full ${inSeason ? "bg-green" : "border border-dashed border-subtle"} ${month === detail.month ? "ring-2 ring-peach ring-offset-1" : ""}`}>
                        <span className="sr-only">Tháng {month}: {inSeason ? "chính vụ" : "ngoài vụ"}</span>
                      </span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 flex flex-wrap gap-4 text-xs text-muted">
        <span className="flex items-center gap-1.5"><span className="h-4 w-3 rounded-full bg-green" aria-hidden />Chính vụ</span>
        <span className="flex items-center gap-1.5"><span className="h-4 w-3 rounded-full border border-dashed border-subtle" aria-hidden />Ngoài vụ</span>
      </p>
    </section>
  );
}

export function IngredientSeasonTable({ detail }: { detail: ReportDetail }) {
  return (
    <section aria-labelledby="ingredient-table" className="rounded-xl border border-line p-4 sm:p-5">
      <h3 id="ingredient-table" className="font-semibold text-strong">Nguyên liệu & mùa vụ</h3>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[28rem] text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs text-muted">
              <th scope="col" className="py-2 font-medium">Nguyên liệu</th>
              <th scope="col" className="py-2 text-right font-medium">Khối lượng</th>
              <th scope="col" className="py-2 text-right font-medium">Kcal</th>
              <th scope="col" className="py-2 pl-4 font-medium">Mùa vụ</th>
            </tr>
          </thead>
          <tbody>
            {detail.ingredients.map((item) => (
              <tr key={item.name} className="border-b border-line last:border-0">
                <td className="py-2.5 font-medium text-strong">{item.name}</td>
                <td className="py-2.5 text-right tabular-nums">{format(item.amount)} {item.unit}</td>
                <td className="py-2.5 text-right tabular-nums">{item.kcal ?? "—"}</td>
                <td className="py-2.5 pl-4">
                  <span className="flex flex-wrap gap-1.5">
                    <Badge tone={SEASON_TONE[item.season.status]}>{seasonLabel(item.season.status)}</Badge>
                    {item.substitutionFor && <Badge tone="brand">Thay {item.substitutionFor}</Badge>}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
          {detail.nutrients[0]?.value !== null && (
            <tfoot>
              <tr className="text-xs text-muted">
                <td className="pt-2">Tổng 1 ly</td>
                <td />
                <td className="pt-2 text-right font-semibold tabular-nums text-strong">{Math.round(detail.nutrients[0].value ?? 0)}</td>
                <td />
              </tr>
            </tfoot>
          )}
        </table>
      </div>
    </section>
  );
}
