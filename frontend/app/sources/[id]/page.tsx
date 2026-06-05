import { notFound } from "next/navigation";
import { api, type ResearchArea } from "@/lib/api";
import { SummaryPanel } from "@/components/SummaryPanel";
import FullTextSection from "@/components/FullTextSection";
import CollapsibleSection from "@/components/CollapsibleSection";
import FindingsSectionClient from "@/components/FindingsSectionClient";
import { formatAuthorsAPA7 } from "@/lib/formatters";

export const dynamic = "force-dynamic";

export default async function SourceDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  let source;
  try {
    source = await api.getSource(Number(id));
  } catch {
    notFound();
  }

  let researchAreas: ResearchArea[] = [];
  try {
    researchAreas = await api.listResearchAreas();
  } catch {
    // backend unreachable or no areas yet — degrade gracefully
  }

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Metadata */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{source.title}</h1>
        <p className="text-gray-500 text-sm mt-1">
          {formatAuthorsAPA7(source.authors) || "—"}
          {source.year ? ` · ${source.year}` : ""}
          {source.journal ? ` · ${source.journal}` : ""}
        </p>
        {source.doi && (
          <p className="text-xs text-gray-400 mt-0.5">DOI: {source.doi}</p>
        )}
        {source.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {source.tags.map((tag) => (
              <span
                key={tag}
                className="inline-block bg-gray-100 text-gray-600 text-xs px-2 py-0.5 rounded"
              >
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Findings — interactive, with inline research-area assignment */}
      <FindingsSectionClient
        findings={source.findings}
        researchAreas={researchAreas}
      />

      {/* KI-Zusammenfassung — collapsible */}
      <CollapsibleSection title="KI-Zusammenfassung">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <SummaryPanel sourceId={source.id} initialSummaries={source.summaries} />
        </div>
      </CollapsibleSection>

      {/* Volltext — collapsible */}
      <FullTextSection texts={source.texts} />

      {/* Notes */}
      {source.notes.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Notizen</h2>
          <ul className="space-y-2">
            {source.notes.map((n) => (
              <li
                key={n.id}
                className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-700"
              >
                {n.text}
                {n.linked_page_number && (
                  <span className="text-xs text-gray-400 ml-2">(S. {n.linked_page_number})</span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
