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
  key_results: string;
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

// --- Review types ---

export type ReviewStatus =
  | "unreviewed"
  | "correct"
  | "partially_correct"
  | "incorrect"
  | "unsupported"
  | "missing_important_context";

export type ValidationStatus =
  | "no_evidence"
  | "evidence_found"
  | "evidence_not_found"
  | "invalid_page";

export type ValidationMethod = "none" | "exact" | "fragment" | "fuzzy";

export interface ReviewableSummary {
  id: number;
  research_question: string;
  methods: string;
  data_basis: string;
  limitations: string;
  relevance: string;
  uncertainty_notes: string;
  review_status: ReviewStatus;
  review_comment: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  confidence_user: number | null;
  created_at: string;
}

export interface ReviewableFinding {
  id: number;
  claim: string;
  evidence_text: string;
  evidence_quote: string;
  page_start: number | null;
  page_end: number | null;
  confidence: string;
  validation_status: ValidationStatus;
  validation_method: ValidationMethod;
  validation_score: number;
  validated_at: string | null;
  review_status: ReviewStatus;
  review_comment: string;
  reviewed_at: string | null;
  reviewed_by: string | null;
  confidence_user: number | null;
  page_preview: string;
  created_at: string;
}

export interface SourceReviewResponse {
  source_id: number;
  summary: ReviewableSummary | null;
  findings: ReviewableFinding[];
}

export interface ReviewUpdateRequest {
  review_status: ReviewStatus;
  review_comment?: string;
  confidence_user?: number | null;
}

export interface EvidenceValidationResponse {
  source_id: number;
  validated: number;
  results: { finding_id: number; validation_status: ValidationStatus }[];
}

// --- HTTP helper ---

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

  // Review
  getSourceReview: (id: number) =>
    req<SourceReviewResponse>(`/api/review/sources/${id}`),
  patchSummaryReview: (summaryId: number, body: ReviewUpdateRequest) =>
    req<ReviewableSummary>(`/api/review/summary/${summaryId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  patchFindingReview: (findingId: number, body: ReviewUpdateRequest) =>
    req<ReviewableFinding>(`/api/review/finding/${findingId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  validateEvidence: (sourceId: number) =>
    req<EvidenceValidationResponse>(
      `/api/review/source/${sourceId}/validate-evidence`,
      { method: "POST" }
    ),
};
