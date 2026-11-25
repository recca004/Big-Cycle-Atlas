import type { ObservatoryCountry } from "@/types/observatory";
import { formatMeasureValue } from "./observatoryService";

interface MeasureDef {
  key: string;
  label: string;
  description: string;
  unit: string;
  value: (country: ObservatoryCountry) => number | null;
  display?: (country: ObservatoryCountry) => string;
  meta?: (country: ObservatoryCountry) => string;
}

interface Props {
  countries: ObservatoryCountry[];
  selectedIso3: string | null;
  demo?: boolean;
}

const snapshotValue = (country: ObservatoryCountry, code: string) =>
  country.indicator_snapshots[code]?.latest?.value ?? null;

const MEASURES: MeasureDef[] = [
  {
    key: "economic_output", label: "Economic output", description: "GDP in current USD", unit: "usd_current",
    value: (c) => c.international_power.economic_size?.value_usd ?? null,
    meta: (c) => c.international_power.economic_size?.period ?? "",
  },
  {
    key: "share_world_trade", label: "Tracked trade share", description: "Share of tracked import/export volume", unit: "%",
    value: (c) => c.international_power.international_trade?.tracked_share_pct ?? null,
    meta: (c) => c.international_power.international_trade?.period ?? "",
  },
  {
    key: "military_resources", label: "Military resources", description: "Military expenditure in USD", unit: "usd_current",
    value: (c) => c.international_power.military_resources?.expenditure_usd ?? null,
    meta: (c) => c.international_power.military_resources?.period ?? "",
  },
  {
    key: "financial_center", label: "Monetary signal", description: "Sovereign 10-year yield", unit: "%",
    value: (c) => (c.international_power.monetary_influence?.gov_10y_yield as number | undefined) ?? null,
    meta: (c) => (c.international_power.monetary_influence?.gov_10y_period as string | undefined) ?? "",
  },
  {
    key: "reserve_currency_status", label: "Reserve-currency status", description: "Currency role in the Atlas market layer", unit: "text",
    value: () => null,
    display: (c) => (c.international_power.monetary_influence?.currency_code as string | undefined) ?? "—",
    meta: (c) => (c.international_power.monetary_influence?.reserve_anchor_role as string | undefined) ?? "Unavailable",
  },
  {
    key: "innovation_output", label: "Innovation intensity", description: "R&D expenditure as % of GDP", unit: "% GDP",
    value: (c) => c.international_power.innovation_scale?.rnd_pct_gdp ?? null,
    meta: (c) => c.international_power.innovation_scale?.period ?? "",
  },
  {
    key: "education_attainment", label: "Education attainment", description: "Tertiary attainment, ages 25–34", unit: "%",
    value: (c) => snapshotValue(c, "TERTIARY_ATTAINMENT_25_34"),
    meta: (c) => c.indicator_snapshots.TERTIARY_ATTAINMENT_25_34?.latest?.period ?? "",
  },
  {
    key: "productivity_competitiveness", label: "Productivity", description: "Labour productivity per hour", unit: "score",
    value: (c) => snapshotValue(c, "LABOUR_PRODUCTIVITY_PER_HOUR"),
    meta: (c) => c.indicator_snapshots.LABOUR_PRODUCTIVITY_PER_HOUR?.latest?.period ?? "",
  },
];

export function PowerMeasuresMatrix({ countries, selectedIso3, demo = false }: Props) {
  const maxima = new Map<string, number>();
  for (const measure of MEASURES) {
    maxima.set(
      measure.key,
      Math.max(1e-9, ...countries.map((country) => Math.abs(measure.value(country) ?? 0))),
    );
  }

  return (
    <div className="measure-matrix-wrap" role="region" aria-label="Eight power measures across all tracked powers" tabIndex={0}>
      <table className="measure-matrix">
        <caption>
          {demo ? "Demonstration values." : "Production provider observations."} Bars are scaled within each measure row only; percentages, scores and USD are not comparable across rows.
        </caption>
        <thead>
          <tr>
            <th scope="col">Measure</th>
            {countries.map((country) => (
              <th key={country.iso3} scope="col" className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                <span>{country.iso3}</span>
                <small>{country.name}</small>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MEASURES.map((measure) => {
            const max = maxima.get(measure.key) ?? 1;
            return (
              <tr key={measure.key}>
                <th scope="row">
                  <span>{measure.label}</span>
                  <small>{measure.description}</small>
                </th>
                {countries.map((country) => {
                  const numeric = measure.value(country);
                  return (
                    <td key={country.iso3} className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                      <span className="measure-value">
                        {measure.display ? measure.display(country) : formatMeasureValue(numeric, measure.unit)}
                      </span>
                      <span className="measure-bar" aria-hidden="true">
                        <span style={{ width: `${numeric === null ? 0 : Math.max(2, (Math.abs(numeric) / max) * 100)}%` }} />
                      </span>
                      <span className="measure-delta">{measure.meta?.(country) || "Unavailable"}</span>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
