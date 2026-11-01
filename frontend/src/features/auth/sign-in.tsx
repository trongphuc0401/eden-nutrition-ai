import { Logo } from "@/components/brand/logo";
import { buttonClass } from "@/components/ui/button";
import { Icon } from "@/components/ui/icon";
import { googleLoginUrl } from "@/lib/api";

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="size-5 rounded-full bg-white p-0.5" aria-hidden="true">
      <path fill="#4285F4" d="M22.6 12.2c0-.8-.1-1.5-.2-2.2H12v4.2h5.9a5 5 0 0 1-2.2 3.3v2.7h3.6c2-1.9 3.3-4.7 3.3-8z" />
      <path fill="#34A853" d="M12 23c3 0 5.5-1 7.3-2.7l-3.6-2.8c-1 .7-2.2 1.1-3.7 1.1-2.9 0-5.3-1.9-6.2-4.5H2.1v2.8A11 11 0 0 0 12 23z" />
      <path fill="#FBBC05" d="M5.8 14.1a6.6 6.6 0 0 1 0-4.2V7.1H2.1a11 11 0 0 0 0 9.8z" />
      <path fill="#EA4335" d="M12 5.4c1.6 0 3.1.6 4.2 1.7l3.2-3.2A11 11 0 0 0 2.1 7.1l3.7 2.8C6.7 7.3 9.1 5.4 12 5.4z" />
    </svg>
  );
}

export function SignIn({ checking }: { checking: boolean }) {
  return (
    <main className="grid min-h-dvh place-items-center bg-cream p-4">
      <section className="grid w-full max-w-5xl overflow-hidden rounded-[28px] border border-line bg-card shadow-card md:grid-cols-[1.1fr_.9fr]">
        <div className="p-8 sm:p-12">
          <Logo subtitle={false} />
          <p className="mt-12 text-sm font-semibold tracking-wide text-action">AI WELLNESS</p>
          <h1 className="mt-3 max-w-lg text-4xl font-semibold leading-tight text-strong sm:text-5xl">Bắt đầu một thói quen tươi mới.</h1>
          <p className="mt-5 max-w-lg text-base leading-7 text-muted">Tạo công thức sinh tố phù hợp với hồ sơ sức khỏe, nguyên liệu bạn chọn và vùng đang sống.</p>
          {checking
            ? <p className={buttonClass({ className: "mt-8 w-full sm:w-auto" })} role="status" aria-live="polite"><span className="size-2 animate-pulse rounded-full bg-brand" />Đang kiểm tra phiên đăng nhập…</p>
            : <a className={buttonClass({ variant: "primary", className: "mt-8 w-full sm:w-auto" })} href={googleLoginUrl}><GoogleMark />Tiếp tục với Google</a>}
          <p className="mt-3 text-xs leading-5 text-muted">Chúng tôi chỉ dùng tên, email và ảnh đại diện Google để lưu báo cáo của riêng bạn.</p>
        </div>
        <div className="relative min-h-72 overflow-hidden bg-orange-soft p-8" aria-hidden="true">
          <div className="absolute -right-10 -top-12 size-56 rounded-full bg-yellow opacity-60" />
          <div className="absolute -bottom-16 -left-12 size-64 rounded-full bg-green opacity-40" />
          <div className="relative mt-20 rounded-card border border-white/80 bg-white/90 p-5 shadow-card">
            <span className="grid size-12 place-items-center rounded-2xl bg-orange-soft text-brand"><Icon name="leaf" className="size-6" /></span>
            <p className="mt-3 text-lg font-semibold text-strong">Nguyên liệu bạn chọn</p>
            <p className="mt-2 text-sm leading-6 text-muted">Rõ nguồn gốc, rõ ngữ cảnh và luôn có quyền điều chỉnh trước khi tạo.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
