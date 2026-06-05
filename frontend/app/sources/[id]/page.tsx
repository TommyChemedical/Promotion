import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { SummaryPanel } from "@/components/SummaryPanel";
import FullTextSection from "@/components/FullTextSection";
import CollapsibleSection from "@/components/CollapsibleSection";

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

  return (
    <div className="space-y-8 max-w-3xl">
      {/* Metadata */}
      <div>
        <h1 className="text-2xl font-semibold text-gray-900">{source.title}</h1>
        <p className="text-gray-500 text-sm mt-1">
          {source.authors || "—"}
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

      {/* Findings — always visible, first */}
      {source.findings.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Findings</h2>
          <ul className="space-y-3">
            {source.findings.map((f) => (
              <li key={f.id} className="bg-white border border-gray-200 rounded-lg p-4 text-sm">
                <div className="flex items-start gap-2 mb-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded border font-medium flex-shrink-0 mt-0.5 ${
                    f.confidence === "high" ? "text-green-700 bg-green-50 border-green-200" :
                    f.confidence === "medium" ? "text-yellow-700 bg-yellow-50 border-yellow-200" :
                    "text-red-700 bg-red-50 border-red-200"
                  }`}>{f.confidence.toUpperCase()}</span>
                  <span className="font-medium text-gray-900">{f.claim}</span>
                </div>
                {f.evidence_quote && (
                  <blockquote className="mt-1 pl-3 border-l-2 border-gray-200 text-gray-500 italic text-xs">
                    „{f.evidence_quote}"
                    {f.page_number ? ` (S. ${f.page_number})` : ""}
                  </blockquote>
                )}
                {f.validation_status && f.validation_status !== "no_evidence" && (
                  <span className={`mt-2 inline-block text-xs px-1.5 py-0.5 rounded ${
                    f.validation_status === "evidence_found" ? "bg-green-50 text-green-700" : "bg-gray-100 text-gray-500"
                  }`}>
                    {f.validation_status === "evidence_found" ? "Beleg verifiziert" : "Beleg nicht gefunden"}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

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
