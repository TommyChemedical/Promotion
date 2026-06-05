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

// --- Matrix types ---

export interface MatrixRow {
  source_id: number;
  source_title: string;
  authors: string;
  year: number | null;
  doi: string;
  journal: string;
  source_review_status: string;
  finding_id: number | null;
  finding_statement: string | null;
  finding_page_start: number | null;
  finding_page_end: number | null;
  evidence_quote: string | null;
  validation_status: string | null;
  validation_method: string | null;
  validation_score: number | null;
  finding_review_status: string | null;
  finding_review_comment: string | null;
  confidence_user: number | null;
  summary_short: string | null;
  summary_review_status: string | null;
  tags: string[];
  notes_count: number;
  created_at: string | null;
  updated_at: string | null;
}

export interface MatrixResponse {
  items: MatrixRow[];
  total: number;
  limit: number;
  offset: number;
  filters_applied: Record<string, unknown>;
}

export interface MatrixFilters {
  q?: string;
  tag?: string[];
  year_from?: number;
  year_to?: number;
  review_status?: string;
  validation_status?: string;
  has_evidence?: boolean;
  only_reviewed?: boolean;
  only_unreviewed?: boolean;
  source_id?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  limit?: number;
  offset?: number;
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

  // Matrix
  getMatrix: (filters?: MatrixFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.q) params.set("q", filters.q);
      if (filters.tag) filters.tag.forEach((t) => params.append("tag", t));
      if (filters.year_from != null) params.set("year_from", String(filters.year_from));
      if (filters.year_to != null) params.set("year_to", String(filters.year_to));
      if (filters.review_status) params.set("review_status", filters.review_status);
      if (filters.validation_status) params.set("validation_status", filters.validation_status);
      if (filters.has_evidence != null) params.set("has_evidence", String(filters.has_evidence));
      if (filters.only_reviewed) params.set("only_reviewed", "true");
      if (filters.only_unreviewed) params.set("only_unreviewed", "true");
      if (filters.source_id != null) params.set("source_id", String(filters.source_id));
      if (filters.sort_by) params.set("sort_by", filters.sort_by);
      if (filters.sort_order) params.set("sort_order", filters.sort_order);
      if (filters.limit != null) params.set("limit", String(filters.limit));
      if (filters.offset != null) params.set("offset", String(filters.offset));
    }
    const qs = params.toString();
    return req<MatrixResponse>(`/api/matrix${qs ? `?${qs}` : ""}`);
  },
  getMatrixExportUrl: (format: "csv" | "md", filters?: MatrixFilters) => {
    const params = new URLSearchParams();
    if (filters) {
      if (filters.q) params.set("q", filters.q);
      if (filters.tag) filters.tag.forEach((t) => params.append("tag", t));
      if (filters.review_status) params.set("review_status", filters.review_status);
      if (filters.validation_status) params.set("validation_status", filters.validation_status);
    }
    const qs = params.toString();
    return `${BASE}/api/matrix/export.${format}${qs ? `?${qs}` : ""}`;
  },
};
