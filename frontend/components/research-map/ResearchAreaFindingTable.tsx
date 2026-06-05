"use client";
import { useState } from "react";
import Link from "next/link";
import { api, type ResearchAreaFindingEntry, type RelevanceValue, type RelationType } from "@/lib/api";

const RELEVANCE_LABELS: Record<RelevanceValue, string> = {
  central: "Zentral", useful: "Nützlich", marginal: "Marginal",
  context_only: "Nur Kontext", do_not_use: "Nicht verwenden",
};

const RELATION_LABELS: Record<RelationType, string> = {
  supports: "Stützt", contradicts: "Widerspricht", differentiates: "Differenziert",
  defines: "Definiert", method: "Methode", theory: "Theorie", evidence: "Beleg",
  limitation: "Limitation", research_gap: "Forschungslücke", background: "Hintergrund",
  other: "Sonstiges",
};

const EVIDENCE_STYLES: Record<string, string> = {
  evidence_found: "text-green-700 bg-green-50",
  evidence_not_found: "text-red-700 bg-red-50",
  no_evidence: "text-gray-500 bg-gray-50",
  invalid_page: "text-yellow-700 bg-yellow-50",
};

const REVIEW_STYLES: Record<string, string> = {
  correct: "text-green-700",
  partially_correct: "text-yellow-700",
  incorrect: "text-red-700",
  unsupported: "text-orange-700",
  unreviewed: "text-gray-400",
};

interface Props {
  areaId: number;
  initialEntries: ResearchAreaFindingEntry[];
}

export function ResearchAreaFindingTable({ areaId, initialEntries }: Props) {
  const [entries, setEntries] = useState<ResearchAreaFindingEntry[]>(initialEntries);
  const [filterReview, setFilterReview] = useState("");
  const [filterRelation, setFilterRelation] = useState("");
  const [filterRelevance, setFilterRelevance] = useState("");
  const [includeUnreviewed, setIncludeUnreviewed] = useState(true);
  const [error, setError] = useState("");

  async function handleRemove(entry: ResearchAreaFindingEntry) {
    if (!confirm("Zuordnung entfernen?")) return;
    try {
      await api.removeFindingAssignment(areaId, entry.finding_id);
      setEntries((prev) => prev.filter((e) => e.finding_id !== entry.finding_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler");
    }
  }

  const visible = entries.filter((e) => {
    if (!includeUnreviewed && e.finding_review_status === "unreviewed") return false;
    if (filterReview && e.finding_review_status !== filterReview) return false;
    if (filterRelation && e.relation_type !== filterRelation) return false;
    if (filterRelevance && e.relevance !== filterRelevance) return false;
    return true;
  });

  return (
    <div className="space-y-3">
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="flex flex-wrap gap-2 text-sm">
        <label className="flex items-center gap-1 text-gray-600">
          <input type="checkbox" checked={includeUnreviewed}
            onChange={(e) => setIncludeUnreviewed(e.target.checked)} />
          Ungeprüft anzeigen
        </label>
        <select value={filterReview} onChange={(e) => setFilterReview(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-sm">
          <option value="">Alle Review-Status</option>
          <option value="correct">Korrekt</option>
          <option value="partially_correct">Teilw. korrekt</option>
          <option value="incorrect">Falsch</option>
          <option value="unreviewed">Ungeprüft</option>
        </select>
        <select value={filterRelation} onChange={(e) => setFilterRelation(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-sm">
          <option value="">Alle Relation-Typen</option>
          {(Object.keys(RELATION_LABELS) as RelationType[]).map((k) => (
            <option key={k} value={k}>{RELATION_LABELS[k]}</option>
          ))}
        </select>
        <select value={filterRelevance} onChange={(e) => setFilterRelevance(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1 text-sm">
          <option value="">Alle Relevanz-Stufen</option>
          {(Object.keys(RELEVANCE_LABELS) as RelevanceValue[]).map((k) => (
            <option key={k} value={k}>{RELEVANCE_LABELS[k]}</option>
          ))}
        </select>
      </div>

      {visible.length === 0 && (
        <p className="text-sm text-gray-400 py-4 text-center">Keine Findings gefunden.</p>
      )}

      <div className="space-y-2">
        {visible.map((entry) => (
          <div key={entry.finding_id} className="bg-white border border-gray-200 rounded-lg p-4 text-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Link href={`/sources/${entry.source_id}`}
                    className="text-xs text-indigo-600 hover:underline font-medium truncate">
                    {entry.source_title}
                  </Link>
                  {entry.year && <span className="text-xs text-gray-400">{entry.year}</span>}
                  {entry.page_start && (
                    <span className="text-xs text-gray-400">S. {entry.page_start}</span>
                  )}
                </div>
                <p className="font-medium text-gray-900">{entry.claim}</p>
                {entry.evidence_quote && (
                  <blockquote className="mt-1 pl-2 border-l-2 border-gray-200 text-gray-500 italic text-xs">
                    „{entry.evidence_quote}"
                  </blockquote>
                )}
                <div className="flex flex-wrap gap-1 mt-2">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${EVIDENCE_STYLES[entry.validation_status] ?? ""}`}>
                    {entry.validation_status === "evidence_found" ? "Beleg ✓" :
                     entry.validation_status === "evidence_not_found" ? "Kein Beleg" :
                     entry.validation_status === "no_evidence" ? "Kein Zitat" : entry.validation_status}
                  </span>
                  <span className={`text-xs ${REVIEW_STYLES[entry.finding_review_status] ?? ""}`}>
                    {entry.finding_review_status}
                  </span>
                  <span className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">
                    {RELATION_LABELS[entry.relation_type as RelationType] ?? entry.relation_type}
                  </span>
                  <span className="text-xs border border-gray-200 text-gray-500 px-1.5 py-0.5 rounded">
                    {RELEVANCE_LABELS[entry.relevance as RelevanceValue] ?? entry.relevance}
                  </span>
                </div>
                {entry.user_comment && (
                  <p className="text-xs text-gray-400 mt-1 italic">{entry.user_comment}</p>
                )}
              </div>
              <div className="flex flex-col gap-1 flex-shrink-0">
                <Link href={`/sources/${entry.source_id}/review`}
                  className="text-xs text-indigo-500 hover:underline">Prüfen</Link>
                <button onClick={() => handleRemove(entry)}
                  className="text-xs text-red-500 hover:text-red-700 text-left">Entfernen</button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
