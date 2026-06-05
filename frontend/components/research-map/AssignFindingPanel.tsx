"use client";
import { useState } from "react";
import { api, type ResearchAreaFindingEntry, type RelevanceValue, type RelationType, type MatrixRow } from "@/lib/api";

const RELEVANCE_OPTIONS: { value: RelevanceValue; label: string }[] = [
  { value: "central", label: "Zentral" },
  { value: "useful", label: "Nützlich" },
  { value: "marginal", label: "Marginal" },
  { value: "context_only", label: "Nur Kontext" },
  { value: "do_not_use", label: "Nicht verwenden" },
];

const RELATION_OPTIONS: { value: RelationType; label: string }[] = [
  { value: "supports", label: "Stützt" },
  { value: "contradicts", label: "Widerspricht" },
  { value: "differentiates", label: "Differenziert" },
  { value: "defines", label: "Definiert" },
  { value: "evidence", label: "Beleg" },
  { value: "method", label: "Methode" },
  { value: "theory", label: "Theorie" },
  { value: "limitation", label: "Limitation" },
  { value: "research_gap", label: "Forschungslücke" },
  { value: "background", label: "Hintergrund" },
  { value: "other", label: "Sonstiges" },
];

interface Props {
  areaId: number;
  assignedFindingIds: Set<number>;
  onAssigned: (entry: ResearchAreaFindingEntry) => void;
}

export function AssignFindingPanel({ areaId, assignedFindingIds, onAssigned }: Props) {
  const [query, setQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MatrixRow[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedFindingId, setSelectedFindingId] = useState<number | null>(null);
  const [relevance, setRelevance] = useState<RelevanceValue>("useful");
  const [relationType, setRelationType] = useState<RelationType>("other");
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setError("");
    try {
      const data = await api.getMatrix({ q: query, limit: 20 });
      setSearchResults(data.items.filter((r) => r.finding_id !== null));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Suchfehler");
    } finally {
      setSearching(false);
    }
  }

  async function handleAssign() {
    if (!selectedFindingId) return;
    setSaving(true);
    setError("");
    try {
      const entry = await api.assignFinding(areaId, {
        finding_id: selectedFindingId,
        relevance,
        relation_type: relationType,
        user_comment: comment,
      });
      onAssigned(entry);
      setSelectedFindingId(null);
      setQuery("");
      setSearchResults([]);
      setComment("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Zuordnen");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3 text-sm">
      {error && <p className="text-red-600">{error}</p>}

      <div className="flex gap-2">
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          placeholder="Finding suchen (Titel, Autoren, Aussage…)"
          className="flex-1 border border-gray-300 rounded-md px-3 py-1.5 text-sm"
        />
        <button onClick={handleSearch} disabled={searching}
          className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-md text-sm disabled:opacity-50">
          {searching ? "…" : "Suchen"}
        </button>
      </div>

      {searchResults.length > 0 && (
        <ul className="border border-gray-200 rounded-lg divide-y divide-gray-100 max-h-60 overflow-y-auto">
          {searchResults.map((row) => {
            const already = assignedFindingIds.has(row.finding_id!);
            const selected = selectedFindingId === row.finding_id;
            return (
              <li key={row.finding_id}
                onClick={() => !already && setSelectedFindingId(row.finding_id!)}
                className={`px-3 py-2 cursor-pointer transition-colors ${
                  already ? "opacity-40 cursor-not-allowed" :
                  selected ? "bg-indigo-50" : "hover:bg-gray-50"
                }`}
              >
                <p className="font-medium text-gray-800 truncate">{row.finding_statement}</p>
                <p className="text-xs text-gray-500 truncate">
                  {row.source_title} {row.year ? `· ${row.year}` : ""}
                  {already && " · bereits zugeordnet"}
                </p>
              </li>
            );
          })}
        </ul>
      )}

      {selectedFindingId && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 space-y-2">
          <p className="text-xs font-medium text-gray-600">Zuordnung konfigurieren</p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-gray-500">Relevanz</label>
              <select value={relevance} onChange={(e) => setRelevance(e.target.value as RelevanceValue)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm mt-0.5">
                {RELEVANCE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Relation</label>
              <select value={relationType} onChange={(e) => setRelationType(e.target.value as RelationType)}
                className="w-full border border-gray-300 rounded px-2 py-1 text-sm mt-0.5">
                {RELATION_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
            </div>
          </div>
          <input value={comment} onChange={(e) => setComment(e.target.value)}
            placeholder="Kommentar (optional)"
            className="w-full border border-gray-300 rounded px-2 py-1 text-sm" />
          <div className="flex gap-2">
            <button onClick={handleAssign} disabled={saving}
              className="px-3 py-1.5 bg-gray-800 text-white rounded-md text-sm disabled:opacity-50 hover:bg-gray-700">
              {saving ? "Zuordnen…" : "Zuordnen"}
            </button>
            <button onClick={() => setSelectedFindingId(null)}
              className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md text-sm hover:bg-gray-200">
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
