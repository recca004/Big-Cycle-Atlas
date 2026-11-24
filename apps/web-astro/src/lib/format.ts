/** Display formatters — mirrors the Next.js app's conventions. */

export function formatPercent(value: number): string {
  return `${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)}%`;
}

export function formatDecimal(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatUsdCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatUsdWhole(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatQuarter(periodStart: string): string {
  const d = new Date(periodStart);
  const quarter = Math.floor(d.getUTCMonth() / 3) + 1;
  return `${d.getUTCFullYear()} Q${quarter}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

export function yearOf(periodStart: string): number {
  return new Date(periodStart).getUTCFullYear();
}

export const SOURCE_LABELS: Record<string, string> = {
  world_bank: "World Bank",
  bis: "BIS",
  oecd: "OECD",
  imf: "IMF",
  wid: "WID",
};

export function sourceLabel(sourceKey: string | null): string {
  if (!sourceKey) return "Unknown source";
  return SOURCE_LABELS[sourceKey] ?? sourceKey;
}
