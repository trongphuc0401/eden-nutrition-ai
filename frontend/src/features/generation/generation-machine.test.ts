import { describe, expect, it } from "vitest";
import { generationReducer, initialGenerationState } from "./generation-machine";
import { demoReport } from "@/lib/demo-data";

describe("generationReducer", () => {
  it("moves through a successful run and preserves its report", () => {
    const running = generationReducer(initialGenerationState, { type: "START" });
    const progressing = generationReducer(running, { type: "STEP", step: 3 });
    const finished = generationReducer(progressing, { type: "RESOLVE", report: { ...demoReport, decision: "pass" } });

    expect(progressing).toMatchObject({ phase: "generating", activeStep: 3 });
    expect(finished).toMatchObject({ phase: "completed", activeStep: 6, report: expect.objectContaining({ id: demoReport.id }) });
  });

  it("does not advance a run that is not active", () => {
    expect(generationReducer(initialGenerationState, { type: "STEP", step: 2 })).toEqual(initialGenerationState);
  });

  it("pauses on a versioned ingredient proposal before producing a report", () => {
    const running = generationReducer(initialGenerationState, { type: "START" });
    const waiting = generationReducer(running, {
      type: "WAIT_CONFIRMATION",
      pending: {
        reportId: "rpt-test",
        proposal: {
          version: 1,
          title: "Sinh tố thử nghiệm",
          ingredients: [{ ingredient_id: "hat-chia", amount: 10, unit: "g", reason: "Bổ sung chất xơ" }],
          suggested_ingredient_ids: ["hat-chia"],
          omitted_selected: [],
          rationale: "Cần xác nhận trước khi tính report.",
        },
      },
    });

    expect(waiting).toMatchObject({ phase: "awaiting_confirmation", pendingConfirmation: { reportId: "rpt-test" } });
    expect(waiting.report).toBeNull();
  });

  it("keeps review, blocked, stopped and failure outcomes distinct", () => {
    const review = generationReducer(initialGenerationState, { type: "RESOLVE", report: demoReport });
    expect(review.phase).toBe("review");
    expect(generationReducer(review, { type: "BLOCK", message: "Ngoài phạm vi" })).toMatchObject({ phase: "blocked", message: "Ngoài phạm vi" });
    expect(generationReducer(review, { type: "STOP" }).phase).toBe("stopped");
    expect(generationReducer(review, { type: "FAIL", message: "Mạng lỗi" })).toMatchObject({ phase: "error", message: "Mạng lỗi" });
  });
});
