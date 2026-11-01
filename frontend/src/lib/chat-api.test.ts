import { afterEach, describe, expect, it, vi } from "vitest";
import { profileFixture as defaultProfile } from "@/test/fixtures";

function sseResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      chunks.forEach((chunk) => controller.enqueue(encoder.encode(chunk)));
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

describe("streamChat", () => {
  afterEach(() => { vi.unstubAllGlobals(); vi.unstubAllEnvs(); vi.resetModules(); });

  it("parses events split across network chunks, in order", async () => {
    const events = 'event: thread\ndata: {"thread_id":"t1"}\n\nevent: status\ndata: {"step":"x","text":"Đang tra dữ liệu dinh dưỡng Cam…"}\n\n'
      + 'event: delta\ndata: {"text":"Cam "}\n\nevent: delta\ndata: {"text":"38 kcal"}\n\nevent: done\ndata: {"message_id":2,"intent":"nutrition_question","thread_id":"t1"}\n\n';
    const cut = [events.slice(0, 17), events.slice(17, 90), events.slice(90, 151), events.slice(151)];
    const fetchMock = vi.fn().mockResolvedValue(sseResponse(cut));
    vi.stubGlobal("fetch", fetchMock);
    const { streamChat } = await import("./chat-api");
    const seen: string[] = [];
    let text = "";
    await streamChat({ message: "dinh dưỡng của cam", threadId: null, profile: defaultProfile, selectedIds: ["oi"] }, (event) => {
      seen.push(event.event);
      if (event.event === "delta") text += event.data.text;
    });
    expect(seen).toEqual(["thread", "status", "delta", "delta", "done"]);
    expect(text).toBe("Cam 38 kcal");
    const body = JSON.parse(fetchMock.mock.calls[0][1].body as string);
    expect(body.profile.height_cm).toBe(defaultProfile.heightCm);
    expect(body.selectedIngredientIds).toEqual(["oi"]);
  });

  it("explains an expired session instead of failing silently", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 401 })));
    const { streamChat } = await import("./chat-api");
    await expect(streamChat({ message: "x", threadId: null, profile: defaultProfile, selectedIds: [] }, () => undefined))
      .rejects.toThrow("Phiên đăng nhập đã hết hạn");
  });
});
