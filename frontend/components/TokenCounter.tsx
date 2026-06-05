"use client";

import { useEffect, useState, useCallback } from "react";
import { api, TokenStats } from "@/lib/api";

const LS_KEY = "token_counter_reset_ts";

function getResetTs(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(LS_KEY);
}

export function resetTokenCounter() {
  const now = new Date().toISOString();
  localStorage.setItem(LS_KEY, now);
  return now;
}

export default function TokenCounter() {
  const [stats, setStats] = useState<TokenStats | null>(null);

  const load = useCallback(async () => {
    const since = getResetTs() ?? undefined;
    const data = await api.getTokenStats(since);
    setStats(data);
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (!stats) return null;

  return (
    <div className="text-xs text-gray-500 leading-relaxed">
      <p>Token-Input: {stats.input_tokens.toLocaleString("de-DE")}</p>
      <p>Token-Output: {stats.output_tokens.toLocaleString("de-DE")}</p>
    </div>
  );
}
