import type { GenerationInput } from "./contracts";
import type { Ingredient, Profile, Report } from "./types";
import { defaultProfile, demoReport, ingredients } from "./demo-data";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const demoMode = process.env.NEXT_PUBLIC_APP_MODE !== "live";

type AuthConfiguration = { google_enabled: boolean; redirect_uri: string; message: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { credentials: "include", ...init });
  if (!response.ok) throw new Error("Không thể kết nối với dịch vụ. Vui lòng thử lại.");
  return response.json() as Promise<T>;
}

export async function getAuthConfiguration(): Promise<AuthConfiguration> {
  if (demoMode) return { google_enabled: false, redirect_uri: "", message: "Demo local đang bật." };
  return request<AuthConfiguration>("/v1/auth/configuration");
}

export async function generateRecipe(payload: GenerationInput): Promise<Report> {
  if (demoMode) { await new Promise((resolve) => setTimeout(resolve, 2800)); return { ...demoReport, id: crypto.randomUUID(), createdAt: "Vừa xong" }; }
  return request<Report>("/v1/generations", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
}

export async function getIngredients(month: number): Promise<Ingredient[]> {
  if (demoMode) return ingredients;
  const response = await request<{ items: Array<Omit<Ingredient, "emoji">> }>(`/v1/ingredients?month=${month}`);
  return response.items.map((item) => ({ ...item, emoji: "🍊" }));
}

export const appMode = demoMode ? "demo" : "live";
export function restoreProfile(): Profile | null { try { const raw = localStorage.getItem("fresh-citrus.profile-draft"); return raw ? { ...defaultProfile, ...JSON.parse(raw) as Profile } : null; } catch { return null; } }
export function persistProfile(profile: Profile): void { localStorage.setItem("fresh-citrus.profile-draft", JSON.stringify(profile)); }
