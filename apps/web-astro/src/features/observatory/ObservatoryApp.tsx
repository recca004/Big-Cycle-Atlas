/** ObservatoryApp — root island for the animated observatory homepage.
 *  Fetches /api/observatory/overview once and shares the payload across
 *  the three-column layout: focus panel | clock | transition monitor,
 *  then the below-the-fold research sections. */

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchObservatoryOverview,
  fetchObservatoryRefreshStatus,
  postObservatoryRefresh,
} from "@/lib/api/client";
import type {
  ObservatoryOverview,
  RefreshJob,
} from "@/types/observatory";
import { ObservatoryClock } from "./ObservatoryClock";
import {
  CountryFocusPanel,
  DailyChangesPanel,
  DataFreshnessIndicator,
  HistoricalPlayback,
  PowerTransitionMonitor,
} from "./panels";
import { stageLabel } from "./stages";

const MODEL = "model_b_domain";

export function ObservatoryApp() {
  const [data, setData] = useState<ObservatoryOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedIso3, setSelectedIso3] = useState<string | null>(null);
  const [histIndex, setHistIndex] = useState<number | null>(null);
  const [job, setJob] = useState<RefreshJob | null>(null);

  useEffect(() => {
    let alive = true;
    fetchObservatoryOverview()
      .then((d) => {
        if (!alive) return;
        setData(d);
        setJob(d.refresh_job);
        // Default focus: highest domestic-condition power under study.
        const top =
          d.countries.find(
            (c) => c.iso3 === d.power_summary.highest_domestic_condition_iso3,
          ) ?? d.countries.find((c) => c.classified) ?? null;
        if (top) setSelectedIso3(top.iso3);
      })
      .catch((e) => {
        if (alive)
          setError(e instanceof Error ? e.message : "Observatory unavailable");
      });
    return () => {
      alive = false;
    };
  }, []);

  const triggerRefresh = useCallback(async () => {
    setJob((j) => (j ? { ...j, status: "running", running: true } : j));
    try {
      const accepted = await postObservatoryRefresh();
      setJob(accepted);
      // Poll status until the job settles, then reload the overview.
      const poll = async () => {
        const st = await fetchObservatoryRefreshStatus();
        setJob(st);
        if (st.status === "running" || st.running) {
          setTimeout(poll, 3000);
        } else if (st.status === "succeeded") {
          const d = await fetchObservatoryOverview();
          setData(d);
        }
      };
      setTimeout(poll, 3000);
    } catch (e) {
      setJob((j) =>
        j
          ? {
              ...j,
              status: "failed",
              running: false,
              error:
                e instanceof Error
                  ? e.message
                  : "Refresh could not be started",
            }
          : j,
      );
    }
  }, []);

  const periods = data?.available_periods ?? [];
  const latestIndex = Math.max(0, periods.length - 1);
  const activeIndex = histIndex ?? latestIndex;
  const playbackPeriod =
    histIndex !== null && histIndex < latestIndex
      ? (periods[histIndex] ?? null)
      : null;

  const selected = useMemo(
    () => data?.countries.find((c) => c.iso3 === selectedIso3) ?? null,
    [data, selectedIso3],
  );

  if (error)
    return (
      <p className="body-md" role="alert">
        Observatory unavailable: {error}
      </p>
    );
  if (!data)
    return (
      <div className="clock-loading" aria-busy="true">
        <div className="clock-skeleton" />
        <p className="obs-muted">Assembling the observatory…</p>
      </div>
    );

  const incumbent = data.countries.find(
    (c) => c.iso3 === data.transition_monitor.incumbent_iso3,
  );

  return (
    <div className="obs-app">
      <div className="obs-grid">
        <div className="obs-col-left">
          <CountryFocusPanel
            country={selected ?? incumbent ?? null}
            powerNote={data.power_summary.separation_note}
          />
          <div className="obs-country-picker">
            <label htmlFor="obs-country-select" className="obs-muted">
              Focus country
            </label>
            <select
              id="obs-country-select"
              className="glass-button"
              value={selectedIso3 ?? ""}
              onChange={(e) => setSelectedIso3(e.target.value)}
            >
              {data.countries.map((c) => (
                <option key={c.iso3} value={c.iso3}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="obs-col-center">
          <ObservatoryClock
            countries={data.countries}
            selectedIso3={selectedIso3}
            onSelect={setSelectedIso3}
            playbackPeriod={playbackPeriod}
          />
          <HistoricalPlayback
            periods={periods}
            index={activeIndex}
            latestIndex={latestIndex}
            onIndex={(i) => setHistIndex(i)}
          />
        </div>

        <div className="obs-col-right">
          <PowerTransitionMonitor data={data.transition_monitor} />
          <DataFreshnessIndicator
            freshness={data.freshness}
            job={job}
            onRefresh={triggerRefresh}
          />
        </div>
      </div>

      <div className="obs-below">
        <section className="obs-panel glass" aria-label="All tracked powers">
          <h2 className="obs-panel-title">Eight powers under study</h2>
          <table className="obs-powers">
            <thead>
              <tr>
                <th>Power</th>
                <th>Experimental stage</th>
                <th className="num">Condition</th>
                <th className="num">Momentum</th>
                <th>Period</th>
              </tr>
            </thead>
            <tbody>
              {data.countries.map((c) => (
                <tr
                  key={c.iso3}
                  className={c.iso3 === selectedIso3 ? "selected" : undefined}
                  onClick={() => setSelectedIso3(c.iso3)}
                >
                  <td>
                    <strong>{c.name}</strong>{" "}
                    <span className="obs-chip">{c.iso3}</span>
                  </td>
                  <td>{stageLabel(c.stage)}</td>
                  <td className="num">
                    {c.domestic_condition_score !== null
                      ? c.domestic_condition_score.toFixed(1)
                      : "—"}
                  </td>
                  <td className="num">
                    {c.momentum !== null ? c.momentum.toFixed(2) : "—"}
                  </td>
                  <td className="obs-muted">{c.period ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="obs-note">
            Condition is the experimental domestic composite — it measures
            internal governance, productivity and cohesion, not international
            dominance. Largest economy:{" "}
            <strong>{data.power_summary.largest_economy_iso3}</strong>, second:{" "}
            <strong>{data.power_summary.second_economy_iso3}</strong>.
          </p>
        </section>

        <DailyChangesPanel data={data.daily_changes} />

        <section className="obs-panel glass" aria-label="Research surface">
          <h2 className="obs-panel-title">The seventeen forces</h2>
          <p className="body-sm">
            {data.countries[0]?.force_summary.scored_count ?? "—"} forces carry
            published numerical levels, alongside dimension-only and context
            profiles. The forces are the primary research surface of the
            observatory.
          </p>
          <p className="obs-links">
            <a href="/forces">Study the 17 forces →</a>
            <a href="/compare">Compare powers →</a>
            <a href="/cycle">Cycle explorer →</a>
            <a href="/methodology">Methodology →</a>
          </p>
        </section>
      </div>
    </div>
  );
}

export { MODEL };
