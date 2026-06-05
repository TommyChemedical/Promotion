import type { ResearchAreaOverview } from "@/lib/api";

export function ResearchAreaOverviewPanel({ overview }: { overview: ResearchAreaOverview }) {
  const stats = [
    { label: "Findings gesamt", value: overview.count_findings_total },
    { label: "Geprüft (korrekt)", value: overview.count_findings_correct },
    { label: "Teilweise korrekt", value: overview.count_findings_partially_correct },
    { label: "Ungeprüft", value: overview.count_findings_unreviewed },
    { label: "Beleg verifiziert", value: overview.count_evidence_found },
    { label: "Beleg fehlt", value: overview.count_evidence_missing },
    { label: "Quellen", value: overview.count_sources },
  ];

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-4 gap-3">
        {stats.map((s) => (
          <div key={s.label} className="bg-white border border-gray-200 rounded-lg p-3 text-center">
            <div className="text-2xl font-semibold text-gray-800">{s.value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {overview.gaps.length > 0 && (
        <div className="space-y-1">
          {overview.gaps.map((gap) => (
            <div key={gap} className="flex items-start gap-2 bg-yellow-50 border border-yellow-200 rounded-md px-3 py-2 text-sm text-yellow-800">
              <span className="mt-0.5">⚠</span>
              <span>{gap}</span>
            </div>
          ))}
        </div>
      )}

      {overview.top_sources.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 uppercase mb-2">Wichtigste Quellen</p>
          <ul className="space-y-1">
            {overview.top_sources.map((s) => (
              <li key={s.source_id} className="text-sm text-gray-700 flex items-center gap-2">
                <span className="text-xs bg-gray-100 text-gray-500 px-1.5 py-0.5 rounded">
                  {s.finding_count} Finding{s.finding_count !== 1 ? "s" : ""}
                </span>
                <span>{s.source_title}</span>
                {s.year && <span className="text-gray-400">{s.year}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
