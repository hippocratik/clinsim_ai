import type { Metadata } from "next";
import Link from "next/link";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "ClinSim AI",
  description: "Interactive clinical case simulator for medical trainees.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${inter.variable} bg-slate-100 text-slate-900 antialiased`}
      >
        <div className="min-h-screen bg-gradient-to-br from-slate-100 via-slate-50 to-emerald-50">
          <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
            <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
              <Link href="/" className="group">
                <p className="text-sm font-semibold uppercase tracking-[0.22em] text-emerald-600 group-hover:text-emerald-700">
                  ClinSim AI
                </p>
                <p className="text-[13px] text-slate-500 group-hover:text-slate-700">
                  Real-data grounded clinical case simulation
                </p>
              </Link>
              <span className="rounded-full bg-emerald-50 px-3 py-1 text-[11px] font-semibold text-emerald-700 ring-1 ring-emerald-100">
                Hackathon MVP
              </span>
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}

