"use client";

import { useState } from "react";
import { LoaderCircle, LogOut } from "lucide-react";

export function LogoutButton({ onLogout, onError, className = "", compact = false }: {
  onLogout: () => Promise<void>;
  onError: (message: string) => void;
  className?: string;
  compact?: boolean;
}) {
  const [busy, setBusy] = useState(false);
  async function logout() {
    if (busy) return;
    setBusy(true);
    try { await onLogout(); }
    catch (error) { onError((error as Error).message); }
    finally { setBusy(false); }
  }
  return <button type="button" onClick={() => void logout()} disabled={busy} aria-label={busy ? "Đang đăng xuất" : "Đăng xuất"} title="Đăng xuất" className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold text-slate-600 transition hover:bg-rose-50 hover:text-rose-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sky-500 disabled:opacity-60 ${className}`}>
    {busy ? <LoaderCircle size={17} className="animate-spin" /> : <LogOut size={17} />}
    {!compact && <span>{busy ? "Đang đăng xuất…" : "Đăng xuất"}</span>}
  </button>;
}
