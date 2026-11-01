import type { ButtonHTMLAttributes } from "react";

export type ButtonVariant = "primary" | "secondary" | "ghost";
export type ButtonSize = "sm" | "md";

/** Shared class list so links and buttons look the same (see .btn* in globals.css). */
export function buttonClass({ variant = "secondary", size = "md", icon = false, className = "" }: { variant?: ButtonVariant; size?: ButtonSize; icon?: boolean; className?: string } = {}) {
  return ["btn", `btn-${variant}`, size === "sm" && "btn-sm", icon && "btn-icon", className].filter(Boolean).join(" ");
}

type Props = ButtonHTMLAttributes<HTMLButtonElement> & { variant?: ButtonVariant; size?: ButtonSize; icon?: boolean };

export function Button({ variant, size, icon, className, type = "button", ...props }: Props) {
  return <button type={type} className={buttonClass({ variant, size, icon, className })} {...props} />;
}
