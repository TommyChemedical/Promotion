"use client";
import type { ReviewStatus } from "@/lib/api";

const OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: "unreviewed", label: "Nicht geprüft" },
  { value: "correct", label: "Korrekt" },
  { value: "partially_correct", label: "Teilweise korrekt" },
  { value: "incorrect", label: "Inkorrekt" },
  { value: "unsupported", label: "Nicht belegt" },
  { value: "missing_important_context", label: "Kontext fehlt" },
];

interface Props {
  value: ReviewStatus;
  onChange: (v: ReviewStatus) => void;
}

export function ReviewStatusSelect({ value, onChange }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as ReviewStatus)}
      className="rounded border border-gray-300 bg-white px-2 py-1 text-sm"
    >
      {OPTIONS.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}
