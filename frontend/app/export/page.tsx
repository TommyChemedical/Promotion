const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function ExportPage() {
  return (
    <div className="max-w-xl">
      <h1 className="text-2xl font-semibold mb-2">Export</h1>
      <p className="text-sm text-gray-500 mb-6">
        Exportieren Sie alle Quellen mit Metadaten, Zusammenfassungen und Findings.
      </p>

      <div className="space-y-4">
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="font-medium text-gray-900 mb-1">CSV-Export</h2>
          <p className="text-sm text-gray-500 mb-3">
            Alle Quellen mit Metadaten und Tags als CSV-Datei. Für Excel, LibreOffice und Datenanalyse.
          </p>
          <a
            href={`${API_URL}/api/export/csv`}
            download="literaturki_export.csv"
            className="inline-block text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md hover:bg-gray-700 transition-colors"
          >
            CSV herunterladen
          </a>
        </div>

        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h2 className="font-medium text-gray-900 mb-1">Markdown-Export</h2>
          <p className="text-sm text-gray-500 mb-3">
            Alle Quellen mit KI-Zusammenfassungen, Kernergebnissen und Findings als Markdown.
            Für Obsidian, Notion, Pandoc und LaTeX-Workflows.
          </p>
          <a
            href={`${API_URL}/api/export/markdown`}
            download="literaturki_export.md"
            className="inline-block text-sm px-3 py-1.5 bg-gray-800 text-white rounded-md hover:bg-gray-700 transition-colors"
          >
            Markdown herunterladen
          </a>
        </div>
      </div>
    </div>
  );
}
