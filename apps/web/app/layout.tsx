import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Big Cycle Atlas",
  description:
    "Where are we in the Big Cycle? A country-level macro cycle tracker built on a measurable Big Cycle framework.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      {/* suppressHydrationWarning silences false-positive attribute mismatches
          injected by browser extensions (e.g. cz-shortcut-listen on <body>) */}
      <body suppressHydrationWarning>
        <div className="flex min-h-screen flex-col">
          <header className="border-b border-border bg-surface">
            <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between px-6">
              <Link href="/" className="headline-sm">
                Big Cycle Atlas
              </Link>
              <nav className="flex items-center gap-6">
                <Link href="/countries" className="text-sm text-on-surface hover:text-primary">
                  Countries
                </Link>
                <Link
                  href="/"
                  className="rounded-md bg-primary px-2.5 py-1.5 text-[13px] text-inverse hover:bg-accent"
                >
                  Dashboard
                </Link>
              </nav>
            </div>
          </header>
          <main className="flex-1">{children}</main>
          <footer className="border-t border-border bg-surface">
            <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-4">
              <span className="label-md text-tertiary">Big Cycle Atlas</span>
              <span className="label-md text-tertiary">Alpha — no live data yet</span>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}