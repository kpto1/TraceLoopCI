import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "TraceLoop CI",
  description: "LLM behavioral regression testing",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="bg-background text-foreground min-h-screen flex flex-col">
        <nav className="border-b border-zinc-800 px-6 py-3 flex items-center gap-6 text-sm">
          <Link href="/" className="font-bold text-base tracking-tight">
            TraceLoop CI
          </Link>
          <Link href="/traces" className="text-zinc-400 hover:text-zinc-100 transition-colors">
            Traces
          </Link>
        </nav>
        <main className="flex-1">{children}</main>
      </body>
    </html>
  );
}
