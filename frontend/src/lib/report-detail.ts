/** Builds the personalised report view-model from the backend NutritionReportDocument. Pure, no React. */

export type NutrientKey = "calories" | "protein" | "carbohydrate" | "fat" | "fiber" | "sugar" | "sodium";
export type SeasonStatus = "in_season" | "year_round" | "out_of_season" | "not_seasonal" | "unknown";
export type RangeStatus = "in" | "slightly_high" | "high" | "low" | "unknown";
export type StepKind = "wash" | "peel" | "cut" | "soak" | "weigh" | "add" | "blend" | "rest" | "pour" | "other";

type Totals = Partial<Record<NutrientKey, number | null>>;

export type DocumentThreshold = { nutrient: string; value: number | null; unit: string; minimum?: number | null; maximum?: number | null; status: "pass" | "review" | "unknown" };
export type DocumentRange = { nutrient: string; unit: string; minimum?: number | null; maximum?: number | null; basis: string };
export type DocumentIngredient = {
  ingredient_id?: string; name: string; amount: number; unit: string; source_label?: string | null;
  season?: { status: SeasonStatus; months: number[] } | null; substitution_for?: string | null;
};

/** The new (optional) fields of NutritionReportDocument. Older reports omit them. */
export type DocumentDetail = {
  created_at: string;
  totals: Totals;
  ingredients: DocumentIngredient[];
  ingredient_nutrition?: { ingredient_id: string; name: string; nutrition: Totals }[];
  thresholds?: DocumentThreshold[];
  reference_ranges?: DocumentRange[];
  profile_snapshot?: { gender?: string | null; age?: number | null; bmi?: number | null; bmi_category?: string | null; allergies?: string[]; preferences?: string[]; dislikes?: string[] } | null;
  scores?: { personal_fit?: { value: number; breakdown: { label: string; points: number }[] } | null; seasonal?: number | null; season_month?: number | null } | null;
  allergen_check?: { checked: string[]; conflicts: string[]; checked_ingredients: number } | null;
  steps?: { title: string; detail: string; minutes: number | null; kind: string }[];
  prep_minutes?: number | null;
  serving_ml?: number | null;
  meal_context?: string | null;
  servings?: number;
  assumptions?: string[];
  missing_data?: string[];
  data_checks?: string[];
  disclaimer?: string;
};

export type NutrientRow = {
  key: NutrientKey; label: string; unit: string; value: number | null;
  min: number | null; max: number | null; status: RangeStatus; basis: string | null;
};

export type ReportDetail = {
  createdAtIso: string;
  month: number;
  servings: number;
  servingMl: number | null;
  mealContext: string | null;
  prepMinutes: number | null;
  profile: NonNullable<DocumentDetail["profile_snapshot"]> | null;
  personalFit: { value: number; breakdown: { label: string; points: number }[] } | null;
  seasonalScore: number | null;
  allergen: { checked: string[]; conflicts: string[]; checkedIngredients: number } | null;
  steps: { title: string; detail: string; minutes: number | null; kind: StepKind }[];
  nutrients: NutrientRow[];
  ingredients: { name: string; amount: number; unit: string; kcal: number | null; season: { status: SeasonStatus; months: number[] }; substitutionFor: string | null }[];
  assumptions: string[];
  missingData: string[];
  dataChecks: string[];
  disclaimer: string | null;
};

export const NUTRIENTS: { key: NutrientKey; label: string; unit: string; aliases: string[] }[] = [
  { key: "calories", label: "Năng lượng", unit: "kcal", aliases: ["năng lượng", "calories", "energy", "kcal"] },
  { key: "carbohydrate", label: "Tinh bột (carb)", unit: "g", aliases: ["carb", "tinh bột", "glucid"] },
  { key: "protein", label: "Đạm", unit: "g", aliases: ["protein", "đạm"] },
  { key: "fat", label: "Chất béo", unit: "g", aliases: ["chất béo", "fat", "lipid"] },
  { key: "fiber", label: "Chất xơ", unit: "g", aliases: ["xơ", "fiber", "celluloza"] },
  { key: "sugar", label: "Đường tổng", unit: "g", aliases: ["đường", "sugar"] },
  { key: "sodium", label: "Natri", unit: "mg", aliases: ["natri", "sodium"] },
];

const STEP_KINDS = new Set<StepKind>(["wash", "peel", "cut", "soak", "weigh", "add", "blend", "rest", "pour"]);
/** How far above the range still counts as "slightly high" (20 %). */
const SLIGHT_MARGIN = 0.2;

export function nutrientKey(label: string): NutrientKey | null {
  const lower = label.toLowerCase();
  if ((NUTRIENTS.map((n) => n.key) as string[]).includes(lower)) return lower as NutrientKey;
  return NUTRIENTS.find((n) => n.aliases.some((alias) => lower.includes(alias)))?.key ?? null;
}

export function rangeStatus(value: number | null, min: number | null, max: number | null): RangeStatus {
  if (value === null || (min === null && max === null)) return "unknown";
  if (max !== null && value > max) return value <= max * (1 + SLIGHT_MARGIN) ? "slightly_high" : "high";
  if (min !== null && value < min) return "low";
  return "in";
}

function round(value: number | null | undefined, digits = 1): number | null {
  if (value === null || value === undefined || Number.isNaN(value)) return null;
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function buildNutrients(document: DocumentDetail): NutrientRow[] {
  const thresholds = new Map<NutrientKey, DocumentThreshold>();
  for (const item of document.thresholds ?? []) {
    const key = nutrientKey(item.nutrient);
    // percent-of-energy rules use "%" and cannot be drawn on a gram axis
    if (key && item.unit !== "%" && !thresholds.has(key)) thresholds.set(key, item);
  }
  const ranges = new Map<NutrientKey, DocumentRange>();
  for (const item of document.reference_ranges ?? []) {
    const key = nutrientKey(item.nutrient);
    if (key) ranges.set(key, item);
  }
  return NUTRIENTS.map(({ key, label, unit }) => {
    const value = round(document.totals[key]);
    // the personal / energy-share range is more specific; the research threshold fills what it does not bound
    const range = ranges.get(key);
    const threshold = thresholds.get(key);
    const min = range?.minimum ?? threshold?.minimum ?? null;
    const max = range?.maximum ?? threshold?.maximum ?? null;
    const basis = range?.basis ?? (threshold ? "Mức khuyến nghị cho bữa phụ" : null);
    return { key, label, unit, value, min, max, status: rangeStatus(value, min, max), basis };
  });
}

/** Returns null for reports created before the backend sent the personalised fields. */
export function buildReportDetail(document: DocumentDetail): ReportDetail | null {
  if (!document.scores && !document.profile_snapshot && !document.steps?.length) return null;
  const kcalByName = new Map((document.ingredient_nutrition ?? []).map((row) => [row.name, row.nutrition.calories ?? null]));
  const created = new Date(document.created_at);
  return {
    createdAtIso: document.created_at,
    month: document.scores?.season_month ?? created.getMonth() + 1,
    servings: document.servings ?? 1,
    servingMl: document.serving_ml ?? null,
    mealContext: document.meal_context ?? null,
    prepMinutes: document.prep_minutes ?? null,
    profile: document.profile_snapshot ?? null,
    personalFit: document.scores?.personal_fit ?? null,
    seasonalScore: document.scores?.seasonal ?? null,
    allergen: document.allergen_check
      ? { checked: document.allergen_check.checked, conflicts: document.allergen_check.conflicts, checkedIngredients: document.allergen_check.checked_ingredients }
      : null,
    steps: (document.steps ?? []).map((step) => ({ ...step, kind: STEP_KINDS.has(step.kind as StepKind) ? (step.kind as StepKind) : "other" })),
    nutrients: buildNutrients(document),
    ingredients: document.ingredients.map((item) => ({
      name: item.name,
      amount: item.amount / Math.max(document.servings ?? 1, 1),
      unit: item.unit,
      kcal: round(kcalByName.get(item.name), 0),
      season: item.season ?? { status: "unknown", months: [] },
      substitutionFor: item.substitution_for ?? null,
    })),
    assumptions: document.assumptions ?? [],
    missingData: document.missing_data ?? [],
    dataChecks: document.data_checks ?? [],
    disclaimer: document.disclaimer ?? null,
  };
}

/** Share of the reference for the balance chart: the upper limit, or the minimum for floor-only nutrients. */
export function referenceShare(row: NutrientRow): number | null {
  const reference = row.max ?? row.min;
  if (row.value === null || !reference) return null;
  return Math.round((row.value / reference) * 100);
}

export function seasonLabel(status: SeasonStatus): string {
  if (status === "year_round") return "Có quanh năm";
  if (status === "in_season") return "Đang vào mùa";
  if (status === "out_of_season") return "Trái vụ";
  if (status === "not_seasonal") return "Không theo mùa";
  return "Chưa có lịch mùa";
}
