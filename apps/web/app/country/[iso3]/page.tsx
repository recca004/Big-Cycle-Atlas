"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { fetchCountry, fetchCountryObservations } from "@/lib/api";
import type { Country } from "@/types/country";
import type { CountryObservation } from "@/lib/api";

const INDICATOR_LABELS: Record<string, string> = {
  GDP_GROWTH: "GDP Growth",
  GDP_CURRENT_USD: "GDP",
  GDP_PER_CAPITA: "GDP per Capita",
};

const TRADE_LABELS: [string, string][] = [
  ["EXPORTS_GDP", "Exports"],
  ["IMPORTS_GDP", "Imports"],
  ["TRADE_BALANCE", "Trade balance"],
  ["CURRENT_ACCOUNT_GDP", "Current account"],
  ["GROSS_CAPITAL_FORMATION_GDP", "Gross capital formation"],
];

const GOVERNANCE_LABELS: [string, string][] = [
  ["RULE_OF_LAW_WGI_SCORE", "Rule of Law"],
  ["CONTROL_OF_CORRUPTION_WGI_SCORE", "Control of Corruption"],
  ["POLITICAL_STABILITY_WGI_SCORE", "Political Stability"],
];

const SOURCE_LABELS: Record<string, string> = {
  world_bank: "World Bank",
  bis: "BIS",
  oecd: "OECD",
};

function formatPercent(value: number): string {
  return `${new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)}%`;
}

function formatDecimal(value: number): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

function formatQuarter(periodStart: string): string {
  const d = new Date(periodStart);
  const quarter = Math.floor(d.getUTCMonth() / 3) + 1;
  return `${d.getUTCFullYear()} Q${quarter}`;
}

function sourceLabel(observation: CountryObservation): string {
  if (!observation.source_key) return "Unknown source";
  return SOURCE_LABELS[observation.source_key] ?? observation.source_key;
}

function formatUsdCompact(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

function formatUsdWhole(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

function yearOf(observation: CountryObservation): number {
  return new Date(observation.period_start).getUTCFullYear();
}

function formatDate(iso: string): string {
  return new Date(iso).toISOString().slice(0, 10);
}

function formatIndicatorValue(
  code: string,
  value: number,
): string {
  if (code === "GDP_GROWTH") return formatPercent(value);
  if (code === "GDP_CURRENT_USD") return formatUsdCompact(value);
  if (code === "GDP_PER_CAPITA") return formatUsdWhole(value);
  return String(value);
}

export default function CountryPage() {
  const params = useParams<{ iso3: string }>();
  const iso3 = (params.iso3 ?? "").toUpperCase();
  const [country, setCountry] = useState<Country | null>(null);
  const [observations, setObservations] = useState<CountryObservation[] | null>(
    null,
  );
  const [state, setState] = useState<"loading" | "error" | "not-found" | "ready">(
    "loading",
  );

  useEffect(() => {
    let cancelled = false;
    fetchCountry(iso3)
      .then(async (data) => {
        if (cancelled) return;
        if (data === null) {
          setState("not-found");
          return;
        }
        setCountry(data);
        try {
          const obs = await fetchCountryObservations(iso3);
          if (!cancelled) setObservations(obs);
        } catch {
          if (!cancelled) setObservations([]);
        }
        if (!cancelled) setState("ready");
      })
      .catch(() => {
        if (!cancelled) setState("error");
      });
    return () => {
      cancelled = true;
    };
  }, [iso3]);

  const byIndicator = new Map<string, CountryObservation[]>();
  for (const obs of observations ?? []) {
    if (!obs.indicator_code) continue;
    const list = byIndicator.get(obs.indicator_code) ?? [];
    list.push(obs);
    byIndicator.set(obs.indicator_code, list);
  }
  // API orders by period_start desc, so the first entry is the latest period
  const latest = (code: string) => byIndicator.get(code)?.[0];
  const growthHistory = (byIndicator.get("GDP_GROWTH") ?? []).slice(0, 10);
  const gapHistory = (byIndicator.get("CREDIT_TO_GDP_GAP") ?? []).slice(0, 8);
  const dsrHistory = (byIndicator.get("DEBT_SERVICE_RATIO") ?? []).slice(0, 8);
  const productivityHistory = (byIndicator.get("LABOUR_PRODUCTIVITY_PER_HOUR") ?? []).slice(0, 8);
  const ulcHistory = (byIndicator.get("UNIT_LABOUR_COST_GROWTH") ?? []).slice(0, 8);
  const latestGap = latest("CREDIT_TO_GDP_GAP");
  const latestDsr = latest("DEBT_SERVICE_RATIO");
  const latestProductivity = latest("LABOUR_PRODUCTIVITY_PER_HOUR");
  const latestUlc = latest("UNIT_LABOUR_COST_GROWTH");
  const hasOecdData = Boolean(latestProductivity || latestUlc);
  const lastRetrieved = (observations ?? []).reduce<string | null>(
    (acc, obs) => (acc === null || obs.retrieved_at > acc ? obs.retrieved_at : acc),
    null,
  );
  const hasEconomicData = (observations ?? []).length > 0;
  const hasTradeData = TRADE_LABELS.some(([code]) => latest(code));
  const hasGovernanceData = GOVERNANCE_LABELS.some(([code]) => latest(code));
  const latestGini = latest("GINI_INDEX");
  const latestMilitaryUsd = latest("MILITARY_EXPENDITURE_USD");
  const latestMilitaryGdp = latest("MILITARY_EXPENDITURE_GDP");
  const hasMilitaryData = Boolean(latestMilitaryUsd || latestMilitaryGdp);

  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-16">
      <p className="label-md mb-8 text-tertiary">Country</p>
      {state === "loading" && <p className="text-sm text-tertiary">Loading country…</p>}
      {state === "error" && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="headline-sm">Country data is currently unavailable.</p>
          <p className="mt-2 text-sm text-tertiary">
            The Atlas could not reach the API. Start the backend with{" "}
            <code>uv run python run.py</code> from apps/api, then reload.
          </p>
        </div>
      )}
      {state === "not-found" && (
        <div className="rounded-lg border border-border bg-surface p-4">
          <p className="headline-sm">{iso3} is not tracked by the Atlas.</p>
          <p className="mt-2 text-sm text-tertiary">
            The list of tracked countries is on the countries page.
          </p>
          <Link
            href="/countries"
            className="mt-4 inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            Back to countries
          </Link>
        </div>
      )}
      {state === "ready" && country && (
        <>
          <h1 className="headline-lg">{country.name}</h1>
          <p className="label-md mt-2 text-tertiary">
            {country.iso3} · {country.region}
          </p>

          <div className="mt-8 rounded-lg border border-border bg-surface p-4">
            <p className="headline-sm">Big Cycle phase</p>
            <p className="mt-2 text-sm text-tertiary">Not yet calculated</p>
            <p className="mt-1 text-sm text-tertiary">
              Force scoring and Big Cycle phase calculation arrive with the force
              engine (Milestone 5).
            </p>
          </div>

          <div className="mt-8 rounded-lg border border-border bg-surface p-4">
            <p className="headline-sm">Big Cycle Forces</p>
            <p className="mt-2 text-sm text-tertiary">
              Which of the 17 forces the Atlas can currently measure for{" "}
              {country.name}.
            </p>
            <Link
              href={`/country/${iso3}/forces`}
              className="mt-3 inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
            >
              View force coverage →
            </Link>
          </div>

          <div className="mt-8 rounded-lg border border-border bg-surface p-4">
            <p className="headline-sm">Economic data</p>
            {!hasEconomicData ? (
              <p className="mt-2 text-sm text-tertiary">
                No imported economic observations yet.
              </p>
            ) : (
              <>
                <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-3">
                  {Object.entries(INDICATOR_LABELS).map(([code, label]) => {
                    const obs = latest(code);
                    return (
                      <div key={code}>
                        <p className="label-md text-tertiary">{label}</p>
                        {obs ? (
                          <>
                            <p className="mt-1 text-2xl font-semibold tabular-nums">
                              {formatIndicatorValue(code, obs.value)}
                            </p>
                            <p className="mt-1 text-sm text-tertiary">
                              {yearOf(obs)} · {sourceLabel(obs)}
                            </p>
                          </>
                        ) : (
                          <p className="mt-1 text-sm text-tertiary">No data</p>
                        )}
                      </div>
                    );
                  })}
                </div>
                {lastRetrieved && (
                  <p className="mt-4 text-sm text-tertiary">
                    Last retrieved {formatDate(lastRetrieved)}
                  </p>
                )}
              </>
            )}
          </div>

          {hasTradeData && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">Trade &amp; Investment</p>
              <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-3">
                {TRADE_LABELS.map(([code, label]) => {
                  const obs = latest(code);
                  return (
                    <div key={code}>
                      <p className="label-md text-tertiary">{label}</p>
                      {obs ? (
                        <>
                          <p className="mt-1 text-2xl font-semibold tabular-nums">
                            {formatPercent(obs.value)}
                          </p>
                          <p className="mt-1 text-sm text-tertiary">% of GDP</p>
                          <p className="mt-1 text-sm text-tertiary">
                            {yearOf(obs)} · Source: {sourceLabel(obs)}
                          </p>
                        </>
                      ) : (
                        <p className="mt-1 text-sm text-tertiary">No data</p>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 text-sm text-tertiary">
                Annual World Bank data. Trade balance is the World Bank&apos;s
                published external balance on goods and services.
              </p>
            </div>
          )}

          {hasGovernanceData && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">Governance</p>
              <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-3">
                {GOVERNANCE_LABELS.map(([code, label]) => {
                  const obs = latest(code);
                  return (
                    <div key={code}>
                      <p className="label-md text-tertiary">{label}</p>
                      {obs ? (
                        <>
                          <p className="mt-1 text-2xl font-semibold tabular-nums">
                            {formatDecimal(obs.value)} / 100
                          </p>
                          <p className="mt-1 text-sm text-tertiary">
                            {yearOf(obs)} · Source: {sourceLabel(obs)} / WGI
                          </p>
                        </>
                      ) : (
                        <p className="mt-1 text-sm text-tertiary">No data</p>
                      )}
                    </div>
                  );
                })}
              </div>
              <p className="mt-4 text-sm text-tertiary">
                Annual World Bank WGI governance scores (0–100 scale). WGI scores
                are perception-based composite governance indicators and include
                measurement uncertainty.
              </p>
            </div>
          )}

          {latestGini && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">Inequality</p>
              <p className="label-md mt-4 text-tertiary">Gini index</p>
              <p className="mt-1 text-2xl font-semibold tabular-nums">
                {formatDecimal(latestGini.value)}
              </p>
              <p className="mt-1 text-sm text-tertiary">
                Latest available: {yearOf(latestGini)} · Source:{" "}
                {sourceLabel(latestGini)}
              </p>
              <p className="mt-4 text-sm text-tertiary">
                Gini measures income inequality only; it is not a complete
                measure of wealth, opportunity, or social-value gaps.
              </p>
            </div>
          )}

          {hasMilitaryData && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">Military</p>
              <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
                <div>
                  <p className="label-md text-tertiary">Military expenditure</p>
                  {latestMilitaryUsd ? (
                    <>
                      <p className="mt-1 text-2xl font-semibold tabular-nums">
                        {formatUsdCompact(latestMilitaryUsd.value)}
                      </p>
                      <p className="mt-1 text-sm text-tertiary">
                        {yearOf(latestMilitaryUsd)} · Source:{" "}
                        {sourceLabel(latestMilitaryUsd)} · Underlying source: SIPRI
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-tertiary">No data</p>
                  )}
                </div>
                <div>
                  <p className="label-md text-tertiary">
                    Military expenditure (% of GDP)
                  </p>
                  {latestMilitaryGdp ? (
                    <>
                      <p className="mt-1 text-2xl font-semibold tabular-nums">
                        {formatPercent(latestMilitaryGdp.value)}
                      </p>
                      <p className="mt-1 text-sm text-tertiary">
                        {yearOf(latestMilitaryGdp)} · Source:{" "}
                        {sourceLabel(latestMilitaryGdp)} · Underlying source: SIPRI
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-tertiary">No data</p>
                  )}
                </div>
              </div>
              <p className="mt-4 text-sm text-tertiary">
                Military expenditure is an input proxy for military strength;
                spending alone does not measure military capability.
              </p>
            </div>
          )}

          {(latestGap || latestDsr) && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">Debt &amp; credit</p>
              <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
                <div>
                  <p className="label-md text-tertiary">Credit-to-GDP gap</p>
                  {latestGap ? (
                    <>
                      <p className="mt-1 text-2xl font-semibold tabular-nums">
                        {formatDecimal(latestGap.value)}
                      </p>
                      <p className="mt-1 text-sm text-tertiary">percentage of GDP</p>
                      <p className="mt-1 text-sm text-tertiary">
                        {formatQuarter(latestGap.period_start)} · Source: {sourceLabel(latestGap)}
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-tertiary">No data</p>
                  )}
                </div>
                <div>
                  <p className="label-md text-tertiary">Debt service ratio</p>
                  {latestDsr ? (
                    <>
                      <p className="mt-1 text-2xl font-semibold tabular-nums">
                        {formatPercent(latestDsr.value)}
                      </p>
                      <p className="mt-1 text-sm text-tertiary">per cent</p>
                      <p className="mt-1 text-sm text-tertiary">
                        {formatQuarter(latestDsr.period_start)} · Source: {sourceLabel(latestDsr)}
                      </p>
                    </>
                  ) : (
                    <p className="mt-1 text-sm text-tertiary">No data</p>
                  )}
                </div>
              </div>

              {gapHistory.length > 0 && (
                <div className="mt-6">
                  <p className="label-md text-tertiary">Credit-to-GDP gap history</p>
                  <table className="mt-2 w-full max-w-sm text-sm tabular-nums">
                    <tbody>
                      {gapHistory.map((obs) => (
                        <tr key={obs.id} className="border-t border-border first:border-t-0">
                          <td className="py-1.5 pr-6 text-tertiary">
                            {formatQuarter(obs.period_start)}
                          </td>
                          <td className="py-1.5 text-right">{formatDecimal(obs.value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {dsrHistory.length > 0 && (
                <div className="mt-6">
                  <p className="label-md text-tertiary">Debt service ratio history</p>
                  <table className="mt-2 w-full max-w-sm text-sm tabular-nums">
                    <tbody>
                      {dsrHistory.map((obs) => (
                        <tr key={obs.id} className="border-t border-border first:border-t-0">
                          <td className="py-1.5 pr-6 text-tertiary">
                            {formatQuarter(obs.period_start)}
                          </td>
                          <td className="py-1.5 text-right">{formatPercent(obs.value)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <p className="mt-4 text-sm text-tertiary">
                Quarterly data from the BIS. DSR levels are comparable within a
                country&apos;s own history, not across countries.
              </p>
            </div>
          )}

          <div className="mt-8 rounded-lg border border-border bg-surface p-4">
            <p className="headline-sm">Productivity &amp; Competitiveness</p>
            {!hasOecdData ? (
              <p className="mt-2 text-sm text-tertiary">
                No OECD productivity data available for this country.
              </p>
            ) : (
              <>
                <div className="mt-4 grid gap-x-8 gap-y-3 sm:grid-cols-2">
                  <div>
                    <p className="label-md text-tertiary">Labour productivity</p>
                    {latestProductivity ? (
                      <>
                        <p className="mt-1 text-2xl font-semibold tabular-nums">
                          {formatDecimal(latestProductivity.value)}
                        </p>
                        <p className="mt-1 text-sm text-tertiary">USD PPP/hour</p>
                        <p className="mt-1 text-sm text-tertiary">
                          {yearOf(latestProductivity)} · Source: {sourceLabel(latestProductivity)}
                        </p>
                      </>
                    ) : (
                      <p className="mt-1 text-sm text-tertiary">No data</p>
                    )}
                  </div>
                  <div>
                    <p className="label-md text-tertiary">Unit labour cost growth</p>
                    {latestUlc ? (
                      <>
                        <p className="mt-1 text-2xl font-semibold tabular-nums">
                          {formatPercent(latestUlc.value)}
                        </p>
                        <p className="mt-1 text-sm text-tertiary">percent per annum</p>
                        <p className="mt-1 text-sm text-tertiary">
                          {formatQuarter(latestUlc.period_start)} · Source: {sourceLabel(latestUlc)}
                        </p>
                      </>
                    ) : (
                      <p className="mt-1 text-sm text-tertiary">No data</p>
                    )}
                  </div>
                </div>

                {productivityHistory.length > 0 && (
                  <div className="mt-6">
                    <p className="label-md text-tertiary">
                      Labour productivity history (USD PPP/hour)
                    </p>
                    <table className="mt-2 w-full max-w-sm text-sm tabular-nums">
                      <tbody>
                        {productivityHistory.map((obs) => (
                          <tr key={obs.id} className="border-t border-border first:border-t-0">
                            <td className="py-1.5 pr-6 text-tertiary">{yearOf(obs)}</td>
                            <td className="py-1.5 text-right">{formatDecimal(obs.value)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {ulcHistory.length > 0 && (
                  <div className="mt-6">
                    <p className="label-md text-tertiary">Unit labour cost growth history</p>
                    <table className="mt-2 w-full max-w-sm text-sm tabular-nums">
                      <tbody>
                        {ulcHistory.map((obs) => (
                          <tr key={obs.id} className="border-t border-border first:border-t-0">
                            <td className="py-1.5 pr-6 text-tertiary">
                              {formatQuarter(obs.period_start)}
                            </td>
                            <td className="py-1.5 text-right">{formatPercent(obs.value)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <p className="mt-4 text-sm text-tertiary">
                  OECD productivity and unit labour cost data. Cost competitiveness
                  is best read as changes relative to each country&apos;s own history.
                </p>
              </>
            )}
          </div>

          {growthHistory.length > 0 && (
            <div className="mt-8 rounded-lg border border-border bg-surface p-4">
              <p className="headline-sm">GDP growth history</p>
              <table className="mt-4 w-full max-w-sm text-sm tabular-nums">
                <tbody>
                  {growthHistory.map((obs) => (
                    <tr key={obs.id} className="border-t border-border first:border-t-0">
                      <td className="py-1.5 pr-6 text-tertiary">{yearOf(obs)}</td>
                      <td className="py-1.5 text-right">
                        {formatPercent(obs.value)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <Link
            href="/countries"
            className="mt-8 inline-flex h-[34px] items-center rounded-md bg-primary px-2.5 text-[13px] text-inverse hover:bg-accent"
          >
            Back to countries
          </Link>
        </>
      )}
    </div>
  );
}