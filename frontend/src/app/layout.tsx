import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "EvalForge — LLM Evaluation Platform",
  description: "Test, benchmark, and red-team your LLM in production",
};

// Runs before React hydrates so the correct theme class is on <html>
// before first paint — otherwise the page briefly flashes the wrong
// theme (dark default, then flips to light) on every load for users
// who've chosen light mode.
const THEME_INIT_SCRIPT = `
(function () {
  try {
    var stored = window.localStorage.getItem("evalforge-theme");
    var theme = stored || (window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark");
    if (theme === "dark") document.documentElement.classList.add("dark");
  } catch (e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 antialiased min-h-screen">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
