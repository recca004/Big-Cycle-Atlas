/** ObservatoryApp — root island for the animated offline observatory.
 *  All data comes from the isolated demonstration layer in offlineData.ts:
 *  no backend request, provider claim, forecast, countdown or prediction. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RefreshJob } from "@/types/observatory";
import { ForcesOverview } from "./ForcesOverview";
import { HistoricalCycleComparison } from "./HistoricalCycleComparison";
import { ObservatoryClock } from "./ObservatoryClock";
import { PowerMeasuresMatrix } from "./PowerMeasuresMatrix";
import {
  buildOfflineTransition,
  createOfflineOverview,
  offlineRefreshScenario,
  runningOfflineRefreshJob,
  DEMO_DISCLAIMER,
} from "./offlineData";
import {
  CountryFocusPanel,
  DailyChangesPanel,
  DataFreshnessIndicator,
  HistoricalPlayback,
  PowerTransitionMonitor,
} from "./panels";
import { stageLabel } from "./stages";

const MODEL = "offline_observatory_demo";

function SectionHeading({ id, kicker, title, children }: { id: string; kicker: string; title: string; children?: React.ReactNode }) {
  return (
    <header className="obs-section-head">
      <p className="obs-kicker">{kicker}</p>
      <h2 id={id}>{title}</h2>
      {children && <p className="obs-section-copy">{children}</p>}
    </header>
  );
}

export function ObservatoryApp() {
  const [data, setData] = useState(() => createOfflineOverview());
  const [selectedIso3, setSelectedIso3] = useState<string | null>(
    () => createOfflineOverview().power_summary.highest_domestic_condition_iso3,
  );
  const [histIndex, setHistIndex] = useState<number | null>(null);
  const [job, setJob] = useState<RefreshJob>(() => data.refresh_job);
  const [refreshStep, setRefreshStep] = useState(0);
  const [incumbent, setIncumbent] = useState("USA");
  const [challenger, setChallenger] = useState("CHN");
  const refreshTimer = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    rootRef.current?.setAttribute("data-hydrated", "true");
  }, []);

  const monitor = useMemo(() => buildOfflineTransition(incumbent, challenger), [incumbent, challenger]);

  useEffect(
    () => () => {
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
    },
    [],
  );

  const triggerRefresh = useCallback(() => {
    if (job.running || job.status === "running") return;
    setJob(runningOfflineRefreshJob());
    refreshTimer.current = window.setTimeout(() => {
      const nextStep = refreshStep + 1;
      const scenario = offlineRefreshScenario(nextStep);
      setData((current) => ({
        ...current,
        freshness: scenario.freshness,
        daily_changes: scenario.dailyChanges,
        refresh_job: scenario.job,
      }));
      setJob(scenario.job);
      setRefreshStep(nextStep);
      refreshTimer.current = null;
    }, 1150);
  }, [job.running, job.status, refreshStep]);

  const periods = data.available_periods;
  const latestIndex = Math.max(0, periods.length - 1);
  const activeIndex = histIndex ?? latestIndex;
  const playbackPeriod = histIndex !== null && histIndex < latestIndex ? (periods[histIndex] ?? null) : null;
  const selected = useMemo(
    () => data.countries.find((country) => country.iso3 === selectedIso3) ?? null,
    [data.countries, selectedIso3],
  );

  return (
    <div className="obs-app" ref={rootRef}>
      <p className="obs-demo-banner" role="note">{DEMO_DISCLAIMER}</p>

      <div className="obs-grid" aria-label="Big Cycle observatory instrument">
        <div className="obs-col-left">
          <div className="obs-country-picker obs-panel glass">
            <label htmlFor="obs-country-select">
              <span className="obs-picker-kicker">Country focus</span>
              <select
                id="obs-country-select"
                className="glass-button"
                value={selectedIso3 ?? ""}
                onChange={(event) => setSelectedIso3(event.target.value)}
              >
                {data.countries.map((country) => (
                  <option key={country.iso3} value={country.iso3}>{country.name}</option>
                ))}
              </select>
            </label>
          </div>
          <CountryFocusPanel country={selected} powerNote={data.power_summary.separation_note} />
        </div>

        <div className="obs-col-center">
          <ObservatoryClock
            countries={data.countries}
            selectedIso3={selectedIso3}
            onSelect={setSelectedIso3}
            playbackPeriod={playbackPeriod}
            playbackControls={
              <HistoricalPlayback
                periods={periods}
                index={activeIndex}
                latestIndex={latestIndex}
                onIndex={(index) => setHistIndex(index)}
                compact
              />
            }
            periodLabel={
              playbackPeriod ? `${playbackPeriod} — historical` : `${periods[latestIndex] ?? "—"} (latest demo)`
            }
          />
        </div>

        <div className="obs-col-right">
          <div className="obs-pair-select obs-panel glass" aria-label="Transition study pair">
            <label>
              <span className="obs-picker-kicker">Incumbent</span>
              <select className="glass-button" value={incumbent} onChange={(event) => setIncumbent(event.target.value)}>
                {data.countries.map((country) => (
                  <option key={country.iso3} value={country.iso3} disabled={country.iso3 === challenger}>{country.name}</option>
                ))}
              </select>
            </label>
            <label>
              <span className="obs-picker-kicker">Challenger</span>
              <select className="glass-button" value={challenger} onChange={(event) => setChallenger(event.target.value)}>
                {data.countries.map((country) => (
                  <option key={country.iso3} value={country.iso3} disabled={country.iso3 === incumbent}>{country.name}</option>
                ))}
              </select>
            </label>
          </div>
          <PowerTransitionMonitor data={monitor} />
        </div>
      </div>

      <div className="obs-research-sections">
        <section className="obs-panel obs-section glass" aria-labelledby="freshness-heading">
          <SectionHeading id="freshness-heading" kicker="Snapshot integrity" title="Freshness and simulated daily change">
            Europe/Zurich collection and calculation timestamps, with an explicit offline simulation of what changed since the prior fixture snapshot.
          </SectionHeading>
          <div className="obs-section-split">
            <DataFreshnessIndicator freshness={data.freshness} job={job} onRefresh={triggerRefresh} />
            <DailyChangesPanel data={data.daily_changes} />
          </div>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="powers-heading">
          <SectionHeading id="powers-heading" kicker="Tracked powers" title="All eight powers under study">
            Domestic condition, momentum and experimental stage across the complete offline demonstration set.
          </SectionHeading>
          <div className="obs-table-wrap">
            <table className="obs-powers">
              <thead>
                <tr>
                  <th scope="col">Power</th>
                  <th scope="col">Experimental stage</th>
                  <th scope="col" className="num">Condition</th>
                  <th scope="col" className="num">Momentum</th>
                  <th scope="col">Region</th>
                  <th scope="col">Period</th>
                </tr>
              </thead>
              <tbody>
                {data.countries.map((country) => (
                  <tr key={country.iso3} className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                    <td>
                      <button type="button" className="obs-power-select" onClick={() => setSelectedIso3(country.iso3)}>
                        <strong>{country.name}</strong> <span className="obs-chip">{country.iso3}</span>
                      </button>
                    </td>
                    <td>{stageLabel(country.stage)}</td>
                    <td className="num">{country.domestic_condition_score?.toFixed(1) ?? "—"}</td>
                    <td className="num">{country.momentum?.toFixed(2) ?? "—"}</td>
                    <td>{country.region}</td>
                    <td className="obs-muted">{country.period ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="obs-note">
            {data.power_summary.separation_note} Largest economy: <strong>{data.power_summary.largest_economy_iso3}</strong>, second: <strong>{data.power_summary.second_economy_iso3}</strong>.
          </p>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="measures-heading">
          <SectionHeading id="measures-heading" kicker="Power measures" title="The eight power measures">
            Output, trade, military resources, innovation, education, productivity, financial depth and reserve-currency status — side by side for every tracked power.
          </SectionHeading>
          <div>
            <PowerMeasuresMatrix selectedIso3={selectedIso3} />
          </div>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="forces-heading">
          <SectionHeading id="forces-heading" kicker="Determinants" title={`The seventeen forces${selected ? ` — ${selected.name}` : ""}`}>
            Synthetic force profiles preserve the distinction between numerical levels, dimension-only evidence and context-only factors.
          </SectionHeading>
          <div>
            <ForcesOverview iso3={selectedIso3} />
          </div>
          <p className="obs-links">
            <a href="/forces">All forces →</a>
            <a href="/compare">Compare powers →</a>
            <a href="/cycle">Cycle explorer →</a>
            <a href="/methodology">Methodology →</a>
          </p>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="history-heading">
          <SectionHeading id="history-heading" kicker="Long-cycle evidence" title="Historical cycle comparisons, 1950–2026">
            Exact annual classification bands for the demonstration histories. Bands are descriptive evidence, not a smoothed projection or future path.
          </SectionHeading>
          <div>
            <HistoricalCycleComparison countries={data.countries} selectedIso3={selectedIso3} onSelect={setSelectedIso3} />
          </div>
        </section>
      </div>
    </div>
  );
}

export { MODEL };
