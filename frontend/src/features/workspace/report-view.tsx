"use client";

import { useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import { Button, buttonClass } from "@/components/ui/button";
import { ContentImage } from "@/components/ui/content-image";
import { Icon } from "@/components/ui/icon";
import type { Report } from "@/lib/types";

const TABS = [{ id: "recipe", label: "Công thức" }, { id: "nutrition", label: "Dinh dưỡng & gợi ý" }] as const;
type Tab = (typeof TABS)[number]["id"];

export function ReportView({ report, hometown, onToggleSaved, onCopy }: { report: Report; hometown: string; onToggleSaved: () => void; onCopy: (text: string) => void }) {
  const [tab, setTab] = useState<Tab>("recipe");
  const tabRefs = useRef<Record<Tab, HTMLButtonElement | null>>({ recipe: null, nutrition: null });
  const nutrients: [string, number | null, string][] = [
    ["Năng lượng", report.nutrition.calories, "kcal"], ["Protein", report.nutrition.protein, "g"], ["Carbohydrate", report.nutrition.carbs, "g"],
    ["Chất béo", report.nutrition.fat, "g"], ["Chất xơ", report.nutrition.fiber, "g"], ["Đường", report.nutrition.sugar, "g"],
  ];
  const onTabKey = (event: KeyboardEvent) => {
    if (event.key !== "ArrowRight" && event.key !== "ArrowLeft" && event.key !== "Home" && event.key !== "End") return;
    event.preventDefault();
    const index = TABS.findIndex((item) => item.id === tab);
    const next = event.key === "Home" ? 0 : event.key === "End" ? TABS.length - 1 : (index + (event.key === "ArrowRight" ? 1 : -1) + TABS.length) % TABS.length;
    setTab(TABS[next].id);
    tabRefs.current[TABS[next].id]?.focus();
  };

  return (
    <article className="overflow-hidden rounded-card border border-line bg-card shadow-card" aria-labelledby={`report-${report.id}`}>
      <div className="relative"><ContentImage name="reportCover" sizes="(min-width: 1280px) 800px, 100vw" className="aspect-[12/5] max-h-56" /></div>
      <div className="p-4 sm:p-6">
        <header className="flex flex-col gap-4 border-b border-line pb-5 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            <Badge tone={report.decision === "pass" ? "good" : "warn"}>{report.decision === "pass" ? "Đã đạt kiểm tra" : "Cần xem xét"}</Badge>
            <h2 id={`report-${report.id}`} className="mt-3 text-2xl font-semibold text-strong">{report.name}</h2>
            <p className="mt-1 text-sm text-muted">1 khẩu phần · {report.createdAt} · Phiên bản {report.version}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" onClick={() => onCopy(report.name)}><Icon name="copy" className="size-4" />Sao chép</Button>
            {report.pdfUrl && <a className={buttonClass({ variant: "primary", size: "sm" })} href={report.pdfUrl}><Icon name="download" className="size-4" />Tải PDF 2 trang</a>}
            <Button size="sm" onClick={onToggleSaved} aria-pressed={report.saved}><Icon name="bookmark" className="size-4" />{report.saved ? "Đã lưu" : "Lưu báo cáo"}</Button>
          </div>
        </header>

        <div className="mt-5 flex gap-2 border-b border-line" role="tablist" aria-label="Nội dung báo cáo">
          {TABS.map((item) => (
            <button key={item.id} ref={(node) => { tabRefs.current[item.id] = node; }} role="tab" id={`tab-${report.id}-${item.id}`} aria-controls={`panel-${report.id}-${item.id}`}
              aria-selected={tab === item.id} tabIndex={tab === item.id ? 0 : -1} onClick={() => setTab(item.id)} onKeyDown={onTabKey}
              className={`-mb-px border-b-2 px-3 pb-3 text-sm font-semibold ${tab === item.id ? "border-brand text-action" : "border-transparent text-muted hover:text-ink"}`}>{item.label}</button>
          ))}
        </div>

        <div role="tabpanel" id={`panel-${report.id}-${tab}`} aria-labelledby={`tab-${report.id}-${tab}`} tabIndex={0} className="mt-6 rounded-xl">
          {tab === "recipe" ? (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
              <div className="space-y-6">
                <Card title="Thành phần">
                  <ul>{report.ingredients.map((item) => (
                    <li key={item.name} className={`flex items-start justify-between gap-3 border-b border-line py-3 last:border-0 ${item.used ? "" : "opacity-60"}`}>
                      <span><strong className="block text-sm text-strong">{item.name}{!item.used && " · không dùng"}</strong><span className="text-sm text-muted">{item.purpose}</span></span>
                      <strong className="shrink-0 text-sm">{item.amount}</strong>
                    </li>
                  ))}</ul>
                </Card>
                {report.tools.length > 0 && <Card title="Dụng cụ chuẩn bị"><ul className="flex flex-wrap gap-2">{report.tools.map((tool) => <li key={tool} className="rounded-lg bg-orange-soft px-3 py-2 text-sm">{tool}</li>)}</ul></Card>}
                <Card title="Cách thực hiện">
                  <ol className="space-y-4">{report.steps.map((step, index) => (
                    <li key={step} className="flex gap-3"><span className="grid size-7 shrink-0 place-items-center rounded-full bg-orange-soft text-sm font-semibold text-action">{index + 1}</span><p className="pt-0.5 text-sm leading-6 text-muted">{step}</p></li>
                  ))}</ol>
                </Card>
              </div>
              <div className="space-y-4">
                <Card title="Tóm tắt một khẩu phần">
                  <dl className="grid grid-cols-2 gap-3">{nutrients.slice(0, 4).map(([label, value, unit]) => (
                    <div key={label} className="rounded-xl bg-cream p-3"><dt className="text-xs text-muted">{label}</dt><dd className="mt-1 font-semibold text-strong">{value ?? "—"} {value !== null ? unit : ""}</dd></div>
                  ))}</dl>
                </Card>
                {report.warning && <div className="rounded-xl border border-yellow-line bg-yellow-soft p-4 text-sm leading-6 text-yellow-text"><strong className="block text-strong">Lưu ý</strong>{report.warning}</div>}
                <Card title="Vì sao phù hợp"><p className="text-sm leading-6 text-muted">{report.reason}</p></Card>
              </div>
            </div>
          ) : (
            <div className="space-y-5">
              <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{nutrients.map(([label, value, unit]) => (
                <div key={label} className="rounded-xl border border-line bg-cream p-4">
                  <dt className="text-sm text-muted">{label}</dt>
                  <dd className="mt-1 text-2xl font-semibold text-strong">{value ?? <span className="text-base">Chưa đủ dữ liệu</span>}{value !== null && <small className="ml-1 text-sm font-medium">{unit}</small>}</dd>
                  <span className="mt-2 block text-xs text-muted">Ước tính cho một khẩu phần</span>
                </div>
              ))}</dl>
              <Card title="Gợi ý dựa trên hướng dẫn dinh dưỡng">
                <p className="text-sm leading-6 text-muted">Công thức hạn chế đường thêm vào, ưu tiên chất xơ và protein thực vật. Chế độ ăn lành mạnh vẫn cần đa dạng thực phẩm, vận động phù hợp và theo dõi cùng chuyên gia nếu bạn có tình trạng sức khỏe cần lưu ý.</p>
                <p className="mt-3 text-xs text-muted">AI tổng hợp nội dung tham khảo, không phải tư vấn y tế cá nhân.</p>
              </Card>
              <Card title="Nguồn và thông tin đã dùng">
                <ul className="list-disc space-y-2 pl-5 text-sm text-muted">{report.sources.map((source) => <li key={source}>{source}</li>)}<li>Hồ sơ tại thời điểm tạo · {hometown}</li></ul>
              </Card>
            </div>
          )}
        </div>
        <p className="mt-6 rounded-xl border border-line bg-cream p-4 text-sm text-muted"><strong className="block text-base text-strong">Muốn thay đổi công thức?</strong>Hỏi trợ lý bên dưới để so sánh hoặc tìm nguyên liệu phù hợp hơn, rồi chọn lại và tạo báo cáo mới.</p>
      </div>
    </article>
  );
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return <section className="rounded-xl border border-line p-4"><h3 className="mb-3 font-semibold text-strong">{title}</h3>{children}</section>;
}
