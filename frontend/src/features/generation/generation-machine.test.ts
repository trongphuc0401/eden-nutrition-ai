import { describe, expect, it } from "vitest";
import { generationReducer, initialGenerationState } from "./generation-machine";
import { demoReport } from "@/lib/demo-data";

describe("generationReducer", () => {
  it("moves through a successful run and preserves its report", () => {
    const running = generationReducer(initialGenerationState, { type: "START" });
    const progressing = generationReducer(running, { type: "STEP", step: 3 });
    const finished = generationReducer(progressing, { type: "RESOLVE", report: { ...demoReport, decision: "pass" } });

    expect(progressing).toMatchObject({ phase: "generating", activeStep: 3 });
    expect(finished).toMatchObject({ phase: "completed", activeStep: 4, report: expect.objectContaining({ id: demoReport.id }) });
  });

  it("does not advance a run that is not active", () => {
    expect(generationReducer(initialGenerationState, { type: "STEP", step: 2 })).toEqual(initialGenerationState);
  });

  it("keeps review, blocked, stopped and failure outcomes distinct", () => {
    const review = generationReducer(initialGenerationState, { type: "RESOLVE", report: demoReport });
    expect(review.phase).toBe("review");
    expect(generationReducer(review, { type: "BLOCK", message: "Ngoài phạm vi" })).toMatchObject({ phase: "blocked", message: "Ngoài phạm vi" });
    expect(generationReducer(review, { type: "STOP" }).phase).toBe("stopped");
    expect(generationReducer(review, { type: "FAIL", message: "Mạng lỗi" })).toMatchObject({ phase: "error", message: "Mạng lỗi" });
  });
});
