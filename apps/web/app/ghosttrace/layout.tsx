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
    <div className="h-full flex flex-col">{children}</div>
  );
}
