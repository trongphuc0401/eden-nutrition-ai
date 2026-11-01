"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import type { Ingredient, PendingConfirmation } from "@/lib/types";

export function ConfirmationPanel({ pending, catalog, confirm, cancel }: { pending: PendingConfirmation; catalog: Ingredient[]; confirm: (ids: string[]) => void; cancel: () => void }) {
  const [accepted, setAccepted] = useState<string[]>(pending.proposal.suggested_ingredient_ids);
  const suggestions = pending.proposal.ingredients.filter((item) => pending.proposal.suggested_ingredient_ids.includes(item.ingredient_id));
  const name = (id: string) => catalog.find((item) => item.id === id)?.name ?? id;
  const toggle = (id: string) => setAccepted((items) => items.includes(id) ? items.filter((item) => item !== id) : [...items, id]);
  return (
    <section className="rounded-card border border-yellow-line bg-yellow-soft p-5 shadow-card sm:p-6" aria-labelledby="confirmation-title">
      <span className="inline-flex rounded-full bg-card px-3 py-1 text-xs font-semibold text-yellow-text">Đang chờ bạn xác nhận</span>
      <h2 id="confirmation-title" className="mt-4 text-2xl font-semibold text-strong">AI đề nghị bổ sung nguyên liệu</h2>
      <p className="mt-2 max-w-2xl leading-6 text-muted">Các nguyên liệu dưới đây chưa có trong báo cáo. Chọn phần bạn đồng ý, hệ thống sẽ tạo lại và kiểm tra toàn bộ công thức.</p>
      <div className="mt-5 space-y-3">
        {suggestions.map((item) => (
          <label key={item.ingredient_id} className="flex cursor-pointer items-start gap-3 rounded-xl border border-line bg-card p-4">
            <input type="checkbox" className="mt-1 size-4 accent-action" checked={accepted.includes(item.ingredient_id)} onChange={() => toggle(item.ingredient_id)} />
            <span><strong className="block text-strong">{name(item.ingredient_id)} · {item.amount} {item.unit}</strong><span className="mt-1 block text-sm leading-5 text-muted">{item.reason}</span></span>
          </label>
        ))}
      </div>
      <div className="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
        <Button onClick={cancel}>Hủy đề xuất</Button>
        <Button variant="primary" onClick={() => confirm(accepted)}>Xác nhận và kiểm tra lại</Button>
      </div>
    </section>
  );
}
