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
