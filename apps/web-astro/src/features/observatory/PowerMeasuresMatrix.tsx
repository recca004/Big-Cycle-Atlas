/** Eight power measures matrix — synthetic offline comparison across all
 *  tracked powers. Values are normalized within each measure row only for
 *  visual scanning; the numeric value remains the primary encoding. */

import { useMemo } from "react";
import {
  POWER_MEASURE_DEFINITIONS,
  OFFLINE_MEASURE_PROFILES,
  formatMeasureValue,
  offlineCountries,
} from "./offlineData";

interface Props {
  selectedIso3: string | null;
}

export function PowerMeasuresMatrix({ selectedIso3 }: Props) {
  const maxima = useMemo(() => {
    const result = new Map<string, number>();
    for (const definition of POWER_MEASURE_DEFINITIONS) {
      result.set(
        definition.key,
        Math.max(
          ...offlineCountries.map((country) => Math.abs(OFFLINE_MEASURE_PROFILES[country.iso3]![definition.key].current)),
          1e-9,
        ),
      );
    }
    return result;
  }, []);

  return (
    <div className="measure-matrix-wrap" role="region" aria-label="Eight power measures across all tracked powers" tabIndex={0}>
      <table className="measure-matrix">
        <caption>
          Synthetic demonstration values, 2026 fixture. Bars are scaled per measure row; percentages, scores and USD are not comparable across rows.
        </caption>
        <thead>
          <tr>
            <th scope="col">Measure</th>
            {offlineCountries.map((country) => (
              <th key={country.iso3} scope="col" className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                <span>{country.iso3}</span>
                <small>{country.name}</small>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {POWER_MEASURE_DEFINITIONS.map((definition) => {
            const max = maxima.get(definition.key) ?? 1;
            return (
              <tr key={definition.key}>
                <th scope="row">
                  <span>{definition.label}</span>
                  <small>{definition.description}</small>
                </th>
                {offlineCountries.map((country) => {
                  const point = OFFLINE_MEASURE_PROFILES[country.iso3]![definition.key];
                  const delta = point.current - point.previous;
                  return (
                    <td key={country.iso3} className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                      <span className="measure-value">{formatMeasureValue(point.current, definition.unit)}</span>
                      <span className="measure-bar" aria-hidden="true">
                        <span style={{ width: `${Math.max(2, (Math.abs(point.current) / max) * 100)}%` }} />
                      </span>
                      <span className={delta >= 0 ? "measure-delta up" : "measure-delta down"}>
                        {delta >= 0 ? "+" : ""}{formatMeasureValue(delta, definition.unit)} vs prior
                      </span>
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
