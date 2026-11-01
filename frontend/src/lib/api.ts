import type { Ingredient, Profile, SessionUser } from "./types";
import { emptyProfile } from "./profile";

// Same-origin by default: next.config.ts proxies /api/* to the backend.
export const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "/api";

/** User-facing message for a failed HTTP status; the backend's own detail wins when it sends one. */
export function httpErrorMessage(status: number, detail?: string): string {
  if (detail) return detail;
  if (status === 401) return "Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.";
  if (status === 403) return "Bạn không có quyền thực hiện thao tác này.";
  if (status === 404) return "Không tìm thấy dữ liệu yêu cầu.";
  if (status === 429) return "Bạn thao tác quá nhanh. Vui lòng đợi một chút rồi thử lại.";
  if (status >= 500) return "Dịch vụ đang gặp sự cố. Vui lòng thử lại sau ít phút.";
  return "Yêu cầu chưa hợp lệ. Vui lòng kiểm tra lại thông tin.";
}

export const NETWORK_ERROR = "Không kết nối được tới máy chủ. Hãy kiểm tra mạng rồi thử lại.";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiUrl}${path}`, { credentials: "include", ...init }).catch(() => { throw new Error(NETWORK_ERROR); });
  if (!response.ok) throw new Error(httpErrorMessage(response.status));
  return response.json() as Promise<T>;
}

export const googleLoginUrl = `${apiUrl}/v1/auth/google/login`;

/** The signed-in user, or null when there is no session (HTTP 401). */
export async function getSession(): Promise<SessionUser | null> {
  const response = await fetch(`${apiUrl}/v1/auth/me`, { credentials: "include" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Không thể kiểm tra phiên đăng nhập.");
  const body = await response.json() as { user: SessionUser };
  return body.user;
}

export async function logout(): Promise<void> {
  const response = await fetch(`${apiUrl}/v1/auth/logout`, { method: "POST", credentials: "include" }).catch(() => { throw new Error(NETWORK_ERROR); });
  if (!response.ok) throw new Error(httpErrorMessage(response.status));
}

export async function getIngredients(month: number, hometown?: string): Promise<Ingredient[]> {
  // Live catalog from the backend (public endpoint): fruit data is never hardcoded in the UI.
  // hometown selects the climate zone (north / central / south) used for "đang mùa"
  const region = hometown ? `&hometown=${encodeURIComponent(hometown)}` : "";
  const response = await request<{ items: Ingredient[] }>(`/v1/ingredients?month=${month}${region}`);
  return response.items;
}

export type AllergenOption = { code: string; label: string };

/** Allergy list from the health_conditions reference data (public endpoint). */
export async function getAllergens(): Promise<AllergenOption[]> {
  const response = await request<{ items: AllergenOption[] }>("/v1/reference/allergens");
  return response.items;
}

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
    return { ...emptyProfile, ...parsed };
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
