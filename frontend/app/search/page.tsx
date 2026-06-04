"use client";

import { useState } from "react";
import Link from "next/link";
import { api, type SearchResult } from "@/lib/api";

function highlightSnippet(snippet: string): string {
  // HTML-escape first, then replace [[...]] markers with <mark>
  const escaped = snippet
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  return escaped.replace(/\[\[/g, "<mark>").replace(/\]\]/g, "</mark>");
}

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const q = query.trim();
    if (q.length < 2) return;
    setLoading(true);
    setError("");
    try {
      const r = await api.search(q);
      setResults(r);
      setSearched(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suche fehlgeschlagen.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-6">Volltextsuche</h1>

      <form onSubmit={handleSearch} className="flex gap-2 mb-6">
        <input
          id="search-input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Suchbegriff eingeben (mind. 2 Zeichen)…"
          className="flex-1 border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
          minLength={2}
        />
        <button
          type="submit"
          disabled={loading || query.trim().length < 2}
          className="px-4 py-2 bg-gray-800 text-white text-sm rounded-md disabled:opacity-50 hover:bg-gray-700 transition-colors"
        >
          {loading ? "Suche…" : "Suchen"}
        </button>
      </form>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {searched && (
        <p className="text-sm text-gray-500 mb-3">
          {results.length === 0
            ? "Keine Treffer gefunden."
            : `${results.length} Treffer`}
        </p>
      )}

      {results.length > 0 && (
        <ul className="space-y-3">
          {results.map((r, i) => (
            <li
              key={i}
              className="bg-white border border-gray-200 rounded-lg p-4 text-sm"
            >
              <div className="flex justify-between items-center mb-1">
                <Link
                  href={`/sources/${r.source_id}`}
                  className="font-medium text-gray-800 hover:underline"
                >
                  Quelle #{r.source_id}
                </Link>
                <span className="text-xs text-gray-400">Seite {r.page_number}</span>
              </div>
              <p
                className="text-gray-600 leading-relaxed [&_mark]:bg-yellow-100 [&_mark]:text-yellow-900 [&_mark]:rounded-sm [&_mark]:px-0.5"
                dangerouslySetInnerHTML={{ __html: highlightSnippet(r.snippet) }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
