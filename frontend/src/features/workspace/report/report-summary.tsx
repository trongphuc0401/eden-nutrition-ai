import type { ReactNode } from "react";
import { Icon } from "@/components/ui/icon";
import type { ReportDetail, StepKind } from "@/lib/report-detail";

export function ProfileChips({ profile }: { profile: NonNullable<ReportDetail["profile"]> }) {
  const chips: { text: string; tone: string }[] = [];
  if (profile.gender) chips.push({ text: profile.age ? `${profile.gender}, ${profile.age} tuổi` : profile.gender, tone: "bg-neutral-soft text-strong" });
  if (profile.bmi) chips.push({ text: `BMI ${profile.bmi.toLocaleString("vi-VN")}${profile.bmi_category ? ` · ${profile.bmi_category}` : ""}`, tone: "bg-neutral-soft text-strong" });
  if (profile.allergies?.length) chips.push({ text: `Dị ứng: ${profile.allergies.join(", ")}`, tone: "bg-coral-soft text-coral-strong" });
  if (profile.preferences?.length) chips.push({ text: `Thích: ${profile.preferences.join(", ")}`, tone: "bg-orange-soft text-action" });
  if (profile.dislikes?.length) chips.push({ text: `Không thích: ${profile.dislikes.join(", ")}`, tone: "bg-neutral-soft text-muted" });
  if (!chips.length) return null;
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
      <span className="shrink-0 text-xs font-medium text-muted">Hồ sơ đầu vào</span>
      <ul className="flex flex-wrap gap-2">{chips.map((chip) => <li key={chip.text} className={`rounded-full px-3 py-1 text-sm ${chip.tone}`}>{chip.text}</li>)}</ul>
    </div>
  );
}

function Tile({ title, children, footer }: { title: string; children: ReactNode; footer?: ReactNode }) {
  return (
    <div className="flex flex-col rounded-xl border border-line bg-cream p-4">
      <h4 className="text-sm text-muted">{title}</h4>
      <div className="mt-2 flex items-baseline gap-1">{children}</div>
      {footer && <div className="mt-2 text-xs text-muted">{footer}</div>}
    </div>
  );
}

export function ScoreTiles({ detail }: { detail: ReportDetail }) {
  const fit = detail.personalFit;
  const allergen = detail.allergen;
  const conflicts = allergen?.conflicts.length ?? 0;
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <Tile title="Điểm phù hợp cá nhân" footer={fit && (
        fit.breakdown.length ? (
          <details>
            <summary className="cursor-pointer font-medium text-action">Vì sao bị trừ điểm</summary>
            <ul className="mt-1.5 space-y-1">{fit.breakdown.map((row) => <li key={row.label} className="flex justify-between gap-2"><span>{row.label}</span><span className="font-semibold text-strong">{row.points}</span></li>)}</ul>
          </details>
        ) : "Đạt mọi ngưỡng đã kiểm tra"
      )}>
        {fit ? <><strong className="text-4xl font-semibold text-action">{fit.value}</strong><span className="text-muted">/100</span></> : <span className="text-sm text-muted">Chưa đủ dữ liệu</span>}
      </Tile>
      <Tile title="Điểm mùa vụ" footer={detail.seasonalScore !== null ? `Theo khối lượng nguyên liệu tươi, tháng ${detail.month}` : "Chưa có lịch mùa cho nguyên liệu đã chọn"}>
        {detail.seasonalScore !== null ? <><strong className="text-4xl font-semibold text-green-text">{detail.seasonalScore}</strong><span className="text-muted">/100</span></> : <span className="text-sm text-muted">—</span>}
      </Tile>
      <Tile title="An toàn dị ứng" footer={allergen?.checked.length ? `Đã đối chiếu: ${allergen.checked.join(", ")}` : "Hồ sơ chưa khai báo dị ứng"}>
        <Icon name={conflicts ? "alert" : "shield"} className={`size-7 self-center ${conflicts ? "text-coral-strong" : "text-green-text"}`} />
        <strong className={`text-4xl font-semibold ${conflicts ? "text-coral-strong" : "text-strong"}`}>{conflicts}</strong>
        <span className="text-muted">xung đột</span>
      </Tile>
    </div>
  );
}

const STEP_PATHS: Record<StepKind, string> = {
  wash: "M12 2.7 6.3 9a7 7 0 1 0 11.4 0z",
  peel: "M3 21 14 10M14 4l6 6-6 6-6-6z",
  cut: "M6 9a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM20 4 8.1 15.9M14.5 14.5 20 20M8.1 8.1 12 12",
  soak: "M2 12c2-2 4-2 6 0s4 2 6 0 4-2 6 0M2 18c2-2 4-2 6 0s4 2 6 0 4-2 6 0M12 3v5",
  weigh: "M12 3v18M5 7h14M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z",
  add: "M12 8v8M8 12h8M4 4h16v16H4z",
  blend: "M7 3h10l-1.5 11h-7zM8.5 14h7l1 7h-9zM12 17.5h.01",
  rest: "M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20zM12 6v6l4 2",
  pour: "M6 8h12l-1.5 13h-9zM5 8h14M9 8l1-5h4",
  other: "M20 6 9 17l-5-5",
};

export function PrepSteps({ detail }: { detail: ReportDetail }) {
  if (!detail.steps.length) return null;
  return (
    <section aria-labelledby="prep-steps">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="prep-steps" className="font-semibold text-strong">Quá trình thực hiện</h3>
        {detail.prepMinutes && <span className="text-sm text-muted">Tổng khoảng {detail.prepMinutes} phút</span>}
      </div>
      <ol className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {detail.steps.map((step, index) => (
          <li key={step.detail} className="flex gap-3 rounded-xl border border-line bg-card p-3">
            <span className="relative grid size-10 shrink-0 place-items-center rounded-xl bg-orange-soft text-action">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className="size-5" aria-hidden><path d={STEP_PATHS[step.kind]} /></svg>
              <span className="absolute -left-1.5 -top-1.5 rounded-full bg-action px-1.5 text-[10px] font-semibold leading-4 text-white">B{index + 1}</span>
            </span>
            <span className="min-w-0">
              <strong className="block text-sm text-strong">{step.title}{step.minutes !== null && <span className="ml-1.5 font-normal text-muted">· {step.minutes < 1 ? `${Math.round(step.minutes * 60)} giây` : `${step.minutes.toLocaleString("vi-VN")} phút`}</span>}</strong>
              <span className="text-sm leading-6 text-muted">{step.detail}</span>
            </span>
          </li>
        ))}
      </ol>
    </section>
  );
}

/** Trust UI: data checks, missing data, assumptions and the medical disclaimer in one place. */
export function TrustFooter({ detail, coverage }: { detail: ReportDetail; coverage?: number }) {
  const blocks: { title: string; items: string[]; tone: string }[] = [
    { title: "Số liệu nên kiểm tra lại", items: detail.dataChecks, tone: "border-coral-line bg-coral-soft text-coral-strong" },
    { title: "Còn thiếu", items: detail.missingData, tone: "border-yellow-line bg-yellow-soft text-yellow-text" },
    { title: "Cách tính đã giả định", items: detail.assumptions, tone: "border-line bg-cream text-muted" },
  ].filter((block) => block.items.length);
  return (
    <div className="space-y-3">
      {coverage !== undefined && (
        <div>
          <div className="flex items-center gap-3 text-sm text-muted">
            <span className="shrink-0">Số liệu đã có</span>
            <span className="h-2 flex-1 overflow-hidden rounded-full bg-neutral-soft" aria-hidden><span className="block h-full rounded-full bg-green" style={{ width: `${Math.round(coverage * 100)}%` }} /></span>
            <strong className="text-strong">{Math.round(coverage * 100)}%</strong>
          </div>
          <p className="mt-1 text-xs text-muted">
            {coverage >= 1
              ? "Mọi nguyên liệu đều có đủ số liệu dinh dưỡng, nên các con số ở trên được tính đầy đủ."
              : `Đã tìm được số liệu cho ${Math.round(coverage * 100)}% các chất cần tính của nguyên liệu. Phần còn thiếu chưa được cộng vào tổng, nên con số thực tế có thể cao hơn một chút.`}
          </p>
        </div>
      )}
      {blocks.map((block) => (
        <div key={block.title} className={`rounded-xl border p-4 text-sm ${block.tone}`}>
          <strong className="block text-strong">{block.title}</strong>
          <ul className="mt-1 list-disc space-y-1 pl-5">{block.items.map((item) => <li key={item}>{item}</li>)}</ul>
        </div>
      ))}
      {detail.disclaimer && <p className="text-xs text-muted">{detail.disclaimer}</p>}
    </div>
  );
}
