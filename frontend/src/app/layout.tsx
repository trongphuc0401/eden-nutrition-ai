import type { Metadata, Viewport } from "next";
import { Poppins } from "next/font/google";
import "./globals.css";

const poppins = Poppins({ subsets: ["latin", "latin-ext"], weight: ["400", "500", "600", "700"], variable: "--font-ui" });

export const metadata: Metadata = {
  title: "Fresh Citrus | Trợ lý dinh dưỡng AI",
  description: "Trợ lý AI tạo sinh tố theo hồ sơ và nguyên liệu địa phương.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { themeColor: "#fffdf5" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi" className={poppins.variable} suppressHydrationWarning><body suppressHydrationWarning>{children}</body></html>;
}
