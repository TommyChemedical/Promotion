"use client";
import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { Source, SourceReviewResponse } from "@/lib/api";
import { SummaryReviewCard } from "@/components/review/SummaryReviewCard";
import { FindingReviewCard } from "@/components/review/FindingReviewCard";
import { formatAuthorsAPA7 } from "@/lib/formatters";

interface Props {
  source: Source;
  reviewData: SourceReviewResponse;
}

export function ReviewPage({ source, reviewData: initial }: Props) {
  const [reviewData, setReviewData] = useState(initial);
  const [validating, setValidating] = useState(false);
  const [validateError, setValidateError] = useState<string | null>(null);

  const findings = reviewData.findings;
  const reviewed = findings.filter((f) => f.review_status !== "unreviewed").length;

  async function handleValidate() {
    setValidating(true);
    setValidateError(null);
    try {
      await api.validateEvidence(source.id);
      const updated = await api.getSourceReview(source.id);
      setReviewData(updated);
    } catch (e) {
      setValidateError(e instanceof Error ? e.message : "Validierungsfehler");
    } finally {
      setValidating(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <div className="mb-4">
        <Link
          href={`/sources/${source.id}`}
          className="text-sm text-blue-600 hover:underline"
        >
          ← Zurück zur Quelle
        </Link>
      </div>

      <div className="mb-6 rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h1 className="text-xl font-bold text-gray-900">{source.title}</h1>
        {source.authors && (
          <p className="mt-1 text-sm text-gray-600">{formatAuthorsAPA7(source.authors)}</p>
        )}
        <div className="mt-1 flex flex-wrap gap-3 text-sm text-gray-500">
          {source.year && <span>{source.year}</span>}
          {source.doi && <span>DOI: {source.doi}</span>}
          {source.journal && <span>{source.journal}</span>}
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-4">
          <span className="text-sm text-gray-600">
            Befunde geprüft: {reviewed} / {findings.length}
          </span>
          <button
            onClick={handleValidate}
            disabled={validating}
            className="rounded bg-indigo-600 px-3 py-1.5 text-sm text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {validating ? "Validiert…" : "Belege erneut validieren"}
          </button>
        </div>
        {validateError && (
          <p className="mt-2 text-sm text-red-600">{validateError}</p>
        )}
      </div>

      {reviewData.summary && (
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-semibold text-gray-800">
            Zusammenfassung prüfen
          </h2>
          <SummaryReviewCard summary={reviewData.summary} />
        </section>
      )}

      {findings.length > 0 && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-gray-800">
            Befunde prüfen ({findings.length})
          </h2>
          <div className="flex flex-col gap-4">
            {findings.map((f) => (
              <FindingReviewCard key={`${f.id}-${f.validated_at ?? "0"}`} finding={f} />
            ))}
          </div>
        </section>
      )}

      {findings.length === 0 && !reviewData.summary && (
        <p className="text-center text-gray-400">
          Keine Daten zur Prüfung vorhanden.
        </p>
      )}
    </div>
  );
}
