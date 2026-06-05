"use client";
import { useState, useCallback } from "react";
import { api } from "@/lib/api";
import type { MatrixFilters, MatrixResponse } from "@/lib/api";
import { MatrixFiltersPanel } from "@/components/matrix/MatrixFilters";
import { MatrixTable } from "@/components/matrix/MatrixTable";
import { ExportButtons } from "@/components/matrix/ExportButtons";

export function MatrixPage() {
  const [data, setData] = useState<MatrixResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeFilters, setActiveFilters] = useState<MatrixFilters>({});

  const handleSearch = useCallback(async (filters: MatrixFilters) => {
    setLoading(true);
    setError(null);
    setActiveFilters(filters);
    try {
      const result = await api.getMatrix(filters);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fehler beim Laden");
    } finally {
      setLoading(false);
    }
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-xl font-semibold text-gray-900">Literatur-Matrix</h1>
        {data && <ExportButtons filters={activeFilters} />}
      </div>

      <MatrixFiltersPanel onSearch={handleSearch} loading={loading} />

      {!data && !loading && (
        <p className="text-gray-500 text-sm text-center py-8">
          Filter setzen und auf „Suchen" klicken.
        </p>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
          {error}
        </div>
      )}

      {data && <MatrixTable rows={data.items} total={data.total} />}
    </div>
  );
}
