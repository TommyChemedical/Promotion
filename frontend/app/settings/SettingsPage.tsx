"use client";

import { useEffect, useState, useCallback } from "react";
import { api, TokenStats } from "@/lib/api";
import { resetTokenCounter } from "@/components/TokenCounter";

export default function SettingsPage() {
  const [allTime, setAllTime] = useState<TokenStats | null>(null);
  const [resetConfirmed, setResetConfirmed] = useState(false);

  const loadAllTime = useCallback(async () => {
    const data = await api.getTokenStats();
    setAllTime(data);
  }, []);

  useEffect(() => {
    loadAllTime();
  }, [loadAllTime]);

  function handleReset() {
    resetTokenCounter();
    setResetConfirmed(true);
    setTimeout(() => setResetConfirmed(false), 2000);
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-semibold mb-6">Einstellungen</h1>

      <section className="bg-white border border-gray-200 rounded-lg p-5">
        <h2 className="text-base font-semibold mb-4">Token-Verbrauch</h2>

        <div className="mb-4">
          <p className="text-sm text-gray-500 mb-2">Gesamt (alle Zeit):</p>
          {allTime ? (
            <div className="text-sm leading-relaxed">
              <p>Token-Input: {allTime.input_tokens.toLocaleString("de-DE")}</p>
              <p>Token-Output: {allTime.output_tokens.toLocaleString("de-DE")}</p>
              <p className="text-gray-400 text-xs mt-1">
                {allTime.total_runs} API-Aufrufe gesamt
              </p>
            </div>
          ) : (
            <p className="text-sm text-gray-400">Lädt…</p>
          )}
        </div>

        <div className="border-t border-gray-100 pt-4">
          <p className="text-sm text-gray-500 mb-3">
            Der Zähler auf der Startseite zeigt nur Tokens seit dem letzten
            Zurücksetzen. Hier können Sie ihn zurücksetzen.
          </p>
          <button
            onClick={handleReset}
            className="text-sm px-3 py-1.5 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 transition-colors"
          >
            {resetConfirmed ? "Zurückgesetzt ✓" : "Zähler zurücksetzen"}
          </button>
        </div>
      </section>
    </div>
  );
}
