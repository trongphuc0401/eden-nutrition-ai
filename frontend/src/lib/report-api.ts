import type { GenerationInput } from "./contracts";
import type { PendingConfirmation, RecipeProposal, Report } from "./types";
import { demoReport } from "./demo-data";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const demoMode = process.env.NEXT_PUBLIC_APP_MODE !== "live";

type Created = { report_id: string; thread_id: string; run_id: string; status: string };
type ReportDocument = {
  report_id: string;
  created_at: string;
  title: string;
  ingredients: Array<{ name: string; amount: number; unit: string }>;
  preparation_steps: string[];
  warning: string;
  summary: string;
  totals: { calories: number | null; protein: number | null; carbohydrate: number | null; fat: number | null; fiber: number | null; sugar: number | null };
  sources: string[];
  data_coverage: number;
  decision: "pass" | "review" | "reject";
  quality_label?: string;
  ai_metadata?: { ai_provider?: string; ai_model?: string };
};
type Status = Created & {
  current_node?: string;
  error?: string;
  warning?: string;
  report?: ReportDocument;
  pdf_url?: string;
  proposal?: RecipeProposal;
  confirmation_required?: boolean;
};

export type ReportOutcome = { kind: "report"; report: Report } | { kind: "confirmation"; pending: PendingConfirmation };

const terminal = new Set(["completed", "review", "rejected", "failed", "cancelled", "awaiting_confirmation"]);
const nodeStep: Record<string, number> = {
  validate_request: 0,
  analyze_profile: 0,
  retrieve_ingredient_data: 1,
  generate_recipe: 2,
  calculate_nutrition: 3,
  safety_and_quality_gate: 4,
  compose_report: 5,
  compose_report_with_warning: 5,
  render_pdf: 6,
  finalize: 6,
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { credentials: "include", ...init });
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as { detail?: string | { message?: string } } | null;
    const detail = typeof problem?.detail === "string" ? problem.detail : problem?.detail?.message;
    throw new Error(detail ?? "Không thể kết nối với dịch vụ report.");
  }
  return response.json() as Promise<T>;
}

function toReport(status: Status): Report {
  const document = status.report;
  if (!document) throw new Error(status.error ?? "Workflow kết thúc nhưng chưa có report.");
  return {
    id: document.report_id,
    name: document.title,
    createdAt: new Date(document.created_at).toLocaleString("vi-VN"),
    saved: false,
    decision: document.decision,
    ingredients: document.ingredients.map((item) => ({
      name: item.name,
      amount: `${item.amount} ${item.unit}`,
      purpose: "Nguyên liệu do người dùng chọn; số liệu truy xuất từ nguồn trên 100 g",
      used: true,
    })),
    nutrition: {
      calories: document.totals.calories,
      protein: document.totals.protein,
      carbs: document.totals.carbohydrate,
      fat: document.totals.fat,
      fiber: document.totals.fiber,
      sugar: document.totals.sugar,
    },
    steps: document.preparation_steps,
    tools: ["Máy xay", "Cân nhà bếp", "Ly định lượng"],
    reason: document.summary,
    warning: [document.warning, document.quality_label].filter(Boolean).join(" "),
    sources: document.sources,
    version: 1,
    pdfUrl: status.pdf_url ? `${apiUrl}${status.pdf_url}` : undefined,
    threadId: status.thread_id,
    runId: status.run_id,
    dataCoverage: document.data_coverage,
    qualityLabel: document.quality_label,
    aiProvider: document.ai_metadata?.ai_provider,
    aiModel: document.ai_metadata?.ai_model,
  };
}

async function waitForResult(reportId: string, onProgress: (step: number) => void, signal?: AbortSignal): Promise<ReportOutcome> {
  while (true) {
    if (signal?.aborted) throw new DOMException("Đã dừng tạo report", "AbortError");
    const status = await json<Status>(`/v1/reports/${reportId}`);
    if (status.current_node) onProgress(nodeStep[status.current_node] ?? 0);
    if (terminal.has(status.status)) {
      if (status.status === "completed" || status.status === "review") return { kind: "report", report: toReport(status) };
      if (status.status === "awaiting_confirmation" && status.proposal) {
        return { kind: "confirmation", pending: { reportId, proposal: status.proposal } };
      }
      throw new Error(status.error ?? `Workflow kết thúc với trạng thái ${status.status}.`);
    }
    await new Promise((resolve) => window.setTimeout(resolve, 350));
  }
}

export async function generateReport(
  payload: GenerationInput,
  onProgress: (step: number) => void,
  signal?: AbortSignal,
): Promise<ReportOutcome> {
  if (demoMode) {
    for (let step = 0; step < 7; step += 1) {
      if (signal?.aborted) throw new DOMException("Đã dừng tạo report", "AbortError");
      onProgress(step);
      await new Promise((resolve) => window.setTimeout(resolve, 180));
    }
    return { kind: "report", report: { ...demoReport, id: crypto.randomUUID(), createdAt: "Vừa xong" } };
  }
  const body = {
    profile: {
      age: payload.profile.age,
      gender: payload.profile.gender,
      height_cm: payload.profile.heightCm,
      weight_kg: payload.profile.weightKg,
      goal: "overweight_obesity_weight_management",
      allergies: payload.profile.allergies,
      preferred_food_types: payload.profile.preferences,
      disliked_ingredients: payload.profile.dislikes,
      medical_notes: payload.profile.notes,
      health_restriction_status: payload.profile.healthRestrictionStatus,
    },
    ingredientIds: payload.ingredientIds,
    servings: payload.servings,
    prompt: payload.prompt ?? "",
    locale: payload.locale,
  };
  const created = await json<Created>("/v1/reports", {
    method: "POST", headers: { "Content-Type": "application/json", "Idempotency-Key": crypto.randomUUID() }, body: JSON.stringify(body),
  });
  const cancel = () => void json(`/v1/reports/${created.report_id}/cancel`, { method: "POST" }).catch(() => undefined);
  signal?.addEventListener("abort", cancel, { once: true });
  try {
    return await waitForResult(created.report_id, onProgress, signal);
  } finally {
    signal?.removeEventListener("abort", cancel);
  }
}

export async function confirmReport(
  pending: PendingConfirmation,
  acceptedIngredientIds: string[],
  onProgress: (step: number) => void,
  signal?: AbortSignal,
): Promise<ReportOutcome> {
  await json<Status>(`/v1/reports/${pending.reportId}/confirmation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ proposal_version: pending.proposal.version, accepted_ingredient_ids: acceptedIngredientIds }),
  });
  return waitForResult(pending.reportId, onProgress, signal);
}

export async function cancelPendingReport(reportId: string): Promise<void> {
  await json(`/v1/reports/${reportId}/cancel`, { method: "POST" });
}
