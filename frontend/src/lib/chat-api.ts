import type { Profile } from "./types";
import { apiUrl } from "./api";
import { toApiProfile } from "./report-api";

export type NutritionKey = "calories" | "protein" | "carbohydrate" | "fat" | "fiber" | "sugar" | "sodium";
export type NutritionRow = {
  ingredient_id: string; name: string; per_100g: Partial<Record<NutritionKey, number | null>>;
  in_season_now: boolean | null; allergens: string[]; source: string; verified: boolean;
};
export type ChatCard = { type: "nutrition"; basis: string; rows: NutritionRow[] };
export type ChatAction =
  | { type: "create_report"; label: string; ingredient_ids: string[]; prompt: string }
  | { type: "prompt"; label: string; prompt: string }
  | { type: "open_picker"; label: string };

export type ChatEvent =
  | { event: "thread"; data: { thread_id: string } }
  | { event: "status"; data: { step: string; text: string } }
  | { event: "delta"; data: { text: string } }
  | { event: "cards"; data: { cards: ChatCard[] } }
  | { event: "actions"; data: { actions: ChatAction[] } }
  | { event: "done"; data: { message_id: number | null; intent: string; thread_id: string; model?: string | null; data_source?: string; dataset_version?: string | null } }
  | { event: "error"; data: { message: string; code?: string } };

export type StoredMessage = {
  id: number; role: "user" | "assistant"; content: string; intent: string | null;
  metadata: { cards?: ChatCard[]; actions?: ChatAction[]; data_source?: string; dataset_version?: string | null };
};

type SendInput = { message: string; threadId: string | null; profile: Profile; selectedIds: string[]; model?: string | null };

export type ChatModel = { id: string; label: string; description: string };
/** `enabled` is false when the backend answers from data templates only; the model choice then has no effect. */
export type ChatModelList = { models: ChatModel[]; default: string; enabled: boolean };

/** The free models the backend allows for chat, or null when the list cannot be loaded. */
export async function fetchChatModels(): Promise<ChatModelList | null> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/models`, { credentials: "include" });
    if (!response.ok) return null;
    return (await response.json()) as ChatModelList;
  } catch {
    return null;
  }
}

/** POST /v1/chat and hand every Server-Sent Event to `onEvent` as it arrives. */
export async function streamChat(input: SendInput, onEvent: (event: ChatEvent) => void, signal?: AbortSignal): Promise<void> {
  const response = await fetch(`${apiUrl}/v1/chat`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify({
      message: input.message,
      thread_id: input.threadId,
      profile: toApiProfile(input.profile),
      selectedIngredientIds: input.selectedIds.slice(0, 8),
      model: input.model ?? undefined,
    }),
    signal,
  });
  if (!response.ok || !response.body) {
    if (response.status === 401) throw new Error("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại rồi gửi lại câu hỏi.");
    throw new Error("Không kết nối được với trợ lý dinh dưỡng. Câu hỏi của bạn vẫn được giữ, bạn có thể thử lại.");
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const block = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      const name = block.match(/^event: (.+)$/m)?.[1];
      const data = block.match(/^data: (.+)$/m)?.[1];
      if (name && data) onEvent({ event: name, data: JSON.parse(data) } as ChatEvent);
      boundary = buffer.indexOf("\n\n");
    }
    if (done) return;
  }
}

export type ChatThreadSummary = {
  id: string;
  title: string;
  report_id?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  message_count: number;
  last_message?: string | null;
};

export type ThreadDetail = {
  thread_id: string;
  title?: string | null;
  report_id?: string | null;
  messages: StoredMessage[];
};

/** Messages of a thread the signed-in user owns, or null when it no longer exists. */
export async function loadThread(threadId: string): Promise<ThreadDetail | null> {
  const response = await fetch(`${apiUrl}/v1/chat/threads/${encodeURIComponent(threadId)}`, { credentials: "include" });
  if (!response.ok) return null;
  const body = (await response.json()) as ThreadDetail;
  return body;
}

export async function listThreads(): Promise<ChatThreadSummary[]> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/threads`, { credentials: "include" });
    if (!response.ok) return [];
    const body = (await response.json()) as { threads: ChatThreadSummary[] };
    return body.threads ?? [];
  } catch {
    return [];
  }
}

export async function createThread(title?: string): Promise<{ thread_id: string; title: string } | null> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/threads`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ title: title || "Đoạn chat mới" }),
    });
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

export async function deleteThread(threadId: string): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/threads/${encodeURIComponent(threadId)}`, {
      method: "DELETE",
      credentials: "include",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function renameThread(threadId: string, title: string): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/threads/${encodeURIComponent(threadId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ title }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function attachReportToThread(threadId: string, reportId: string): Promise<boolean> {
  try {
    const response = await fetch(`${apiUrl}/v1/chat/threads/${encodeURIComponent(threadId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({ report_id: reportId }),
    });
    return response.ok;
  } catch {
    return false;
  }
}

