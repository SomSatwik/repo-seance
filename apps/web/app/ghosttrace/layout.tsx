"use strict";

import type { Metadata } from "next";
import { Geist_Mono } from "next/font/google";
import "@/app/globals.css";

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GhostTrace",
  description: "Terminal companion — deterministic safety classifications.",
};

export default function GhostTraceLayout({
  children,
}: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
