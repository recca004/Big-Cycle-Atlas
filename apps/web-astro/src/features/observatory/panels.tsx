/** Observatory side panels — all data is EXPERIMENTAL model output and
 *  labelled as such. Nothing here fabricates forecasts or countdowns. */

import { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import type {
  DailyChanges,
  ObservatoryCountry,
  ObservatoryFreshness,
  RefreshJob,
  TransitionMonitor,
} from "@/types/observatory";
import { stageLabel } from "./stages";
import { formatMeasureValue } from "./observatoryService";

const fmtUsd = (v: number) =>
  v >= 1e12
    ? `$${(v / 1e12).toFixed(1)}T`
    : v >= 1e9
      ? `$${(v / 1e9).toFixed(0)}B`
      : `$${(v / 1e6).toFixed(0)}M`;

/** Unit-aware measurement formatting — trillions/billions for USD,
 *  percentage points for rates/ratios, per-capita grouping otherwise. */
export function fmtMeasure(v: number, unit: string): string {
  if (/^usd/i.test(unit)) return fmtUsd(v);
  if (/%/.test(unit))
    return `${v.toLocaleString("en-CH", { maximumFractionDigits: 1 })}%`;
  if (/score/i.test(unit))
    return v.toLocaleString("en-CH", { maximumFractionDigits: 1 });
  return v.toLocaleString("en-CH", { maximumFractionDigits: 0 });
}

/* ---------- PowerStudyCard (balanced first-screen incumbent/challenger panels) ---------- */

function formatCurrencySummary(country: ObservatoryCountry, demo: boolean): { text: string; period: string } {
  const m = country.international_power.monetary_influence;
  if (!m) return { text: "Unavailable", period: "—" };
  if (demo) {
    return {
      text: `${m.currency_code ?? country.iso3} · demo fixture`,
      period: "2026 demo",
    };
  }
  const ccy = m.currency_code ?? "—";
  if (m.is_shared_currency_area) {
    const areaShare =
      m.currency_area_cofer_share_pct != null
        ? `${m.currency_area_cofer_share_pct.toFixed(1)}% COFER`
        : "COFER n/a";
    return {
      text: `${ccy} shared area (${areaShare} · not national)`,
      period: m.cofer_period ?? m.fx_turnover_period ?? "—",
    };
  }
  const parts: string[] = [ccy];
  if (m.cofer_reserve_share_pct != null) {
    parts.push(`${m.cofer_reserve_share_pct.toFixed(1)}% reserves`);
  } else {
    parts.push("COFER n/a");
  }
  if (m.fx_turnover_share_200pct != null) {
    parts.push(`${m.fx_turnover_share_200pct.toFixed(1)}% FX`);
  }
  return {
    text: parts.join(" · "),
    period: [m.cofer_period, m.fx_turnover_period].filter(Boolean).join(" / ") || "—",
  };
}

export function PowerStudyCard({
  role,
  selectId,
  country,
  countries,
  disabledIso3,
  playbackPeriod,
  isFocused,
  demo = false,
  onChangeCountry,
  onInspectDetails,
}: {
  role: "Incumbent" | "Challenger";
  selectId: string;
  country: ObservatoryCountry | null;
  countries: ObservatoryCountry[];
  disabledIso3: string;
  playbackPeriod: string | null;
  isFocused: boolean;
  demo?: boolean;
  onChangeCountry: (iso3: string) => void;
  onInspectDetails: (iso3: string) => void;
}) {
  if (!country) return null;

  const histPoint = playbackPeriod
    ? country.history.find((pt) => pt.period === playbackPeriod)
    : null;
  const activeStage = playbackPeriod ? (histPoint?.stage ?? null) : country.stage;
  const activeScore = playbackPeriod ? (histPoint?.score ?? null) : country.domestic_condition_score;
  const activePeriodLabel = playbackPeriod ?? country.period ?? "latest";

  const gs = country.international_power.global_shares;
  const econ = country.international_power.economic_size;
  const trade = country.international_power.international_trade;
  const mil = country.international_power.military_resources;
  const ccy = formatCurrencySummary(country, demo);

  const shareRow = (
    label: string,
    worldPct: number | null | undefined,
    worldPeriod: string | null | undefined,
    fallbackPct?: number | null,
    fallbackPeriod?: string | null,
    fallbackSuffix = "tracked",
  ) => {
    const pct = worldPct ?? (demo ? (fallbackPct ?? null) : null);
    const rawPeriod = worldPct != null ? worldPeriod : fallbackPeriod;
    const periodNote = rawPeriod
      ? playbackPeriod
        ? `latest ${rawPeriod}`
        : rawPeriod
      : "—";
    return (
      <div className="obs-study-row" key={label}>
        <dt>{label}</dt>
        <dd>
          <span className="obs-study-val">
            {pct != null ? `${pct.toFixed(1)}%` : "Unavailable"}
            {worldPct == null && pct != null ? ` (${fallbackSuffix})` : ""}
          </span>
          <span className="obs-study-period">{periodNote}</span>
        </dd>
      </div>
    );
  };

  return (
    <section
      className={isFocused ? "obs-panel glass obs-study-card focused" : "obs-panel glass obs-study-card"}
      aria-label={`${role} country under study — ${country.name}`}
    >
      <div className="obs-study-head">
        <label htmlFor={selectId} className="obs-study-picker">
          <span className="obs-study-role">{role} under study</span>
          <select
            id={selectId}
            className="glass-button"
            value={country.iso3}
            onChange={(e) => onChangeCountry(e.target.value)}
          >
            {countries.map((c) => (
              <option key={c.iso3} value={c.iso3} disabled={c.iso3 === disabledIso3}>
                {c.name} ({c.iso3})
              </option>
            ))}
          </select>
        </label>
        <span className="obs-chip">{country.iso3}</span>
      </div>

      <div className="obs-study-stage">
        <div>
          <span className="obs-muted">
            Experimental domestic stage ({activePeriodLabel})
          </span>
          <strong>
            {activeStage ? stageLabel(activeStage) : `Unclassified in ${activePeriodLabel}`}
          </strong>
        </div>
        <div className="obs-study-cond">
          <span className="obs-muted">Condition</span>
          <strong>{activeScore != null ? activeScore.toFixed(1) : "—"}</strong>
        </div>
      </div>

      <dl className="obs-study-metrics">
        {shareRow(
          "Global nominal GDP share",
          gs?.nominal_gdp?.share_pct,
          gs?.nominal_gdp?.period,
          econ?.tracked_share_pct,
          econ?.period,
        )}
        {shareRow(
          "Global PPP GDP share",
          gs?.ppp_gdp?.share_pct,
          gs?.ppp_gdp?.period,
          econ?.tracked_share_pct,
          econ?.period,
        )}
        {shareRow(
          "Merchandise export share",
          gs?.merchandise_exports?.share_pct,
          gs?.merchandise_exports?.period,
          trade?.tracked_share_pct,
          trade?.period,
        )}
        {shareRow(
          "Military expenditure share",
          gs?.military_expenditure?.share_pct,
          gs?.military_expenditure?.period,
          mil?.tracked_share_pct,
          mil?.period,
        )}
        <div className="obs-study-row">
          <dt>Currency influence</dt>
          <dd>
            <span className="obs-study-val">{ccy.text}</span>
            <span className="obs-study-period">
              {playbackPeriod && ccy.period !== "—" ? `latest ${ccy.period}` : ccy.period}
            </span>
          </dd>
        </div>
      </dl>

      <div className="obs-study-actions">
        <button
          type="button"
          className="glass-button"
          onClick={() => onInspectDetails(country.iso3)}
        >
          Inspect 17 forces & details
        </button>
        <a href={`/country/${country.iso3}`} className="obs-inline-link">
          Country page →
        </a>
      </div>
    </section>
  );
}

/* ---------- CompactTransitionMonitor (first-screen status summary) ---------- */

export function CompactTransitionMonitor({
  data,
  onOpenComparison,
}: {
  data: TransitionMonitor;
  onOpenComparison: () => void;
}) {
  const fr = data.forecast_readiness;
  return (
    <section className="obs-panel glass obs-monitor obs-monitor-compact" aria-label="Power transition monitor">
      <div className="obs-compact-monitor-head">
        <h2 className="obs-panel-title">Power transition monitor</h2>
        <span className="badge badge-warn">Evidence-gated</span>
      </div>

      <div className="obs-monitor-pair compact">
        <div>
          <span className="obs-muted">Incumbent under study</span>
          <strong>
            {data.incumbent_name} <span className="obs-chip">{data.incumbent_iso3}</span>
          </strong>
        </div>
        <div>
          <span className="obs-muted">Challenger under study</span>
          <strong>
            {data.challenger_name} <span className="obs-chip">{data.challenger_iso3}</span>
          </strong>
        </div>
      </div>

      <div className="obs-window compact">
        <div>
          <span className="obs-muted">Transition window status</span>
          <strong className={fr.overall_available ? "" : "obs-window-none"}>
            {fr.estimated_transition_window || "Not estimable"}
          </strong>
        </div>
        <span className="obs-muted">
          Strict release-safe periods: <strong>{fr.strict_eligible_periods}</strong>
        </span>
      </div>

      <p className="obs-muted obs-compact-limit">
        Research status: {fr.methodology_status}. Retrospective latest-vintage series and shared-input
        composite models cannot support a transition countdown or forecast probability.
      </p>

      <button
        type="button"
        className="glass-button obs-open-comparison-btn"
        onClick={onOpenComparison}
      >
        Open detailed comparison ({data.measurements.length} measures) →
      </button>
    </section>
  );
}

/* ---------- CountryFocusPanel (detailed research panel) ---------- */

export function CountryFocusPanel({
  country,
  powerNote,
}: {
  country: ObservatoryCountry | null;
  powerNote: string;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (ref.current)
      gsap.fromTo(
        ref.current.querySelectorAll("[data-fade]"),
        { opacity: 0, y: 8 },
        { opacity: 1, y: 0, duration: 0.4, stagger: 0.05, ease: "power2.out" },
      );
  }, [country?.iso3]);

  if (!country)
    return (
      <section className="obs-panel glass" aria-label="Selected country">
        <h2 className="obs-panel-title">Country under study</h2>
        <p className="body-sm">Select a marker on the clock.</p>
      </section>
    );

  const snaps = Object.entries(country.indicator_snapshots)
    .filter(([, snapshot]) => snapshot?.latest?.value != null)
    .slice(0, 5);
  const snap = (code: string) => country.indicator_snapshots[code]?.latest?.value ?? null;
  const power = country.international_power;
  const econ = power.economic_size;
  const military = power.military_resources;
  const trade = power.international_trade as { tracked_share_pct?: number | null } | undefined;
  const monetary = power.monetary_influence as { currency_code?: string; gov_10y_yield?: number | null; reserve_anchor_role?: string } | undefined;
  return (
    <section
      className="obs-panel glass"
      aria-label={`${country.name} — country under study`}
      ref={ref}
    >
      <h2 className="obs-panel-title" data-fade>
        {country.name}
        <span className="obs-chip">{country.iso3}</span>
      </h2>
      <dl className="obs-facts">
        <div data-fade>
          <dt>Experimental cycle stage</dt>
          <dd>
            <strong>{stageLabel(country.stage)}</strong>
            {country.direction ? (
              <span className="obs-muted"> · {country.direction}</span>
            ) : null}
          </dd>
        </div>
        <div data-fade>
          <dt>Domestic condition (0–100)</dt>
          <dd>
            <strong>
              {country.domestic_condition_score !== null
                ? country.domestic_condition_score.toFixed(1)
                : "—"}
            </strong>
            {country.domestic_condition_rank ? (
              <span className="obs-muted">
                {" "}
                · rank {country.domestic_condition_rank}/8
              </span>
            ) : null}
          </dd>
        </div>
        <div data-fade>
          <dt>Momentum</dt>
          <dd>
            {country.momentum !== null ? country.momentum.toFixed(2) : "—"}
            {country.momentum !== null && (
              <span aria-hidden="true"> {country.momentum > 0 ? "▲" : "▼"}</span>
            )}
          </dd>
        </div>
        <div data-fade>
          <dt>Forces scored</dt>
          <dd>
            {country.force_summary.scored_count} numerical ·{" "}
            {country.force_summary.dimension_only_count} dimension-only ·{" "}
            {country.force_summary.context_only_count} context
          </dd>
        </div>
        {econ?.value_usd != null && (
          <div data-fade>
            <dt>Economic size ({econ.period})</dt>
            <dd>
              {fmtUsd(econ.value_usd)}
              <span className="obs-muted">
                {" "}
                · {econ.tracked_share_pct?.toFixed(1) ?? "—"}% of tracked output
              </span>
            </dd>
          </div>
        )}
        {military?.expenditure_usd != null && (
          <div data-fade>
            <dt>Military expenditure</dt>
            <dd>
              {fmtUsd(military.expenditure_usd)}
              <span className="obs-muted">
                {" "}
                · {military.pct_gdp?.toFixed(1) ?? "—"}% GDP
              </span>
            </dd>
          </div>
        )}
      </dl>
      <div className="obs-di-grid" data-fade>
        <div className="obs-di-card domestic">
          <h3>Domestic condition</h3>
          <dl>
            <div><dt>Productivity</dt><dd>{formatMeasureValue(snap("LABOUR_PRODUCTIVITY_PER_HOUR"), "score")}</dd></div>
            <div><dt>Innovation</dt><dd>{formatMeasureValue(snap("RND_EXPENDITURE_GDP"), "% of GDP")}</dd></div>
            <div><dt>Education</dt><dd>{formatMeasureValue(snap("TERTIARY_ATTAINMENT_25_34"), "% of adults")}</dd></div>
          </dl>
          <p>Internal capacity: cohesion, human capital, institutions and productivity.</p>
        </div>
        <div className="obs-di-card international">
          <h3>International power</h3>
          <dl>
            <div><dt>Output</dt><dd>{formatMeasureValue(econ?.value_usd ?? null, "usd_current")}</dd></div>
            <div><dt>Trade share</dt><dd>{formatMeasureValue(trade?.tracked_share_pct ?? null, "% of tracked trade")}</dd></div>
            <div><dt>Finance / reserve</dt><dd>{monetary?.currency_code ?? "—"} · {formatMeasureValue(monetary?.gov_10y_yield ?? null, "% 10Y")}</dd></div>
          </dl>
          <p>{monetary?.reserve_anchor_role ?? "External scale: output, trade reach, capital markets and military resources."}</p>
        </div>
      </div>
      {snaps.length > 0 && (
        <table className="obs-snaps" data-fade>
          <caption className="obs-muted">Latest measurements</caption>
          <tbody>
            {snaps.map(([code, s]) => (
              <tr key={code}>
                <td>{code.replaceAll("_", " ").toLowerCase()}</td>
                <td>
                  {s.latest!.value >= 1e9
                    ? fmtUsd(s.latest.value)
                    : s.latest!.value.toLocaleString("en-CH", {
                        maximumFractionDigits: 1,
                      })}
                </td>
                <td className="obs-muted">{s.latest!.period}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="obs-note" data-fade>{powerNote}</p>
      <p className="obs-links" data-fade>
        <a href={`/country/${country.iso3}`}>Country profile →</a>
        <a href={`/country/${country.iso3}/forces`}>17-force profile →</a>
      </p>
    </section>
  );
}

/* ---------- PowerTransitionMonitor (right column) ---------- */

export function PowerTransitionMonitor({ data }: { data: TransitionMonitor }) {
  const fr = data.forecast_readiness;
  const top = data.measurements;
  return (
    <section className="obs-panel glass obs-monitor" aria-label="Power transition monitor">
      <h2 className="obs-panel-title">Power transition monitor</h2>
      <div className="obs-monitor-pair">
        <div>
          <span className="obs-muted">Incumbent under study</span>
          <strong>
            {data.incumbent_name} <span className="obs-chip">{data.incumbent_iso3}</span>
          </strong>
          <span className="obs-sub">
            {stageLabel(data.incumbent_stage)}
            {data.incumbent_direction ? ` · ${data.incumbent_direction}` : ""}
          </span>
        </div>
        <div>
          <span className="obs-muted">Challenger under study</span>
          <strong>
            {data.challenger_name} <span className="obs-chip">{data.challenger_iso3}</span>
          </strong>
          <span className="obs-sub">
            {stageLabel(data.challenger_stage)}
            {data.challenger_direction ? ` · ${data.challenger_direction}` : ""}
          </span>
        </div>
      </div>
      <div className="obs-measure-list">
        {top.map((m) => {
          const iv = m.incumbent_value;
          const cv = m.challenger_value;
          const both = iv !== null && cv !== null;
          const max = both ? Math.max(Math.abs(iv!), Math.abs(cv!), 1e-9) : 1;
          const rel = m.relationship ?? "insufficient_data";
          return (
            <div key={m.key} className="obs-mrow" data-rel={rel}>
              <div className="obs-mrow-head">
                <span className="obs-mrow-label">{m.label}</span>
                <span className="obs-mrow-period obs-muted">
                  {m.period ?? ""}
                  {m.source ? ` · ${m.source}` : ""}
                </span>
              </div>
              {both && (
                <div className="obs-mbars" role="img" aria-label={`${m.label}: ${data.incumbent_iso3} ${fmtMeasure(iv!, m.unit)}, ${data.challenger_iso3} ${fmtMeasure(cv!, m.unit)}`}>
                  <div className="obs-mbar">
                    <span
                      className="obs-mbar-fill inc"
                      style={{ width: `${(Math.abs(iv!) / max) * 100}%` }}
                    />
                    <span className="obs-mbar-val">
                      {data.incumbent_iso3} {fmtMeasure(iv!, m.unit)}
                    </span>
                  </div>
                  <div className="obs-mbar">
                    <span
                      className="obs-mbar-fill chal"
                      style={{ width: `${(Math.abs(cv!) / max) * 100}%` }}
                    />
                    <span className="obs-mbar-val">
                      {data.challenger_iso3} {fmtMeasure(cv!, m.unit)}
                    </span>
                  </div>
                </div>
              )}
              <div className="obs-mrow-foot">
                {m.challenger_to_incumbent_ratio !== null && (
                  <span className="obs-muted">
                    challenger at {(m.challenger_to_incumbent_ratio * 100).toFixed(0)}% of incumbent
                  </span>
                )}
                {rel !== "insufficient_data" && rel !== "stable" && m.trend_note ? (
                  <span className={`obs-trend ${rel}`}>
                    {rel === "convergence" ? "narrowing" : "widening"} — {m.trend_note}
                  </span>
                ) : rel === "stable" ? (
                  <span className="obs-trend stable">stable over recent history</span>
                ) : (
                  <span className="obs-trend unknown">direction unknown</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      <p className="obs-note">
        Relative size and direction are descriptive measurements — higher debt,
        trade intensity or spending is not inherently positive or negative.
      </p>
      {(data.historical_evidence.incumbent_transitions?.length ?? 0) > 0 && (
        <p className="obs-muted">
          Historical record: {data.incumbent_iso3} saw{" "}
          {data.historical_evidence.incumbent_transitions!.length} stage
          transitions since 1950, {data.challenger_iso3} saw{" "}
          {data.historical_evidence.challenger_transitions?.length ?? 0}.
        </p>
      )}
      <div className="obs-window">
        <span className="obs-muted">Transition window status</span>
        <strong className={fr.overall_available ? "" : "obs-window-none"}>
          {fr.estimated_transition_window}
        </strong>
      </div>
      <div className="obs-horizons">
        {fr.horizons.map((h) => (
          <span
            key={h.horizon}
            className={
              h.available ? "obs-horizon available" : "obs-horizon"
            }
            title={h.status_label}
          >
            {h.horizon_label}: {h.available ? "supported" : "gated"}
          </span>
        ))}
      </div>
      <p className="obs-note">
        Forecast readiness is evidence-gated — the monitor reports what the
        historical record supports. No countdown is implied.
      </p>
    </section>
  );
}

/* ---------- DataFreshnessIndicator ---------- */

export function DataFreshnessIndicator({
  freshness,
  job,
  onRefresh,
  demo = false,
}: {
  freshness: ObservatoryFreshness;
  job: RefreshJob | null;
  onRefresh: () => void;
  demo?: boolean;
}) {
  return (
    <section
      className="obs-panel glass obs-fresh"
      aria-label="Data freshness"
      data-status={freshness.status}
    >
      <div className="obs-fresh-head">
        <h2 className="obs-panel-title">Data freshness{demo ? " · simulated" : ""}</h2>
        <span className={`obs-status s-${freshness.status}`}>
          {freshness.status_label}
        </span>
      </div>
      <dl className="obs-facts cols2">
        <div>
          <dt>Collection</dt>
          <dd>{freshness.latest_collection_zurich ?? "—"}</dd>
        </div>
        <div>
          <dt>Calculation</dt>
          <dd>{freshness.latest_calculation_zurich ?? "—"}</dd>
        </div>
        <div>
          <dt>Last attempted update</dt>
          <dd>{freshness.latest_update_attempt_zurich ?? "—"}</dd>
        </div>
        <div>
          <dt>Last successful update</dt>
          <dd>{freshness.latest_successful_update_zurich ?? "—"}</dd>
        </div>
        <div>
          <dt>Observation period</dt>
          <dd>{freshness.latest_observation_period ?? "—"}</dd>
        </div>
        <div>
          <dt>New / revised</dt>
          <dd>
            {freshness.new_observations_count} new ·{" "}
            {freshness.revisions_count} revisions ·{" "}
            {freshness.changed_classifications_count} classifications
          </dd>
        </div>
      </dl>
      {freshness.provider_failures.length > 0 && (
        <p className="obs-warn">
          Provider issues:{" "}
          {freshness.provider_failures
            .map((f) => `${f.provider_name} (${f.latest_status})`)
            .join(", ")}
        </p>
      )}
      <div className="obs-fresh-actions">
        <button
          type="button"
          className="glass-button"
          onClick={onRefresh}
          disabled={job?.status === "running" || job?.running}
        >
          {job?.status === "running" || job?.running
            ? "Refreshing…"
            : demo
              ? "Run simulated refresh"
              : "Refresh production data"}
        </button>
        <span className="obs-muted">{demo ? "Offline fixture · no backend workflow" : "Production collection workflow"}</span>
      </div>
      {job?.status === "running" && (
        <p className="obs-muted" role="status">
          {job.current_provider
            ? `Collecting ${job.current_provider} (${job.completed_steps}/${job.total_steps})…`
            : "Refresh in progress…"}
        </p>
      )}
      {job?.error && <p className="obs-warn" role="alert">{job.error}</p>}
    </section>
  );
}

/* ---------- DailyChangesPanel ---------- */

export function DailyChangesPanel({ data, demo = false }: { data: DailyChanges; demo?: boolean }) {
  // Compact one-line state when nothing changed — no large empty card.
  if (data.changes.length === 0)
    return (
      <section className="obs-panel glass obs-changes-compact" aria-label="What has changed">
        <h2 className="obs-panel-title">What changed in the {demo ? "simulated " : ""}snapshot?</h2>
        <p className="obs-muted">
          {data.summary_message}
          {data.previous_snapshot_zurich
            ? ` · compared with ${data.previous_snapshot_zurich}`
            : ""}
        </p>
      </section>
    );
  return (
    <section className="obs-panel glass" aria-label="What has changed">
      <h2 className="obs-panel-title">What changed in the {demo ? "simulated " : ""}snapshot?</h2>
      {data.changes.length === 0 ? (
        <p className="obs-muted">{data.summary_message}</p>
      ) : (
        <table className="obs-changes">
          <thead>
            <tr>
              <th>Country</th>
              <th>Measurement</th>
              <th className="num">Was</th>
              <th className="num">Now</th>
              <th className="num">Δ</th>
              <th>Period</th>
            </tr>
          </thead>
          <tbody>
            {data.changes.slice(0, 12).map((c, i) => (
              <tr key={i}>
                <td>{c.iso3 ?? "—"}</td>
                <td>{c.measurement}</td>
                <td className="num">{fmt(c.previous)}</td>
                <td className="num">{fmt(c.current)}</td>
                <td className="num">{c.difference != null ? fmt(c.difference) : "—"}</td>
                <td className="obs-muted">{c.period ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {data.previous_snapshot_zurich && (
        <p className="obs-muted">
          Compared with previous snapshot · {data.previous_snapshot_zurich}
        </p>
      )}
    </section>
  );
}

const fmt = (v: number | string | null | undefined) => {
  if (v == null) return "—";
  if (typeof v === "string") return v;
  if (Math.abs(v) >= 1e9) return fmtUsd(v);
  if (Math.abs(v) < 10) return v.toFixed(1);
  return v.toLocaleString("en-CH", { maximumFractionDigits: 1 });
};

/* ---------- HistoricalPlayback ---------- */

export function HistoricalPlayback({
  periods,
  index,
  onIndex,
  latestIndex,
  compact = false,
}: {
  periods: string[];
  index: number;
  onIndex: (i: number | null) => void;
  latestIndex: number;
  /** Controls-only rendering for the unified glass control bar. */
  compact?: boolean;
}) {
  const [playing, setPlaying] = useState(false);
  const [speedMs, setSpeedMs] = useState(700);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!playing) {
      if (timer.current) clearInterval(timer.current);
      return;
    }
    timer.current = setInterval(() => {
      onIndexStep();
    }, speedMs);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playing, speedMs, index]);

  const onIndexStep = () => {
    if (index >= latestIndex) {
      setPlaying(false);
      return;
    }
    onIndex(index + 1);
  };

  const controls = (
    <>
        <button
          type="button"
          className="glass-button"
          onClick={() => {
            setPlaying(false);
            onIndex(Math.max(0, index - 1));
          }}
          disabled={index <= 0}
          aria-label="Previous period"
        >
          ◂
        </button>
        <button
          type="button"
          className="glass-button"
          onClick={() => {
            if (!playing && index >= latestIndex) onIndex(0);
            setPlaying((v) => !v);
          }}
          aria-label={playing ? "Pause playback" : "Play historical classification"}
        >
          {playing ? "Pause" : "Play"}
        </button>
        <button
          type="button"
          className="glass-button"
          onClick={() => {
            setPlaying(false);
            onIndex(Math.min(latestIndex, index + 1));
          }}
          disabled={index >= latestIndex}
          aria-label="Next period"
        >
          ▸
        </button>
        <input
          type="range"
          min={0}
          max={latestIndex}
          value={index}
          onChange={(e) => {
            setPlaying(false);
            onIndex(Number(e.target.value));
          }}
          aria-label="Historical period"
          className="obs-slider"
        />
        <select
          value={speedMs}
          onChange={(e) => setSpeedMs(Number(e.target.value))}
          className="glass-button"
          aria-label="Playback speed"
        >
          <option value={1200}>0.5×</option>
          <option value={700}>1×</option>
          <option value={350}>2×</option>
        </select>
        <button
          type="button"
          className="glass-button"
          onClick={() => {
            setPlaying(false);
            onIndex(null);
          }}
          disabled={index === latestIndex}
        >
          Latest
        </button>
    </>
  );

  if (compact) return controls;

  return (
    <div className="obs-playback" role="group" aria-label="Historical playback">
      <div className="obs-playback-row">{controls}</div>
      <p className="obs-playback-period" role="status">
        Observation period: <strong>{periods[index] ?? "—"}</strong>
        {index === latestIndex
          ? " (latest available)"
          : " — historical classifications, not interpolated"}
      </p>
    </div>
  );
}
