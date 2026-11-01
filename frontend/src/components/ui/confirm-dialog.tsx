"use client";

import { useId } from "react";
import { Button } from "./button";
import { Modal } from "./modal";

/** Confirmation step for destructive actions (rulebook: risky actions are confirmed). */
export function ConfirmDialog({ open, title, description, confirmLabel, onConfirm, onCancel }: {
  open: boolean; title: string; description: string; confirmLabel: string; onConfirm: () => void; onCancel: () => void;
}) {
  const titleId = useId();
  return (
    <Modal open={open} onClose={onCancel} labelledBy={titleId} panelClassName="max-w-md p-6">
      <h2 id={titleId} className="text-lg font-semibold text-strong">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-muted">{description}</p>
      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button onClick={onCancel} data-autofocus>Hủy</Button>
        <Button variant="primary" onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}
