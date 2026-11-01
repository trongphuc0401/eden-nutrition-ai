import type { SessionUser } from "@/lib/types";

function initials(user: SessionUser | null) {
  const source = user?.name || user?.email || "Fresh Citrus";
  return source.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase()).join("");
}

/** Decorative avatar: the user's name is always rendered as text next to it. */
export function Avatar({ user }: { user: SessionUser | null }) {
  // eslint-disable-next-line @next/next/no-img-element -- Google avatar host is external and tiny; next/image would need remotePatterns config.
  if (user?.avatar_url) return <img src={user.avatar_url} alt="" referrerPolicy="no-referrer" className="size-9 shrink-0 rounded-full border border-line object-cover" />;
  return <span className="grid size-9 shrink-0 place-items-center rounded-full border border-line bg-orange-soft text-sm font-semibold text-action" aria-hidden="true">{initials(user)}</span>;
}
