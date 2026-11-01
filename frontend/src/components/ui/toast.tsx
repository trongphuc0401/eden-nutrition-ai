import { Icon } from "./icon";

export type Toast = { text: string; tone?: "success" | "error" } | null;

export function ToastMessage({ toast, close }: { toast: Toast; close: () => void }) {
  if (!toast) return null;
  const error = toast.tone === "error";
  return (
    <div role={error ? "alert" : "status"} className={`fixed inset-x-4 top-4 z-50 ml-auto max-w-sm rounded-xl border px-4 py-3 text-sm shadow-card ${error ? "border-coral-line bg-coral-soft text-coral-strong" : "border-green-line bg-green-soft text-green-text"}`}>
      <div className="flex items-start gap-3">
        <Icon name={error ? "alert" : "check"} className="mt-0.5 size-4" />
        <span className="flex-1">{toast.text}</span>
        <button onClick={close} aria-label="Đóng thông báo" className="-m-1 rounded p-1 hover:bg-white/60"><Icon name="close" className="size-4" /></button>
      </div>
    </div>
  );
}
