"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, type Finding, type ResearchArea } from "@/lib/api";

interface Props {
  findings: Finding[];
  researchAreas: ResearchArea[];
}

const CONFIDENCE_STYLE: Record<string, string> = {
  high: "text-green-700 bg-green-50 border-green-200",
  medium: "text-yellow-700 bg-yellow-50 border-yellow-200",
  low: "text-red-700 bg-red-50 border-red-200",
};

export default function FindingsSectionClient({ findings, researchAreas }: Props) {
  // Per-finding: set of assigned research_area_ids
  const [assigned, setAssigned] = useState<Record<number, Set<number>>>(() => {
    const init: Record<number, Set<number>> = {};
    for (const f of findings) {
      init[f.id] = new Set(f.research_area_ids);
    }
    return init;
  });
  const [openDropdown, setOpenDropdown] = useState<number | null>(null);
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpenDropdown(null);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  async function handleAssign(findingId: number, areaId: number) {
    const key = `${findingId}-${areaId}`;
    setLoading((prev) => ({ ...prev, [key]: true }));
    try {
      await api.assignFinding(areaId, {
        finding_id: findingId,
        relevance: "useful",
        relation_type: "supports",
      });
      setAssigned((prev) => {
        const next = { ...prev };
        next[findingId] = new Set(prev[findingId] ?? []);
        next[findingId].add(areaId);
        return next;
      });
    } catch {
      // 409 = already assigned, still mark locally
      setAssigned((prev) => {
        const next = { ...prev };
        next[findingId] = new Set(prev[findingId] ?? []);
        next[findingId].add(areaId);
        return next;
      });
    } finally {
      setLoading((prev) => ({ ...prev, [key]: false }));
    }
  }

  if (findings.length === 0) return null;

  return (
    <section ref={containerRef}>
      <h2 className="text-lg font-semibold mb-3">Findings</h2>
      <ul className="space-y-3">
        {findings.map((f) => {
          const assignedAreas = researchAreas.filter((a) => assigned[f.id]?.has(a.id));
          const unassignedAreas = researchAreas.filter((a) => !assigned[f.id]?.has(a.id));
          const isOpen = openDropdown === f.id;

          return (
            <li key={f.id} className="bg-white border border-gray-200 rounded-lg p-4 text-sm">
              {/* Header row: confidence + claim + assign button */}
              <div className="flex items-start gap-2">
                <span className={`text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 mt-0.5 ${CONFIDENCE_STYLE[f.confidence] ?? ""}`}>
                  {f.confidence.toUpperCase()}
                </span>
                <span className="font-medium text-gray-900 flex-1">{f.claim}</span>

                {/* Assign button + dropdown */}
                {researchAreas.length > 0 && (
                  <div className="relative flex-shrink-0">
                    <button
                      onClick={() => setOpenDropdown(isOpen ? null : f.id)}
                      className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 px-2 py-1 rounded border border-indigo-200 hover:bg-indigo-50 transition-colors"
                      title="Einer Research-Area zuordnen"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                      </svg>
                      Einordnen
                    </button>

                    {isOpen && (
                      <div className="absolute right-0 top-full mt-1 z-20 w-64 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden">
                        <div className="px-3 py-2 border-b border-gray-100 text-xs font-medium text-gray-500 uppercase tracking-wide">
                          Research-Area wählen
                        </div>
                        <ul className="max-h-52 overflow-y-auto">
                          {/* Already assigned */}
                          {assignedAreas.map((area) => (
                            <li
                              key={area.id}
                              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-400 cursor-default"
                            >
                              <svg className="w-3.5 h-3.5 text-indigo-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                              </svg>
                              <span className="truncate">{area.title}</span>
                            </li>
                          ))}
                          {/* Unassigned */}
                          {unassignedAreas.map((area) => {
                            const key = `${f.id}-${area.id}`;
                            const busy = loading[key];
                            return (
                              <li
                                key={area.id}
                                onClick={() => !busy && handleAssign(f.id, area.id)}
                                className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 cursor-pointer transition-colors"
                              >
                                {busy ? (
                                  <svg className="w-3.5 h-3.5 animate-spin text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                                  </svg>
                                ) : (
                                  <svg className="w-3.5 h-3.5 text-gray-300 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                                  </svg>
                                )}
                                <span className="truncate">{area.title}</span>
                              </li>
                            );
                          })}
                          {researchAreas.length === 0 && (
                            <li className="px-3 py-2 text-xs text-gray-400">Noch keine Areas angelegt</li>
                          )}
                        </ul>
                        <div className="px-3 py-2 border-t border-gray-100">
                          <Link
                            href="/research-map"
                            className="text-xs text-indigo-500 hover:underline"
                            onClick={() => setOpenDropdown(null)}
                          >
                            Research-Map öffnen →
                          </Link>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Quote */}
              {f.evidence_quote && (
                <blockquote className="mt-1 pl-3 border-l-2 border-gray-200 text-gray-500 italic text-xs">
                  „{f.evidence_quote}"
                  {f.page_number ? ` (S. ${f.page_number})` : ""}
                </blockquote>
              )}

              {/* Status + assigned area badges */}
              <div className="flex flex-wrap items-center gap-1.5 mt-2">
                {f.validation_status && f.validation_status !== "no_evidence" && (
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    f.validation_status === "evidence_found" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {f.validation_status === "evidence_found" ? "Beleg verifiziert" : "Beleg nicht gefunden"}
                  </span>
                )}
                {assignedAreas.map((area) => (
                  <Link
                    key={area.id}
                    href={`/research-map/${area.id}`}
                    className="text-xs bg-indigo-50 text-indigo-600 border border-indigo-100 rounded px-1.5 py-0.5 hover:bg-indigo-100 transition-colors"
                  >
                    {area.title}
                  </Link>
                ))}
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
