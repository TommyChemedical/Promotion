"use client";

import { useState } from "react";
import { DocumentText } from "@/lib/api";

export default function FullTextSection({ texts }: { texts: DocumentText[] }) {
  const [open, setOpen] = useState(false);

  return (
    <section>
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 text-sm text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className="text-base leading-none">{open ? "▾" : "▸"}</span>
        Volltext anzeigen
        <span className="text-gray-400">({texts.length} Seiten)</span>
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          {texts.map((t) => (
            <div key={t.id} className="bg-white border border-gray-200 rounded-lg p-4">
              <div className="text-xs text-gray-400 mb-2 font-medium">Seite {t.page_number}</div>
              <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">{t.text}</p>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
