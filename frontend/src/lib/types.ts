export type GenerationStatus = "idle" | "generating" | "completed" | "review" | "blocked" | "error" | "stopped";

export type Profile = {
  age: number; gender: string; heightCm: number; weightKg: number; hometown: string;
  allergies: string[]; dislikes: string[]; preferences: string[]; notes: string;
};

export type Ingredient = { id: string; name: string; emoji: string; seasonal: "in" | "out" | "unknown"; region: string; kind: "fruit" | "support" };

export type Report = {
  id: string; name: string; createdAt: string; saved: boolean; decision: "pass" | "review";
  ingredients: { name: string; amount: string; purpose: string; used: boolean }[];
  nutrition: { calories: number | null; protein: number | null; carbs: number | null; fat: number | null; fiber: number | null; sugar: number | null };
  steps: string[]; tools: string[]; reason: string; warning: string; sources: string[]; version: number;
};
