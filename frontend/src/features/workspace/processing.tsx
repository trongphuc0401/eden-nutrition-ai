import { Button } from "@/components/ui/button";
import { ContentImage } from "@/components/ui/content-image";
import { Icon } from "@/components/ui/icon";

const STEPS = [
  ["Kiểm tra yêu cầu", "Đang xác thực hồ sơ và nguyên liệu..."],
  ["Truy xuất dữ liệu", "Đang lấy số liệu dinh dưỡng có nguồn..."],
  ["Tạo công thức", "Đang dùng đúng nguyên liệu bạn đã chọn..."],
  ["Tính dinh dưỡng", "Đang tính từ dữ liệu trên 100 g..."],
  ["Kiểm tra an toàn", "Đang đối chiếu dị ứng và ngưỡng đánh giá..."],
  ["Biên soạn báo cáo", "Đang rút gọn nội dung cho đúng hai trang..."],
  ["Dựng PDF", "Đang tạo file A4..."],
] as const;

/** Visible AI state while the report workflow runs; the user can always stop it. */
export function Processing({ current, hometown, onStop }: { current: number; hometown: string; onStop: () => void }) {
  const active = STEPS[Math.min(current, STEPS.length - 1)];
  return (
    <section className="rounded-card border-2 border-brand bg-warm p-4 shadow-card sm:p-5" aria-labelledby="processing-title" aria-live="polite">
      <div className="grid gap-5 lg:grid-cols-[240px_minmax(0,1fr)]">
        <ol className="space-y-4 rounded-xl border border-line bg-card p-4">
          {STEPS.map(([title, copy], index) => {
            const done = index < current, now = index === current;
            return (
              <li key={title} className="flex gap-3" aria-current={now ? "step" : undefined}>
                <span className={`grid size-6 shrink-0 place-items-center rounded-full text-xs font-semibold ${done ? "bg-green-text text-white" : now ? "bg-brand text-white" : "border-2 border-line bg-card text-subtle"}`}>
                  {done ? <Icon name="check" className="size-3.5" /> : index + 1}
                </span>
                <span className={index > current ? "opacity-60" : ""}>
                  <strong className="block text-sm text-strong">{title}</strong>
                  <span className="mt-0.5 block text-xs text-muted">{now ? copy : done ? "Đã hoàn tất" : "Đang chờ bước trước"}</span>
                </span>
              </li>
            );
          })}
        </ol>
        <div>
          <div className="overflow-hidden rounded-xl border border-line"><ContentImage name="processing" sizes="(min-width: 1024px) 480px, 100vw" className="max-h-48" /></div>
          <span className="mt-4 inline-flex items-center gap-2 rounded-full bg-orange-soft px-3 py-1 text-xs font-semibold text-action"><span className="size-2 animate-pulse rounded-full bg-brand" />Đang tạo báo cáo</span>
          <h2 id="processing-title" className="mt-3 text-2xl font-semibold text-strong">{active[0]}...</h2>
          <p className="mt-2 max-w-xl leading-6 text-muted">AI đang dùng hồ sơ của bạn, khu vực {hometown} và danh sách nguyên liệu bạn đã xác nhận. Số liệu thiếu sẽ được ghi rõ là ước tính.</p>
          <Button className="mt-5" onClick={onStop}><Icon name="stop" className="size-4" />Dừng tạo</Button>
        </div>
      </div>
    </section>
  );
}
