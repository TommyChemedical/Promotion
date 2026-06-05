"use client";
import { useState } from "react";
import type { MatrixFilters as Filters } from "@/lib/api";

interface Props {
  onSearch: (filters: Filters) => void;
  loading: boolean;
}

export function MatrixFiltersPanel({ onSearch, loading }: Props) {
  const [q, setQ] = useState("");
  const [tag, setTag] = useState("");
  const [yearFrom, setYearFrom] = useState("");
  const [yearTo, setYearTo] = useState("");
  const [reviewStatus, setReviewStatus] = useState("");
  const [validationStatus, setValidationStatus] = useState("");
  const [hasEvidence, setHasEvidence] = useState("");
  const [onlyUnreviewed, setOnlyUnreviewed] = useState(false);
  const [onlyReviewed, setOnlyReviewed] = useState(false);
  const [sortBy, setSortBy] = useState("updated_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [limit, setLimit] = useState("100");

  function handleSearch() {
    const filters: Filters = {};
    if (q.trim()) filters.q = q.trim();
    if (tag.trim())
      filters.tag = tag
        .split(",")
        .map((t) => t.trim())
        .filter(Boolean);
    if (yearFrom) filters.year_from = parseInt(yearFrom, 10);
    if (yearTo) filters.year_to = parseInt(yearTo, 10);
    if (reviewStatus) filters.review_status = reviewStatus;
    if (validationStatus) filters.validation_status = validationStatus;
    if (hasEvidence === "true") filters.has_evidence = true;
    if (hasEvidence === "false") filters.has_evidence = false;
    if (onlyUnreviewed) filters.only_unreviewed = true;
    if (onlyReviewed) filters.only_reviewed = true;
    filters.sort_by = sortBy;
    filters.sort_order = sortOrder;
    const parsedLimit = parseInt(limit, 10);
    if (!isNaN(parsedLimit) && parsedLimit > 0) filters.limit = parsedLimit;
    onSearch(filters);
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Freitextsuche…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          className="flex-1 min-w-48 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="text"
          placeholder="Tags (kommagetrennt)"
          value={tag}
          onChange={(e) => setTag(e.target.value)}
          className="w-48 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Jahr von"
          value={yearFrom}
          onChange={(e) => setYearFrom(e.target.value)}
          className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
        <input
          type="number"
          placeholder="Jahr bis"
          value={yearTo}
          onChange={(e) => setYearTo(e.target.value)}
          className="w-24 border border-gray-300 rounded px-3 py-1.5 text-sm"
        />
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={reviewStatus}
          onChange={(e) => setReviewStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Alle Review-Status</option>
          <option value="unreviewed">Ungeprüft</option>
          <option value="correct">Korrekt</option>
          <option value="partially_correct">Teilweise korrekt</option>
          <option value="incorrect">Falsch</option>
          <option value="unsupported">Nicht belegt</option>
          <option value="missing_important_context">Kontext fehlt</option>
        </select>
        <select
          value={validationStatus}
          onChange={(e) => setValidationStatus(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Alle Evidenz-Status</option>
          <option value="evidence_found">Belegt</option>
          <option value="evidence_not_found">Nicht belegt</option>
          <option value="no_evidence">Kein Zitat</option>
          <option value="invalid_page">Ungültige Seite</option>
        </select>
        <select
          value={hasEvidence}
          onChange={(e) => setHasEvidence(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="">Alle Belege</option>
          <option value="true">Mit Beleg</option>
          <option value="false">Ohne Beleg</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={onlyUnreviewed}
            onChange={(e) => setOnlyUnreviewed(e.target.checked)}
          />
          Nur ungeprüft
        </label>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={onlyReviewed}
            onChange={(e) => setOnlyReviewed(e.target.checked)}
          />
          Nur geprüft
        </label>
      </div>
      <div className="flex flex-wrap gap-2 items-center">
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="updated_at">Sortierung: Zuletzt geändert</option>
          <option value="created_at">Sortierung: Erstellt</option>
          <option value="year">Sortierung: Jahr</option>
          <option value="title">Sortierung: Titel</option>
          <option value="review_status">Sortierung: Review-Status</option>
          <option value="validation_status">Sortierung: Evidenz-Status</option>
        </select>
        <select
          value={sortOrder}
          onChange={(e) => setSortOrder(e.target.value as "asc" | "desc")}
          className="border border-gray-300 rounded px-2 py-1.5 text-sm"
        >
          <option value="desc">Absteigend</option>
          <option value="asc">Aufsteigend</option>
        </select>
        <label className="flex items-center gap-1 text-sm text-gray-600">
          Limit:
          <input
            type="number"
            value={limit}
            min={1}
            max={500}
            onChange={(e) => setLimit(e.target.value)}
            className="w-16 border border-gray-300 rounded px-2 py-1 text-sm"
          />
        </label>
        <button
          onClick={handleSearch}
          disabled={loading}
          className="ml-auto bg-indigo-600 text-white px-4 py-1.5 rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
        >
          {loading ? "Suche…" : "Suchen"}
        </button>
      </div>
    </div>
  );
}
