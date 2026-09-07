import Link from "next/link";
import { INITIAL_COUNTRIES } from "@big-cycle-atlas/shared";

export default function HomePage() {
  const regions = [...new Set(INITIAL_COUNTRIES.map((c) => c.region))];

  return (
    <div className="mx-auto w-full max-w-6xl px-6">
      <section className="pb-16 pt-20">
        <p className="label-md mb-8 text-tertiary">A measurable Big Cycle framework</p>
        <h1 className="headline-display max-w-3xl">Where are we in the Big Cycle?</h1>
        <p className="body-md mt-8 max-w-xl text-secondary">
          Big Cycle Atlas tracks the economic and institutional forces that shape the
          rise and decline of countries — 17 forces, scored from public data, placed
          into a transparent cycle model.
        </p>
        <div className="mt-10 flex gap-4">
          <Link
            href="/countries"
            className="inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            View countries
          </Link>
        </div>
      </section>

      <section className="border-t border-border pb-24 pt-12">
        <div className="mb-8 flex items-baseline justify-between">
          <h2 className="headline-lg">Tracked countries</h2>
          <span className="label-md text-tertiary">
            {INITIAL_COUNTRIES.length} countries · {regions.length} regions
          </span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {INITIAL_COUNTRIES.map((country) => (
            <div
              key={country.iso3}
              className="rounded-lg border border-border bg-surface p-4"
            >
              <div className="flex items-baseline justify-between">
                <span className="headline-sm">{country.name}</span>
                <span className="label-md text-tertiary">{country.iso3}</span>
              </div>
              <p className="mt-1 text-[13px] text-tertiary">{country.region}</p>
              <div className="mt-4">
                <span className="inline-flex items-center rounded-full bg-neutral px-2.5 py-1 text-xs font-medium text-tertiary">
                  Phase — not yet calculated
                </span>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-8 text-sm text-tertiary">
          Scoring and phase calculation arrive with the force engine (Milestone 5).
          No live or simulated scores are shown on this page.
        </p>
      </section>
    </div>
  );
}