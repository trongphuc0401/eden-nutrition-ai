"use client";

import { useState } from "react";
import { Logo } from "@/components/brand/logo";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/ui/confirm-dialog";
import { Icon, type IconName } from "@/components/ui/icon";
import type { ChatThreadSummary } from "@/lib/chat-api";
import type { SessionUser } from "@/lib/types";

export type View = "signin" | "onboarding" | "workspace" | "history" | "saved" | "profile";

const NAV: { view: View; icon: IconName; label: string }[] = [
  { view: "workspace", icon: "sparkles", label: "Trợ lý AI" },
  { view: "history", icon: "history", label: "Lịch sử" },
  { view: "saved", icon: "bookmark", label: "Công thức đã lưu" },
];

type Props = {
  view: View; setView: (view: View) => void; onNewThread: () => void; user: SessionUser | null; onLogout: () => void;
  threads: ChatThreadSummary[]; activeThreadId: string | null; onSelectThread: (threadId: string) => void; onDeleteThread: (threadId: string) => void;
};

/** Navigation content, shared by the desktop rail and the mobile drawer. */
export function SidebarContent({ view, setView, onNewThread, threads, activeThreadId, onSelectThread, onDeleteThread }: Props) {
  const [pendingDelete, setPendingDelete] = useState<ChatThreadSummary | null>(null);
  return (
    <div className="flex h-full min-h-0 flex-col">
      <button className="mb-6 rounded-xl text-left" onClick={() => setView("workspace")} aria-label="Fresh Citrus, về trợ lý AI"><Logo /></button>
      <Button variant="primary" className="mb-4 w-full" onClick={onNewThread}><Icon name="plus" />Đoạn chat mới</Button>
      <nav className="space-y-1" aria-label="Điều hướng chính">
        {NAV.map((item) => {
          const active = view === item.view;
          return (
            <button key={item.view} onClick={() => setView(item.view)} aria-current={active ? "page" : undefined}
              className={`flex min-h-10 w-full items-center gap-3 rounded-xl px-3 text-left text-[15px] transition ${active ? "bg-orange-soft font-semibold text-action" : "text-muted hover:bg-orange-soft hover:text-ink"}`}>
              <Icon name={item.icon} />{item.label}
            </button>
          );
        })}
      </nav>
      <div className="mt-4 flex min-h-0 flex-1 flex-col border-t border-line pt-3">
        <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wider text-muted">Các phiên chat</h2>
        <ul className="flex-1 space-y-1 overflow-y-auto pr-1">
          {threads.map((thread) => {
            const active = activeThreadId === thread.id;
            return (
              <li key={thread.id} className={`group flex items-center rounded-xl border text-sm transition ${active ? "border-peach bg-orange-soft font-semibold text-action" : "border-transparent text-ink hover:bg-warm"}`}>
                <button onClick={() => onSelectThread(thread.id)} aria-current={active ? "true" : undefined} className="flex min-h-9 min-w-0 flex-1 items-center gap-2 rounded-xl px-2.5 text-left">
                  <Icon name="chat" className="size-4 text-subtle" /><span className="truncate" title={thread.title}>{thread.title}</span>
                </button>
                <button onClick={() => setPendingDelete(thread)} aria-label={`Xóa phiên “${thread.title}”`}
                  className="mr-1 grid size-8 shrink-0 place-items-center rounded-lg text-muted opacity-0 transition hover:bg-coral-soft hover:text-coral-strong focus-visible:opacity-100 group-hover:opacity-100">
                  <Icon name="trash" className="size-4" />
                </button>
              </li>
            );
          })}
          {threads.length === 0 && <li className="px-2 py-2 text-sm text-muted">Chưa có phiên chat nào.</li>}
        </ul>
      </div>
      <ConfirmDialog open={pendingDelete !== null} title="Xóa phiên chat này?" description={`“${pendingDelete?.title ?? ""}” và các tin nhắn trong phiên sẽ bị xóa. Thao tác này không hoàn tác được.`}
        confirmLabel="Xóa phiên" onCancel={() => setPendingDelete(null)} onConfirm={() => { if (pendingDelete) onDeleteThread(pendingDelete.id); setPendingDelete(null); }} />
    </div>
  );
}

export function Sidebar(props: Props) {
  return <aside className="hidden w-64 shrink-0 rounded-panel border border-line bg-card p-5 shadow-card xl:block xl:h-full xl:overflow-hidden"><SidebarContent {...props} /></aside>;
}
