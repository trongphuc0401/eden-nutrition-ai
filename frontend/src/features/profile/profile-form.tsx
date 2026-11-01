"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Field, NumberField, SelectField } from "@/components/ui/field";
import { Icon } from "@/components/ui/icon";
import { MultiCombobox } from "@/components/ui/multi-combobox";
import type { CatalogStatus } from "@/features/workspace/ingredient-picker";
import { getAllergens, type AllergenOption } from "@/lib/api";
import { bmi, BMI_SCOPE_MIN, profileSummary } from "@/lib/profile";
import type { Ingredient, Profile } from "@/lib/types";

const STEPS = [
  { title: "Thông tin cơ thể", copy: "Giúp AI tạo công thức phù hợp hơn. Bạn luôn có thể sửa sau." },
  { title: "Dị ứng & ghi chú", copy: "Xác nhận rõ giúp hệ thống không tự suy đoán rủi ro sức khỏe." },
  { title: "Khẩu vị & quê quán", copy: "Dùng để ưu tiên nguyên liệu đang mùa ở khu vực của bạn." },
  { title: "Xem lại hồ sơ", copy: "Kiểm tra lần cuối trước khi lưu." },
];
const toOptions = (values: string[]) => values.map((value) => ({ value, label: value }));

type Props = {
  profile: Profile; catalog: Ingredient[]; catalogStatus: CatalogStatus; onRetryCatalog: () => void;
  save: (profile: Profile) => void; cancel: () => void; onboarding: boolean;
};

export function ProfileForm({ profile, catalog, catalogStatus, onRetryCatalog, save, cancel, onboarding }: Props) {
  const [draft, setDraft] = useState(profile);
  const [step, setStep] = useState(0);
  const [allergens, setAllergens] = useState<AllergenOption[]>([]);
  const [allergenStatus, setAllergenStatus] = useState<CatalogStatus>("loading");
  const [allergenAttempt, setAllergenAttempt] = useState(0);
  const set = <K extends keyof Profile>(key: K, value: Profile[K]) => setDraft((old) => ({ ...old, [key]: value }));
  const canContinue = step === 0 ? draft.age >= 18 && draft.heightCm >= 100 && draft.weightKg > 25 && Boolean(draft.gender)
    : step === 2 ? Boolean(draft.hometown) : true;

  useEffect(() => {
    let cancelled = false;
    getAllergens()
      .then((items) => { if (!cancelled) { setAllergens(items); setAllergenStatus("ready"); } })
      .catch(() => { if (!cancelled) setAllergenStatus("error"); });
    return () => { cancelled = true; };
  }, [allergenAttempt]);

  // Every option list comes from the API: allergies from health_conditions, ingredients from the live catalog.
  const allergenOptions = allergens.map((item) => ({ value: item.label, label: item.label }));
  const ingredientOptions = (exclude: string[]) => catalog.filter((item) => !exclude.includes(item.name))
    .map((item) => ({ value: item.name, label: item.name, hint: item.kind === "fruit" ? item.region : "Nguyên liệu phụ" }));
  const catalogProps = { status: catalogStatus, onRetry: onRetryCatalog };
  const last = step === STEPS.length - 1;

  return (
    <section className="soft-card mx-auto w-full max-w-3xl overflow-hidden" aria-labelledby="profile-step-title">
      <div className="border-b border-line bg-cream p-5 sm:p-6">
        <p className="text-sm font-semibold text-action">Bước {step + 1}/{STEPS.length}</p>
        <div className="mt-2 flex gap-1.5" aria-hidden="true">{STEPS.map((item, index) => <span key={item.title} className={`h-1.5 flex-1 rounded-full ${index <= step ? "bg-brand" : "bg-line"}`} />)}</div>
        <h2 id="profile-step-title" className="mt-4 text-2xl font-semibold text-strong">{STEPS[step].title}</h2>
        <p className="mt-1 text-sm text-muted">{STEPS[step].copy}</p>
      </div>

      <div className="min-h-80 p-5 sm:p-6">
        {step === 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            <NumberField label="Tuổi" min={18} value={draft.age} onChange={(value) => set("age", value)} />
            <SelectField label="Giới tính" value={draft.gender} options={toOptions(["Nữ", "Nam", "Khác"])} onChange={(value) => set("gender", value)} />
            <NumberField label="Chiều cao (cm)" min={100} value={draft.heightCm} onChange={(value) => set("heightCm", value)} />
            <NumberField label="Cân nặng (kg)" min={26} value={draft.weightKg} onChange={(value) => set("weightKg", value)} />
            <p className="text-sm text-muted sm:col-span-2">BMI ước tính: <strong className="text-strong">{bmi(draft) ? bmi(draft).toFixed(1) : "—"}</strong>. Phiên bản thử nghiệm hiện phục vụ người trưởng thành có BMI ≥ {BMI_SCOPE_MIN}.</p>
          </div>
        )}
        {step === 1 && (
          <div className="space-y-5">
            <MultiCombobox label="Dị ứng" help="Gõ để tìm và chọn các dị ứng của bạn. Chỉ để trống khi bạn chưa chắc." placeholder="Tìm dị ứng, ví dụ: đậu nành"
              options={allergenOptions} values={draft.allergies} onChange={(value) => set("allergies", value)}
              status={allergenStatus} onRetry={() => { setAllergenStatus("loading"); setAllergenAttempt((attempt) => attempt + 1); }} />
            <Field label="Ghi chú sức khỏe" help="Kết quả có ghi chú hoặc chưa xác nhận sẽ được đánh dấu cần xem xét. Đây không phải chẩn đoán.">
              {(id, helpId) => <textarea id={id} aria-describedby={helpId} className="field min-h-28" value={draft.notes} onChange={(event) => set("notes", event.target.value)} placeholder="Ví dụ: cần theo dõi đường huyết..." />}
            </Field>
          </div>
        )}
        {step === 2 && (
          <div className="space-y-5">
            <MultiCombobox label="Nguyên liệu ưa thích" help="AI sẽ ưu tiên các nguyên liệu này khi phù hợp." placeholder="Tìm nguyên liệu, ví dụ: ổi"
              options={ingredientOptions(draft.dislikes)} values={draft.preferences} onChange={(value) => set("preferences", value)} {...catalogProps} />
            <MultiCombobox label="Nguyên liệu không thích" help="AI sẽ tránh dùng các nguyên liệu này." placeholder="Tìm nguyên liệu, ví dụ: chuối"
              options={ingredientOptions(draft.preferences)} values={draft.dislikes} onChange={(value) => set("dislikes", value)} {...catalogProps} />
            <SelectField label="Quê quán" help="Khu vực này được ưu tiên khi gợi ý nguyên liệu đang mùa." value={draft.hometown}
              options={toOptions(["TP. Hồ Chí Minh", "Hà Nội", "Nghệ An", "Cần Thơ", "Đà Nẵng"])} onChange={(value) => set("hometown", value)} />
          </div>
        )}
        {step === 3 && (
          <dl className="space-y-3">
            <ReviewRow label="Cơ thể" value={profileSummary(draft)} />
            <ReviewRow label="Dị ứng" value={draft.allergies.join(", ") || "Chưa xác nhận"} />
            <ReviewRow label="Ưa thích" value={draft.preferences.join(", ") || "Chưa có"} />
            <ReviewRow label="Không thích" value={draft.dislikes.join(", ") || "Không có"} />
            <ReviewRow label="Quê quán" value={draft.hometown} />
            <ReviewRow label="Ghi chú" value={draft.notes || "Không có"} />
          </dl>
        )}
      </div>

      <div className="flex flex-col-reverse gap-3 border-t border-line p-5 sm:flex-row sm:justify-between sm:p-6">
        {step === 0
          ? (onboarding ? <span /> : <Button onClick={cancel}>Hủy</Button>)
          : <Button onClick={() => setStep(step - 1)}><Icon name="chevronLeft" className="size-4" />Quay lại</Button>}
        <Button variant="primary" disabled={!canContinue} onClick={() => last ? save(draft) : setStep(step + 1)}>{last ? "Lưu hồ sơ" : "Tiếp tục"}</Button>
      </div>
    </section>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-line bg-cream p-4"><dt className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</dt><dd className="mt-1 text-sm font-semibold text-strong">{value}</dd></div>;
}
