"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  attachReportToThread,
  createThread as apiCreateThread,
  deleteThread as apiDeleteThread,
  listThreads,
  loadThread,
  renameThread as apiRenameThread,
  streamChat,
  type ChatAction,
  type ChatCard,
  type ChatThreadSummary,
} from "@/lib/chat-api";
import type { Profile } from "@/lib/types";

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  /** assistant only: what the agent is doing / did, shown instead of a bare spinner */
  steps: string[];
  state: "streaming" | "done" | "error" | "stopped";
  cards: ChatCard[];
  actions: ChatAction[];
  error?: string;
  dataSource?: string;
  datasetVersion?: string | null;
  /** user only: the question an assistant answer belongs to, so "Thử lại" can resend it */
  prompt?: string;
};

const THREAD_KEY = "fresh-citrus.chat-thread";

function readThread(): string | null {
  try { return sessionStorage.getItem(THREAD_KEY); } catch { return null; }
}

function writeThread(threadId: string | null): void {
  try {
    if (threadId) sessionStorage.setItem(THREAD_KEY, threadId);
    else sessionStorage.removeItem(THREAD_KEY);
  } catch { /* storage unavailable */ }
}

const newId = () => (typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : String(Date.now() + Math.random()));

export function useChat({ profile, selectedIds, live }: { profile: Profile; selectedIds: string[]; live: boolean }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [threadTitle, setThreadTitle] = useState<string | null>(null);
  const [threadReportId, setThreadReportId] = useState<string | null>(null);
  const [threads, setThreads] = useState<ChatThreadSummary[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const streaming = messages.some((message) => message.state === "streaming");

  const refreshThreads = useCallback(async () => {
    if (!live) return;
    try {
      const list = await listThreads();
      setThreads(list);
    } catch { /* ignore */ }
  }, [live]);

  // Initial load: fetch thread list and restore active thread from sessionStorage
  useEffect(() => {
    if (!live) return;
    void refreshThreads();
    const saved = readThread();
    if (!saved) return;
    loadThread(saved).then((detail) => {
      if (!detail) { writeThread(null); return; }
      setThreadId(detail.thread_id);
      setThreadTitle(detail.title ?? null);
      setThreadReportId(detail.report_id ?? null);
      setMessages(detail.messages.map((message) => ({
        id: String(message.id), role: message.role, text: message.content, steps: [], state: "done",
        cards: message.metadata.cards ?? [], actions: message.metadata.actions ?? [],
        dataSource: message.metadata.data_source, datasetVersion: message.metadata.dataset_version,
      })));
    }).catch(() => undefined);
  }, [live, refreshThreads]);

  const selectThread = useCallback(async (targetThreadId: string) => {
    if (abortRef.current) abortRef.current.abort();
    const detail = await loadThread(targetThreadId);
    if (!detail) {
      writeThread(null);
      return;
    }
    setThreadId(detail.thread_id);
    setThreadTitle(detail.title ?? null);
    setThreadReportId(detail.report_id ?? null);
    writeThread(detail.thread_id);
    setMessages(detail.messages.map((message) => ({
      id: String(message.id), role: message.role, text: message.content, steps: [], state: "done",
      cards: message.metadata.cards ?? [], actions: message.metadata.actions ?? [],
      dataSource: message.metadata.data_source, datasetVersion: message.metadata.dataset_version,
    })));
  }, []);

  const newThread = useCallback(async (initialTitle = "Đoạn chat mới") => {
    if (abortRef.current) abortRef.current.abort();
    setMessages([]);
    setThreadReportId(null);
    if (live) {
      const created = await apiCreateThread(initialTitle);
      if (created) {
        setThreadId(created.thread_id);
        setThreadTitle(created.title);
        writeThread(created.thread_id);
        await refreshThreads();
        return created.thread_id;
      }
    }
    setThreadId(null);
    setThreadTitle(initialTitle);
    writeThread(null);
    return null;
  }, [live, refreshThreads]);

  const removeThread = useCallback(async (targetThreadId: string) => {
    await apiDeleteThread(targetThreadId);
    await refreshThreads();
    if (threadId === targetThreadId) {
      setMessages([]);
      setThreadId(null);
      setThreadTitle(null);
      setThreadReportId(null);
      writeThread(null);
    }
  }, [threadId, refreshThreads]);

  const renameThreadTitle = useCallback(async (targetThreadId: string, newTitle: string) => {
    await apiRenameThread(targetThreadId, newTitle);
    if (threadId === targetThreadId) setThreadTitle(newTitle);
    await refreshThreads();
  }, [threadId, refreshThreads]);

  const linkReport = useCallback(async (reportId: string) => {
    if (threadId && live) {
      await attachReportToThread(threadId, reportId);
      setThreadReportId(reportId);
      await refreshThreads();
    }
  }, [threadId, live, refreshThreads]);

  const update = (id: string, change: (message: ChatMessage) => ChatMessage) =>
    setMessages((all) => all.map((message) => (message.id === id ? change(message) : message)));

  const send = useCallback(async (text: string) => {
    const question = text.trim();
    if (!question || abortRef.current) return;
    const assistantId = newId();
    setMessages((all) => [
      ...all,
      { id: newId(), role: "user", text: question, steps: [], state: "done", cards: [], actions: [], prompt: question },
      { id: assistantId, role: "assistant", text: "", steps: ["Đang gửi câu hỏi…"], state: "streaming", cards: [], actions: [], prompt: question },
    ]);
    const controller = new AbortController();
    abortRef.current = controller;
    try {
      await streamChat({ message: question, threadId, profile, selectedIds }, (event) => {
        switch (event.event) {
          case "thread":
            setThreadId(event.data.thread_id);
            writeThread(event.data.thread_id);
            break;
          case "status":
            update(assistantId, (m) => ({ ...m, steps: [...m.steps.filter((s) => s !== "Đang gửi câu hỏi…"), event.data.text] }));
            break;
          case "delta":
            update(assistantId, (m) => ({ ...m, text: m.text + event.data.text }));
            break;
          case "cards":
            update(assistantId, (m) => ({ ...m, cards: event.data.cards }));
            break;
          case "actions":
            update(assistantId, (m) => ({ ...m, actions: event.data.actions }));
            break;
          case "done":
            update(assistantId, (m) => ({ ...m, state: "done", dataSource: event.data.data_source, datasetVersion: event.data.dataset_version }));
            void refreshThreads();
            break;
          case "error":
            update(assistantId, (m) => ({ ...m, state: "error", error: event.data.message }));
            break;
        }
      }, controller.signal);
      update(assistantId, (m) => (m.state === "streaming" ? { ...m, state: "error", error: "Kết nối bị ngắt trước khi trợ lý trả lời xong. Bạn có thể thử lại." } : m));
    } catch (error) {
      const aborted = error instanceof DOMException && error.name === "AbortError";
      update(assistantId, (m) => ({
        ...m,
        state: aborted ? "stopped" : "error",
        error: aborted ? undefined : error instanceof Error ? error.message : "Trợ lý chưa trả lời được. Bạn có thể thử lại.",
      }));
    } finally {
      abortRef.current = null;
    }
  }, [profile, selectedIds, threadId, refreshThreads]);

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setThreadId(null);
    setThreadTitle(null);
    setThreadReportId(null);
    writeThread(null);
  }, []);

  return {
    messages,
    streaming,
    threadId,
    threadTitle,
    threadReportId,
    threads,
    refreshThreads,
    selectThread,
    newThread,
    removeThread,
    renameThreadTitle,
    linkReport,
    send,
    stop,
    reset,
  };
}

