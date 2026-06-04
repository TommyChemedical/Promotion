Extrahiere die wichtigsten Befunde aus dem folgenden wissenschaftlichen Text.

**Regeln:**
- Gib nur Befunde zurück, die direkt im Text belegt sind.
- Zitiere die genaue Textstelle als `evidence_text`.
- Wenn keine Textstelle gefunden wird, setze `confidence` auf `low`.
- Erfinde nichts.
- Antworte ausschließlich mit validem JSON. Kein Text davor oder danach.

**Ausgabeformat:**

{
  "findings": [
    {
      "claim": "...",
      "evidence_text": "...",
      "page_number": null,
      "confidence": "low|medium|high"
    }
  ]
}

**Text:**

{text}
