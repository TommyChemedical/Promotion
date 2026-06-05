"use client";
import { useState } from "react";
import Link from "next/link";
import { api, type ResearchArea } from "@/lib/api";
import { ResearchAreaBadge } from "./ResearchAreaBadge";
import { ResearchAreaForm } from "./ResearchAreaForm";

interface Props {
  initialAreas: ResearchArea[];
}

export function ResearchAreaList({ initialAreas }: Props) {
  const [areas, setAreas] = useState<ResearchArea[]>(initialAreas);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<ResearchArea | null>(null);
  const [error, setError] = useState("");

  function handleSaved(saved: ResearchArea) {
    setAreas((prev) => {
      const idx = prev.findIndex((a) => a.id === saved.id);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = saved;
        return next;
      }
      return [...prev, saved];
    });
    setShowForm(false);
    setEditing(null);
  }

  async function handleDelete(area: ResearchArea) {
    if (!confirm(`"${area.title}" löschen? Alle Zuordnungen werden entfernt.`)) return;
    try {
      await api.deleteResearchArea(area.id);
      setAreas((prev) => prev.filter((a) => a.id !== area.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Löschen");
    }
  }

  const topLevel = areas.filter((a) => !a.parent_id);
  const children = (parentId: number) => areas.filter((a) => a.parent_id === parentId);

  function renderArea(area: ResearchArea, depth = 0): React.ReactNode {
    return (
      <div key={area.id}>
        <div
          className={`flex items-center justify-between bg-white border border-gray-200 rounded-lg px-4 py-3 hover:border-gray-300 transition-colors ${depth > 0 ? "ml-6" : ""}`}
        >
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <ResearchAreaBadge type={area.area_type} />
            <Link
              href={`/research-map/${area.id}`}
              className="font-medium text-gray-900 hover:text-gray-600 truncate"
            >
              {area.title}
            </Link>
            {area.description && (
              <span className="text-xs text-gray-400 truncate hidden sm:block">
                {area.description}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <button
              onClick={() => { setEditing(area); setShowForm(true); }}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Bearbeiten
            </button>
            <button
              onClick={() => handleDelete(area)}
              className="text-xs text-red-500 hover:text-red-700"
            >
              Löschen
            </button>
          </div>
        </div>
        {children(area.id).map((child) => renderArea(child, depth + 1))}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {error && (
        <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded p-3">{error}</p>
      )}

      <div className="flex justify-between items-center">
        <p className="text-sm text-gray-500">{areas.length} Bereiche</p>
        <button
          onClick={() => { setEditing(null); setShowForm(true); }}
          className="text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md hover:bg-gray-700"
        >
          + Neuer Bereich
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3">{editing ? "Bereich bearbeiten" : "Neuer Bereich"}</h3>
          <ResearchAreaForm
            areas={areas}
            initial={editing ?? undefined}
            onSaved={handleSaved}
            onCancel={() => { setShowForm(false); setEditing(null); }}
          />
        </div>
      )}

      {areas.length === 0 && !showForm && (
        <p className="text-sm text-gray-400 text-center py-8">
          Noch keine Bereiche. Legen Sie den ersten an.
        </p>
      )}

      <div className="space-y-2">
        {topLevel.map((area) => renderArea(area))}
      </div>
    </div>
  );
}
