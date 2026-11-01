"use client";

import { Fragment, useEffect, useRef, type ReactNode } from "react";
import { Badge } from "@/components/ui/badge";
import type { ChatAction, ChatCard, NutritionKey } from "@/lib/chat-api";
import { scrollWithin } from "@/lib/scroll";
import type { ChatMessage } from "./use-chat";

const COLUMNS: { key: NutritionKey; label: string; unit: string }[] = [
  { key: "calories", label: "Năng lượng", unit: "kcal" },
  { key: "protein", label: "Protein", unit: "g" },
  { key: "carbohydrate", label: "Carbohydrate", unit: "g" },
  { key: "fat", label: "Chất béo", unit: "g" },
  { key: "fiber", label: "Chất xơ", unit: "g" },
  { key: "sugar", label: "Đường", unit: "g" },
];

type Props = {
  messages: ChatMessage[];
  onAction: (action: ChatAction) => void;
  onRetry: (prompt: string) => void;
  onCopy: (text: string) => void;
  busy: boolean;
};

/** Conversation with the nutrition agent: user turns, agent steps, answers, nutrition tables and next actions. */
export function ChatThread({ messages, onAction, onRetry, onCopy, busy }: Props) {
  const endRef = useRef<HTMLDivElement>(null);
  const last = messages[messages.length - 1];
  useEffect(() => { scrollWithin(endRef.current, "end"); }, [messages.length, last?.text.length, last?.state]);

  return (
    <section aria-label="Cuộc trò chuyện với trợ lý dinh dưỡng">
      <ol className="space-y-4" aria-live="polite">
        {messages.map((message) => (
          <li key={message.id}>
            {message.role === "user"
              ? <UserMessage text={message.text} />
              : <AssistantMessage message={message} onAction={onAction} onRetry={onRetry} onCopy={onCopy} busy={busy} />}
          </li>
        ))}
      </ol>
      <div ref={endRef} />
    </section>
  );
}

function UserMessage({ text }: { text: string }) {
  return (
    <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md border border-line bg-orange-soft px-4 py-3 text-[15px] leading-6 text-ink sm:max-w-[70%]">
      <span className="sr-only">Bạn: </span>{text}
    </div>
  );
}

function AssistantMessage({ message, onAction, onRetry, onCopy, busy }: { message: ChatMessage } & Omit<Props, "messages">) {
  const thinking = message.state === "streaming" && !message.text;
  return (
    <article className="max-w-full rounded-2xl rounded-bl-md border border-line bg-card p-4 shadow-card sm:max-w-[92%]">
      <span className="sr-only">Trợ lý: </span>
      {thinking && <AgentSteps steps={message.steps} active />}
      {message.text && <RichText text={message.text} />}
      {message.state === "streaming" && message.text && <p className="mt-2 text-xs text-subtle">Đang viết câu trả lời…</p>}
      {message.cards.map((card, index) => <NutritionTable key={index} card={card} />)}
      {message.state === "error" && (
        <div className="mt-3 rounded-xl border border-coral-line bg-coral-soft p-3 text-sm text-coral-strong" role="alert">
          <p className="font-semibold">Trợ lý chưa trả lời được</p>
          <p className="mt-1">{message.error}</p>
        </div>
      )}
      {message.state === "stopped" && <p className="mt-2 text-sm text-muted">Bạn đã dừng câu trả lời này. Câu hỏi vẫn được giữ, bạn có thể hỏi lại.</p>}
      {message.state === "done" && message.actions.length > 0 && <ActionRow actions={message.actions} onAction={onAction} disabled={busy} />}
      {message.state !== "streaming" && (
        <footer className="mt-3 flex flex-wrap items-center gap-2 border-t border-line pt-3 text-xs text-muted">
          {message.text && <button type="button" className="rounded-lg px-2 py-1 font-semibold hover:bg-orange-soft" onClick={() => onCopy(message.text)}>Sao chép</button>}
          {message.prompt && <button type="button" className="rounded-lg px-2 py-1 font-semibold hover:bg-orange-soft disabled:opacity-50" onClick={() => onRetry(message.prompt!)} disabled={busy}>Hỏi lại</button>}
          {message.steps.length > 0 && (
            <details className="min-w-0">
              <summary className="cursor-pointer rounded-lg px-2 py-1 font-semibold hover:bg-orange-soft">Các bước AI đã làm</summary>
              <AgentSteps steps={message.steps} />
            </details>
          )}
          {message.dataSource && (
            <span className="ml-auto rounded-full border border-line px-2 py-0.5">
              Dữ liệu: {message.dataSource === "supabase" ? "cơ sở dữ liệu dinh dưỡng" : "bộ dữ liệu nội bộ"}{message.datasetVersion ? ` · ${message.datasetVersion}` : ""}
            </span>
          )}
        </footer>
      )}
    </article>
  );
}

function AgentSteps({ steps, active = false }: { steps: string[]; active?: boolean }) {
  return (
    <ol className={active ? "space-y-1 rounded-xl border border-yellow-line bg-yellow-soft p-3 text-sm text-yellow-text" : "mt-2 space-y-1 pl-2 text-xs"}>
      {steps.map((step, index) => {
        const current = active && index === steps.length - 1;
        return (
          <li key={`${step}-${index}`} className="flex items-start gap-2">
            <span aria-hidden="true" className={current ? "mt-1.5 size-2 shrink-0 animate-pulse rounded-full bg-yellow" : "mt-1.5 size-2 shrink-0 rounded-full bg-green"} />
            <span>{step}{current ? "" : <span className="sr-only"> (xong)</span>}</span>
          </li>
        );
      })}
    </ol>
  );
}

function ActionRow({ actions, onAction, disabled }: { actions: ChatAction[]; onAction: (action: ChatAction) => void; disabled: boolean }) {
  const primary = actions.find((action) => action.type === "create_report");
  const others = actions.filter((action) => action !== primary);
  return (
    <div className="mt-4 flex flex-wrap items-center gap-2">
      {primary && <button type="button" className="btn btn-primary disabled:cursor-not-allowed disabled:opacity-60" onClick={() => onAction(primary)} disabled={disabled}>{disabled ? "Đang tạo báo cáo công thức…" : primary.label}</button>}
      {others.map((action) => (
        <button key={`${action.type}-${action.label}`} type="button" onClick={() => onAction(action)} disabled={disabled}
          className={action.type === "open_picker" ? "btn btn-secondary" : "rounded-lg border border-line bg-card px-3 py-1.5 text-sm hover:border-peach disabled:opacity-50"}>
          {action.label}
        </button>
      ))}
    </div>
  );
}

function NutritionTable({ card }: { card: ChatCard }) {
  return (
    <div className="mt-4 overflow-x-auto rounded-xl border border-line">
      <table className="w-full min-w-[520px] text-left text-sm">
        <caption className="bg-cream px-3 py-2 text-left text-xs font-semibold text-muted">Giá trị dinh dưỡng trên {card.basis}</caption>
        <thead className="text-xs text-muted">
          <tr>
            <th scope="col" className="px-3 py-2 font-semibold">Nguyên liệu</th>
            {COLUMNS.map((column) => <th key={column.key} scope="col" className="px-3 py-2 text-right font-semibold">{column.label}<span className="block font-normal">{column.unit}</span></th>)}
          </tr>
        </thead>
        <tbody>
          {card.rows.map((row) => (
            <tr key={row.ingredient_id} className="border-t border-line">
              <th scope="row" className="px-3 py-2 font-semibold">
                {row.name}
                <span className="mt-1 flex flex-wrap gap-1 font-normal">
                  {row.in_season_now !== null && <Badge tone={row.in_season_now ? "good" : "neutral"}>{row.in_season_now ? "Đang mùa" : "Trái mùa"}</Badge>}
                  {row.allergens.map((allergen) => <Badge key={allergen} tone="alert">{allergen}</Badge>)}
                  {!row.verified && <Badge tone="warn">Chưa xác minh</Badge>}
                </span>
              </th>
              {COLUMNS.map((column) => {
                const value = row.per_100g[column.key];
                return <td key={column.key} className="px-3 py-2 text-right tabular-nums">{value === null || value === undefined ? <span className="text-subtle">chưa có</span> : Math.round(value * 10) / 10}</td>;
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}


/** Minimal safe formatter for agent text: paragraphs, "- " bullets and **bold** (no HTML injection). */
function RichText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/);
  return (
    <div className="space-y-3 text-[15px] leading-6 text-ink">
      {blocks.map((block, index) => {
        const lines = block.split("\n").filter(Boolean);
        const bullets = lines.every((line) => line.startsWith("- "));
        if (bullets) return <ul key={index} className="list-disc space-y-1 pl-5">{lines.map((line, i) => <li key={i}>{inline(line.slice(2))}</li>)}</ul>;
        return <p key={index}>{lines.map((line, i) => <Fragment key={i}>{i > 0 && <br />}{line.startsWith("- ") ? <>• {inline(line.slice(2))}</> : inline(line)}</Fragment>)}</p>;
      })}
    </div>
  );
}

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean).map((part, index) =>
    part.startsWith("**") && part.endsWith("**") ? <strong key={index} className="font-semibold">{part.slice(2, -2)}</strong> : <Fragment key={index}>{part}</Fragment>);
}
