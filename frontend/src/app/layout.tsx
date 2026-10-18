import type { Metadata } from "next";
import { Inter, Poppins } from "next/font/google";
import "./globals.css";
import { Providers } from "./providers";

const inter = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-reference" });
const poppins = Poppins({ subsets: ["latin", "latin-ext"], weight: ["400", "500", "600", "700"], variable: "--font-ui" });

export const metadata: Metadata = {
  title: "Fresh Citrus | AI Wellness",
  description: "Trợ lý AI tạo sinh tố theo hồ sơ và nguyên liệu địa phương.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="vi" className={`${inter.variable} ${poppins.variable}`} suppressHydrationWarning><body suppressHydrationWarning><Providers>{children}</Providers></body></html>;
}
