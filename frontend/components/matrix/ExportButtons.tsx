"use client";
import type { MatrixFilters } from "@/lib/api";
import { api } from "@/lib/api";

export function ExportButtons({ filters }: { filters: MatrixFilters }) {
  return (
    <div className="flex gap-2">
      <a
        href={api.getMatrixExportUrl("csv", filters)}
        download="matrix_export.csv"
        className="text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-3 py-1.5 hover:border-gray-400"
      >
        CSV
      </a>
      <a
        href={api.getMatrixExportUrl("md", filters)}
        download="matrix_export.md"
        className="text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded px-3 py-1.5 hover:border-gray-400"
      >
        Markdown
      </a>
    </div>
  );
}
