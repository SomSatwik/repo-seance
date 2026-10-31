import type { Metadata } from "next";
import { Geist, Geist_Mono, Creepster, MedievalSharp } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const creepster = Creepster({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-creepster",
});

const medieval = MedievalSharp({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-medieval",
});

export const metadata: Metadata = {
  title: "Repo Séance — Haunted Codebases & Forensic Ghosts",
  description: "Find and interrogate haunted repositories, dormant git histories, and forensic code ghosts.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${creepster.variable} ${medieval.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
