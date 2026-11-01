"use client";

import { useEffect, useRef, useState } from "react";
import { Avatar } from "@/components/layout/avatar";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import type { SessionUser } from "@/lib/types";

export function Topbar({
  title,
  onMenu,
  onContext,
  user,
  onOpenProfile,
  onLogout,
}: {
  title: string;
  onMenu: () => void;
  onContext?: () => void;
  user: SessionUser | null;
  onOpenProfile?: () => void;
  onLogout?: () => void;
}) {
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!dropdownOpen) return;
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDropdownOpen(false);
    };
    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [dropdownOpen]);

  return (
    <header className="sticky top-0 z-30 flex min-h-16 shrink-0 items-center justify-between gap-3 border-b border-line bg-card/95 px-4 shadow-bar backdrop-blur-md sm:px-6 lg:min-h-20">
      <div className="flex min-w-0 items-center gap-2">
        <Button variant="ghost" icon className="xl:hidden" onClick={onMenu} aria-label="Mở điều hướng"><Icon name="menu" /></Button>
        <h1 className="truncate text-h1-mobile font-semibold tracking-tight text-strong lg:text-h1">{title}</h1>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <span className="hidden items-center gap-2 rounded-full border border-green-line bg-green-soft px-3 py-1 text-xs font-semibold text-green-text sm:flex">
          <span className="relative flex size-2">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#22c55e] opacity-75"></span>
            <span className="relative inline-flex size-2 rounded-full bg-[#22c55e]"></span>
          </span>
          Hệ thống ổn định
        </span>
        {onContext && <Button size="sm" className="lg:hidden" onClick={onContext} aria-label="Mở thông tin và ngữ cảnh"><Icon name="panel" className="size-4" /><span className="hidden sm:inline">Ngữ cảnh</span></Button>}
        <div ref={dropdownRef} className="relative">
          <button
            type="button"
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex items-center rounded-full transition hover:ring-2 hover:ring-brand focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
            aria-label="Tài khoản và cài đặt"
            aria-haspopup="menu"
            aria-expanded={dropdownOpen}
          >
            <Avatar user={user} />
          </button>
          {dropdownOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 rounded-2xl border border-line bg-card p-1.5 shadow-card z-50">
              {user && (
                <div className="border-b border-line px-3 py-2">
                  <strong className="block truncate text-sm text-strong">{user.name ?? "Tài khoản Google"}</strong>
                  {user.email && <small className="block truncate text-xs text-muted">{user.email}</small>}
                </div>
              )}
              <div className="pt-1 space-y-0.5" role="menu">
                {onOpenProfile && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setDropdownOpen(false);
                      onOpenProfile();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm text-ink transition hover:bg-orange-soft hover:text-action"
                  >
                    <Icon name="user" className="size-4 text-action" />
                    <span>Hồ sơ sức khỏe</span>
                  </button>
                )}
                {onLogout && (
                  <button
                    type="button"
                    role="menuitem"
                    onClick={() => {
                      setDropdownOpen(false);
                      onLogout();
                    }}
                    className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-sm text-coral-strong transition hover:bg-coral-soft"
                  >
                    <Icon name="logout" className="size-4" />
                    <span>Đăng xuất</span>
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
