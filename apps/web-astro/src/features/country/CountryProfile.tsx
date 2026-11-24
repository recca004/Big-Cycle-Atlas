import { useEffect, useMemo, useState } from "react";
import { fetchCountry, fetchCountryObservations } from "@/lib/api/client";
import type { Country, CountryObservation } from "@/types/api";
import {
  formatDate,
  formatDecimal,
  formatPercent,
  formatQuarter,
  formatUsdCompact,
  formatUsdWhole,
  sourceLabel,
  yearOf,
} from "@/lib/format";

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

type State = "loading" | "error" | "not-found" | "ready";

function formatIndicatorValue(code: string, value: number): string {
  if (code === "GDP_GROWTH") return formatPercent(value);
  if (code === "GDP_CURRENT_USD") return formatUsdCompact(value);
  if (code === "GDP_PER_CAPITA") return formatUsdWhole(value);
  return String(value);
}

function Metric({
  label,
  children,
  meta,
}: {
  label: string;
  children?: React.ReactNode;
  meta?: React.ReactNode;
}) {
  return (
    <div>
      <p className="label-md text-tertiary">{label}</p>
      {children ?? <p className="body-sm">No data</p>}
      {meta}
    </div>
  );
}

function Value({ children }: { children: React.ReactNode }) {
  return <p className="metric-value">{children}</p>;
}

function Meta({ children }: { children: React.ReactNode }) {
  return <p className="section-note" style={{ marginTop: 4 }}>{children}</p>;
}

export function CountryProfile({ iso3 }: { iso3: string }) {
  const [country, setCountry] = useState<Country | null>(null);
  const [observations, setObservations] = useState<CountryObservation[] | null>(
    null,
  );
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    const controller = new AbortController();
    fetchCountry(iso3, { signal: controller.signal })
      .then(async (data) => {
        if (data === null) {
          setState("not-found");
          return;
        }
        setCountry(data);
        try {
          const page = await fetchCountryObservations(
            iso3,
            { limit: 1000 },
            { signal: controller.signal },
          );
          setObservations(page.items);
        } catch {
          setObservations([]);
        }
        setState("ready");
      })
      .catch(() => setState("error"));
    return () => controller.abort();
  }, [iso3]);

  const byIndicator = useMemo(() => {
    const map = new Map<string, CountryObservation[]>();
    for (const obs of observations ?? []) {
      if (!obs.indicator_code) continue;
      const list = map.get(obs.indicator_code) ?? [];
      list.push(obs);
      map.set(obs.indicator_code, list);
    }
    return map;
  }, [observations]);

  const latest = (code: string) => byIndicator.get(code)?.[0];
  const gapHistory = (byIndicator.get("CREDIT_TO_GDP_GAP") ?? []).slice(0, 8);
  const dsrHistory = (byIndicator.get("DEBT_SERVICE_RATIO") ?? []).slice(0, 8);
  const latestGap = latest("CREDIT_TO_GDP_GAP");
  const latestDsr = latest("DEBT_SERVICE_RATIO");
  const latestProductivity = latest("LABOUR_PRODUCTIVITY_PER_HOUR");
  const latestUlc = latest("UNIT_LABOUR_COST_GROWTH");
  const latestGini = latest("GINI_INDEX");
  const latestMilitaryUsd = latest("MILITARY_EXPENDITURE_USD");
  const latestMilitaryGdp = latest("MILITARY_EXPENDITURE_GDP");
  const latestGovDebt = latest("GOVERNMENT_DEBT_GDP");
  const latestInflation = latest("INFLATION_CPI");
  const latestTertiary = latest("TERTIARY_ATTAINMENT_25_34");
  const latestWealth = latest("WEALTH_SHARE_TOP_10");
  const hasOecdData = Boolean(latestProductivity || latestUlc);
  const hasTradeData = TRADE_LABELS.some(([code]) => latest(code));
  const hasGovernanceData = GOVERNANCE_LABELS.some(([code]) => latest(code));
  const hasMilitaryData = Boolean(latestMilitaryUsd || latestMilitaryGdp);
  const hasDebtData = Boolean(latestGap || latestDsr || latestGovDebt);
  const lastRetrieved = (observations ?? []).reduce<string | null>(
    (acc, obs) => (acc === null || obs.retrieved_at > acc ? obs.retrieved_at : acc),
    null,
  );

  if (state === "loading") {
    return <p className="body-sm">Loading country…</p>;
  }

  if (state === "error") {
    return (
      <div className="glass-subtle state-box" role="alert">
        <p className="headline-sm">Country data is currently unavailable.</p>
        <p className="body-sm">
          The Atlas could not reach the API. Start the backend with{" "}
          <code>uv run python run.py</code> from <code>apps/api</code>, then
          reload.
        </p>
      </div>
    );
  }

  if (state === "not-found") {
    return (
      <div className="glass-subtle state-box">
        <p className="headline-sm">{iso3} is not tracked by the Atlas.</p>
        <p className="body-sm">
          The list of tracked countries is on the{" "}
          <a href="/countries">countries page</a>.
        </p>
      </div>
    );
  }

  if (!country) return null;

  return (
    <div className="section-stack">
      <div className="glass" style={{ padding: "var(--space-5)" }}>
        <p className="headline-sm">Big Cycle phase</p>
        <p className="body-sm" style={{ marginTop: "var(--space-2)" }}>
          Not yet calculated — force scoring and Big Cycle phase calculation
          arrive with the cycle engine (Milestone 6).
        </p>
      </div>

      <div className="glass" style={{ padding: "var(--space-5)" }}>
        <p className="headline-sm">Big Cycle Forces</p>
        <p className="body-sm" style={{ marginTop: "var(--space-2)" }}>
          Which of the 17 forces the Atlas can currently measure for{" "}
          {country.name}.
        </p>
        <a
          className="btn btn-primary"
          style={{ marginTop: "var(--space-3)" }}
          href={`/country/${iso3}/forces`}
        >
          View force coverage →
        </a>
      </div>

      <div className="glass" style={{ padding: "var(--space-5)" }}>
        <p className="headline-sm">Economic data</p>
        {(observations ?? []).length === 0 ? (
          <p className="body-sm" style={{ marginTop: "var(--space-2)" }}>
            No imported economic observations yet.
          </p>
        ) : (
          <>
            <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
              {Object.entries(INDICATOR_LABELS).map(([code, label]) => {
                const obs = latest(code);
                return (
                  <Metric key={code} label={label}>
                    {obs ? (
                      <>
                        <Value>{formatIndicatorValue(code, obs.value)}</Value>
                        <Meta>
                          {yearOf(obs.period_start)} · {sourceLabel(obs.source_key)}
                        </Meta>
                      </>
                    ) : undefined}
                  </Metric>
                );
              })}
              {latestInflation && (
                <Metric label="Inflation (CPI)">
                  <Value>{formatPercent(latestInflation.value)}</Value>
                  <Meta>
                    {yearOf(latestInflation.period_start)} ·{" "}
                    {sourceLabel(latestInflation.source_key)}
                  </Meta>
                </Metric>
              )}
            </div>
            {lastRetrieved && (
              <p className="section-note">
                Last retrieved {formatDate(lastRetrieved)}
              </p>
            )}
          </>
        )}
      </div>

      {hasTradeData && (
        <div className="glass" style={{ padding: "var(--space-5)" }}>
          <p className="headline-sm">Trade &amp; Investment</p>
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            {TRADE_LABELS.map(([code, label]) => {
              const obs = latest(code);
              return (
                <Metric key={code} label={label}>
                  {obs ? (
                    <>
                      <Value>{formatPercent(obs.value)}</Value>
                      <Meta>
                        % of GDP · {yearOf(obs.period_start)} ·{" "}
                        {sourceLabel(obs.source_key)}
                      </Meta>
                    </>
                  ) : undefined}
                </Metric>
              );
            })}
          </div>
          <p className="section-note">
            Annual World Bank data. Trade balance is the World Bank&apos;s
            published external balance on goods and services.
          </p>
        </div>
      )}

      {hasGovernanceData && (
        <div className="glass" style={{ padding: "var(--space-5)" }}>
          <p className="headline-sm">Governance</p>
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            {GOVERNANCE_LABELS.map(([code, label]) => {
              const obs = latest(code);
              return (
                <Metric key={code} label={label}>
                  {obs ? (
                    <>
                      <Value>{formatDecimal(obs.value)} / 100</Value>
                      <Meta>
                        {yearOf(obs.period_start)} · {sourceLabel(obs.source_key)}{" "}
                        / WGI
                      </Meta>
                    </>
                  ) : undefined}
                </Metric>
              );
            })}
          </div>
          <p className="section-note">
            Annual World Bank WGI governance scores (0–100). WGI scores are
            perception-based composites and include measurement uncertainty.
          </p>
        </div>
      )}

      {(latestGini || latestWealth || latestTertiary) && (
        <div className="glass" style={{ padding: "var(--space-5)" }}>
          <p className="headline-sm">Inequality &amp; education</p>
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            {latestGini && (
              <Metric label="Gini index">
                <Value>{formatDecimal(latestGini.value)}</Value>
                <Meta>
                  Latest available: {yearOf(latestGini.period_start)} ·{" "}
                  {sourceLabel(latestGini.source_key)}
                </Meta>
              </Metric>
            )}
            {latestWealth && (
              <Metric label="Top 10% wealth share">
                <Value>{formatPercent(latestWealth.value * 100)}</Value>
                <Meta>
                  {yearOf(latestWealth.period_start)} ·{" "}
                  {sourceLabel(latestWealth.source_key)}
                </Meta>
              </Metric>
            )}
            {latestTertiary && (
              <Metric label="Tertiary attainment (25–34)">
                <Value>{formatPercent(latestTertiary.value)}</Value>
                <Meta>
                  {yearOf(latestTertiary.period_start)} ·{" "}
                  {sourceLabel(latestTertiary.source_key)}
                </Meta>
              </Metric>
            )}
          </div>
          <p className="section-note">
            Gini measures income inequality only; it is not a complete measure
            of wealth, opportunity, or social-value gaps.
          </p>
        </div>
      )}

      {hasMilitaryData && (
        <div className="glass" style={{ padding: "var(--space-5)" }}>
          <p className="headline-sm">Military</p>
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            <Metric label="Military expenditure">
              {latestMilitaryUsd ? (
                <>
                  <Value>{formatUsdCompact(latestMilitaryUsd.value)}</Value>
                  <Meta>
                    {yearOf(latestMilitaryUsd.period_start)} · SIPRI via{" "}
                    {sourceLabel(latestMilitaryUsd.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
            <Metric label="Military expenditure (% of GDP)">
              {latestMilitaryGdp ? (
                <>
                  <Value>{formatPercent(latestMilitaryGdp.value)}</Value>
                  <Meta>
                    {yearOf(latestMilitaryGdp.period_start)} · SIPRI via{" "}
                    {sourceLabel(latestMilitaryGdp.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
          </div>
          <p className="section-note">
            Military expenditure is an input proxy for military strength;
            spending alone does not measure military capability.
          </p>
        </div>
      )}

      {hasDebtData && (
        <div className="glass" style={{ padding: "var(--space-5)" }}>
          <p className="headline-sm">Debt &amp; credit</p>
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            <Metric label="Credit-to-GDP gap">
              {latestGap ? (
                <>
                  <Value>{formatDecimal(latestGap.value)}</Value>
                  <Meta>
                    % of GDP · {formatQuarter(latestGap.period_start)} ·{" "}
                    {sourceLabel(latestGap.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
            <Metric label="Debt service ratio">
              {latestDsr ? (
                <>
                  <Value>{formatPercent(latestDsr.value)}</Value>
                  <Meta>
                    per cent · {formatQuarter(latestDsr.period_start)} ·{" "}
                    {sourceLabel(latestDsr.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
            <Metric label="Government debt">
              {latestGovDebt ? (
                <>
                  <Value>{formatPercent(latestGovDebt.value)}</Value>
                  <Meta>
                    % of GDP · {yearOf(latestGovDebt.period_start)} ·{" "}
                    {sourceLabel(latestGovDebt.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
          </div>

          {gapHistory.length > 0 && (
            <div className="mini-history">
              <p className="label-md text-tertiary">Credit-to-GDP gap history</p>
              <table>
                <tbody>
                  {gapHistory.map((obs) => (
                    <tr key={obs.id}>
                      <td>{formatQuarter(obs.period_start)}</td>
                      <td>{formatDecimal(obs.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {dsrHistory.length > 0 && (
            <div className="mini-history">
              <p className="label-md text-tertiary">Debt service ratio history</p>
              <table>
                <tbody>
                  {dsrHistory.map((obs) => (
                    <tr key={obs.id}>
                      <td>{formatQuarter(obs.period_start)}</td>
                      <td>{formatPercent(obs.value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          <p className="section-note">
            Quarterly data from the BIS. DSR levels are comparable within a
            country&apos;s own history, not across countries.
          </p>
        </div>
      )}

      <div className="glass" style={{ padding: "var(--space-5)" }}>
        <p className="headline-sm">Productivity &amp; competitiveness</p>
        {!hasOecdData ? (
          <p className="body-sm" style={{ marginTop: "var(--space-2)" }}>
            No OECD productivity data available for this country.
          </p>
        ) : (
          <div className="metric-grid" style={{ marginTop: "var(--space-4)" }}>
            <Metric label="Labour productivity">
              {latestProductivity ? (
                <>
                  <Value>{formatDecimal(latestProductivity.value)}</Value>
                  <Meta>
                    USD PPP/hour · {yearOf(latestProductivity.period_start)} ·{" "}
                    {sourceLabel(latestProductivity.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
            <Metric label="Unit labour cost growth">
              {latestUlc ? (
                <>
                  <Value>{formatPercent(latestUlc.value)}</Value>
                  <Meta>
                    % p.a. · {formatQuarter(latestUlc.period_start)} ·{" "}
                    {sourceLabel(latestUlc.source_key)}
                  </Meta>
                </>
              ) : undefined}
            </Metric>
          </div>
        )}
      </div>
    </div>
  );
}
