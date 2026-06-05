"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { ReviewableSummary, ReviewStatus } from "@/lib/api";
import { ReviewStatusSelect } from "./ReviewStatusSelect";

export function SummaryReviewCard({ summary: initial }: { summary: ReviewableSummary }) {
  const [summary, setSummary] = useState(initial);
  const [status, setStatus] = useState<ReviewStatus>(initial.review_status);
  const [comment, setComment] = useState(initial.review_comment);
  const [confidence, setConfidence] = useState<number | null>(initial.confidence_user);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patchSummaryReview(summary.id, {
        review_status: status,
        review_comment: comment,
        confidence_user: confidence,
      });
      setSummary(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <h3 className="mb-3 font-semibold text-gray-900">Zusammenfassung</h3>
      <dl className="mb-4 space-y-2 text-sm text-gray-700">
        {summary.research_question && (
          <>
            <dt className="font-medium">Forschungsfrage</dt>
            <dd>{summary.research_question}</dd>
          </>
        )}
        {summary.methods && (
          <>
            <dt className="font-medium mt-2">Methoden</dt>
            <dd>{summary.methods}</dd>
          </>
        )}
        {summary.data_basis && (
          <>
            <dt className="font-medium mt-2">Datenbasis</dt>
            <dd>{summary.data_basis}</dd>
          </>
        )}
        {summary.limitations && (
          <>
            <dt className="font-medium mt-2">Einschränkungen</dt>
            <dd>{summary.limitations}</dd>
          </>
        )}
        {summary.relevance && (
          <>
            <dt className="font-medium mt-2">Relevanz</dt>
            <dd>{summary.relevance}</dd>
          </>
        )}
      </dl>
      <div className="flex flex-col gap-2">
        <ReviewStatusSelect value={status} onChange={setStatus} />
        <textarea
          value={comment}
          onChange={(e) => setComment(e.target.value)}
          placeholder="Kommentar (optional)"
          className="rounded border border-gray-300 px-2 py-1 text-sm"
          rows={2}
        />
        <label className="flex items-center gap-2 text-sm text-gray-700">
          Vertrauen (1–5):
          <input
            type="number"
            min={1}
            max={5}
            value={confidence ?? ""}
            onChange={(e) =>
              setConfidence(e.target.value ? parseInt(e.target.value, 10) : null)
            }
            className="w-16 rounded border border-gray-300 px-1 py-0.5 text-sm"
          />
        </label>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          onClick={handleSave}
          disabled={saving}
          className="self-start rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving ? "Speichert…" : "Speichern"}
        </button>
      </div>
    </div>
  );
}
