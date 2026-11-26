/** BigCycleClockWidget — resizable workspace widget wrapping the flat
 *  SVG dial (widgets stay 2D for footprint; the full 3D instrument lives
 *  on the homepage). Data comes from the observatory overview endpoint. */

import { useEffect, useState } from "react";
import { fetchObservatoryOverview } from "@/lib/api/client";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { CycleDial, type DialCountry } from "./CycleDial";
import { stageLabel } from "./stages";

export function BigCycleClockWidget({ config }: WidgetProps) {
  const [countries, setCountries] = useState<DialCountry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const focus = (config.country as string | undefined) ?? null;

  useEffect(() => {
    let alive = true;
    fetchObservatoryOverview()
      .then((d) => {
        if (alive)
          setCountries(
            d.countries.map((c) => ({
              iso3: c.iso3,
              name: c.name,
              stage: c.stage,
              score: c.score,
              momentum: c.momentum,
              period: c.period,
            })),
          );
      })
      .catch((e) => {
        if (alive) setError(e instanceof Error ? e.message : "unavailable");
      });
    return () => {
      alive = false;
    };
  }, []);

  if (error)
    return (
      <p className="body-sm" role="alert">
        Clock unavailable: {error}
      </p>
    );
  if (!countries)
    return <div className="clock-skeleton" aria-busy="true" />;

  return (
    <figure className="clock-figure" aria-label="Big Cycle Clock widget">
      <CycleDial
        countries={countries}
        selectedIso3={focus}
        onSelect={() => {}}
        decorative
        animate={false}
        compact
      />
      <figcaption className="clock-caption">
        Experimental {focus ? `${focus} focus — ` : ""}
        positions are model outputs; no countdown implied.{" "}
        {countries.filter((c) => c.stage).length}/8 classified ·{" "}
        {countries.find((c) => c.iso3 === focus)?.stage
          ? `${focus}: ${stageLabel(countries.find((c) => c.iso3 === focus)!.stage)}`
          : ""}
      </figcaption>
    </figure>
  );
}
