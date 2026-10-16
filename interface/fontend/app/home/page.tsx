'use client'

import { useLayoutEffect, useState } from 'react'
import { flushSync } from 'react-dom'
import { HeroShowcase } from './HeroShowcase'
import { BrandLogo } from '@/components/BrandLogo'
import { ThemeToggle } from '@/components/ThemeToggle'
import './home.css'
import './home-refresh.css'
import './banner-layout-v2.css'
import './home-header-theme.css'
import { ArrowRight, Check, CircleAlert, LogIn, Menu, Pill, ShieldCheck, Sparkles, Stethoscope, X } from 'lucide-react'
const iconHome = '/home-slides/iconhome.svg'
const features = [
  { title: 'Chuẩn hóa tên thuốc', text: 'Nhận diện tên thương mại, hoạt chất, liều dùng và nhóm sản phẩm.', icon: Pill },
  { title: 'Tra tương tác toàn diện', text: 'Đối chiếu thuốc–thuốc và thuốc–thực phẩm chức năng.', icon: CircleAlert },
  { title: 'Giải thích dễ hiểu', text: 'Xếp mức độ nghiêm trọng và gợi ý câu hỏi cho bác sĩ, dược sĩ.', icon: ShieldCheck },
]

const testimonials = [
  { quote: 'Giao diện rất dễ dùng. Tôi biết ngay cần hỏi dược sĩ điều gì trước khi uống thêm thuốc.', name: 'Nguyễn Minh Anh', role: 'Người dùng MediCheck' },
  { quote: 'MediCheck giúp tôi rà soát cả vitamin và thuốc không kê đơn trong cùng một lần kiểm tra.', name: 'Trần Quốc Huy', role: 'Người chăm sóc gia đình' },
  { quote: 'Phần giải thích theo mức độ ưu tiên rõ ràng, không làm người dùng hoang mang.', name: 'Lê Thu Hà', role: 'Dược sĩ tư vấn' },
]

export default function Page() {
  const [menuOpen, setMenuOpen] = useState(false)
  const [chatOpen, setChatOpen] = useState(false)
  const [darkMode, setDarkMode] = useState(false)

  useLayoutEffect(() => {
    setDarkMode(document.documentElement.classList.contains('dark'))
  }, [])

  const changeTheme = (next: boolean) => {
    const commitTheme = () => {
      flushSync(() => {
        const root = document.documentElement
        root.classList.toggle('dark', next)
        root.classList.toggle('light', !next)
        root.style.colorScheme = next ? 'dark' : 'light'
        setDarkMode(next)
      })
      try {
        window.localStorage.setItem('medicheck-theme', next ? 'dark' : 'light')
      } catch {
        // Keep the selected theme for this page when storage is unavailable.
      }
    }

    if (!document.startViewTransition || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      commitTheme()
      return
    }

    const root = document.documentElement
    root.classList.add('home-theme-transition')
    try {
      const transition = document.startViewTransition(commitTheme)
      transition.finished.then(
        () => root.classList.remove('home-theme-transition'),
        () => root.classList.remove('home-theme-transition'),
      )
    } catch {
      root.classList.remove('home-theme-transition')
      commitTheme()
    }
  }

  return (
    <main className={`medicheck-home min-h-screen bg-white text-slate-900 transition-colors duration-500 ${darkMode ? 'theme-dark' : ''}`}>
      <header className="home-header fixed left-1/2 top-4 z-40 flex w-[calc(100%-2rem)] max-w-6xl -translate-x-1/2 items-center justify-between gap-3 rounded-full border border-white/70 bg-white/55 px-4 py-2 shadow-lg shadow-sky-100/30 backdrop-blur-xl sm:px-6">
        <a href="#top" aria-label="Về đầu trang" className="home-header-brand flex shrink-0 items-center">
          <img src="/brand-icon.png" alt="VINMEC" className="home-header-logo" />
        </a>
        <nav className="hidden items-center gap-7 text-xs font-semibold text-slate-500 lg:flex">
          <a href="#features" className="transition hover:text-teal-600">Tính năng</a>
          <a href="#process" className="transition hover:text-teal-600">Quy trình</a>
          <a href="#stories" className="transition hover:text-teal-600">Câu chuyện</a>
          <a href="#safety" className="transition hover:text-teal-600">An toàn thuốc</a>
        </nav>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ThemeToggle checked={darkMode} onCheckedChange={changeTheme} compact />
          <button onClick={() => setChatOpen(true)} className="home-header-cta hidden items-center rounded-full bg-teal-600 px-6 py-3 text-sm font-bold text-white shadow-md shadow-teal-200 transition hover:bg-teal-700 sm:inline-flex">Bắt đầu kiểm tra <ArrowRight className="ml-2 inline size-4" /></button>
          <a href="/login" aria-label="Đăng nhập" title="Đăng nhập" className="home-header-login hidden items-center justify-center rounded-full border border-teal-200/80 bg-white/60 text-teal-700 transition hover:bg-teal-50 sm:inline-flex"><LogIn className="size-4" /></a>
        </div>
        <button aria-label="Mở menu" onClick={() => setMenuOpen(!menuOpen)} className="rounded-lg p-2 text-slate-500 lg:hidden"><Menu className="size-5" /></button>
      </header>
      {menuOpen && <div className="fixed left-4 right-4 top-20 z-30 rounded-2xl border border-sky-100 bg-white p-4 shadow-xl lg:hidden"><div className="flex flex-col gap-4 text-sm font-semibold text-slate-600"><a href="#features" onClick={() => setMenuOpen(false)}>Tính năng</a><a href="#process" onClick={() => setMenuOpen(false)}>Quy trình</a><a href="#stories" onClick={() => setMenuOpen(false)}>Câu chuyện</a><a href="/login" onClick={() => setMenuOpen(false)} className="home-menu-login flex items-center gap-2 rounded-xl border border-teal-200 px-4 py-3"><LogIn className="size-4" />Đăng nhập</a><button onClick={() => { setMenuOpen(false); setChatOpen(true) }} className="rounded-xl bg-teal-600 px-4 py-3 text-white">Bắt đầu kiểm tra</button></div></div>}

      <section id="top" className="relative overflow-hidden bg-[#e9f8f7] px-5 pb-20 pt-36 sm:px-8 lg:pb-28 lg:pt-44">
        <div className="absolute -right-32 -top-32 size-[440px] rounded-full bg-teal-200/40 blur-3xl" />
        <div className="absolute -bottom-40 left-1/3 size-[420px] rounded-full bg-cyan-100/80 blur-3xl" />
        <div className="relative mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[1fr_0.9fr]">
          <div>
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[0.18em] text-teal-700"><Sparkles className="size-3.5" /> Trợ lý an toàn thuốc</div>
            <h1 className="max-w-xl text-5xl font-bold leading-[0.98] tracking-[-0.05em] text-slate-900 sm:text-6xl" style={{ fontFamily: 'var(--font-inter), system-ui, sans-serif' }}>An tâm hơn với <span className="text-teal-600">mỗi loại thuốc.</span></h1>
            <p className="mt-6 max-w-lg text-base leading-7 text-slate-600">MediCheck giúp bạn kiểm tra tương tác giữa thuốc kê đơn, thuốc OTC và thực phẩm chức năng bằng một cuộc trò chuyện rõ ràng, dễ hiểu.</p>
            <div className="mt-8 flex flex-wrap items-center gap-3"><button onClick={() => setChatOpen(true)} className="rounded-full bg-teal-600 px-6 py-3.5 text-sm font-bold text-white shadow-xl shadow-teal-200 transition hover:-translate-y-0.5 hover:bg-teal-700">Kiểm tra danh sách thuốc <ArrowRight className="ml-2 inline size-4" /></button><a href="#process" className="rounded-full border border-teal-200 bg-white/60 px-5 py-3.5 text-sm font-bold text-teal-700 transition hover:bg-white">Xem cách hoạt động</a></div>
              </div>
          <HeroShowcase onStart={() => setChatOpen(true)} />
        </div>
      </section>

      <section id="features" className="relative overflow-hidden bg-[#f7fbfb] px-5 py-20 text-slate-900 sm:px-8 lg:py-28"><div className="absolute -left-40 top-10 size-96 rounded-full bg-teal-100/60 blur-3xl" /><div className="absolute -right-32 bottom-0 size-96 rounded-full bg-cyan-100/70 blur-3xl" /><div className="relative mx-auto max-w-6xl"><div className="grid gap-8 lg:grid-cols-[1fr_0.72fr] lg:items-end"><div><div className="mb-5 inline-flex items-center gap-2 rounded-full border border-teal-200 bg-white px-3 py-1.5 text-[10px] font-black uppercase tracking-[0.2em] text-teal-700 shadow-sm"><ShieldCheck className="size-3.5" /> Kiến thức rõ ràng</div><h2 className="max-w-2xl text-4xl font-black leading-[1.08] tracking-[-0.04em] text-slate-900 sm:text-5xl">Mọi thông tin bạn cần để dùng thuốc <span className="text-teal-600">an toàn hơn.</span></h2></div><p className="max-w-md text-sm leading-7 text-slate-500">Từ tên thuốc đến những tương tác khó nhận biết, mọi thứ được gom lại trong một trải nghiệm đơn giản để bạn tự tin hỏi đúng người, đúng lúc.</p></div><div className="mt-12 grid gap-4 md:grid-cols-3">{features.map(({ title, text, icon: Icon }, index) => <article key={title} className={`group relative overflow-hidden rounded-[1.5rem] border p-6 transition duration-300 hover:-translate-y-1 hover:shadow-xl ${index === 1 ? 'border-teal-600 bg-teal-600 text-white shadow-xl shadow-teal-900/15' : 'border-teal-100 bg-white shadow-sm hover:border-teal-300'}`}><div className={`flex size-12 items-center justify-center rounded-2xl ${index === 1 ? 'bg-white/20 text-white' : 'bg-teal-400/15 text-teal-300'}`}><Icon className="size-5" /></div><p className={`mt-8 text-[10px] font-black uppercase tracking-[0.18em] ${index === 1 ? 'text-teal-50' : 'text-teal-300'}`}>0{index + 1}</p><h3 className="mt-3 text-lg font-black">{title}</h3><p className={`mt-3 text-sm leading-6 ${index === 1 ? 'text-teal-50/85' : 'text-slate-400'}`}>{text}</p><button onClick={() => setChatOpen(true)} className={`mt-8 text-xs font-bold transition group-hover:translate-x-1 ${index === 1 ? 'text-white' : 'text-teal-300'}`}>Khám phá cùng MediCheck <ArrowRight className="ml-1 inline size-3.5" /></button></article>)}</div></div></section>

      <section id="process" className="bg-[#eff9f8] px-5 py-20 sm:px-8 lg:py-28"><div className="mx-auto grid max-w-6xl items-center gap-14 lg:grid-cols-[0.9fr_1fr]"><div className="rounded-[2rem] bg-teal-700 p-7 text-white shadow-2xl shadow-teal-100 sm:p-10"><div className="mb-10 flex items-center justify-between"><span className="rounded-full bg-white/15 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-teal-50">Quy trình 4 bước</span><Stethoscope className="size-6 text-teal-100" /></div>{['Nhận danh sách thuốc', 'Chuẩn hóa tên và hoạt chất', 'Tra tương tác thuốc–thuốc, thuốc–thực phẩm', 'Xếp mức độ và gợi ý trao đổi'].map((step, index) => <div key={step} className="flex gap-4 border-t border-white/15 py-5"><span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-white text-xs font-black text-teal-700">{index + 1}</span><div><p className="font-bold">{step}</p><p className="mt-1 text-xs leading-5 text-teal-100/70">{['Thêm thuốc kê đơn, thuốc không kê đơn và vitamin bạn đang dùng.', 'Làm rõ tên thuốc và thành phần để tra cứu đúng thông tin.', 'Xem những kết hợp cần lưu ý trong danh sách của bạn.', 'Hiểu thông tin và chuẩn bị câu hỏi cho bác sĩ, dược sĩ.'][index]}</p></div></div>)}</div><div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-teal-600">Từ danh sách đến hành động</p><h2 className="mt-4 text-3xl font-black tracking-tight sm:text-4xl" style={{ fontFamily: 'inherit' }}>Bạn luôn biết bước<br />tiếp theo là gì.</h2><p className="mt-5 max-w-lg text-sm leading-7 text-slate-500">Không chỉ đưa ra cảnh báo, MediCheck giúp bạn chuẩn bị câu hỏi cụ thể để trao đổi với bác sĩ hoặc dược sĩ. Không tự ý ngừng hay thay đổi thuốc.</p><button onClick={() => setChatOpen(true)} className="mt-8 rounded-full bg-teal-600 px-6 py-3.5 text-sm font-bold text-white shadow-lg shadow-teal-200 hover:bg-teal-700">Bắt đầu cùng MediCheck <ArrowRight className="ml-2 inline size-4" /></button></div></div></section>

      <section id="stories" className="relative overflow-hidden bg-white px-5 py-20 sm:px-8 lg:py-28"><div className="absolute right-0 top-0 h-full w-1/3 bg-gradient-to-l from-teal-50/80 to-transparent" /><div className="relative mx-auto max-w-6xl"><div className="flex flex-col justify-between gap-6 md:flex-row md:items-end"><div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-teal-700">Người dùng nói gì</p><h2 className="mt-4 max-w-xl text-4xl font-black leading-[1.08] tracking-[-0.04em] text-slate-900 sm:text-5xl">An tâm hơn trong <span className="text-teal-600">mỗi quyết định.</span></h2></div><p className="max-w-xs text-sm leading-6 text-slate-500">Một quyết định tốt bắt đầu từ thông tin dễ hiểu và một cuộc trao đổi đúng lúc.</p></div><div className="mt-14 grid gap-5 text-left md:grid-cols-3">{testimonials.map((item, index) => <article key={item.name} className={`relative flex min-h-64 flex-col rounded-[1.75rem] p-7 shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl ${index === 1 ? 'bg-slate-900 text-white shadow-slate-200' : 'border border-teal-100/80 bg-white'}`}><div className="flex items-center justify-between"><div className={`flex size-10 items-center justify-center rounded-full text-sm font-black ${index === 1 ? 'bg-teal-500 text-white' : 'bg-teal-100 text-teal-700'}`}>{item.name.charAt(0)}</div><div className={`flex gap-1 text-xs ${index === 1 ? 'text-teal-300' : 'text-teal-600'}`} aria-label="Đánh giá 5 sao"><img src={iconHome} alt="" /></div></div><div className={`mt-7 text-4xl font-black leading-none ${index === 1 ? 'text-teal-400' : 'text-teal-600'}`}></div><p className={`mt-2 text-sm leading-6 ${index === 1 ? 'text-slate-200' : 'text-slate-600'}`}>{item.quote}</p><div className="mt-auto border-t border-current/10 pt-5"><p className="text-xs font-black">{item.name}</p><p className={`mt-1 text-[10px] ${index === 1 ? 'text-slate-400' : 'text-slate-400'}`}>{item.role}</p></div></article>)}</div></div></section>

      <section id="safety" className="px-5 pb-20 sm:px-8"><div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-8 rounded-[2rem] bg-[#dff4f2] p-8 sm:p-12 lg:flex-row lg:items-center"><div><p className="text-[10px] font-black uppercase tracking-[0.2em] text-teal-700" style={{ fontFamily: 'inherit' }}>Sẵn sàng bắt đầu?</p><h2 className="mt-4 max-w-lg text-3xl font-black tracking-tight text-slate-900 sm:text-4xl" style={{ fontFamily: 'inherit' }}>Kiểm tra danh sách thuốc của bạn ngay hôm nay.</h2></div><button onClick={() => setChatOpen(true)} className="shrink-0 rounded-full bg-teal-600 px-7 py-4 text-sm font-bold text-white shadow-xl shadow-teal-200 hover:bg-teal-700" style={{ fontFamily: 'var(--font-inter), system-ui, sans-serif' }}>Mở MediCheck <ArrowRight className="ml-2 inline size-4" /></button></div></section>

      <footer className="border-t border-slate-100 px-5 py-8 sm:px-8"><div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left"><div className="flex items-center gap-2"><BrandLogo size={32} className="bg-white" /><span className="font-black text-slate-800">Medi<span className="text-teal-600">Check</span></span></div><p className="text-[10px] text-slate-400">Thông tin tham khảo, không thay thế chẩn đoán y khoa.</p></div></footer>

      {chatOpen && <div className="fixed inset-0 z-50 flex items-end justify-center bg-slate-950/30 p-3 backdrop-blur-sm sm:items-center"><div className="flex h-[min(720px,calc(100vh-1.5rem))] w-full max-w-2xl flex-col overflow-hidden rounded-3xl bg-white shadow-2xl"><div className="flex items-center justify-between border-b border-slate-100 px-5 py-4"><div className="flex items-center gap-3"><BrandLogo size={36} className="rounded-xl bg-white" /><div><p className="text-sm font-black text-slate-800">MediCheck Assistant</p><p className="text-[10px] text-emerald-600">Đang hoạt động</p></div></div><button aria-label="Đóng" onClick={() => setChatOpen(false)} className="rounded-lg p-2 text-slate-400 hover:bg-slate-50"><X className="size-5" /></button></div><div className="flex flex-1 flex-col justify-end gap-4 overflow-y-auto bg-[#f5fbfb] p-5"><div className="max-w-[85%] rounded-2xl rounded-tl-sm border border-teal-100 bg-white p-4 text-sm leading-6 text-slate-600 shadow-sm">Xin chào. Hãy gửi danh sách thuốc, thuốc OTC, vitamin hoặc thực phẩm chức năng bạn đang dùng. Tôi sẽ chuẩn hóa tên, tra tương tác và giải thích kết quả theo mức độ.</div><div className="max-w-[85%] self-end rounded-2xl rounded-tr-sm bg-teal-600 p-4 text-sm leading-6 text-white">Tôi muốn bắt đầu kiểm tra danh sách thuốc.</div><button onClick={() => setChatOpen(false)} className="self-start rounded-full bg-teal-100 px-4 py-2 text-xs font-bold text-teal-700">Tiếp tục với bản đầy đủ <ArrowRight className="ml-1 inline size-3.5" /></button></div><div className="border-t border-slate-100 p-4"><div className="flex items-center gap-2 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-400">Nhập tên thuốc hoặc đặt câu hỏi...<ArrowRight className="ml-auto size-4 text-teal-500" /></div><p className="mt-2 text-center text-[10px] text-slate-400">MediCheck không thay thế tư vấn y tế chuyên môn.</p></div></div></div>}
    </main>
  )
}
