"use client";

import { useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";

const SUGGESTIONS = ["Tìm hiểu dinh dưỡng của chuối", "Tạo sinh tố giàu chất xơ với ổi"];

export function PromptBox({ onSubmit, busy, onStop, showSuggestions }: { onSubmit: (prompt: string) => void; busy: boolean; onStop: () => void; showSuggestions: boolean }) {
  const [value, setValue] = useState("");
  const submit = () => { if (value.trim() && !busy) { onSubmit(value.trim()); setValue(""); } };
  const keyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) { event.preventDefault(); submit(); }
  };
  return (
    <section className="rounded-card border border-peach bg-warm p-3 shadow-card sm:p-4">
      <label htmlFor="prompt" className={showSuggestions ? "text-sm text-muted" : "sr-only"}>Hỏi trợ lý về dinh dưỡng, hoặc yêu cầu tạo công thức và báo cáo PDF</label>
      {showSuggestions && (
        <div className="scrollbar-none -mx-1 mt-3 flex gap-2 overflow-x-auto px-1 sm:flex-wrap">
          {SUGGESTIONS.map((text) => <Button key={text} size="sm" className="shrink-0 font-normal" onClick={() => onSubmit(text)} disabled={busy}>{text}</Button>)}
        </div>
      )}
      <div className={`flex items-end gap-2 ${showSuggestions ? "mt-3" : ""}`}>
        <textarea id="prompt" value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={keyDown} rows={1}
          className="field max-h-40 min-h-11 resize-none [field-sizing:content]" placeholder="Ví dụ: Tạo sinh tố ít đường từ ổi…" />
        {busy
          ? <Button icon className="size-11 shrink-0" onClick={onStop} aria-label="Dừng câu trả lời"><Icon name="stop" className="size-4" /></Button>
          : <Button variant="primary" icon className="size-11 shrink-0" onClick={submit} disabled={!value.trim()} aria-label="Gửi câu hỏi"><Icon name="send" className="size-4" /></Button>}
      </div>
      <p className="mt-2 hidden text-xs text-subtle sm:block">Enter để gửi · Shift + Enter để xuống dòng</p>
    </section>
  );
}
