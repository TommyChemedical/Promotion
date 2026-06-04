import { notFound } from "next/navigation";
import { api } from "@/lib/api";
import { SummaryPanel } from "@/components/SummaryPanel";

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

      {/* AI Summary */}
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <SummaryPanel sourceId={source.id} initialSummaries={source.summaries} />
      </div>

      {/* Findings */}
      {source.findings.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold mb-3">Findings</h2>
          <ul className="space-y-3">
            {source.findings.map((f) => (
              <li key={f.id} className="bg-white border border-gray-200 rounded-lg p-4 text-sm">
                <div className="font-medium text-gray-900">{f.claim}</div>
                {f.evidence_text && (
                  <blockquote className="mt-1 text-gray-500 italic border-l-2 border-gray-200 pl-3">
                    „{f.evidence_text}"
                    {f.page_number ? ` (S. ${f.page_number})` : ""}
                  </blockquote>
                )}
                <span className="text-xs text-gray-400 mt-1 inline-block">
                  Konfidenz: {f.confidence}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

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

      {/* Full text */}
      <section>
        <h2 className="text-lg font-semibold mb-3">
          Volltext{" "}
          <span className="text-gray-400 font-normal text-base">
            ({source.texts.length} Seiten)
          </span>
        </h2>
        <div className="space-y-4">
          {source.texts.map((t) => (
            <div key={t.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-2 font-medium">Seite {t.page_number}</div>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{t.text}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
