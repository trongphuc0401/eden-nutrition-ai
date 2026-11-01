import type { ReportDetail } from "./report-detail";

export type GenerationStatus = "idle" | "generating" | "completed" | "review" | "blocked" | "error" | "stopped";

export type ActivityLevel = "sedentary" | "light" | "moderate" | "active";

export type Profile = {
  age: number; gender: string; heightCm: number; weightKg: number; hometown: string;
  allergies: string[]; dislikes: string[]; preferences: string[]; notes: string;
  activityLevel: ActivityLevel;
  healthRestrictionStatus: "no" | "yes" | "unknown";
};

// Served by GET /v1/ingredients (reference data in Supabase); never hardcoded in the UI.
export type Ingredient = { id: string; name: string; seasonal: "in" | "out" | "unknown"; region: string; kind: "fruit" | "support"; season_months?: number[]; source?: string };

export type Report = {
  id: string; name: string; createdAt: string; saved: boolean; decision: "pass" | "review" | "reject";
  ingredients: { name: string; amount: string; purpose: string; used: boolean }[];
  nutrition: { calories: number | null; protein: number | null; carbs: number | null; fat: number | null; fiber: number | null; sugar: number | null };
  steps: string[]; tools: string[]; reason: string; warning: string; sources: string[]; version: number;
  pdfUrl?: string; threadId?: string; runId?: string; dataCoverage?: number;
  qualityLabel?: string; aiProvider?: string; aiModel?: string;
  /** Personalised analysis (scores, ranges, seasons). Missing on reports made before it existed. */
  detail?: ReportDetail | null;
};

export type RecipeProposal = {
  version: number; title: string;
  ingredients: { ingredient_id: string; amount: number; unit: "g" | "ml"; reason: string }[];
  suggested_ingredient_ids: string[];
  omitted_selected: { ingredient_id: string; reason: string }[];
  rationale: string;
};

export type PendingConfirmation = {
  reportId: string;
  proposal: RecipeProposal;
};

export type SessionUser = { id: string; email: string | null; name: string | null; avatar_url: string | null };
