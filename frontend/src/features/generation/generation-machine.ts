import type { PendingConfirmation, Report } from "@/lib/types";

export type GenerationPhase = "idle" | "generating" | "awaiting_confirmation" | "completed" | "review" | "blocked" | "error" | "stopped";

export type GenerationState = {
  phase: GenerationPhase;
  activeStep: number;
  report: Report | null;
  message: string | null;
  pendingConfirmation: PendingConfirmation | null;
};

export type GenerationEvent =
  | { type: "START" }
  | { type: "STEP"; step: number }
  | { type: "RESOLVE"; report: Report }
  | { type: "WAIT_CONFIRMATION"; pending: PendingConfirmation }
  | { type: "BLOCK"; message: string }
  | { type: "FAIL"; message: string }
  | { type: "STOP" }
  | { type: "RESET" };

export const initialGenerationState: GenerationState = { phase: "idle", activeStep: 0, report: null, message: null, pendingConfirmation: null };

export function generationReducer(state: GenerationState, event: GenerationEvent): GenerationState {
  switch (event.type) {
    case "START": return { phase: "generating", activeStep: 0, report: null, message: null, pendingConfirmation: null };
    case "STEP": return state.phase === "generating" ? { ...state, activeStep: Math.max(0, Math.min(6, event.step)) } : state;
    case "RESOLVE": return { phase: event.report.decision === "review" ? "review" : "completed", activeStep: 6, report: event.report, message: null, pendingConfirmation: null };
    case "WAIT_CONFIRMATION": return { ...state, phase: "awaiting_confirmation", pendingConfirmation: event.pending, message: null };
    case "BLOCK": return { ...state, phase: "blocked", message: event.message };
    case "FAIL": return { ...state, phase: "error", message: event.message };
    case "STOP": return { ...state, phase: "stopped", message: "Đã gửi yêu cầu dừng tạo công thức." };
    case "RESET": return initialGenerationState;
  }
}
