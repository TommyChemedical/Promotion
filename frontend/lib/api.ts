const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface Source {
  id: number;
  title: string;
  authors: string;
  year: number | null;
  doi: string;
  journal: string;
  filename: string;
  created_at: string;
  tags: string[];
}

export interface DocumentText {
  id: number;
  page_number: number;
  text: string;
}

export interface Finding {
  id: number;
  claim: string;
  evidence_text: string;
  page_number: number | null;
  confidence: "low" | "medium" | "high";
  relevance: string;
  created_at: string;
}

export interface Note {
  id: number;
  text: string;
  linked_page_number: number | null;
  linked_quote: string;
  created_at: string;
}

export interface KeyResult {
  claim: string;
  evidence_text: string;
  page_number: number | null;
  confidence: "low" | "medium" | "high";
}

export interface Summary {
  id: number;
  model_name: string;
  prompt_version: string;
  research_question: string;
  methods: string;
  data_basis: string;
  key_results: string; // JSON string of KeyResult[]
  limitations: string;
  relevance: string;
  uncertainty_notes: string;
  created_at: string;
}

export interface SourceDetail extends Source {
  texts: DocumentText[];
  summaries: Summary[];
  findings: Finding[];
  notes: Note[];
}

export interface SearchResult {
  source_id: number;
  page_number: number;
  snippet: string;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, options);
  if (!r.ok) {
    let msg = `HTTP ${r.status}`;
    try {
      const body = await r.json();
      msg = body.detail ?? JSON.stringify(body);
    } catch {
      msg = await r.text();
    }
    throw new Error(msg);
  }
  return r.json() as Promise<T>;
}

export const api = {
  getSources: () => req<Source[]>("/api/sources"),
  getSource: (id: number) => req<SourceDetail>(`/api/sources/${id}`),
  deleteSource: (id: number) =>
    req<{ ok: boolean }>(`/api/sources/${id}`, { method: "DELETE" }),
  uploadSource: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return req<Source>("/api/sources/upload", { method: "POST", body: form });
  },
  summarize: (id: number) =>
    req<Summary>(`/api/sources/${id}/summarize`, { method: "POST" }),
  addTag: (id: number, name: string) =>
    req<{ ok: boolean }>(`/api/sources/${id}/tags`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  addNote: (id: number, text: string) =>
    req<Note>(`/api/sources/${id}/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }),
  search: (q: string) =>
    req<SearchResult[]>(`/api/search?q=${encodeURIComponent(q)}`),
};
