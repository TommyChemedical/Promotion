# LiteraturKI

Lokales KI-Hilfsprogramm für wissenschaftliche Literaturarbeit.

**Funktionen:**
- PDFs hochladen und Volltext extrahieren
- Quellen in SQLite speichern und verwalten
- Volltextsuche über alle PDF-Texte (FTS5)
- KI-generierte strukturierte Zusammenfassungen (Anthropic API)
- Key Findings mit Belegstellen und Konfidenz-Bewertung
- Tags und Notizen zu Quellen
- Export als CSV und Markdown

## Voraussetzungen

- Python 3.11+
- Node.js 20+
- Anthropic API Key ([console.anthropic.com](https://console.anthropic.com))

## Backend starten

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# ANTHROPIC_API_KEY in .env eintragen
uvicorn app.main:app --reload --port 8000
```

API läuft dann auf http://localhost:8000  
Dokumentation: http://localhost:8000/docs

## Frontend starten

```bash
cd frontend
npm install
# .env.local ist bereits enthalten
npm run dev
```

Frontend läuft auf http://localhost:3000

## Tests ausführen

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest tests/ -v
```

## Verwendung

1. **PDF hochladen:** Seite „Hochladen" → PDF auswählen → Hochladen
2. **Quelle öffnen:** Seite „Quellen" → Details
3. **KI-Zusammenfassung erstellen:** Detailseite → „Erstellen" (benötigt API Key)
4. **Suchen:** Seite „Suche" → Suchbegriff eingeben
5. **Exportieren:** Seite „Export" → CSV oder Markdown herunterladen

## Technologie

| Bereich | Technologie |
|---|---|
| Backend | Python 3.11, FastAPI, SQLAlchemy, SQLite |
| PDF-Extraktion | PyMuPDF |
| Suche | SQLite FTS5 |
| KI-Analyse | Anthropic API (Haiku / Sonnet) |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |

## KI-Modelle

Konfigurierbar über `.env`:

- `ANTHROPIC_MODEL_FAST=claude-haiku-4-5` — für Tags (günstig, schnell)
- `ANTHROPIC_MODEL_DEEP=claude-sonnet-4-6` — für Zusammenfassungen (gründlich)

## Wissenschaftliche Grundsätze

- Jede KI-Aussage wird mit einer Textstelle belegt
- Unbelegte Aussagen werden als `low confidence` markiert
- Prompts, Modell, Version und Datum werden gespeichert (LLMRun)
- Der Nutzer kann alle KI-Ergebnisse manuell ergänzen

## Projektstruktur

```
LiteraturKI/
  backend/
    app/
      api/          # FastAPI Router (sources, search, summarize, export)
      services/     # pdf_service, llm_service, search_service, export_service
      prompts/      # Versionierte Prompt-Templates
      models.py     # SQLAlchemy Datenmodelle
      database.py   # DB-Engine und FTS5-Initialisierung
      config.py     # Pydantic Settings
    tests/          # pytest-Tests
    uploads/        # Hochgeladene PDFs (gitignored)
  frontend/
    app/            # Next.js App Router Pages
    components/     # React-Komponenten
    lib/            # API-Client
```

## Review & Validation System

### Review Status Values

Each Summary and Finding has a `review_status` field set by the user via the review API:

| Status | Bedeutung |
|--------|-----------|
| `unreviewed` | Noch nicht manuell geprüft (Standard) |
| `correct` | Inhalt korrekt und vollständig belegt |
| `partially_correct` | Teilweise korrekt, aber Einschränkungen |
| `incorrect` | Inhaltlich falsch |
| `unsupported` | Keine ausreichende Belegstelle vorhanden |
| `missing_important_context` | Korrekt, aber wichtiger Kontext fehlt |

### Evidence Validation

When a finding is created from a summary (automatic) or manually added, the system checks whether the `evidence_quote` appears in the extracted PDF page text.

**Algorithm:**
1. If `evidence_quote` is empty → `no_evidence`
2. Look up `DocumentText` for the given `page_number`
3. If page not found → `evidence_not_found`
4. Normalize whitespace (lowercase, collapse spaces/newlines)
5. Check exact substring match
6. If no exact match: check word overlap (≥ 75% of quote words appear in page text)
7. Match found → `evidence_found`, no match → `evidence_not_found`

**Validation Status Values:**

| Status | Bedeutung |
|--------|-----------|
| `no_evidence` | Kein Zitat angegeben — Finding kann nicht automatisch geprüft werden |
| `evidence_found` | Zitat im extrahierten Seitentext gefunden (exakt oder fuzzy) |
| `evidence_not_found` | Zitat konnte im angegebenen Seitentext nicht gefunden werden |

### Why Findings Without Evidence Are Not Automatically Rejected

Findings with `no_evidence` or `evidence_not_found` are **preserved and visible** because:

- OCR quality may be imperfect — a quote may not match even if the source is correct
- The LLM may paraphrase rather than quote verbatim
- Multi-page evidence cannot always be captured in a single quote
- The user must make the final scientific judgement

These findings are flagged as unverified (`review_status: unreviewed` + `validation_status: no_evidence/evidence_not_found`) and must be manually reviewed before being treated as established findings.

### Limits of Automatic Checking

- The fuzzy matcher uses word overlap — it does not understand semantic meaning
- Evidence spread across multiple pages may not be fully captured
- Tables and figures cannot be validated through text matching
- The LLM may cite the wrong page number — always verify manually for critical claims

### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/review/sources/{id}` | Full review view: summary + findings with page previews |
| `PATCH` | `/api/review/summary/{id}` | Set review_status, comment, confidence_user |
| `PATCH` | `/api/review/finding/{id}` | Set review_status, comment, confidence_user |
| `POST` | `/api/review/source/{id}/validate-evidence` | Re-run evidence validation for all findings |
