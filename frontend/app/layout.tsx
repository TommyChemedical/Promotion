import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "LiteraturKI",
  description: "Wissenschaftliche Literaturverwaltung mit KI-Unterstützung",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="de">
      <body className="bg-gray-50 text-gray-900 min-h-screen">
        <nav className="bg-white border-b border-gray-200 px-6 py-3">
          <div className="max-w-5xl mx-auto flex items-center gap-6">
            <span className="font-semibold text-gray-800">LiteraturKI</span>
            <Link href="/sources" className="text-sm text-gray-600 hover:text-gray-900">
              Quellen
            </Link>
            <Link href="/upload" className="text-sm text-gray-600 hover:text-gray-900">
              Hochladen
            </Link>
            <Link href="/search" className="text-sm text-gray-600 hover:text-gray-900">
              Suche
            </Link>
            <Link href="/export" className="text-sm text-gray-600 hover:text-gray-900">
              Export
            </Link>
            <Link href="/matrix" className="text-sm text-gray-600 hover:text-gray-900">
              Matrix
            </Link>
          </div>
        </nav>
        <main className="max-w-5xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
