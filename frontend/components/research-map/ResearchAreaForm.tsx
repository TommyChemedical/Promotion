"use client";
import { useState } from "react";
import { api, type ResearchArea, type AreaType } from "@/lib/api";

const AREA_TYPES: AreaType[] = [
  "research_question", "chapter", "theme", "argument",
  "method", "theory", "literature_gap", "other",
];

const TYPE_LABELS: Record<AreaType, string> = {
  research_question: "Forschungsfrage", chapter: "Kapitel",
  theme: "Thema", argument: "Argument", method: "Methode",
  theory: "Theorie", literature_gap: "Forschungslücke", other: "Sonstiges",
};

interface Props {
  areas: ResearchArea[];
  initial?: ResearchArea;
  onSaved: (area: ResearchArea) => void;
  onCancel: () => void;
}

export function ResearchAreaForm({ areas, initial, onSaved, onCancel }: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [areaType, setAreaType] = useState<AreaType>(initial?.area_type ?? "other");
  const [parentId, setParentId] = useState<string>(initial?.parent_id != null ? String(initial.parent_id) : "");
  const [sortOrder, setSortOrder] = useState(initial?.sort_order ?? 0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setError("Titel ist erforderlich"); return; }
    setSaving(true);
    setError("");
    try {
      const body = {
        title: title.trim(),
        description,
        area_type: areaType,
        parent_id: parentId ? Number(parentId) : undefined,
        sort_order: sortOrder,
      };
      const saved = initial
        ? await api.updateResearchArea(initial.id, body)
        : await api.createResearchArea(body);
      onSaved(saved);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fehler beim Speichern");
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Titel *</label>
        <input
          value={title} onChange={(e) => setTitle(e.target.value)}
          className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-gray-400"
          placeholder="z. B. Kapitel 2: Forschungsstand"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Typ</label>
        <select
          value={areaType} onChange={(e) => setAreaType(e.target.value as AreaType)}
          className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
        >
          {AREA_TYPES.map((t) => (
            <option key={t} value={t}>{TYPE_LABELS[t]}</option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Beschreibung</label>
        <textarea
          value={description} onChange={(e) => setDescription(e.target.value)}
          rows={2}
          className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          placeholder="Optional: kurze Beschreibung"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Übergeordnete Area</label>
          <select
            value={parentId} onChange={(e) => setParentId(e.target.value)}
            className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          >
            <option value="">— keine —</option>
            {areas
              .filter((a) => a.id !== initial?.id)
              .map((a) => <option key={a.id} value={a.id}>{a.title}</option>)
            }
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Reihenfolge</label>
          <input
            type="number" value={sortOrder}
            onChange={(e) => setSortOrder(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-md px-3 py-1.5 text-sm"
          />
        </div>
      </div>
      <div className="flex gap-2 pt-1">
        <button
          type="submit" disabled={saving}
          className="text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md hover:bg-gray-700 disabled:opacity-50"
        >
          {saving ? "Speichern…" : initial ? "Aktualisieren" : "Anlegen"}
        </button>
        <button type="button" onClick={onCancel}
          className="text-sm px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200">
          Abbrechen
        </button>
      </div>
    </form>
  );
}
