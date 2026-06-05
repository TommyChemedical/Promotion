"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import type { ReviewableFinding, ReviewStatus } from "@/lib/api";
import { ReviewStatusSelect } from "./ReviewStatusSelect";
import { EvidenceBadge } from "./EvidenceBadge";

const BORDER: Record<ReviewStatus, string> = {
  correct: "border-green-300",
  partially_correct: "border-yellow-300",
  unreviewed: "border-gray-200",
  missing_important_context: "border-yellow-300",
  incorrect: "border-red-300",
  unsupported: "border-red-300",
};

export function FindingReviewCard({ finding: initial }: { finding: ReviewableFinding }) {
  const [finding, setFinding] = useState(initial);
  const [status, setStatus] = useState<ReviewStatus>(initial.review_status);
  const [comment, setComment] = useState(initial.review_comment);
  const [confidence, setConfidence] = useState<number | null>(initial.confidence_user);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPreview, setShowPreview] = useState(false);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.patchFindingReview(finding.id, {
        review_status: status,
        review_comment: comment,
        confidence_user: confidence,
      });
      setFinding(updated);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className={`rounded-lg border ${BORDER[status]} bg-white p-4 shadow-sm`}>
      <p className="mb-2 text-sm font-medium text-gray-900">{finding.claim}</p>
      <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-gray-500">
        {finding.page_start != null && (
          <span>
            Seite {finding.page_start}
            {finding.page_end != null && finding.page_end !== finding.page_start
              ? `–${finding.page_end}`
              : ""}
          </span>
        )}
        <EvidenceBadge
          validationStatus={finding.validation_status}
          validationMethod={finding.validation_method}
          validationScore={finding.validation_score}
        />
      </div>
      {finding.evidence_quote && (
        <blockquote className="mb-2 rounded bg-gray-50 px-3 py-2 text-sm italic text-gray-700 border-l-4 border-gray-300">
          „{finding.evidence_quote}"
        </blockquote>
      )}
      {finding.page_preview && (
        <>
          <button
            onClick={() => setShowPreview((v) => !v)}
            className="mb-2 text-xs text-blue-600 hover:underline"
          >
            {showPreview ? "Vorschau ausblenden" : "Seitenvorschau anzeigen"}
          </button>
          {showPreview && (
            <pre className="mb-2 rounded bg-gray-50 px-3 py-2 text-xs text-gray-700 whitespace-pre-wrap border border-gray-200">
              {finding.page_preview}
            </pre>
          )}
        </>
      )}
      <div className="flex flex-col gap-2 mt-3">
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
