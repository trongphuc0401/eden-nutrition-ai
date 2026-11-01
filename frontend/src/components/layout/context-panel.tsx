import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { IngredientAvatar } from "@/features/workspace/ingredient-avatar";
import type { Ingredient, Profile } from "@/lib/types";

type Props = { profile: Profile; selected: Ingredient[]; openSelector: () => void; createReport: () => void; busy: boolean };

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-line bg-cream p-4">
      <div className="mb-2 flex items-center justify-between gap-2"><h3 className="text-sm font-semibold text-strong">{title}</h3>{action}</div>
      {children}
    </section>
  );
}

function EditButton({ label, onClick }: { label: string; onClick: () => void }) {
  return <Button variant="ghost" size="sm" icon onClick={onClick} aria-label={label} title={label}><Icon name="pencil" className="size-4" /></Button>;
}

/** Chosen ingredients and notes the AI is using. */
export function ContextPanelBody({ profile, selected, openSelector, createReport, busy }: Props) {
  return (
    <div className="space-y-3">
      <Section title={`Nguyên liệu đã chọn (${selected.length})`} action={<EditButton label="Chỉnh sửa nguyên liệu" onClick={openSelector} />}>
        <p className="mb-2 flex items-center gap-1 text-xs text-muted"><Icon name="mapPin" className="size-3.5" />{profile.hometown} · Tháng {new Date().getMonth() + 1}</p>
        {selected.length ? (
          <ul className="flex flex-wrap gap-1.5">{selected.map((item) => <li key={item.id} className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card py-1 pl-1 pr-2 text-sm"><IngredientAvatar ingredient={item} size="sm" />{item.name}</li>)}</ul>
        ) : <p className="text-sm text-muted">Chưa chọn nguyên liệu nào.</p>}
        <div className="mt-3 flex flex-col gap-2">
          {selected.length > 0
            ? <Button size="sm" className="w-full" onClick={createReport} disabled={busy}>Tạo báo cáo với nguyên liệu này</Button>
            : <Button size="sm" className="w-full" onClick={openSelector}>Mở danh mục nguyên liệu</Button>}
        </div>
      </Section>
      <Section title="Lưu ý khác">
        <ul className="flex flex-wrap gap-1.5">
          {profile.allergies.map((item) => <li key={item} className="rounded-lg border border-coral-line bg-card px-2 py-1 text-sm text-coral-strong">Dị ứng: {item}</li>)}
          {profile.dislikes.map((item) => <li key={item} className="rounded-lg border border-line bg-card px-2 py-1 text-sm text-muted">Không thích: {item}</li>)}
        </ul>
        {!profile.allergies.length && !profile.dislikes.length && <p className="text-sm text-muted">Không có lưu ý đặc biệt.</p>}
      </Section>
    </div>
  );
}

export function ContextPanelHeader({ titleId, trailing }: { titleId: string; trailing?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-2 border-b border-line bg-warm px-4 py-3">
      <h2 id={titleId} className="text-base font-semibold text-strong">Thông tin & ngữ cảnh</h2>
      {trailing}
    </div>
  );
}

/** Desktop (lg+): pinned column beside the workspace. Below lg it lives in a drawer (see page). */
export function ContextPanel(props: Props) {
  return (
    <aside aria-labelledby="context-title" className="hidden w-80 shrink-0 self-start overflow-hidden rounded-card border border-line bg-card shadow-card lg:sticky lg:top-0 lg:block">
      <ContextPanelHeader titleId="context-title" trailing={<span className="text-subtle" title="Luôn hiển thị khi bạn cuộn"><Icon name="pin" className="size-4" label="Ghim cố định" /></span>} />
      <div className="max-h-[calc(100dvh-11rem)] overflow-y-auto p-4"><ContextPanelBody {...props} /></div>
    </aside>
  );
}
