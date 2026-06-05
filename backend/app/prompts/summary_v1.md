Du bist ein wissenschaftlicher Assistent. Analysiere den folgenden Textabschnitt aus einer wissenschaftlichen Publikation und gib eine strukturierte JSON-Zusammenfassung zurück.

**Wichtig:** Dies ist {chunk_info}. Extrahiere alle Informationen, die in diesem Abschnitt enthalten sind. Felder, die im vorliegenden Abschnitt nicht vorkommen, lasse als leeren String oder leeres Array.

**Regeln:**
- Alle Textfelder der JSON-Antwort müssen auf Deutsch verfasst sein. Übersetze englische Inhalte ins Deutsche.
- Jede Aussage muss mit einer Textstelle aus dem Quellentext belegt sein.
- Wenn keine belegende Textstelle gefunden wird, setze `confidence` auf `low`.
- Erfinde keine Inhalte. Markiere Unsicherheiten explizit.
- Trenne belegte Aussagen von Interpretationen.
- Antworte ausschließlich mit validem JSON. Kein Text davor oder danach. Keine Markdown-Code-Blöcke.
- `evidence_quote` muss ein wörtliches Zitat aus dem Quellentext sein (im Original, nicht übersetzt). Falls kein direktes Zitat verfügbar, leeres Feld lassen.
- Extrahiere alle Kernergebnisse (`key_results`), die in diesem Abschnitt erkennbar sind – auch wenn es sich um Zwischen- oder Teilergebnisse handelt.

**Ausgabeformat (nur dieses JSON, nichts anderes):**

{
  "research_question": "...",
  "methods": "...",
  "data_basis": "...",
  "key_results": [
    {
      "claim": "...",
      "evidence_text": "Beschreibung, warum diese Textstelle die Aussage belegt",
      "evidence_quote": "wörtliches Originalzitat aus dem Quellentext",
      "page_number": null,
      "confidence": "low|medium|high"
    }
  ],
  "limitations": "...",
  "relevance": "...",
  "uncertainty_notes": "..."
}

**Textabschnitt der Quelle:**

{text}
