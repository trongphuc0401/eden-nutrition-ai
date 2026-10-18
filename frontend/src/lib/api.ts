import type { Ingredient, Profile, SessionUser } from "./types";
import { defaultProfile, ingredients } from "./demo-data";

// Same-origin by default: next.config.ts proxies /api/* to the backend.
export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "/api";
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

export const googleLoginUrl = `${apiUrl}/v1/auth/google/login`;

/** The signed-in user, or null when there is no session (HTTP 401). */
export async function getSession(): Promise<SessionUser | null> {
  if (demoMode) return null;
  const response = await fetch(`${apiUrl}/v1/auth/me`, { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Không thể kiểm tra phiên đăng nhập.");
  const body = await response.json() as { user: SessionUser };
  return body.user;
}

export async function logout(): Promise<void> {
  await fetch(`${apiUrl}/v1/auth/logout`, { method: "POST", credentials: "include" });
}

export async function getIngredients(month: number, hometown?: string): Promise<Ingredient[]> {
  if (demoMode) return ingredients;
  // hometown selects the climate zone (north / central / south) used for "đang mùa"
  const region = hometown ? `&hometown=${encodeURIComponent(hometown)}` : "";
  const response = await request<{ items: Array<Omit<Ingredient, "emoji">> }>(`/v1/ingredients?month=${month}${region}`);
  return response.items.map((item) => ({ ...item, emoji: "🍊" }));
}

export const appMode = demoMode ? "demo" : "live";
export function restoreProfile(): Profile | null { try { const raw = localStorage.getItem("fresh-citrus.profile-draft"); return raw ? { ...defaultProfile, ...JSON.parse(raw) as Profile } : null; } catch { return null; } }
export function persistProfile(profile: Profile): void { localStorage.setItem("fresh-citrus.profile-draft", JSON.stringify(profile)); }
