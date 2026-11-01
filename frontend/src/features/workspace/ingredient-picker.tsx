"use client";

import { useMemo, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Modal } from "@/components/ui/modal";
import type { Ingredient } from "@/lib/types";
import { IngredientAvatar } from "./ingredient-avatar";

export type CatalogStatus = "loading" | "ready" | "error";

type Props = {
  open: boolean; catalog: Ingredient[]; status: CatalogStatus; onRetry: () => void;
  selectedIds: string[]; setSelectedIds: (ids: string[]) => void; close: () => void;
};

export function IngredientPicker({ open, catalog, status, onRetry, selectedIds, setSelectedIds, close }: Props) {
  const [query, setQuery] = useState("");
  const results = useMemo(() => catalog.filter((ingredient) => ingredient.name.toLowerCase().includes(query.trim().toLowerCase())), [catalog, query]);
  const toggle = (id: string) => setSelectedIds(selectedIds.includes(id) ? selectedIds.filter((item) => item !== id) : [...selectedIds, id]);

  return (
    <Modal open={open} onClose={close} labelledBy="ingredient-title" panelClassName="flex flex-col p-5">
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 id="ingredient-title" className="text-xl font-semibold text-strong">Chọn nguyên liệu của bạn</h2>
          <p className="mt-1 text-sm leading-6 text-muted">AI chỉ dùng trái cây và nguyên liệu phụ bạn chọn; có thể thêm nước và đá.</p>
        </div>
        <Button variant="ghost" icon onClick={close} aria-label="Đóng"><Icon name="close" /></Button>
      </div>
      <label className="relative mb-4 block">
        <span className="sr-only">Tìm nguyên liệu</span>
        <Icon name="search" className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-subtle" />
        <input className="field pl-10" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Tìm trái cây hoặc nguyên liệu phụ..." data-autofocus disabled={status !== "ready"} />
      </label>

      <div className="min-h-48" aria-busy={status === "loading"}>
        {status === "loading" && (
          <ul className="grid gap-2 sm:grid-cols-2" aria-label="Đang tải danh mục">
            {Array.from({ length: 6 }, (_, index) => <li key={index} className="h-16 animate-pulse rounded-xl bg-neutral-soft" />)}
          </ul>
        )}
        {status === "error" && (
          <div className="grid place-items-center rounded-xl border border-coral-line bg-coral-soft p-6 text-center" role="alert">
            <p className="font-semibold text-coral-strong">Không tải được danh mục nguyên liệu</p>
            <p className="mt-1 text-sm text-muted">Kiểm tra kết nối rồi thử lại. Các lựa chọn hiện tại vẫn được giữ.</p>
            <Button size="sm" className="mt-4" onClick={onRetry}><Icon name="refresh" className="size-4" />Thử lại</Button>
          </div>
        )}
        {status === "ready" && results.length === 0 && (
          <div className="rounded-xl border border-dashed border-line p-6 text-center">
            <p className="font-semibold text-strong">Không có nguyên liệu khớp “{query}”</p>
            <p className="mt-1 text-sm text-muted">Thử tên khác, ví dụ “cam” hoặc “ổi”.</p>
            <Button size="sm" variant="ghost" className="mt-3" onClick={() => setQuery("")}>Xóa tìm kiếm</Button>
          </div>
        )}
        {status === "ready" && results.length > 0 && (
          <ul className="grid max-h-[48dvh] gap-2 overflow-y-auto sm:grid-cols-2">
            {results.map((ingredient) => {
              const checked = selectedIds.includes(ingredient.id);
              return (
                <li key={ingredient.id}>
                  <label className={`flex min-h-16 cursor-pointer items-center gap-3 rounded-xl border p-3 transition ${checked ? "border-brand bg-orange-soft" : "border-line bg-card hover:border-peach"}`}>
                    <input className="size-4 accent-action" type="checkbox" checked={checked} onChange={() => toggle(ingredient.id)} />
                    <IngredientAvatar ingredient={ingredient} />
                    <span className="min-w-0 flex-1">
                      <span className="block text-sm font-semibold text-strong">{ingredient.name}</span>
                      <span className="block truncate text-xs text-muted" title={ingredient.source ? `Nguồn: ${ingredient.source}` : undefined}>{ingredient.kind === "fruit" ? ingredient.region : "Nguyên liệu phụ"}</span>
                    </span>
                    <SeasonBadge seasonal={ingredient.seasonal} />
                  </label>
                </li>
              );
            })}
          </ul>
        )}
      </div>

      <div className="mt-5 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={close}>Hủy</Button>
        <Button variant="primary" onClick={close}>Dùng {selectedIds.length} nguyên liệu</Button>
      </div>
    </Modal>
  );
}

function SeasonBadge({ seasonal }: { seasonal: Ingredient["seasonal"] }) {
  if (seasonal === "in") return <Badge tone="good">Đang mùa</Badge>;
  if (seasonal === "out") return <Badge tone="warn">Trái mùa</Badge>;
  return <Badge>Chưa rõ mùa</Badge>;
}
