import Link from "next/link";
import type { Source } from "@/lib/api";

export function SourceCard({ source }: { source: Source }) {
  return (
    <Link
      href={`/sources/${source.id}`}
      className="block bg-white border border-gray-200 rounded-lg p-4 hover:border-gray-400 hover:shadow-sm transition-all"
    >
      <div className="flex justify-between items-start gap-4">
        <div className="flex-1 min-w-0">
          <h2 className="font-medium text-gray-900 truncate">{source.title}</h2>
          <p className="text-sm text-gray-500 mt-0.5">
            {source.authors || "—"}
            {source.year ? ` · ${source.year}` : ""}
            {source.journal ? ` · ${source.journal}` : ""}
          </p>
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
        <Link
          href={`/sources/${source.id}/review`}
          onClick={(e) => e.stopPropagation()}
          className="flex-shrink-0 text-sm text-indigo-600 hover:text-indigo-900 underline-offset-2 hover:underline"
        >
          Prüfen
        </Link>
      </div>
    </Link>
  );
}
