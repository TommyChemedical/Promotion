"use client";

type BadgeVariant = "positive" | "cautious" | "warning" | "neutral";

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  positive: "bg-green-100 text-green-800",
  cautious: "bg-yellow-100 text-yellow-800",
  warning: "bg-red-100 text-red-800",
  neutral: "bg-gray-100 text-gray-600",
};

export function ValidationBadge({
  status,
  method,
}: {
  status: string | null;
  method?: string | null;
}) {
  if (!status) return <span className="text-gray-400 text-xs">—</span>;
  const variant: BadgeVariant =
    status === "evidence_found"
      ? "positive"
      : status === "evidence_not_found" || status === "invalid_page"
      ? "warning"
      : "neutral";
  const labels: Record<string, string> = {
    evidence_found: "Belegt",
    evidence_not_found: "Nicht belegt",
    no_evidence: "Kein Zitat",
    invalid_page: "Ungültige Seite",
  };
  const label = labels[status] ?? status;
  const methodLabel = method && method !== "none" ? ` (${method})` : "";
  return (
    <span
      className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${VARIANT_CLASSES[variant]}`}
    >
      {label}
      {methodLabel}
    </span>
  );
}

export function ReviewBadge({ status }: { status: string | null }) {
  if (!status || status === "unreviewed") {
    return (
      <span className="inline-block text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">
        Ungeprüft
      </span>
    );
  }
  const variant: BadgeVariant =
    status === "correct"
      ? "positive"
      : status === "partially_correct" || status === "missing_important_context"
      ? "cautious"
      : "warning";
  const labels: Record<string, string> = {
    correct: "Korrekt",
    partially_correct: "Teilweise korrekt",
    incorrect: "Falsch",
    unsupported: "Nicht belegt",
    missing_important_context: "Kontext fehlt",
  };
  return (
    <span
      className={`inline-block text-xs px-2 py-0.5 rounded font-medium ${VARIANT_CLASSES[variant]}`}
    >
      {labels[status] ?? status}
    </span>
  );
}
