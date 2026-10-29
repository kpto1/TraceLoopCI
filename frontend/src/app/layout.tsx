import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "TraceLoop CI",
  description: "LLM behavioral regression testing",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <nav>
          <Link href="/" className="brand">TraceLoop CI</Link>
          <Link href="/traces">Traces</Link>
          <Link href="/datasets">数据集与评测</Link>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  );
}
