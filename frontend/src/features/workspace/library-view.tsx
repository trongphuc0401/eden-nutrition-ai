import { Button } from "@/components/ui/button";
import { ContentImage } from "@/components/ui/content-image";
import { Icon } from "@/components/ui/icon";
import type { Report } from "@/lib/types";

const COPY = {
  history: { title: "Các lần tạo gần đây", empty: "Chưa có công thức nào", hint: "Công thức bạn tạo trong phiên này sẽ hiện ở đây.", image: "emptyHistory" },
  saved: { title: "Công thức bạn đã lưu", empty: "Chưa lưu công thức nào", hint: "Bấm “Lưu báo cáo” trên một công thức để xem lại sau.", image: "emptySaved" },
} as const;

export function LibraryView({ kind, reports, onOpen, onStart }: { kind: keyof typeof COPY; reports: Report[]; onOpen: (report: Report) => void; onStart: () => void }) {
  const copy = COPY[kind];
  return (
    <section className="soft-card min-w-0 flex-1 p-5 sm:p-6" aria-labelledby="library-title">
      <h2 id="library-title" className="text-xl font-semibold text-strong">{copy.title}</h2>
      {reports.length ? (
        <ul className="mt-5 space-y-3">
          {reports.map((entry) => (
            <li key={entry.id}>
              <button onClick={() => onOpen(entry)} className="flex w-full items-center justify-between gap-3 rounded-xl border border-line p-4 text-left transition hover:border-peach hover:bg-orange-soft">
                <span className="min-w-0"><strong className="block truncate text-strong">{entry.name}</strong><small className="text-sm text-muted">{entry.createdAt} · Phiên bản {entry.version}</small></span>
                <Icon name="arrowRight" className="size-4 text-muted" />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mx-auto mt-6 max-w-sm text-center">
          <div className="overflow-hidden rounded-card"><ContentImage name={copy.image} sizes="384px" /></div>
          <p className="mt-5 font-semibold text-strong">{copy.empty}</p>
          <p className="mt-1 text-sm leading-6 text-muted">{copy.hint}</p>
          <Button variant="primary" className="mt-5" onClick={onStart}><Icon name="sparkles" className="size-4" />Tạo công thức</Button>
        </div>
      )}
    </section>
  );
}
