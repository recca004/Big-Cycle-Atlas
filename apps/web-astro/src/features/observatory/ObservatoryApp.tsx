import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { fetchFoundationEvaluations, fetchValidationSummary } from "@/lib/api/client";
import { AddToWorkspace } from "@/features/workspace/AddToWorkspace";
import type {
  CurrencyEvidence,
  ObservatoryModelComparison,
  ObservatoryOverview,
  RefreshJob,
  TransitionMonitor,
} from "@/types/observatory";
import type {
  FoundationEvaluationsResponse,
  ValidationSummaryResponse,
} from "@/types/validation";
import { CoverageMatrix } from "./CoverageMatrix";
import type { DialModelGhost } from "./CycleDial";
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
  CompactTransitionMonitor,
  CountryFocusPanel,
  DailyChangesPanel,
  DataFreshnessIndicator,
  HistoricalPlayback,
  PowerStudyCard,
  PowerTransitionMonitor,
} from "./panels";
import { stageLabel } from "./stages";

interface Props {
  mode?: ObservatoryMode;
}

export const MODEL_LABELS: Record<string, { name: string; short: string; summary: string }> = {
  model_a_equal: {
    name: "Equal-weight",
    short: "Equal",
    summary: "Equal weight per available compatible force",
  },
  model_b_domain: {
    name: "Domain-balanced",
    short: "Domain",
    summary: "Equal weight per populated force domain",
  },
  model_c_overlap: {
    name: "Overlap-adjusted",
    short: "Overlap",
    summary: "Declared conceptual-overlap groups share one unit weight",
  },
  model_d_comparable: {
    name: "Fixed comparable subset",
    short: "Comparable",
    summary: "Strict subset of forces populated across all eight powers",
  },
  offline_observatory_demo: {
    name: "Demonstration fixture",
    short: "Demo",
    summary: "Synthetic offline interface fixture",
  },
};

export function humanModelName(modelId: string): string {
  return MODEL_LABELS[modelId]?.name ?? modelId;
}

const HISTORY_RANGES = [
  { key: "standard", label: "1980+", startYear: 1980, description: "Default research range (1980–latest)" },
  { key: "extended", label: "1970+", startYear: 1970, description: "Extended post-Bretton-Woods range" },
  { key: "all", label: "All data", startYear: 1960, description: "Earliest mapped raw observations" },
] as const;

const HISTORICAL_EVENTS = [
  { year: 1971, label: "End of US dollar–gold convertibility", source: "US Federal Reserve historical record" },
  { year: 1973, label: "First oil price shock", source: "IEA/OPEC historical record" },
  { year: 1979, label: "Second oil price shock", source: "IEA/OPEC historical record" },
  { year: 1989, label: "Fall of the Berlin Wall", source: "European historical record" },
  { year: 1990, label: "German reunification (statistical break)", source: "German federal historical record" },
  { year: 1991, label: "Dissolution of the Soviet Union", source: "United Nations historical record" },
  { year: 1999, label: "Euro launch (DEM/FRF → EUR break)", source: "European Central Bank record" },
  { year: 2001, label: "China joins the WTO", source: "World Trade Organization" },
  { year: 2008, label: "Global financial crisis", source: "Financial Stability Board record" },
  { year: 2010, label: "European sovereign debt crisis", source: "European Central Bank record" },
  { year: 2020, label: "COVID-19 pandemic", source: "World Health Organization" },
  { year: 2022, label: "Global inflation & monetary tightening", source: "IMF/BIS policy records" },
] as const;

const RESEARCH_TABS = [
  { id: "power", label: "International power" },
  { id: "forces", label: "17 Forces" },
  { id: "models", label: "Big Cycle models" },
  { id: "validation", label: "Theory validation" },
  { id: "history", label: "Historical research" },
  { id: "changes", label: "Daily changes" },
  { id: "coverage", label: "Data coverage" },
] as const;

type ResearchTabId = (typeof RESEARCH_TABS)[number]["id"];

const CANONICAL_COUNTRY_ORDER = ["USA", "CHN", "IND", "JPN", "DEU", "GBR", "FRA", "CHE"];

function buildTimelinePeriods(rangeStart: number, classifiedPeriods: string[]): string[] {
  if (!classifiedPeriods.length) return [String(rangeStart)];
  const firstClassifiedYear = Number(classifiedPeriods[0]!.slice(0, 4));
  const earlyYears: string[] = [];
  if (Number.isFinite(firstClassifiedYear) && rangeStart < firstClassifiedYear) {
    for (let yr = rangeStart; yr < firstClassifiedYear; yr += 1) {
      earlyYears.push(String(yr));
    }
  }
  return [...earlyYears, ...classifiedPeriods];
}

function CurrencyReserveTable({ evidence }: { evidence: CurrencyEvidence }) {
  return (
    <div className="obs-currency-section">
      <div className="obs-section-subhead">
        <h3>International reserve & currency usage (currency-area entities)</h3>
        <p className="obs-muted">
          Currency influence is measured on currencies and currency areas — never assigned as a full national share to
          individual Eurozone members, and never zero-imputed where a currency is unreported.
        </p>
      </div>
      <div className="obs-table-wrap">
        <table className="obs-powers obs-currency-table">
          <thead>
            <tr>
              <th scope="col">Currency</th>
              <th scope="col">Entity scope</th>
              <th scope="col" className="num">IMF COFER reserve share</th>
              <th scope="col">COFER period</th>
              <th scope="col" className="num">BIS FX turnover (200% sum)</th>
              <th scope="col">FX survey</th>
              <th scope="col" className="num">BIS cross-border bank claims</th>
              <th scope="col">Methodological note</th>
            </tr>
          </thead>
          <tbody>
            {evidence.currencies.map((row) => (
              <tr key={row.currency_code}>
                <td><strong>{row.currency_code}</strong></td>
                <td className="obs-muted">{row.entity_type.replaceAll("_", " ")}</td>
                <td className="num">
                  {row.cofer_reserve_share_pct != null ? `${row.cofer_reserve_share_pct.toFixed(2)}%` : "Not separately reported"}
                </td>
                <td className="obs-muted">{row.cofer_period ?? "—"}</td>
                <td className="num">
                  {row.fx_turnover_share_200pct != null ? `${row.fx_turnover_share_200pct.toFixed(2)}%` : "—"}
                </td>
                <td className="obs-muted">{row.fx_turnover_period ?? "—"}</td>
                <td className="num">
                  {row.lbs_claims_share_pct != null ? `${row.lbs_claims_share_pct.toFixed(2)}%` : "Not separately disclosed"}
                </td>
                <td className="obs-muted">{row.note ?? "Direct currency measurement"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <details className="obs-breaks-disclosure">
        <summary>Recorded IMF COFER & BIS currency methodology breaks ({evidence.methodology_breaks.length})</summary>
        <ul className="obs-breaks-list">
          {evidence.methodology_breaks.map((b) => (
            <li key={b.break_code}>
              <strong>{b.period}:</strong> {b.description}
            </li>
          ))}
        </ul>
      </details>
    </div>
  );
}

function TheoryValidationOverviewTab({ demo }: { demo: boolean }) {
  const [summary, setSummary] = useState<ValidationSummaryResponse | null>(null);
  const [evals, setEvals] = useState<FoundationEvaluationsResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (demo) return;
    const ctrl = new AbortController();
    Promise.all([
      fetchValidationSummary({ signal: ctrl.signal }),
      fetchFoundationEvaluations({ signal: ctrl.signal }),
    ])
      .then(([s, e]) => {
        setSummary(s);
        setEvals(e);
      })
      .catch((error: unknown) => {
        if (!ctrl.signal.aborted) {
          setErr(error instanceof Error ? error.message : "Validation summary unavailable");
        }
      });
    return () => ctrl.abort();
  }, [demo]);

  if (demo) {
    return (
      <div className="obs-validation-tab">
        <p className="obs-muted">
          Demonstration fixture active: live scientific-validation registry requests are disabled so demo mode stays
          strictly isolated from backend endpoints.
        </p>
        <p className="obs-links">
          <a href="/research/validation">Open Theory Validation registry →</a>
        </p>
      </div>
    );
  }

  if (err) {
    return <p className="obs-warn">{err}</p>;
  }
  if (!summary) {
    return <p className="obs-muted">Loading 50-question scientific validation summary…</p>;
  }

  const impl = summary.by_implementation_status;
  const val = summary.by_research_validation_status;
  const untestable = val.currently_untestable ?? 0;
  const exploratory = val.exploratory_findings ?? 0;
  const contradictory = val.evidence_inconsistent_with_registered_claim ?? 0;
  const untested = val.untested ?? 0;
  const insufficient = val.insufficient_evidence ?? 0;
  const methodsCount =
    (impl.research_method_implemented ?? 0) + (impl.evaluation_implemented ?? 0);
  const latestEval = evals?.evaluations?.at(-1);

  return (
    <div className="obs-validation-tab">
      <p className="obs-section-copy">
        Implementation coverage and scientific validation status are tracked on separate axes across all{" "}
        <strong>{summary.count}</strong> canonical questions (<code>{summary.registry_version}</code>). Data or code
        coverage is never combined with scientific proof into a single completion percentage.
      </p>

      <div className="obs-val-kpi-grid">
        <div className="obs-val-card">
          <span className="obs-muted">Registered questions</span>
          <strong className="obs-val-num">{summary.count}</strong>
          <span className="obs-sub">5 theory categories (Q01–Q50)</span>
        </div>
        <div className="obs-val-card">
          <span className="obs-muted">Currently untestable</span>
          <strong className="obs-val-num warn">{untestable}</strong>
          <span className="obs-sub">Missing independent outcome registries</span>
        </div>
        <div className="obs-val-card">
          <span className="obs-muted">Exploratory findings</span>
          <strong className="obs-val-num info">{exploratory}</strong>
          <span className="obs-sub">Q08 falsification & protocol framework</span>
        </div>
        <div className="obs-val-card">
          <span className="obs-muted">Contradictory findings</span>
          <strong className="obs-val-num bad">{contradictory}</strong>
          <span className="obs-sub">Q11, Q14, Q17 preserved negative H01 tests</span>
        </div>
        <div className="obs-val-card">
          <span className="obs-muted">Available research methods</span>
          <strong className="obs-val-num">{methodsCount}</strong>
          <span className="obs-sub">
            {impl.evaluation_implemented ?? 0} evaluated · {impl.research_method_implemented ?? 0} method-ready
          </span>
        </div>
      </div>

      <div className="obs-val-dual">
        <div className="obs-val-axis">
          <h3>Implementation coverage (engineering & data)</h3>
          <dl className="obs-facts">
            <div><dt>Data available</dt><dd><strong>{impl.data_available ?? 0}</strong> questions</dd></div>
            <div><dt>Partially implemented</dt><dd><strong>{impl.partially_implemented ?? 0}</strong> questions</dd></div>
            <div><dt>Research method implemented</dt><dd><strong>{impl.research_method_implemented ?? 0}</strong> questions</dd></div>
            <div><dt>Evaluation implemented</dt><dd><strong>{impl.evaluation_implemented ?? 0}</strong> questions</dd></div>
            <div><dt>Not implemented</dt><dd><strong>{impl.not_implemented ?? 0}</strong> questions</dd></div>
          </dl>
        </div>

        <div className="obs-val-axis">
          <h3>Scientific validation status (empirical findings)</h3>
          <dl className="obs-facts">
            <div><dt>Currently untestable</dt><dd><strong>{untestable}</strong> questions</dd></div>
            <div><dt>Untested (data or method present)</dt><dd><strong>{untested}</strong> questions</dd></div>
            <div><dt>Insufficient evidence</dt><dd><strong>{insufficient}</strong> questions</dd></div>
            <div><dt>Exploratory findings</dt><dd><strong>{exploratory}</strong> question (Q08)</dd></div>
            <div><dt>Evidence inconsistent with claim</dt><dd><strong>{contradictory}</strong> questions (Q11, Q14, Q17)</dd></div>
            <div><dt>Evidence supporting a registered claim</dt><dd><strong>{val.evidence_supporting_registered_claim ?? 0}</strong> questions</dd></div>
          </dl>
        </div>
      </div>

      {latestEval && (
        <div className="obs-val-eval-banner">
          <strong>Latest held-out protocol evaluation:</strong>{" "}
          <code>{String(latestEval.evaluation_key)}</code> →{" "}
          <span className="badge badge-warn">
            {String(latestEval.result_state).replaceAll("_", " ")}
          </span>
        </div>
      )}

      <div className="obs-tab-footer">
        <div className="obs-links">
          <a href="/research/validation" className="glass-button">
            Explore all 50 validation questions →
          </a>
          <a href="/research/validation?question=Q11">Inspect Q11 contradictory benchmark →</a>
          <a href="/research/validation?question=Q08">Inspect Q08 exploratory framework →</a>
        </div>
        <div className="obs-ws-actions">
          <AddToWorkspace typeId="validation-coverage" label="Add coverage widget" />
          <AddToWorkspace typeId="validation-questions" label="Add questions widget" />
        </div>
      </div>
    </div>
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
  const [selectedIso3, setSelectedIso3] = useState<string | null>("USA");
  const [histIndex, setHistIndex] = useState<number | null>(null);
  const [job, setJob] = useState<RefreshJob | null>(null);
  const [incumbent, setIncumbent] = useState("USA");
  const [challenger, setChallenger] = useState("CHN");
  const [monitor, setMonitor] = useState<TransitionMonitor | null>(null);
  const [monitorError, setMonitorError] = useState<string | null>(null);
  const [rangeStart, setRangeStart] = useState<number>(1980);
  const [selectedModel, setSelectedModel] = useState("model_b_domain");
  const [showAllModels, setShowAllModels] = useState(false);
  const [modelComparison, setModelComparison] = useState<ObservatoryModelComparison | null>(null);
  const [activeTab, setActiveTab] = useState<ResearchTabId>("power");
  const [incumbentOpen, setIncumbentOpen] = useState(true);
  const [challengerOpen, setChallengerOpen] = useState(true);
  const refreshTimer = useRef<number | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const tabsSectionRef = useRef<HTMLElement>(null);
  const detailedMonitorRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth <= 900) {
      setIncumbentOpen(false);
      setChallengerOpen(false);
    }
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
        setSelectedIso3((prev) => prev ?? overview.power_summary.largest_economy_iso3 ?? "USA");
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
          setData((current) =>
            current
              ? {
                  ...current,
                  freshness: scenario.freshness,
                  daily_changes: scenario.dailyChanges,
                  refresh_job: scenario.job,
                }
              : current,
          );
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

  const orderedCountries = [...data.countries].sort((a, b) => {
    const ai = CANONICAL_COUNTRY_ORDER.indexOf(a.iso3);
    const bi = CANONICAL_COUNTRY_ORDER.indexOf(b.iso3);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  const timelinePeriods = buildTimelinePeriods(rangeStart, data.available_periods);
  const latestIndex = Math.max(0, timelinePeriods.length - 1);
  const activeIndex = histIndex ?? latestIndex;
  const playbackPeriod =
    histIndex !== null && histIndex < latestIndex ? (timelinePeriods[histIndex] ?? null) : null;

  const selected = data.countries.find((c) => c.iso3 === selectedIso3) ?? orderedCountries[0] ?? null;
  const incumbentCountry = data.countries.find((c) => c.iso3 === incumbent) ?? orderedCountries[0] ?? null;
  const challengerCountry = data.countries.find((c) => c.iso3 === challenger) ?? orderedCountries[1] ?? null;
  const firstClassifiedPeriod = data.available_periods[0] ?? "1995-Q4";
  const latestPeriod = data.available_periods.at(-1) ?? data.scoring_period ?? "latest";
  const playbackYear = playbackPeriod ? Number(playbackPeriod.slice(0, 4)) : null;
  const classifiedAtPlayback =
    !playbackPeriod ||
    data.countries.some((c) => c.history.find((pt) => pt.period === playbackPeriod)?.stage);
  const activeEventYear = playbackYear
    ? HISTORICAL_EVENTS.filter((event) => event.year <= playbackYear).at(-1)?.year
    : null;

  const allModelGhosts: DialModelGhost[] = (() => {
    if (!modelComparison || !selectedIso3) return [];
    const row = modelComparison.countries.find((c) => c.iso3 === selectedIso3);
    if (!row) return [];
    return modelComparison.models
      .map((m) => {
        const marker = row.models[m.model_id];
        if (!marker?.stage) return null;
        return {
          modelId: m.model_id,
          modelLabel: MODEL_LABELS[m.model_id]?.short ?? m.model_id,
          stage: marker.stage,
          score: marker.score,
        };
      })
      .filter((x): x is DialModelGhost => x !== null);
  })();

  const disagreementByIso = new Map<string, string>();
  if (modelComparison) {
    for (const c of modelComparison.countries) {
      const stages = new Set(
        modelComparison.models.map((m) => c.models[m.model_id]?.stage).filter(Boolean),
      );
      disagreementByIso.set(c.iso3, stages.size > 1 ? `${stages.size} stages` : "Agreement");
    }
  }

  const inspectCountryDetails = (iso3: string) => {
    setSelectedIso3(iso3);
    setActiveTab("forces");
    tabsSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  const openDetailedComparison = () => {
    setActiveTab("power");
    requestAnimationFrame(() => {
      (detailedMonitorRef.current ?? tabsSectionRef.current)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    });
  };

  const handleTabKeyDown = (e: React.KeyboardEvent, idx: number) => {
    let nextIdx: number | null = null;
    if (e.key === "ArrowRight") nextIdx = (idx + 1) % RESEARCH_TABS.length;
    else if (e.key === "ArrowLeft") nextIdx = (idx - 1 + RESEARCH_TABS.length) % RESEARCH_TABS.length;
    else if (e.key === "Home") nextIdx = 0;
    else if (e.key === "End") nextIdx = RESEARCH_TABS.length - 1;
    if (nextIdx !== null) {
      e.preventDefault();
      const target = RESEARCH_TABS[nextIdx]!;
      setActiveTab(target.id);
      document.getElementById(`obs-tab-${target.id}`)?.focus();
    }
  };

  return (
    <div className="obs-app" ref={rootRef} data-hydrated="true" data-source={demo ? "demo" : "production"}>
      {demo && (
        <p className="obs-demo-banner" role="note">
          Demonstration fixture — synthetic observations for interface review only. No backend measurement, forecast or
          production result.
        </p>
      )}

      {/* Row 1: Balanced 3-column first-screen Observatory instrument */}
      <div className="obs-grid" aria-label="Big Cycle observatory instrument">
        <div className="obs-col-left">
          <details
            className="obs-mobile-disclosure"
            open={incumbentOpen}
            onToggle={(e) => setIncumbentOpen((e.currentTarget as HTMLDetailsElement).open)}
          >
            <summary className="obs-mobile-summary">
              <span>Incumbent: <strong>{incumbentCountry?.name ?? incumbent}</strong> ({incumbent})</span>
              <span className="obs-muted">{incumbentCountry?.stage ? stageLabel(incumbentCountry.stage) : "Unclassified"}</span>
            </summary>
            <PowerStudyCard
              role="Incumbent"
              selectId="obs-incumbent-select"
              country={incumbentCountry}
              countries={orderedCountries}
              disabledIso3={challenger}
              playbackPeriod={playbackPeriod}
              isFocused={selectedIso3 === incumbent}
              demo={demo}
              onChangeCountry={(iso3) => {
                setIncumbent(iso3);
                setSelectedIso3(iso3);
              }}
              onInspectDetails={inspectCountryDetails}
            />
          </details>

          <section className="obs-panel glass obs-model-card" aria-label="Experimental model configuration">
            <div className="obs-model-card-row">
              <label className="obs-model-picker">
                <span className="obs-picker-kicker">Composite specification</span>
                <select
                  className="glass-button"
                  value={selectedModel}
                  onChange={(event) => setSelectedModel(event.target.value)}
                  aria-label="Select experimental domestic-condition model"
                >
                  {data.model.available_models.map((model) => (
                    <option key={model.model_id} value={model.model_id}>
                      {humanModelName(model.model_id)}
                    </option>
                  ))}
                </select>
              </label>
              <label className="obs-focus-picker" htmlFor="obs-country-select">
                <span className="obs-picker-kicker">Research focus</span>
                <select
                  id="obs-country-select"
                  className="glass-button"
                  value={selectedIso3 ?? ""}
                  onChange={(event) => setSelectedIso3(event.target.value)}
                >
                  {orderedCountries.map((c) => (
                    <option key={c.iso3} value={c.iso3}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
            <p className="obs-muted obs-model-card-note">
              <strong>{humanModelName(selectedModel)}</strong> (<code>{selectedModel}</code>) ·{" "}
              {MODEL_LABELS[selectedModel]?.summary ?? data.model.model_id}. Domestic condition (0–100) is always
              separated from international power shares.
            </p>
          </section>
        </div>

        <div className="obs-col-center">
          {!classifiedAtPlayback && playbackPeriod && (
            <p className="obs-unclassified-note" role="status">
              <strong>{playbackPeriod}:</strong> Raw economic observations exist for this year, while experimental cycle
              classifications begin at <strong>{firstClassifiedPeriod}</strong>. Snapshot figures on side cards remain
              labelled with their actual observation period.
            </p>
          )}
          <ObservatoryClock
            countries={orderedCountries}
            selectedIso3={selectedIso3}
            onSelect={setSelectedIso3}
            playbackPeriod={playbackPeriod}
            periodLabel={
              playbackPeriod
                ? `${playbackPeriod} — historical${classifiedAtPlayback ? "" : " (unclassified)"}`
                : `${latestPeriod} · latest classified`
            }
            allModelGhosts={allModelGhosts}
            showAllModels={showAllModels && !demo}
            onToggleAllModels={!demo && allModelGhosts.length > 0 ? () => setShowAllModels((v) => !v) : undefined}
          />
        </div>

        <div className="obs-col-right">
          <details
            className="obs-mobile-disclosure"
            open={challengerOpen}
            onToggle={(e) => setChallengerOpen((e.currentTarget as HTMLDetailsElement).open)}
          >
            <summary className="obs-mobile-summary">
              <span>Challenger: <strong>{challengerCountry?.name ?? challenger}</strong> ({challenger})</span>
              <span className="obs-muted">{challengerCountry?.stage ? stageLabel(challengerCountry.stage) : "Unclassified"}</span>
            </summary>
            <PowerStudyCard
              role="Challenger"
              selectId="obs-challenger-select"
              country={challengerCountry}
              countries={orderedCountries}
              disabledIso3={incumbent}
              playbackPeriod={playbackPeriod}
              isFocused={selectedIso3 === challenger}
              demo={demo}
              onChangeCountry={(iso3) => {
                setChallenger(iso3);
                setSelectedIso3(iso3);
              }}
              onInspectDetails={inspectCountryDetails}
            />
          </details>

          {monitor ? (
            <CompactTransitionMonitor data={monitor} onOpenComparison={openDetailedComparison} />
          ) : (
            <section className="obs-panel glass obs-monitor obs-monitor-compact" role="status">
              <h2 className="obs-panel-title">Power transition monitor</h2>
              <p className="obs-muted">{monitorError ?? "Loading production transition comparison…"}</p>
            </section>
          )}
        </div>
      </div>

      {/* Row 2: Unified full-width historical playback bar */}
      <section className="obs-panel glass obs-unified-playback" aria-label="Historical playback and horizon">
        <div className="obs-playback-top">
          <div className="obs-range-buttons" role="group" aria-label="Choose the earliest requested history year">
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

          <div className="obs-playback-controls-inline" role="group" aria-label="Historical playback controls">
            <HistoricalPlayback
              periods={timelinePeriods}
              index={activeIndex}
              latestIndex={latestIndex}
              onIndex={(index) => setHistIndex(index)}
              compact
            />
          </div>

          <span className="obs-playback-readout" role="status">
            Active period:{" "}
            <strong>
              {playbackPeriod
                ? `${playbackPeriod}${classifiedAtPlayback ? " (classified)" : " (pre-classification raw era)"}`
                : `${latestPeriod} (latest)`}
            </strong>
          </span>
        </div>

        <div className="obs-event-rail" aria-label="Sourced historical context">
          {HISTORICAL_EVENTS.filter((event) => event.year >= rangeStart).map((event) => (
            <button
              key={event.year}
              type="button"
              className={event.year === activeEventYear ? "obs-event active" : "obs-event"}
              title={`${event.year}: ${event.label}. Source: ${event.source}. Click to inspect nearest period.`}
              onClick={() => {
                const targetIdx = timelinePeriods.findIndex((p) => Number(p.slice(0, 4)) >= event.year);
                if (targetIdx >= 0) setHistIndex(targetIdx);
              }}
            >
              <strong>{event.year}</strong> {event.label}
            </button>
          ))}
        </div>
      </section>

      {/* Row 3: Compact eight-country research strip (no dominance ranking) */}
      <section className="obs-country-strip-wrap" aria-label="Tracked countries research selector">
        <div className="obs-country-strip" role="group" aria-label="Select a country for focused research">
          {orderedCountries.map((country) => {
            const histPt = playbackPeriod
              ? country.history.find((pt) => pt.period === playbackPeriod)
              : null;
            const stage = playbackPeriod ? (histPt?.stage ?? null) : country.stage;
            const disagreement = disagreementByIso.get(country.iso3) ?? "Single view";
            const isSelected = country.iso3 === selectedIso3;
            return (
              <button
                key={country.iso3}
                type="button"
                className={isSelected ? "obs-strip-item selected" : "obs-strip-item"}
                aria-pressed={isSelected}
                onClick={() => setSelectedIso3(country.iso3)}
              >
                <div className="obs-strip-top">
                  <strong>{country.name}</strong>
                  <span className="obs-chip">{country.iso3}</span>
                </div>
                <div className="obs-strip-stage">
                  {stage ? stageLabel(stage) : "Unclassified"}
                </div>
                <div className="obs-strip-meta">
                  <span className={disagreement === "Agreement" ? "obs-disagree ok" : "obs-disagree warn"}>
                    {demo ? "Demo model" : disagreement}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      </section>

      {/* Row 4: Tabbed Research Workspace (replaces long vertical stack without deleting information) */}
      <section className="obs-tabs-shell glass" ref={tabsSectionRef} aria-label="Observatory research modules">
        <div className="obs-tablist" role="tablist" aria-label="Research categories">
          {RESEARCH_TABS.map((tab, idx) => {
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                id={`obs-tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={active}
                aria-controls={`obs-tabpanel-${tab.id}`}
                tabIndex={active ? 0 : -1}
                className={active ? "obs-tab active" : "obs-tab"}
                onClick={() => setActiveTab(tab.id)}
                onKeyDown={(e) => handleTabKeyDown(e, idx)}
              >
                {tab.label}
              </button>
            );
          })}
        </div>

        {activeTab === "power" && (
          <div id="obs-tabpanel-power" role="tabpanel" aria-labelledby="obs-tab-power" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="measures-heading">International power & incumbent–challenger evidence</h2>
                <p className="obs-section-copy">
                  Global output, trade, military expenditure, innovation, banking intermediation and reserve-currency
                  shares — reported with explicit observation years and without manufacturing a single composite power
                  score.
                </p>
              </div>
              <div className="obs-ws-actions">
                <AddToWorkspace typeId="country-ranking" label="Add ranking to Workspace" />
                <a href="/compare" className="glass-button">Compare powers →</a>
                <a href="/trade" className="glass-button">Trade & flows →</a>
              </div>
            </div>

            <div ref={detailedMonitorRef} id="transition-comparison-detail" className="obs-tab-block">
              <details className="obs-mobile-detail-block" open={incumbentOpen || activeTab === "power"}>
                <summary className="obs-mobile-summary">
                  Detailed incumbent–challenger measure bars ({monitor?.measurements.length ?? 0})
                </summary>
                {monitor ? (
                  <PowerTransitionMonitor data={monitor} />
                ) : (
                  <p className="obs-muted">{monitorError ?? "Loading detailed comparison…"}</p>
                )}
              </details>
            </div>

            {data.currency_evidence && !demo && (
              <div className="obs-tab-block">
                <CurrencyReserveTable evidence={data.currency_evidence} />
              </div>
            )}

            <div className="obs-tab-block">
              <h3>Sixteen separated international-power & capacity measurements</h3>
              <PowerMeasuresMatrix countries={orderedCountries} selectedIso3={selectedIso3} demo={demo} />
            </div>
          </div>
        )}

        {activeTab === "forces" && (
          <div id="obs-tabpanel-forces" role="tabpanel" aria-labelledby="obs-tab-forces" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="forces-heading">
                  The seventeen Atlas forces{selected ? ` — ${selected.name} (${selected.iso3})` : ""}
                </h2>
                <p className="obs-section-copy">
                  {demo
                    ? "Synthetic force profiles preserve status distinctions."
                    : "Approved numerical levels, dimension-only signals and context profiles preserve evidence ceilings."}
                </p>
              </div>
              <div className="obs-ws-actions">
                {selected && (
                  <AddToWorkspace
                    typeId="all-forces"
                    config={{ country: selected.iso3 }}
                    label="Add 17 forces to Workspace"
                  />
                )}
                <a href="/forces" className="glass-button">Forces explorer →</a>
                {selected && (
                  <a href={`/country/${selected.iso3}/forces`} className="glass-button">
                    {selected.iso3} force detail →
                  </a>
                )}
              </div>
            </div>

            <div className="obs-forces-split">
              <CountryFocusPanel country={selected} powerNote={data.power_summary.separation_note} />
              <div className="obs-forces-matrix-col">
                <ForcesOverview country={selected} demo={demo} />
              </div>
            </div>
          </div>
        )}

        {activeTab === "models" && (
          <div id="obs-tabpanel-models" role="tabpanel" aria-labelledby="obs-tab-models" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="model-comparison-heading">
                  Experimental domestic-condition models — {modelComparison?.active_period ?? latestPeriod}
                </h2>
                <p className="obs-section-copy">
                  Four weighting rules over shared underlying observations. Stage disagreements measure model
                  specification sensitivity, not a probability of correctness; equivalent models are not independent
                  empirical evidence.
                </p>
              </div>
              <div className="obs-ws-actions">
                <AddToWorkspace
                  typeId="cycle-history"
                  config={{ country: selectedIso3 ?? "USA", model: selectedModel }}
                  label="Add cycle history"
                />
                <AddToWorkspace typeId="big-cycle-clock" config={{ country: selectedIso3 ?? "USA" }} label="Add clock widget" />
                <a href="/cycle" className="glass-button">Cycle explorer →</a>
                <a href="/forecast" className="glass-button">Forecast gates →</a>
                <a href="/methodology" className="glass-button">Methodology →</a>
              </div>
            </div>

            {modelComparison ? (
              <>
                <div className="obs-table-wrap">
                  <table className="obs-powers obs-model-comparison">
                    <thead>
                      <tr>
                        <th scope="col">Power</th>
                        {modelComparison.models.map((model) => (
                          <th key={model.model_id} scope="col">
                            <span>{humanModelName(model.model_id)}</span>
                          </th>
                        ))}
                        <th scope="col">Model sensitivity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {modelComparison.countries.map((country) => {
                        const stages = modelComparison.models
                          .map((model) => country.models[model.model_id]?.stage)
                          .filter(Boolean);
                        const uniqueCount = new Set(stages).size;
                        return (
                          <tr
                            key={country.iso3}
                            className={country.iso3 === selectedIso3 ? "selected" : undefined}
                            onClick={() => setSelectedIso3(country.iso3)}
                          >
                            <td>
                              <strong>{country.name}</strong> <span className="obs-chip">{country.iso3}</span>
                            </td>
                            {modelComparison.models.map((model) => {
                              const marker = country.models[model.model_id];
                              return (
                                <td key={model.model_id}>
                                  {marker?.stage ? stageLabel(marker.stage) : "—"}
                                  <span className="obs-muted obs-model-score">
                                    {marker?.score != null ? ` ${marker.score.toFixed(1)}` : ""}
                                  </span>
                                </td>
                              );
                            })}
                            <td>
                              {uniqueCount > 1 ? `${uniqueCount} stages (specification-sensitive)` : "Stage agreement"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="obs-equivalence-callout">
                  <strong>Mathematical equivalence & shared-input audit:</strong>{" "}
                  <strong>Domain-balanced</strong> and <strong>Overlap-adjusted</strong> are{" "}
                  <strong>materially equivalent</strong> under current populated forces (100% stage and near-exact score
                  agreement across 368 historical country-period comparisons). All four models share the same underlying
                  observation tables (<code>independent_evidence = false</code> across every pair).
                </div>

                <details className="obs-tech-ids-details">
                  <summary>Technical model identifiers & pairwise equivalence diagnostics</summary>
                  <div className="obs-table-wrap">
                    <table className="obs-changes">
                      <thead>
                        <tr>
                          <th>Display name</th>
                          <th>Technical identifier</th>
                          <th>Version</th>
                          <th>Weighting rule</th>
                        </tr>
                      </thead>
                      <tbody>
                        {modelComparison.models.map((m) => (
                          <tr key={m.model_id}>
                            <td><strong>{humanModelName(m.model_id)}</strong></td>
                            <td><code>{m.model_id}</code></td>
                            <td>{m.model_version}</td>
                            <td>{m.notes}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              </>
            ) : (
              <p className="obs-muted">
                {demo ? "Multi-model comparison is disabled in the single-model offline demonstration fixture." : "Loading four-model comparison…"}
              </p>
            )}
          </div>
        )}

        {activeTab === "validation" && (
          <div id="obs-tabpanel-validation" role="tabpanel" aria-labelledby="obs-tab-validation" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="validation-heading">50-question scientific validation roadmap</h2>
              </div>
              <div className="obs-ws-actions">
                <a href="/research/validation" className="glass-button">Full Theory Validation page →</a>
              </div>
            </div>
            <TheoryValidationOverviewTab demo={demo} />
          </div>
        )}

        {activeTab === "history" && (
          <div id="obs-tabpanel-history" role="tabpanel" aria-labelledby="obs-tab-history" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="relative-history-heading">Historical measure & stage comparison ({rangeStart}–{latestPeriod})</h2>
                <p className="obs-section-copy">
                  Continuous calendar axes preserve pre-classification gaps ({rangeStart}–{firstClassifiedPeriod}) and
                  missing provider observations without stretching or interpolation.
                </p>
              </div>
              <div className="obs-ws-actions">
                <AddToWorkspace
                  typeId="indicator-chart"
                  config={{ countries: [incumbent, challenger, "IND"], indicator: "GDP_CURRENT_USD" }}
                  label="Add indicator chart"
                />
                <a href="/research" className="glass-button">Research lab →</a>
              </div>
            </div>

            {!demo && (
              <div className="obs-tab-block">
                <RelativePowerHistory rangeStart={rangeStart} currencyEvidence={data.currency_evidence} />
              </div>
            )}

            <div className="obs-tab-block">
              <h3 id="history-heading">Experimental domestic-stage bands ({rangeStart}–{latestPeriod})</h3>
              <HistoricalCycleComparison
                countries={orderedCountries}
                selectedIso3={selectedIso3}
                onSelect={setSelectedIso3}
                rangeStart={rangeStart}
                demo={demo}
              />
            </div>
          </div>
        )}

        {activeTab === "changes" && (
          <div id="obs-tabpanel-changes" role="tabpanel" aria-labelledby="obs-tab-changes" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="freshness-heading">
                  {demo ? "Freshness and simulated daily change" : "Snapshot freshness and daily changes"}
                </h2>
                <p className="obs-section-copy">
                  Europe/Zurich collection timestamps, provider revisions and classification diffs against the prior
                  saved Observatory snapshot.
                </p>
              </div>
              <div className="obs-ws-actions">
                <AddToWorkspace typeId="ingestion-status" label="Add ingestion status" />
                <a href="/data" className="glass-button">Data explorer →</a>
                <a href="/sources" className="glass-button">Sources →</a>
              </div>
            </div>
            <div className="obs-section-split">
              <DataFreshnessIndicator freshness={data.freshness} job={job} onRefresh={triggerRefresh} demo={demo} />
              <DailyChangesPanel data={data.daily_changes} demo={demo} />
            </div>
          </div>
        )}

        {activeTab === "coverage" && (
          <div id="obs-tabpanel-coverage" role="tabpanel" aria-labelledby="obs-tab-coverage" className="obs-tabpanel">
            <div className="obs-tab-head">
              <div>
                <h2 id="coverage-heading">Verified raw-data coverage inventory</h2>
                <p className="obs-section-copy">
                  Earliest and latest real observations across all tracked countries and providers prior to any
                  normalization or composite aggregation.
                </p>
              </div>
              <div className="obs-ws-actions">
                <AddToWorkspace typeId="coverage-matrix" label="Add coverage matrix" />
                <a href="/progress" className="glass-button">Force progress →</a>
                <a href="/sources" className="glass-button">Provider status →</a>
              </div>
            </div>
            {demo ? (
              <p className="obs-muted">Raw database coverage matrix is disabled in offline demonstration mode.</p>
            ) : (
              <CoverageMatrix />
            )}
          </div>
        )}
      </section>
    </div>
  );
}
