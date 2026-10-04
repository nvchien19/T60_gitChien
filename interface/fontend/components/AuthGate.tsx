"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { Eye, EyeOff, Pill, Stethoscope, LockKeyhole, LoaderCircle } from "lucide-react";
import { api, ApiError, type AuthUser } from "@/lib/api";
import { BrandLogo } from "@/components/BrandLogo";

export function AuthGate({ children }: { children: (user: AuthUser, logout: () => Promise<void>) => ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    api<AuthUser>("/auth/me").then(value => { if (!cancelled) setUser(value); })
      .catch(e => { if (!cancelled && (!(e instanceof ApiError) || e.status !== 401)) setError(e.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    const expired = () => { setUser(null); };
    window.addEventListener("session-expired", expired);
    return () => { cancelled = true; window.removeEventListener("session-expired", expired); };
  }, [retry]);
  async function logout() {
    await api("/auth/logout", {});
    setUser(null);
  }
  if (loading) return <main className="login-scene"><div role="status" className="login-loading"><LoaderCircle className="animate-spin" /> Đang kiểm tra phiên đăng nhập…</div></main>;
  if (!user) return <LoginScreen onLogin={setUser} connectionError={error} onRetry={() => setRetry(x => x + 1)} />;
  return children(user, logout);
}

function LoginScreen({ onLogin, connectionError, onRetry }: { onLogin: (user: AuthUser) => void; connectionError: string; onRetry: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [help, setHelp] = useState(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try { onLogin(await api<AuthUser>("/auth/login", { email: email.trim(), password, remember })); }
    catch (e) { setError((e as Error).message); }
    finally { setBusy(false); }
  }
  return <main className="login-scene">
    <div className="login-art" aria-hidden="true">
      <div className="medical-grid" />
      <i className="capsule capsule-one" /><i className="capsule capsule-two" /><i className="capsule capsule-three" /><i className="capsule capsule-four" />
      <span className="molecule molecule-one" /><span className="molecule molecule-two" />
    </div>
    <a href="/" className="login-brand"><BrandLogo size={32} /><span>Medication <strong>Safety</strong></span></a>
    <section className="login-card" aria-labelledby="login-title">
      <div className="login-symbol"><BrandLogo size={72} alt="Logo Medication Safety" /></div>
      <h1 id="login-title">Chào mừng trở lại!</h1>
      <p className="login-subtitle">Đăng nhập để kết nối và chăm sóc an toàn hơn.</p>
      <div className="login-roles"><span><Stethoscope size={15} /> Bác sĩ</span><span><Pill size={15} /> Dược sĩ</span></div>
      <form onSubmit={submit} className="login-form">
        <label htmlFor="login-email">Email</label>
        <input id="login-email" name="email" type="email" autoComplete="username" placeholder="VD: contact@pharmacy.vn" required maxLength={254} value={email} onChange={e => setEmail(e.target.value)} disabled={busy} />
        <label htmlFor="login-password">Mật khẩu</label>
        <div className="login-password"><input id="login-password" name="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Nhập mật khẩu" required maxLength={256} value={password} onChange={e => setPassword(e.target.value)} disabled={busy} /><button type="button" aria-label={showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu"} aria-pressed={showPassword} onClick={() => setShowPassword(x => !x)}>{showPassword ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>
        <div className="login-options"><label><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} disabled={busy} /> Ghi nhớ tài khoản</label><button type="button" onClick={() => setHelp(x => !x)} aria-expanded={help}>Quên mật khẩu?</button></div>
        {help && <p className="login-help" role="status">Liên hệ quản trị viên để đặt lại mật khẩu cho tài khoản của bạn.</p>}
        {(error || connectionError) && <div className="login-error" role="alert">{error || connectionError}{connectionError && <button type="button" onClick={onRetry}>Thử kết nối lại</button>}</div>}
        <button type="submit" className="login-submit" disabled={busy}>{busy ? <><LoaderCircle size={17} className="animate-spin" /> Đang đăng nhập…</> : "Đăng nhập"}</button>
      </form>
      <p className="login-note"><LockKeyhole size={13} /> Tài khoản được cấp bởi quản trị viên</p>
    </section>
    <p className="login-footer">Kết nối bác sĩ & dược sĩ · Đồng hành cùng an toàn dùng thuốc</p>
  </main>;
}
