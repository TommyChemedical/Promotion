/**
 * Format an author string to APA 7th edition in-text citation style.
 *
 * Rules:
 *   1 author  → "Dupont"
 *   2 authors → "Dupont & Martin"
 *   3+        → "Dupont et al."
 *
 * Input formats handled:
 *   "Last, First; Last, First"   (semicolon-separated, Last-First)
 *   "Last, First and Last, First"
 *   "Last, First & Last, First"
 *   "First Last, First Last"     (comma-separated, First-Last — rare in metadata)
 *   "Last, First"                (single author, Last-First)
 *   "First Last"                 (single author, First-Last)
 */
export function formatAuthorsAPA7(authors: string): string {
  if (!authors.trim()) return "";

  let parts: string[];

  if (authors.includes(";")) {
    // Most reliable: semicolons separate multiple authors
    parts = authors.split(";").map((s) => s.trim()).filter(Boolean);
  } else if (/ and /i.test(authors) || / & /.test(authors)) {
    parts = authors.split(/ and | & /i).map((s) => s.trim()).filter(Boolean);
  } else {
    // Single author
    parts = [authors.trim()];
  }

  const lastNames = parts.map((author) => {
    const trimmed = author.trim();
    if (trimmed.includes(",")) {
      // "Last, First [Initials]" → take everything before first comma
      return trimmed.split(",")[0].trim();
    }
    // "First Last" → last word
    const words = trimmed.split(/\s+/);
    return words[words.length - 1].replace(/\.$/, "");
  });

  if (lastNames.length === 1) return lastNames[0];
  if (lastNames.length === 2) return `${lastNames[0]} & ${lastNames[1]}`;
  return `${lastNames[0]} et al.`;
}
