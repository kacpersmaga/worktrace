import type { Metadata } from "next";
import { Bricolage_Grotesque, Instrument_Sans, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const body = Instrument_Sans({ subsets: ["latin", "latin-ext"], variable: "--font-body" });
const heading = Bricolage_Grotesque({ subsets: ["latin", "latin-ext"], variable: "--font-heading" });
const code = JetBrains_Mono({ subsets: ["latin"], variable: "--font-code" });

export const metadata: Metadata = {
  title: "WorkTrace",
  description: "See how work really flows: process and task mining for KYP.ai exports and plain event logs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${body.variable} ${heading.variable} ${code.variable}`}>
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
