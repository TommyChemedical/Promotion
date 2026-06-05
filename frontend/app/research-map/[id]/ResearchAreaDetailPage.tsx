"use client";

import { useState } from "react";
import Link from "next/link";
import { api, type ResearchArea, type ResearchAreaOverview, type ResearchAreaFindingEntry } from "@/lib/api";
import { ResearchAreaBadge } from "@/components/research-map/ResearchAreaBadge";
import { ResearchAreaOverviewPanel } from "@/components/research-map/ResearchAreaOverview";
import { ResearchAreaFindingTable } from "@/components/research-map/ResearchAreaFindingTable";
import { AssignFindingPanel } from "@/components/research-map/AssignFindingPanel";
import CollapsibleSection from "@/components/CollapsibleSection";

interface Props {
  area: ResearchArea;
  initialOverview: ResearchAreaOverview;
  initialEntries: ResearchAreaFindingEntry[];
}

export function ResearchAreaDetailPage({ area, initialOverview, initialEntries }: Props) {
  const [entries, setEntries] = useState<ResearchAreaFindingEntry[]>(initialEntries);
  const [overview, setOverview] = useState<ResearchAreaOverview>(initialOverview);

  async function refreshOverview() {
    try {
      const updated = await api.getResearchAreaOverview(area.id);
      setOverview(updated);
    } catch { /* silent */ }
  }

  function handleAssigned(entry: ResearchAreaFindingEntry) {
    setEntries((prev) => [...prev, entry]);
    refreshOverview();
  }

  const assignedIds = new Set(entries.map((e) => e.finding_id));

  const apiBase = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const exportCsvUrl = `${apiBase}/api/matrix/export.csv?research_area_id=${area.id}`;
  const exportMdUrl = `${apiBase}/api/matrix/export.md?research_area_id=${area.id}`;

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link href="/research-map" className="text-sm text-gray-500 hover:text-gray-700">
            ← Research-Map
          </Link>
        </div>
        <div className="flex items-start gap-3">
          <ResearchAreaBadge type={area.area_type} />
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">{area.title}</h1>
            {area.description && (
              <p className="text-gray-500 text-sm mt-1">{area.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-3 mt-4">
          <a href={exportCsvUrl} download
            className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
            CSV exportieren
          </a>
          <a href={exportMdUrl} download
            className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded hover:bg-gray-200">
            Markdown exportieren
          </a>
        </div>
      </div>

      <section>
        <h2 className="text-lg font-semibold mb-3">Übersicht</h2>
        <ResearchAreaOverviewPanel overview={overview} />
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3">
          Zugeordnete Findings{" "}
          <span className="text-gray-400 font-normal text-base">({entries.length})</span>
        </h2>
        <ResearchAreaFindingTable
          areaId={area.id}
          entries={entries}
          onEntryRemoved={(fid) => setEntries((prev) => prev.filter((e) => e.finding_id !== fid))}
        />
      </section>

      <CollapsibleSection title="Finding zuordnen">
        <AssignFindingPanel
          areaId={area.id}
          assignedFindingIds={assignedIds}
          onAssigned={handleAssigned}
        />
      </CollapsibleSection>
    </div>
  );
}
