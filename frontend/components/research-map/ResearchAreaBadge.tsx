import type { AreaType } from "@/lib/api";

const TYPE_LABELS: Record<AreaType, string> = {
  research_question: "Forschungsfrage",
  chapter: "Kapitel",
  theme: "Thema",
  argument: "Argument",
  method: "Methode",
  theory: "Theorie",
  literature_gap: "Forschungslücke",
  other: "Sonstiges",
};

const TYPE_COLORS: Record<AreaType, string> = {
  research_question: "bg-blue-50 text-blue-700 border-blue-200",
  chapter: "bg-purple-50 text-purple-700 border-purple-200",
  theme: "bg-green-50 text-green-700 border-green-200",
  argument: "bg-orange-50 text-orange-700 border-orange-200",
  method: "bg-cyan-50 text-cyan-700 border-cyan-200",
  theory: "bg-rose-50 text-rose-700 border-rose-200",
  literature_gap: "bg-yellow-50 text-yellow-700 border-yellow-200",
  other: "bg-gray-50 text-gray-600 border-gray-200",
};

export function ResearchAreaBadge({ type }: { type: AreaType }) {
  return (
    <span className={`inline-flex text-xs px-1.5 py-0.5 rounded border font-medium ${TYPE_COLORS[type] ?? TYPE_COLORS.other}`}>
      {TYPE_LABELS[type] ?? type}
    </span>
  );
}
