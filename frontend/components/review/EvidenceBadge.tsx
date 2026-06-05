"use client";
import type { ValidationStatus, ValidationMethod } from "@/lib/api";

interface Props {
  validationStatus: ValidationStatus;
  validationMethod: ValidationMethod;
  validationScore: number;
}

const STATUS_CONFIG: Record<ValidationStatus, { label: string; cls: string }> = {
  evidence_found: { label: "Beleg gefunden", cls: "bg-green-100 text-green-800 border-green-300" },
  evidence_not_found: { label: "Kein Beleg", cls: "bg-yellow-100 text-yellow-800 border-yellow-300" },
  no_evidence: { label: "Kein Zitat", cls: "bg-gray-100 text-gray-600 border-gray-300" },
  invalid_page: { label: "Ungültige Seite", cls: "bg-red-100 text-red-700 border-red-300" },
};

const METHOD_LABEL: Record<ValidationMethod, string> = {
  none: "",
  exact: "exakt",
  fragment: "Fragment",
  fuzzy: "fuzzy",
};

export function EvidenceBadge({ validationStatus, validationMethod, validationScore }: Props) {
  const cfg = STATUS_CONFIG[validationStatus] ?? STATUS_CONFIG.no_evidence;
  const method = METHOD_LABEL[validationMethod];
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${cfg.cls}`}
    >
      {cfg.label}
      {method && (
        <span className="opacity-60">
          ({method} {(validationScore * 100).toFixed(0)}%)
        </span>
      )}
    </span>
  );
}
