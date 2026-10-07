"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";
import { LoaderCircle } from "lucide-react";
import { api, ApiError, type AuthUser } from "@/lib/api";

export function AuthGate({ children }: { children: (user: AuthUser, logout: () => Promise<void>) => ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api<AuthUser>("/auth/me")
      .then(value => { if (!cancelled) setUser(value); })
      .catch(e => {
        if (cancelled) return;
        if (e instanceof ApiError && e.status === 401) router.replace("/login");
        else setError(e.message);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    const expired = () => { setUser(null); router.replace("/login"); };
    window.addEventListener("session-expired", expired);
    return () => { cancelled = true; window.removeEventListener("session-expired", expired); };
  }, [retry, router]);

  async function logout() {
    await api("/auth/logout", {});
    setUser(null);
    router.replace("/login");
  }

  if (loading || !user) return <main className="flex min-h-dvh items-center justify-center bg-background p-6 text-foreground">
    {error ? <div role="alert" className="max-w-md rounded-xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-700">
      {error}<button type="button" onClick={() => setRetry(x => x + 1)} className="ml-3 rounded font-semibold underline focus-visible:outline-2 focus-visible:outline-offset-4">Thử kết nối lại</button>
    </div> : <div role="status" className="flex items-center gap-3"><LoaderCircle className="animate-spin" /> {loading ? "Đang kiểm tra phiên đăng nhập…" : "Đang chuyển đến trang đăng nhập…"}</div>}
  </main>;
  return children(user, logout);
}
