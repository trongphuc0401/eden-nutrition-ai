import type { GenerationInput } from "./contracts";
import type { PendingConfirmation, Profile, RecipeProposal, Report } from "./types";
import { apiUrl, httpErrorMessage, NETWORK_ERROR } from "./api";
import { buildReportDetail, type DocumentDetail } from "./report-detail";

type Created = { report_id: string; thread_id: string; run_id: string; status: string };
type ReportDocument = DocumentDetail & {
  report_id: string;
  created_at: string;
  title: string;
  ingredients: DocumentDetail["ingredients"];
  preparation_steps: string[];
  warning: string;
  summary: string;
  totals: { calories: number | null; protein: number | null; carbohydrate: number | null; fat: number | null; fiber: number | null; sugar: number | null; sodium?: number | null };
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

/** Profile in the backend's snake_case shape (shared by /v1/reports and /v1/chat). */
export function toApiProfile(profile: Profile) {
  return {
    age: profile.age,
    gender: profile.gender,
    height_cm: profile.heightCm,
    weight_kg: profile.weightKg,
    goal: "overweight_obesity_weight_management",
    allergies: profile.allergies,
    preferred_food_types: profile.preferences,
    disliked_ingredients: profile.dislikes,
    medical_notes: profile.notes,
    health_restriction_status: profile.healthRestrictionStatus,
    activity_level: profile.activityLevel,
    hometown: profile.hometown,
  };
}

export type ReportOutcome = { kind: "report"; report: Report } | { kind: "confirmation"; pending: PendingConfirmation };

const terminal = new Set(["completed", "review", "rejected", "failed", "cancelled", "awaiting_confirmation"]);
const nodeStep: Record<string, number> = {
  validate_request: 0,
  analyze_profile: 0,
  retrieve_ingredient_data: 1,
  generate_recipe: 2,
  calculate_nutrition: 3,
  adjust_recipe_amounts: 3,
  safety_and_quality_gate: 4,
  compose_report: 5,
  compose_report_with_warning: 5,
  render_pdf: 6,
  finalize: 6,
};

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { credentials: "include", ...init }).catch((error: unknown) => {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw new Error(NETWORK_ERROR);
  });
  if (!response.ok) {
    const problem = await response.json().catch(() => null) as { detail?: string | { message?: string } } | null;
    const detail = typeof problem?.detail === "string" ? problem.detail : problem?.detail?.message;
    throw new Error(httpErrorMessage(response.status, detail));
  }
  return response.json() as Promise<T>;
}

function toReport(status: Status): Report {
  const document = status.report;
  if (!document) throw new Error(status.error ?? "Workflow kết thúc nhưng chưa có báo cáo.");
  return {
    id: document.report_id,
    name: document.title,
    createdAt: new Date(document.created_at).toLocaleString("vi-VN"),
    saved: false,
    decision: document.decision,
    ingredients: document.ingredients.map((item) => ({
      name: item.name,
      amount: `${item.amount} ${item.unit}`,
      purpose: item.substitution_for
        ? `Thay ${item.substitution_for} · ${item.source_label ?? "số liệu trên 100 g"}`
        : item.source_label ?? "Số liệu truy xuất từ nguồn trên 100 g",
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
    detail: buildReportDetail(document),
  };
}

/** Poll fast while the workflow is usually busy, then back off; give up well after a stuck job could recover. */
const FAST_POLL_MS = 350;
const SLOW_POLL_MS = 1500;
const FAST_POLL_WINDOW_MS = 15_000;
const MAX_WAIT_MS = 6 * 60_000;

async function waitForResult(reportId: string, onProgress: (step: number) => void, signal?: AbortSignal): Promise<ReportOutcome> {
  const startedAt = Date.now();
  while (true) {
    if (signal?.aborted) throw new DOMException("Đã dừng tạo báo cáo", "AbortError");
    const elapsed = Date.now() - startedAt;
    if (elapsed > MAX_WAIT_MS) {
      throw new Error("Report đang xử lý lâu hơn bình thường nên đã ngừng chờ. Lựa chọn của bạn vẫn được giữ, bạn có thể thử lại.");
    }
    const status = await json<Status>(`/v1/reports/${reportId}`);
    if (status.current_node) onProgress(nodeStep[status.current_node] ?? 0);
    if (terminal.has(status.status)) {
      if (status.status === "completed" || status.status === "review") return { kind: "report", report: toReport(status) };
      if (status.status === "awaiting_confirmation" && status.proposal) {
        return { kind: "confirmation", pending: { reportId, proposal: status.proposal } };
      }
      throw new Error(status.error ?? `Workflow kết thúc với trạng thái ${status.status}.`);
    }
    await new Promise((resolve) => window.setTimeout(resolve, elapsed < FAST_POLL_WINDOW_MS ? FAST_POLL_MS : SLOW_POLL_MS));
  }
}

export async function generateReport(
  payload: GenerationInput,
  onProgress: (step: number) => void,
  signal?: AbortSignal,
): Promise<ReportOutcome> {
  const body = {
    profile: toApiProfile(payload.profile),
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

export async function fetchReport(reportId: string): Promise<Report | null> {
  try {
    const status = await json<Status>(`/v1/reports/${encodeURIComponent(reportId)}`);
    if (status.status === "completed" || status.status === "review") {
      return toReport(status);
    }
    return null;
  } catch {
    return null;
  }
}
