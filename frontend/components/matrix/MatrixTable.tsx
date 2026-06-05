"use client";
import Link from "next/link";
import type { MatrixRow } from "@/lib/api";
import { ValidationBadge, ReviewBadge } from "./StatusBadge";
import { formatAuthorsAPA7 } from "@/lib/formatters";

interface Props {
  rows: MatrixRow[];
  total: number;
}

function truncate(s: string | null, len = 80): string {
  if (!s) return "—";
  return s.length > len ? s.slice(0, len) + "…" : s;
}

export function MatrixTable({ rows, total }: Props) {
  if (rows.length === 0) {
    return (
      <p className="text-gray-500 text-sm py-8 text-center">
        Keine Ergebnisse.
      </p>
    );
  }

  return (
    <div>
      <p className="text-sm text-gray-500 mb-2">{total} Einträge</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Quelle
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Jahr
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Tags
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Finding (KI-Vorschlag)
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Seiten
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Evidenz-Status
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Review-Status
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Confidence
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Kommentar
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-700">
                Aktionen
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr
                key={`${row.source_id}-${row.finding_id ?? i}`}
                className="border-b border-gray-100 hover:bg-gray-50"
              >
                <td className="px-3 py-2 max-w-48">
                  <div
                    className="font-medium text-gray-900 truncate"
                    title={row.source_title}
                  >
                    {truncate(row.source_title, 40)}
                  </div>
                  <div className="text-xs text-gray-500 truncate">
                    {formatAuthorsAPA7(row.authors) || "—"}
                  </div>
                </td>
                <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                  {row.year ?? "—"}
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1">
                    {row.tags.map((t) => (
                      <span
                        key={t}
                        className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded"
                      >
                        {t}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-3 py-2 max-w-64">
                  {row.finding_statement ? (
                    <span title={row.finding_statement} className="text-gray-800">
                      {truncate(row.finding_statement)}
                    </span>
                  ) : (
                    <span className="text-gray-400 italic">Kein Finding</span>
                  )}
                  {row.research_areas?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {row.research_areas.map((ra) => (
                        <Link
                          key={ra.research_area_id}
                          href={`/research-map/${ra.research_area_id}`}
                          className="text-xs bg-indigo-50 text-indigo-600 border border-indigo-100 rounded px-1.5 py-0.5 hover:bg-indigo-100"
                        >
                          {ra.title}
                        </Link>
                      ))}
                    </div>
                  )}
                </td>
                <td className="px-3 py-2 text-gray-600 whitespace-nowrap">
                  {row.finding_page_start != null
                    ? row.finding_page_end &&
                      row.finding_page_end !== row.finding_page_start
                      ? `${row.finding_page_start}–${row.finding_page_end}`
                      : String(row.finding_page_start)
                    : "—"}
                </td>
                <td className="px-3 py-2">
                  <ValidationBadge
                    status={row.validation_status}
                    method={row.validation_method}
                  />
                </td>
                <td className="px-3 py-2">
                  <ReviewBadge
                    status={row.finding_review_status ?? row.source_review_status}
                  />
                </td>
                <td className="px-3 py-2 text-gray-600">
                  {row.confidence_user != null
                    ? `${row.confidence_user}/5`
                    : "—"}
                </td>
                <td
                  className="px-3 py-2 max-w-40 text-gray-600"
                  title={row.finding_review_comment ?? ""}
                >
                  {truncate(row.finding_review_comment, 40)}
                </td>
                <td className="px-3 py-2 whitespace-nowrap">
                  <Link
                    href={`/sources/${row.source_id}`}
                    className="text-indigo-600 hover:underline text-xs mr-2"
                  >
                    Details
                  </Link>
                  <Link
                    href={`/sources/${row.source_id}/review`}
                    className="text-indigo-600 hover:underline text-xs"
                  >
                    Prüfen
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
