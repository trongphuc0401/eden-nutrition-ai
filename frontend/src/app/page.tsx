"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ContextPanel, ContextPanelBody, ContextPanelHeader } from "@/components/layout/context-panel";
import { Sidebar, SidebarContent, type View } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { Modal } from "@/components/ui/modal";
import { ToastMessage, type Toast } from "@/components/ui/toast";
import { SignIn } from "@/features/auth/sign-in";
import { ChatThread } from "@/features/chat/chat-thread";
import { useChat } from "@/features/chat/use-chat";
import { generationReducer, initialGenerationState } from "@/features/generation/generation-machine";
import { ProfileForm } from "@/features/profile/profile-form";
import { ConfirmationPanel } from "@/features/workspace/confirmation-panel";
import { EmptyWorkspace } from "@/features/workspace/empty-workspace";
import { IngredientPicker, type CatalogStatus } from "@/features/workspace/ingredient-picker";
import { LibraryView } from "@/features/workspace/library-view";
import { Processing } from "@/features/workspace/processing";
import { PromptBox } from "@/features/workspace/prompt-box";
import { ReportView } from "@/features/workspace/report-view";
import { getIngredients, getSession, isProfileCompleted, logout, markProfileCompleted, persistProfile, restoreProfile } from "@/lib/api";
import type { ChatAction } from "@/lib/chat-api";
import { generationInputSchema } from "@/lib/contracts";
import { emptyProfile, inScope } from "@/lib/profile";
import { cancelPendingReport, confirmReport, fetchReport, generateReport } from "@/lib/report-api";
import type { Ingredient, Profile, Report, SessionUser } from "@/lib/types";

const TITLES: Record<View, string> = {
  signin: "Fresh Citrus", onboarding: "Thiết lập hồ sơ", workspace: "Trợ lý dinh dưỡng",
  history: "Lịch sử công thức", saved: "Công thức đã lưu", profile: "Hồ sơ sức khỏe",
};

export default function Home() {
  const [view, setView] = useState<View>("signin");
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [catalog, setCatalog] = useState<Ingredient[]>([]);
  const [catalogStatus, setCatalogStatus] = useState<CatalogStatus>("loading");
  const [catalogAttempt, setCatalogAttempt] = useState(0);
  const [showPicker, setShowPicker] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [generation, dispatchGeneration] = useReducer(generationReducer, initialGenerationState);
  const [toast, setToast] = useState<Toast>(null);
  const [sessionReports, setSessionReports] = useState<Report[]>([]);
  const [activeReportId, setActiveReportId] = useState<string | null>(null);
  const [user, setUser] = useState<SessionUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const abortRef = useRef<AbortController | null>(null);
  const profileHydrated = useRef(false);
  const toastTimer = useRef<number | undefined>(undefined);
  const reportSectionRef = useRef<HTMLDivElement>(null);

  const report = generation.report;
  const status = generation.phase;
  const currentReport = sessionReports.find((r) => r.id === activeReportId) ?? sessionReports[sessionReports.length - 1] ?? report;
  const selected = catalog.filter((ingredient) => selectedIds.includes(ingredient.id));

  const openToast = useCallback((text: string, tone: "success" | "error" = "success") => {
    window.clearTimeout(toastTimer.current);
    setToast({ text, tone });
    toastTimer.current = window.setTimeout(() => setToast(null), tone === "error" ? 6000 : 4200);
  }, []);
  const scrollToReport = () => window.setTimeout(() => reportSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 120);

  // eslint-disable-next-line react-hooks/set-state-in-effect -- hydrate profile from localStorage on mount
  useEffect(() => { const saved = restoreProfile(); if (saved) setProfile(saved); profileHydrated.current = true; }, []);
  useEffect(() => { if (profileHydrated.current) persistProfile(profile, user?.id); }, [profile, user?.id]);
  useEffect(() => {
    const url = new URL(window.location.href); const authError = url.searchParams.get("auth_error");
    if (authError) { url.searchParams.delete("auth_error"); window.history.replaceState(null, "", url); }
    getSession().then((sessionUser) => {
      setUser(sessionUser);
      if (authError) openToast("Đăng nhập Google chưa thành công. Vui lòng thử lại.", "error");
      if (sessionUser) {
        const userSaved = restoreProfile(sessionUser.id); if (userSaved) setProfile(userSaved);
        setView(isProfileCompleted(sessionUser.id) ? "workspace" : "onboarding");
      }
    }).catch(() => openToast("Không thể kiểm tra phiên đăng nhập. Vui lòng tải lại trang.", "error")).finally(() => setCheckingSession(false));
  }, [openToast]);
  // Keep only selections the loaded catalog can show: the user must see (and be able to remove) every ingredient that is sent.
  useEffect(() => {
    let cancelled = false;
    getIngredients(new Date().getMonth() + 1, profile.hometown)
      .then((items) => { if (cancelled) return; setCatalog(items); setSelectedIds((ids) => ids.filter((id) => items.some((item) => item.id === id))); setCatalogStatus("ready"); })
      .catch(() => { if (!cancelled) setCatalogStatus("error"); });
    return () => { cancelled = true; };
  }, [profile.hometown, catalogAttempt]);
  const retryCatalog = () => { setCatalogStatus("loading"); setCatalogAttempt((attempt) => attempt + 1); };

  const chat = useChat({ profile, selectedIds, enabled: Boolean(user) });
  useEffect(() => {
    if (!chat.threadReportId) return;
    fetchReport(chat.threadReportId).then((loadedReport) => {
      if (!loadedReport) return;
      setSessionReports((prev) => (prev.some((r) => r.id === loadedReport.id) ? prev : [loadedReport, ...prev]));
      dispatchGeneration({ type: "RESOLVE", report: loadedReport });
    }).catch(() => openToast("Không tải được báo cáo của phiên chat này. Vui lòng thử lại.", "error"));
  }, [chat.threadReportId, openToast]);

  const go = (next: View) => { setView(next); setMenuOpen(false); setContextOpen(false); };
  const resetGeneration = () => { dispatchGeneration({ type: "RESET" }); setSessionReports([]); setActiveReportId(null); };
  const handleSelectThread = async (threadId: string) => { resetGeneration(); await chat.selectThread(threadId); go("workspace"); };
  const handleNewSession = async () => { resetGeneration(); await chat.newThread(); go("workspace"); };
  const handleDeleteThread = async (threadId: string) => {
    try { await chat.removeThread(threadId); openToast("Đã xóa phiên chat."); }
    catch (error) { openToast(error instanceof Error ? error.message : "Không xóa được phiên chat.", "error"); }
  };
  const copyText = (text: string) => { navigator.clipboard?.writeText(text).then(() => openToast("Đã sao chép.")).catch(() => openToast("Không sao chép được, hãy chọn và sao chép thủ công.", "error")); };

  const acceptOutcome = (outcome: Awaited<ReturnType<typeof generateReport>>) => {
    if (outcome.kind === "report") {
      dispatchGeneration({ type: "RESOLVE", report: outcome.report });
      setSessionReports((prev) => [...prev.filter((r) => r.id !== outcome.report.id), outcome.report]);
      setActiveReportId(outcome.report.id);
      void chat.linkReport(outcome.report.id);
      openToast("Báo cáo và công thức sinh tố đã hoàn tất!");
    } else {
      dispatchGeneration({ type: "WAIT_CONFIRMATION", pending: outcome.pending });
    }
    scrollToReport();
  };
  const runWorkflow = async (work: (signal: AbortSignal) => ReturnType<typeof generateReport>, fallback: string) => {
    dispatchGeneration({ type: "START" });
    scrollToReport();
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      acceptOutcome(await work(controller.signal));
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") return;
      const message = error instanceof Error ? error.message : fallback;
      dispatchGeneration({ type: "FAIL", message });
      openToast(message, "error");
    } finally {
      abortRef.current = null;
    }
  };
  const onStep = (step: number) => dispatchGeneration({ type: "STEP", step });
  const begin = async (prompt = "", ids?: string[]) => {
    const chosen = ids ?? selectedIds;
    if (!inScope(profile)) { dispatchGeneration({ type: "BLOCK", message: "Hồ sơ chưa thuộc phạm vi thử nghiệm." }); openToast("Hồ sơ hiện ngoài phạm vi thử nghiệm (BMI ≥ 23).", "error"); return; }
    if (!chosen.some((id) => catalog.find((item) => item.id === id)?.kind === "fruit")) { setShowPicker(true); openToast("Chọn ít nhất một loại trái cây trước khi tạo.", "error"); return; }
    const parsed = generationInputSchema.safeParse({ profile, ingredientIds: chosen, prompt: prompt || undefined });
    if (!parsed.success) { openToast(parsed.error.issues[0]?.message ?? "Yêu cầu chưa hợp lệ.", "error"); return; }
    setContextOpen(false);
    await runWorkflow((signal) => generateReport(parsed.data, onStep, signal), "Không thể tạo báo cáo.");
  };
  const confirmSuggestions = async (ids: string[]) => {
    const pending = generation.pendingConfirmation;
    if (pending) await runWorkflow((signal) => confirmReport(pending, ids, onStep, signal), "Không thể xác nhận đề xuất.");
  };
  const cancelConfirmation = async () => {
    const pending = generation.pendingConfirmation; if (!pending) return;
    try { await cancelPendingReport(pending.reportId); dispatchGeneration({ type: "STOP" }); openToast("Đã hủy đề xuất đang chờ xác nhận."); }
    catch (error) { openToast(error instanceof Error ? error.message : "Không thể hủy đề xuất.", "error"); }
  };
  const stopGeneration = () => { abortRef.current?.abort(); dispatchGeneration({ type: "STOP" }); openToast("Đã dừng tạo báo cáo."); };
  // Agent actions are proposals: nothing runs until the user clicks, and a report only uses ingredients the picker shows.
  const handleChatAction = (action: ChatAction) => {
    if (action.type === "prompt") { void chat.send(action.prompt); return; }
    if (action.type === "open_picker") { setShowPicker(true); return; }
    const ids = action.ingredient_ids.filter((id) => catalog.some((item) => item.id === id));
    if (!ids.length) { openToast("Các nguyên liệu này chưa có trong danh mục để tạo báo cáo.", "error"); setShowPicker(true); return; }
    setSelectedIds(ids);
    void begin(action.prompt, ids);
  };
  const toggleSaved = (target: Report) => {
    const updated = { ...target, saved: !target.saved };
    setSessionReports((list) => list.some((item) => item.id === target.id) ? list.map((item) => (item.id === target.id ? updated : item)) : [...list, updated]);
    dispatchGeneration({ type: "RESOLVE", report: updated });
    openToast(updated.saved ? "Đã lưu công thức vào thư viện." : "Đã bỏ lưu công thức.");
  };
  const openReport = (entry: Report) => { setActiveReportId(entry.id); dispatchGeneration({ type: "RESOLVE", report: entry }); go("workspace"); };
  const signOut = async () => {
    abortRef.current?.abort();
    try { await logout(); }
    catch (error) { openToast(error instanceof Error ? error.message : "Không thể đăng xuất. Vui lòng thử lại.", "error"); return; }
    setUser(null); resetGeneration(); go("signin"); openToast("Bạn đã đăng xuất.");
  };
  const saveProfile = (next: Profile) => { setProfile(next); persistProfile(next, user?.id); markProfileCompleted(user?.id); go("workspace"); openToast("Hồ sơ sức khỏe đã được lưu."); };

  const toastNode = <ToastMessage toast={toast} close={() => setToast(null)} />;
  if (view === "signin") return <><SignIn checking={checkingSession} />{toastNode}</>;

  const reports = sessionReports.length ? sessionReports : report ? [report] : [];
  const busy = status === "generating" || chat.streaming;
  const showContext = view === "workspace" || view === "history" || view === "saved";
  const reportIndex = currentReport ? sessionReports.findIndex((r) => r.id === currentReport.id) + 1 || 1 : 0;
  const sidebarProps = {
    view, setView: go, onNewThread: () => void handleNewSession(), user, onLogout: () => void signOut(),
    threads: chat.threads, activeThreadId: chat.threadId, onSelectThread: (id: string) => void handleSelectThread(id), onDeleteThread: (id: string) => void handleDeleteThread(id),
  };
  const contextProps = { profile, selected, openSelector: () => setShowPicker(true), createReport: () => void begin(), busy };

  const workspace = (
    <section className="flex min-h-full min-w-0 flex-1 flex-col">
      <div className="flex-1 space-y-6 pb-4">
        {chat.messages.length === 0 && !currentReport && status === "idle"
          ? <EmptyWorkspace selectIngredients={() => setShowPicker(true)} start={() => void begin()} blocked={!inScope(profile)} />
          : <>
            {chat.messages.length > 0 && <ChatThread messages={chat.messages} onAction={handleChatAction} onRetry={(prompt) => void chat.send(prompt)} onCopy={copyText} busy={busy} />}
            {status === "generating" && <div ref={reportSectionRef}><Processing current={generation.activeStep} hometown={profile.hometown} onStop={stopGeneration} /></div>}
            {status === "awaiting_confirmation" && generation.pendingConfirmation && <div ref={reportSectionRef}><ConfirmationPanel pending={generation.pendingConfirmation} catalog={catalog} confirm={(ids) => void confirmSuggestions(ids)} cancel={() => void cancelConfirmation()} /></div>}
            {(status === "error" || status === "stopped" || status === "blocked") && (
              <div className="rounded-card border border-coral-line bg-coral-soft p-5 sm:p-6">
                <h2 className="text-xl font-semibold text-strong">{status === "stopped" ? "Bạn đã dừng yêu cầu" : status === "blocked" ? "Chưa thể tạo công thức" : "Không thể tạo công thức"}</h2>
                {generation.message && status !== "stopped" && <p className="mt-3 rounded-xl border border-coral-line bg-card p-3 text-sm font-semibold text-coral-strong" role="alert">{generation.message}</p>}
                <p className="mt-2 text-muted">{status === "blocked" ? "Cập nhật hồ sơ sức khỏe nếu thông tin chưa đúng." : "Thông tin đã nhập vẫn được giữ. Bạn có thể thử lại hoặc chỉnh lựa chọn."}</p>
                <div className="mt-5 flex flex-wrap gap-3">
                  {status === "blocked"
                    ? <Button variant="primary" onClick={() => go("profile")}>Cập nhật hồ sơ</Button>
                    : <Button variant="primary" onClick={() => void begin()}><Icon name="refresh" className="size-4" />Thử lại</Button>}
                  <Button onClick={() => setShowPicker(true)}>Chỉnh nguyên liệu</Button>
                </div>
              </div>
            )}
            {currentReport && (
              <div ref={reportSectionRef} className="space-y-3 pt-2">
                {sessionReports.length > 1 && (
                  <div className="rounded-xl border border-peach bg-warm p-3">
                    <p className="mb-2 text-xs font-semibold text-action">Các công thức đã tạo trong phiên này ({sessionReports.length})</p>
                    <div className="flex flex-wrap gap-1.5">
                      {sessionReports.map((r, index) => (
                        <button key={r.id} onClick={() => openReport(r)} aria-pressed={currentReport.id === r.id}
                          className={`rounded-lg px-2.5 py-1 text-sm transition ${currentReport.id === r.id ? "bg-action font-semibold text-white" : "border border-line bg-card text-ink hover:bg-orange-soft"}`}>#{index + 1} {r.name}</button>
                      ))}
                    </div>
                  </div>
                )}
                <p className="text-sm font-semibold text-action">Công thức sinh tố #{reportIndex}</p>
                <ReportView report={currentReport} hometown={profile.hometown} onToggleSaved={() => toggleSaved(currentReport)} onCopy={copyText} />
              </div>
            )}
          </>}
      </div>
      {status !== "generating" && status !== "awaiting_confirmation" && (
        <div className="sticky bottom-0 z-20 mt-auto bg-gradient-to-t from-card via-card/95 to-transparent pt-3">
          <PromptBox onSubmit={(text) => void chat.send(text)} busy={chat.streaming} onStop={chat.stop} showSuggestions={chat.messages.length === 0 && !currentReport}
            model={{ list: chat.modelList, value: chat.model, onChange: chat.setModel }} />
        </div>
      )}
    </section>
  );

  const content = view === "onboarding" || view === "profile"
    ? <div className="min-w-0 flex-1"><ProfileForm key={view} profile={profile} catalog={catalog} catalogStatus={catalogStatus} onRetryCatalog={retryCatalog} save={saveProfile} cancel={() => go("workspace")} onboarding={view === "onboarding"} /></div>
    : view === "history" ? <LibraryView kind="history" reports={[...reports].reverse()} onOpen={openReport} onStart={() => go("workspace")} />
      : view === "saved" ? <LibraryView kind="saved" reports={reports.filter((entry) => entry.saved)} onOpen={openReport} onStart={() => go("workspace")} />
        : workspace;

  return (
    <main className="h-dvh w-full overflow-hidden bg-cream xl:p-4">
      <div className="flex h-full min-h-0 gap-4">
        <Sidebar {...sidebarProps} />
        <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-card xl:rounded-panel xl:border xl:border-line xl:shadow-card">
          <Topbar title={TITLES[view]} onMenu={() => setMenuOpen(true)} onContext={showContext ? () => setContextOpen(true) : undefined} user={user} onOpenProfile={() => go("profile")} onLogout={() => void signOut()} />
          <div className="flex min-h-0 flex-1 gap-6 overflow-y-auto p-4 sm:p-6 lg:items-start">
            {content}
            {showContext && <ContextPanel {...contextProps} />}
          </div>
        </section>
      </div>
      <Modal open={menuOpen} onClose={() => setMenuOpen(false)} placement="left" label="Điều hướng" panelClassName="p-5"><SidebarContent {...sidebarProps} /></Modal>
      <Modal open={contextOpen && showContext} onClose={() => setContextOpen(false)} placement="right" labelledBy="context-drawer-title">
        <ContextPanelHeader titleId="context-drawer-title" trailing={<Button variant="ghost" icon size="sm" onClick={() => setContextOpen(false)} aria-label="Đóng"><Icon name="close" className="size-4" /></Button>} />
        <div className="p-4"><ContextPanelBody {...contextProps} /></div>
      </Modal>
      <IngredientPicker open={showPicker} catalog={catalog} status={catalogStatus} onRetry={retryCatalog} selectedIds={selectedIds} setSelectedIds={setSelectedIds} close={() => setShowPicker(false)} />
      {toastNode}
    </main>
  );
}
