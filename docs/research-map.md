# Research-Map

## Was ist die Research-Map?

Die Research-Map ist eine Arbeitsebene über der Literatur-Matrix. Sie erlaubt es, geprüfte Findings aus der Literatur thematisch und argumentativ zu ordnen — für Kapitel, Forschungsfragen, Argumente oder Theorien einer Dissertation.

**Die Research-Map ist kein Schreibautomat.** Sie generiert keine Texte. Sie ordnet, strukturiert und hilft beim Überblick.

## Unterschied zur Matrix

| Literatur-Matrix | Research-Map |
|---|---|
| Alle Findings aller Quellen | Findings einem Thema/Kapitel zugeordnet |
| Flache Tabellenansicht | Hierarchische Strukturierung |
| Filter nach Status, Evidenz | Filter nach Relevanz, Relation, Kapitel |
| Export für Gesamtübersicht | Export pro Thema/Kapitel |

## ResearchAreas — Typen

| Typ | Beschreibung |
|---|---|
| `research_question` | Forschungsfrage der Dissertation |
| `chapter` | Kapitel oder Abschnitt |
| `theme` | Thematischer Bereich |
| `argument` | Argumentationsstrang |
| `method` | Methodenbereich |
| `theory` | Theoretischer Rahmen |
| `literature_gap` | Forschungslücke |
| `other` | Sonstiges |

## relevance — Bedeutung

Gibt an, wie wichtig ein Finding für diesen Bereich ist — **Nutzerbewertung, keine KI**.

| Wert | Bedeutung |
|---|---|
| `central` | Kernaussage für diesen Bereich |
| `useful` | Nützlich, aber nicht zentral |
| `marginal` | Randständig, evtl. als Fußnote |
| `context_only` | Nur Hintergrundinformation |
| `do_not_use` | Gefunden, aber bewusst ausgeschlossen |

## relation_type — Bedeutung

Wie verhält sich das Finding zu diesem Bereich — **Nutzerbewertung, keine KI**.

| Wert | Bedeutung |
|---|---|
| `supports` | Stützt das Argument/die These |
| `contradicts` | Widerspricht, ist Gegenposition |
| `differentiates` | Differenziert, schränkt ein |
| `defines` | Definiert einen Begriff/Konzept |
| `evidence` | Empirischer Beleg |
| `method` | Methodisch relevant |
| `theory` | Theoretisch einschlägig |
| `limitation` | Zeigt Grenzen auf |
| `research_gap` | Belegt eine Forschungslücke |
| `background` | Hintergrundwissen |

## Warum manuelle Zuordnung?

Die Zuordnung von Findings zu Bereichen ist eine **intellektuelle Entscheidung**. Welches Finding welches Argument stützt, ist abhängig vom eigenen Argumentationsplan — nicht von Keyword-Matching oder LLM-Interpretation. Die KI kann Vorschläge machen (zukünftiges Feature), aber die Entscheidung trifft der Nutzer.

## Qualitätshinweise (Gaps)

Die Übersichtsseite zeigt regelbasierte Hinweise — **keine KI-Interpretationen**:

- **"Viele unreviewed Findings"** — mehr als die Hälfte ungeprüft
- **"Viele Findings ohne validierten Beleg"** — Beleg nicht im Text gefunden
- **"Keine zentralen Findings"** — kein Finding als "zentral" markiert
- **"Viele widersprechende Findings"** — mehr als 2 mit `contradicts`
- **"Nur eine Quelle"** — Argumentationsbasis zu schmal

## Export

CSV- und Markdown-Export pro Bereich über die Matrix-API mit `research_area_id`-Filter. Die Exporte sind Arbeitsmaterial — kein fertiger Text.
