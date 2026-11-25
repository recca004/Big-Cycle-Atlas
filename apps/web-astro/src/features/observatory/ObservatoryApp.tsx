import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  ObservatoryModelComparison,
  ObservatoryOverview,
  RefreshJob,
  TransitionMonitor,
} from "@/types/observatory";
import { CoverageMatrix } from "./CoverageMatrix";
import { ForcesOverview } from "./ForcesOverview";
import { HistoricalCycleComparison } from "./HistoricalCycleComparison";
import { ObservatoryClock } from "./ObservatoryClock";
import { PowerMeasuresMatrix } from "./PowerMeasuresMatrix";
import { RelativePowerHistory } from "./RelativePowerHistory";
import {
  createObservatoryService,
  invalidateObservatoryCaches,
  type ObservatoryMode,
} from "./observatoryService";
import {
  CountryFocusPanel,
  DailyChangesPanel,
  DataFreshnessIndicator,
  HistoricalPlayback,
  PowerTransitionMonitor,
} from "./panels";
import { stageLabel } from "./stages";

interface Props {
  mode?: ObservatoryMode;
}

const HISTORY_RANGES = [
  { key: "standard", label: "1980+", startYear: 1980, description: "Primary research range" },
  { key: "extended", label: "1970+", startYear: 1970, description: "Extended post-Bretton-Woods range" },
  { key: "all", label: "All data", startYear: 1960, description: "Earliest mapped raw observations" },
] as const;

const HISTORICAL_EVENTS = [
  { year: 1971, label: "End of US dollar–gold convertibility", source: "US Federal Reserve historical record" },
  { year: 1973, label: "First oil price shock", source: "IEA/OPEC historical record" },
  { year: 1979, label: "Second oil price shock", source: "IEA/OPEC historical record" },
  { year: 1989, label: "Fall of the Berlin Wall", source: "European historical record" },
  { year: 1990, label: "German reunification", source: "German federal historical record" },
  { year: 1991, label: "Dissolution of the Soviet Union", source: "United Nations historical record" },
  { year: 2001, label: "China joins the WTO", source: "World Trade Organization" },
  { year: 2008, label: "Global financial crisis", source: "Financial Stability Board record" },
  { year: 2010, label: "European sovereign debt crisis", source: "European Central Bank record" },
  { year: 2020, label: "COVID-19 pandemic", source: "World Health Organization" },
  { year: 2021, label: "Global inflation and monetary tightening", source: "IMF/BIS policy records" },
] as const;

function SectionHeading({ id, kicker, title, children }: { id: string; kicker: string; title: string; children?: React.ReactNode }) {
  return (
    <header className="obs-section-head">
      <p className="obs-kicker">{kicker}</p>
      <h2 id={id}>{title}</h2>
      {children && <p className="obs-section-copy">{children}</p>}
    </header>
  );
}

export function ObservatoryApp({ mode }: Props) {
  const [resolvedMode] = useState<ObservatoryMode>(() => {
    if (mode) return mode;
    if (typeof window !== "undefined" && new URLSearchParams(window.location.search).has("demo")) return "demo";
    return "production";
  });
  const demo = resolvedMode === "demo";
  const service = useMemo(() => createObservatoryService(resolvedMode), [resolvedMode]);
  const [data, setData] = useState<ObservatoryOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedIso3, setSelectedIso3] = useState<string | null>(null);
  const [histIndex, setHistIndex] = useState<number | null>(null);
  const [job, setJob] = useState<RefreshJob | null>(null);
  const [incumbent, setIncumbent] = useState("USA");
  const [challenger, setChallenger] = useState("CHN");
  const [monitor, setMonitor] = useState<TransitionMonitor | null>(null);
  const [monitorError, setMonitorError] = useState<string | null>(null);
  const [rangeStart, setRangeStart] = useState<number>(1980);
  const [selectedModel, setSelectedModel] = useState("model_b_domain");
  const [modelComparison, setModelComparison] = useState<ObservatoryModelComparison | null>(null);
  const refreshTimer = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    rootRef.current?.setAttribute("data-hydrated", "true");
  }, []);

  useEffect(() => {
    let alive = true;
    setData(null);
    setError(null);
    setHistIndex(null);
    service
      .loadOverview(rangeStart, selectedModel)
      .then((overview) => {
        if (!alive) return;
        setData(overview);
        setSelectedIso3(overview.power_summary.highest_domestic_condition_iso3);
        setMonitor(overview.transition_monitor);
        setJob(overview.refresh_job);
      })
      .catch((err: unknown) => {
        if (!alive) return;
        setError(err instanceof Error ? err.message : "Unable to load observatory data");
      });
    return () => {
      alive = false;
    };
  }, [service, rangeStart, selectedModel]);

  useEffect(() => {
    if (!data) return;
    let alive = true;
    setModelComparison(null);
    service
      .loadModelComparison(rangeStart)
      .then((next) => alive && setModelComparison(next))
      .catch(() => alive && setModelComparison(null));
    return () => {
      alive = false;
    };
  }, [service, rangeStart, data]);

  useEffect(() => {
    if (!data) return;
    if (
      incumbent === data.transition_monitor.incumbent_iso3 &&
      challenger === data.transition_monitor.challenger_iso3
    ) {
      setMonitor(data.transition_monitor);
      setMonitorError(null);
      return;
    }
    let alive = true;
    setMonitor(null);
    setMonitorError(null);
    service
      .loadTransition(incumbent, challenger, rangeStart, selectedModel)
      .then((next) => {
        if (alive) setMonitor(next);
      })
      .catch((err: unknown) => {
        if (alive) setMonitorError(err instanceof Error ? err.message : "Transition comparison unavailable");
      });
    return () => {
      alive = false;
    };
  }, [data, incumbent, challenger, rangeStart, selectedModel, service]);

  useEffect(
    () => () => {
      if (refreshTimer.current !== null) window.clearTimeout(refreshTimer.current);
    },
    [],
  );

  const triggerRefresh = useCallback(() => {
    if (job?.running || job?.status === "running") return;
    if (demo) {
      void service.requestRefresh().then(setJob);
      refreshTimer.current = window.setTimeout(() => {
        void import("./offlineData").then((fixture) => {
          const scenario = fixture.offlineRefreshScenario(1);
          setData((current) => current ? {
            ...current,
            freshness: scenario.freshness,
            daily_changes: scenario.dailyChanges,
            refresh_job: scenario.job,
          } : current);
          setJob(scenario.job);
        });
        refreshTimer.current = null;
      }, 1100);
      return;
    }

    void service
      .requestRefresh()
      .then((accepted) => {
        setJob(accepted);
        const poll = async () => {
          const status = await service.loadRefreshStatus();
          setJob(status);
          if (status.status === "running" || status.running) {
            refreshTimer.current = window.setTimeout(() => void poll(), 3000);
          } else if (status.status === "succeeded") {
            invalidateObservatoryCaches();
            setData(await service.loadOverview(rangeStart, selectedModel));
          }
        };
        void poll();
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Refresh request failed");
      });
  }, [demo, job?.running, job?.status, rangeStart, selectedModel, service]);

  if (error && !data) {
    return (
      <div className="obs-app obs-error" ref={rootRef} role="alert">
        <section className="obs-panel glass">
          <p className="obs-kicker">Observatory unavailable</p>
          <h2>Production atlas data could not be loaded.</h2>
          <p className="obs-muted">
            {error}. No offline demonstration values were substituted for real observations.
          </p>
          <button type="button" className="glass-button" onClick={() => window.location.reload()}>
            Retry connection
          </button>
        </section>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="clock-loading" aria-busy="true" ref={rootRef}>
        <div className="clock-skeleton" />
        <p className="obs-muted">Assembling the production observatory…</p>
      </div>
    );
  }

  const periods = data.available_periods;
  const latestIndex = Math.max(0, periods.length - 1);
  const activeIndex = histIndex ?? latestIndex;
  const playbackPeriod = histIndex !== null && histIndex < latestIndex ? (periods[histIndex] ?? null) : null;
  const selected = data.countries.find((country) => country.iso3 === selectedIso3) ?? null;
  const firstHistoryPeriod = periods[0] ?? "available history";
  const latestPeriod = periods[latestIndex] ?? data.scoring_period ?? "latest";
  const playbackYear = playbackPeriod ? Number(playbackPeriod.slice(0, 4)) : null;
  const classifiedAtPlayback = !playbackPeriod || data.countries.some(
    (country) => country.history.find((point) => point.period === playbackPeriod)?.stage,
  );
  const activeEventYear = playbackYear
    ? HISTORICAL_EVENTS.filter((event) => event.year <= playbackYear).at(-1)?.year
    : null;

  return (
    <div className="obs-app" ref={rootRef} data-source={demo ? "demo" : "production"}>
      {demo && <p className="obs-demo-banner" role="note">Demonstration fixture — synthetic observations for interface review only. No backend measurement, forecast or production result.</p>}

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
          <section className="obs-range-picker obs-panel glass" aria-label="Historical research range">
            <div className="obs-range-copy">
              <span className="obs-picker-kicker">Research horizon</span>
              <strong>{data.scoring_period} latest calculated period</strong>
            </div>
            <div className="obs-range-buttons" role="group" aria-label="Choose the earliest requested cycle period">
              {HISTORY_RANGES.map((range) => (
                <button
                  key={range.key}
                  type="button"
                  className={range.startYear === rangeStart ? "glass-button active" : "glass-button"}
                  title={range.description}
                  onClick={() => setRangeStart(range.startYear)}
                >
                  {range.label}
                </button>
              ))}
            </div>
            <label className="obs-model-picker">
              <span className="obs-picker-kicker">Experimental model</span>
              <select
                className="glass-button"
                value={selectedModel}
                onChange={(event) => setSelectedModel(event.target.value)}
                aria-label="Select experimental domestic-condition model"
              >
                {data.model.available_models.map((model) => (
                  <option key={model.model_id} value={model.model_id}>{model.model_id}</option>
                ))}
              </select>
            </label>
          </section>
          {!classifiedAtPlayback && (
            <p className="obs-unclassified-note" role="status">
              Historical observations available — cycle classification unavailable for this period.
            </p>
          )}
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
            periodLabel={playbackPeriod ? `${playbackPeriod} — historical` : `${latestPeriod} · experimental domestic-condition cycle`}
          />
          <section className="obs-event-rail" aria-label="Sourced historical context">
            {HISTORICAL_EVENTS.filter((event) => event.year >= rangeStart).map((event) => (
              <span
                key={event.year}
                className={event.year === activeEventYear ? "obs-event active" : "obs-event"}
                title={`${event.year}: ${event.label}. Source: ${event.source}.`}
              >
                <strong>{event.year}</strong> {event.label}
              </span>
            ))}
          </section>
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
          {monitor ? (
            <PowerTransitionMonitor data={monitor} />
          ) : (
            <section className="obs-panel glass" role="status">
              <h2 className="obs-panel-title">Power transition monitor</h2>
              <p className="obs-muted">{monitorError ?? "Loading production transition comparison…"}</p>
            </section>
          )}
        </div>
      </div>

      <div className="obs-research-sections">
        <section className="obs-panel obs-section glass" aria-labelledby="freshness-heading">
          <SectionHeading id="freshness-heading" kicker="Snapshot integrity" title={demo ? "Freshness and simulated daily change" : "Freshness and daily change"}>
            {demo ? "Simulated Europe/Zurich collection timestamps and fixture changes." : "Europe/Zurich collection and calculation timestamps, revisions and production snapshot changes."}
          </SectionHeading>
          <div className="obs-section-split">
            <DataFreshnessIndicator freshness={data.freshness} job={job} onRefresh={triggerRefresh} demo={demo} />
            <DailyChangesPanel data={data.daily_changes} demo={demo} />
          </div>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="powers-heading">
          <SectionHeading id="powers-heading" kicker="Tracked powers" title="All eight powers under study">
            Domestic condition, momentum and experimental stage across the complete {demo ? "demonstration" : "production"} set.
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

        {modelComparison && (
          <section className="obs-panel obs-section glass" aria-labelledby="model-comparison-heading">
            <SectionHeading id="model-comparison-heading" kicker="Model evidence" title={`Experimental model comparison — ${modelComparison.active_period ?? "latest"}`}>
              Actual stage markers for each selectable model. Equivalent model pairs are labelled and do not count as independent confirmation.
            </SectionHeading>
            <div className="obs-table-wrap">
              <table className="obs-powers obs-model-comparison">
                <thead>
                  <tr>
                    <th scope="col">Power</th>
                    {modelComparison.models.map((model) => (
                      <th key={model.model_id} scope="col">{model.model_id}</th>
                    ))}
                    <th scope="col">Disagreement</th>
                  </tr>
                </thead>
                <tbody>
                  {modelComparison.countries.map((country) => {
                    const stages = modelComparison.models
                      .map((model) => country.models[model.model_id]?.stage)
                      .filter(Boolean);
                    return (
                      <tr key={country.iso3} className={country.iso3 === selectedIso3 ? "selected" : undefined}>
                        <td><strong>{country.name}</strong> <span className="obs-chip">{country.iso3}</span></td>
                        {modelComparison.models.map((model) => {
                          const marker = country.models[model.model_id];
                          return (
                            <td key={model.model_id}>
                              {marker?.stage ? stageLabel(marker.stage) : "—"}
                              <span className="obs-muted obs-model-score">
                                {marker?.score !== null && marker?.score !== undefined ? ` ${marker.score.toFixed(1)}` : ""}
                              </span>
                            </td>
                          );
                        })}
                        <td>{new Set(stages).size > 1 ? `${new Set(stages).size} stages` : "Agreement"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="obs-note">
              {modelComparison.note}
              {Object.entries(modelComparison.equivalence)
                .filter(([, result]) => result.equivalent_under_current_data)
                .map(([pair]) => ` ${pair.replaceAll("__", " ↔ ")} is materially equivalent under current evidence.`)}
            </p>
          </section>
        )}

        <section className="obs-panel obs-section glass" aria-labelledby="measures-heading">
          <SectionHeading id="measures-heading" kicker="International power" title="Measured international-power evidence">
            Production output, trade, military, monetary, innovation, education, financial-depth and productivity measures — shown only where source observations exist. No composite power ranking is inferred.
          </SectionHeading>
          <div>
            <PowerMeasuresMatrix countries={data.countries} selectedIso3={selectedIso3} demo={demo} />
          </div>
        </section>

        <section className="obs-panel obs-section glass" aria-labelledby="forces-heading">
          <SectionHeading id="forces-heading" kicker="Determinants" title={`The seventeen forces${selected ? ` — ${selected.name}` : ""}`}>
            {demo ? "Synthetic force profiles preserve status distinctions." : "Approved numerical levels, dimension-only signals and context profiles preserve evidence gates."}
          </SectionHeading>
          <div>
            <ForcesOverview country={selected} demo={demo} />
          </div>
          <p className="obs-links">
            <a href="/forces">All forces →</a>
            <a href="/compare">Compare powers →</a>
            <a href="/cycle">Cycle explorer →</a>
            <a href="/methodology">Methodology →</a>
          </p>
        </section>

        {!demo && (
          <section className="obs-panel obs-section glass" aria-labelledby="relative-history-heading">
            <SectionHeading id="relative-history-heading" kicker="Relative power" title="Historical measure comparison">
              Comparable latest-vintage observations across all tracked powers. Units remain separated by the selected measure.
            </SectionHeading>
            <RelativePowerHistory rangeStart={rangeStart} />
          </section>
        )}

        {!demo && (
          <section className="obs-panel obs-section glass" aria-labelledby="coverage-heading">
            <SectionHeading id="coverage-heading" kicker="Evidence inventory" title="Verified raw-data coverage">
              Earliest and latest real observations are reported before force calculations or experimental cycle classifications. Blank cells remain unsupported rather than interpolated.
            </SectionHeading>
            <CoverageMatrix />
          </section>
        )}

        <section className="obs-panel obs-section glass" aria-labelledby="history-heading">
          <SectionHeading id="history-heading" kicker="Long-cycle evidence" title={`Historical cycle comparisons, ${firstHistoryPeriod}–${latestPeriod}`}>
            Exact classified periods from {demo ? "the demonstration fixture" : "the production composite model"}. Bands are descriptive evidence, not a smoothed projection or future path.
          </SectionHeading>
          <div>
            <HistoricalCycleComparison countries={data.countries} selectedIso3={selectedIso3} onSelect={setSelectedIso3} demo={demo} />
          </div>
        </section>
      </div>
    </div>
  );
}
