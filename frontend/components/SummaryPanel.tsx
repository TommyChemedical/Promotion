"use client";

import { useState } from "react";
import { api, type Summary, type KeyResult } from "@/lib/api";

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "text-green-700 bg-green-50 border-green-200",
  medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
  low: "text-red-700 bg-red-50 border-red-200",
};

interface Props {
  sourceId: number;
  initialSummaries: Summary[];
}

export function SummaryPanel({ sourceId, initialSummaries }: Props) {
  const [summaries, setSummaries] = useState<Summary[]>(initialSummaries);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const latest = summaries[summaries.length - 1] ?? null;

  async function handleSummarize() {
    setLoading(true);
    setError("");
    try {
      const s = await api.summarize(sourceId);
      setSummaries((prev) => [...prev, s]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Erstellen der Zusammenfassung.");
    } finally {
      setLoading(false);
    }
  }

  let keyResults: KeyResult[] = [];
  if (latest) {
    try {
      keyResults = JSON.parse(latest.key_results) as KeyResult[];
    } catch {
      keyResults = [];
    }
  }

  return (
    <section>
      <div className="flex justify-between items-center mb-3">
        <h2 className="text-lg font-semibold">KI-Zusammenfassung</h2>
        <button
          onClick={handleSummarize}
          disabled={loading}
          className="text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md disabled:opacity-50 hover:bg-gray-700 transition-colors"
        >
          {loading ? "Wird analysiert…" : latest ? "Neu erstellen" : "Erstellen"}
        </button>
      </div>

      {loading && (
        <p className="text-sm text-gray-500 bg-gray-50 border border-gray-200 rounded-md px-3 py-2 mb-3">
          Die KI analysiert den Text — das dauert je nach Länge 1–3 Minuten. Bitte warten…
        </p>
      )}

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md px-3 py-2 mb-3">
          {error}
        </p>
      )}

      {!latest && !loading && (
        <p className="text-sm text-gray-500">
          Noch keine Zusammenfassung vorhanden. Klicken Sie auf „Erstellen".
        </p>
      )}

      {latest && (
        <div className="space-y-3 text-sm">
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5">
            <span className="font-medium text-gray-600 whitespace-nowrap">Forschungsfrage</span>
            <span>{latest.research_question || "—"}</span>
            <span className="font-medium text-gray-600 whitespace-nowrap">Methoden</span>
            <span>{latest.methods || "—"}</span>
            <span className="font-medium text-gray-600 whitespace-nowrap">Datenbasis</span>
            <span>{latest.data_basis || "—"}</span>
            <span className="font-medium text-gray-600 whitespace-nowrap">Limitationen</span>
            <span>{latest.limitations || "—"}</span>
            <span className="font-medium text-gray-600 whitespace-nowrap">Relevanz</span>
            <span>{latest.relevance || "—"}</span>
          </div>

          {latest.uncertainty_notes && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-md px-3 py-2 text-yellow-800">
              <span className="font-medium">Unsicherheiten: </span>
              {latest.uncertainty_notes}
            </div>
          )}

          {keyResults.length > 0 && (
            <div>
              <h3 className="font-medium text-gray-700 mb-2">Kernergebnisse</h3>
              <ul className="space-y-2">
                {keyResults.map((r, i) => (
                  <li key={i} className="border-l-2 border-gray-200 pl-3">
                    <div className="flex items-start gap-2">
                      <span
                        className={`text-xs px-1.5 py-0.5 rounded border font-medium mt-0.5 flex-shrink-0 ${
                          CONFIDENCE_STYLES[r.confidence] ?? CONFIDENCE_STYLES.low
                        }`}
                      >
                        {r.confidence.toUpperCase()}
                      </span>
                      <span className="text-gray-800">{r.claim}</span>
                    </div>
                    {r.evidence_text && (
                      <blockquote className="mt-1 pl-2 border-l border-gray-200 text-gray-500 italic text-xs">
                        „{r.evidence_text}"
                        {r.page_number ? ` (S. ${r.page_number})` : ""}
                      </blockquote>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-xs text-gray-400">
            Modell: {latest.model_name} · Version: {latest.prompt_version} ·{" "}
            {new Date(latest.created_at).toLocaleDateString("de-DE")}
          </p>
        </div>
      )}
    </section>
  );
}
