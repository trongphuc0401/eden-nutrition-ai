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
const PROFILE_COMPLETED_KEY = "fresh-citrus.profile-completed";

export function isProfileCompleted(userId?: string): boolean {
  try {
    const key = userId ? `${PROFILE_COMPLETED_KEY}-${userId}` : PROFILE_COMPLETED_KEY;
    return localStorage.getItem(key) === "true";
  } catch {
    return false;
  }
}

export function markProfileCompleted(userId?: string): void {
  try {
    const key = userId ? `${PROFILE_COMPLETED_KEY}-${userId}` : PROFILE_COMPLETED_KEY;
    localStorage.setItem(key, "true");
  } catch { /* storage unavailable */ }
}

export function restoreProfile(userId?: string): Profile | null {
  try {
    const key = userId ? `fresh-citrus.profile-${userId}` : "fresh-citrus.profile-draft";
    const raw = localStorage.getItem(key) || (userId ? localStorage.getItem("fresh-citrus.profile-draft") : null);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Profile>;
    if (parsed.notes === "Tiền đái tháo đường" && parsed.allergies?.includes("Sữa") && parsed.dislikes?.includes("Chuối")) {
      return { ...defaultProfile, allergies: [], dislikes: [], preferences: [], notes: "", healthRestrictionStatus: "no" };
    }
    return { ...defaultProfile, ...parsed };
  } catch {
    return null;
  }
}
export function persistProfile(profile: Profile, userId?: string): void {
  try {
    const key = userId ? `fresh-citrus.profile-${userId}` : "fresh-citrus.profile-draft";
    localStorage.setItem(key, JSON.stringify(profile));
  } catch { /* storage unavailable */ }
}
