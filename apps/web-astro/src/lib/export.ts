/** CSV/JSON export helpers (Mission 4 §12).
 *  toCsv guards against spreadsheet formula injection: any cell whose
 *  text begins with =, +, - or @ is prefixed with a single quote. */

const DANGEROUS = /^[=+\-@]/;

function csvCell(value: unknown): string {
  if (value == null) return "";
  let s = String(value);
  if (DANGEROUS.test(s)) s = `'${s}`;
  if (/[",\n\r]/.test(s)) s = `"${s.replaceAll('"', '""')}"`;
  return s;
}

export function toCsv(
  headers: string[],
  rows: (string | number | null | undefined)[][],
): string {
  const head = headers.map(csvCell).join(",");
  const body = rows.map((r) => r.map(csvCell).join(",")).join("\n");
  return `${head}\n${body}\n`;
}

export function downloadText(
  filename: string,
  content: string,
  mime = "text/plain",
): void {
  const blob = new Blob([content], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
