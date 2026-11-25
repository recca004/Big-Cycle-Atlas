import { useEffect, useMemo, useState } from "react";
import {
  fetchCountryAvailability,
  fetchCountryCycle,
  fetchExecutionModes,
  fetchModelDiagnostics,
  fetchReleaseEvidence,
} from "@/lib/api/client";
import type {
  AvailabilityResponse,
  CompositeResult,
  ExecutionModesResponse,
  ModelDiagnosticsManifest,
  ReleaseEvidenceResponse,
} from "@/types/research";

const MODES = [
  "retrospective_latest_vintage",
  "strict_as_of",
  "research_assumption",
] as const;

function useFetch<T>(fn: (c: AbortController) => Promise<T>, deps: unknown[]) {
  const [state, setState] = useState<
    { kind: "loading" | "ready" | "error"; data?: T; error?: string }
  >({ kind: "loading" });
  useEffect(() => {
    const c = new AbortController();
    setState({ kind: "loading" });
    fn(c)
      .then((data) => setState({ kind: "ready", data }))
      .catch((e) => setState({ kind: "error", error: String(e) }));
    return () => c.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return state;
}

/** Mission 4 §30 — historical validation panel.
 *
 * Shows how information selection actually works: execution mode, info
 * cutoff, stored release evidence, and what strict mode can (and today
 * cannot) produce. Never presents a retrospective curve as a backtest.
 */
export function HistoricalValidation({ iso3, model }: {
  iso3: string;
  model: string;
}) {
  const [mode, setMode] = useState<string>("retrospective_latest_vintage");
  const [cutoff, setCutoff] = useState<string>("2020-12-31");

  const modes = useFetch<ExecutionModesResponse>(fetchExecutionModes, []);
  const evidence = useFetch<ReleaseEvidenceResponse>(fetchReleaseEvidence, []);
  const availability = useFetch<AvailabilityResponse>(
    (c) => fetchCountryAvailability(iso3, { signal: c.signal }),
    [iso3],
  );
  const diagnostics = useFetch<ModelDiagnosticsManifest>(
    fetchModelDiagnostics, [],
  );

  const needsCutoff = mode !== "retrospective_latest_vintage";
  const probe = useFetch<CompositeResult>(
    (c) => fetchCountryCycle(iso3, model, {
      signal: c.signal,
      executionMode: mode,
      ...(needsCutoff ? { infoCutoff: cutoff } : {}),
    }),
    [iso3, model, mode, needsCutoff ? cutoff : null],
  );

  const strictEligible = useMemo(() => {
    if (availability.kind !== "ready" || !availability.data) return null;
    const inds = availability.data.indicators;
    return {
      total: inds.length,
      eligible: inds.filter((i) => i.strict_eligible).length,
      withEvidence: inds.reduce(
        (s, i) => s + i.with_release_evidence, 0,
      ),
      observations: inds.reduce((s, i) => s + i.observation_count, 0),
    };
  }, [availability]);

  const disagreement = diagnostics.data?.model_disagreement?.[iso3];
  const composite = probe.kind === "ready" ? probe.data : undefined;

  return (
    <div className="glass">
      <h2 className="headline-sm panel-title">Historical validation</h2>
      <p className="body-sm">
        Retrospective views use the latest stored vintages — later revisions
        are visible in earlier periods' inputs, so these are{" "}
        <em>not backtests</em>. Strict as-of mode only admits observations
        with provider release evidence published at/before the cutoff.
      </p>

      {/* Execution mode probe */}
      <div className="research-controls glass-subtle">
        <label>
          Execution mode{" "}
          <select className="config-select" value={mode}
                  onChange={(e) => setMode(e.target.value)}>
            {MODES.map((m) => <option key={m}>{m}</option>)}
          </select>
        </label>
        {needsCutoff && (
          <label>
            Information cutoff{" "}
            <input className="config-select" type="date" value={cutoff}
                   onChange={(e) => setCutoff(e.target.value)} />
          </label>
        )}
        {composite && (
          <span className={`badge badge-${composite.backtest_safe ? "ok" : "warn"}`}>
            {composite.execution_mode ?? mode} · backtest_safe=
            {String(composite.backtest_safe)}
          </span>
        )}
      </div>
      {probe.kind === "ready" && composite && (
        <p className="body-sm">
          {mode === "strict_as_of"
            ? composite.composite.score === null
              ? "Strict result: unavailable — no observations carry provider release evidence for this period. Strict mode reports this honestly instead of falling back to latest-vintage data."
              : `Strict result: ${composite.composite.score.toFixed(1)}`
            : `Retrospective result: ${composite.composite.score?.toFixed(1) ?? "unavailable"} — later revisions are visible in this number's inputs.`}
        </p>
      )}
      {probe.kind === "error" && (
        <p className="body-sm">Probe failed: {probe.error}</p>
      )}

      {/* Release-evidence availability */}
      {strictEligible && (
        <p className="body-sm">
          Stored release evidence for {iso3}:{" "}
          <strong>{strictEligible.withEvidence}</strong> of{" "}
          {strictEligible.observations} observations ·{" "}
          {strictEligible.eligible} of {strictEligible.total} indicators
          strict-eligible.
        </p>
      )}

      {/* Provider evidence matrix */}
      {evidence.data && (
        <div className="table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Provider</th><th>Release dates</th><th>Revision dates</th>
                <th>Vintage history</th><th>Assumed lag</th>
              </tr>
            </thead>
            <tbody>
              {evidence.data.providers.map((p) => (
                <tr key={p.source_key}>
                  <td>{p.provider}</td>
                  <td>{p.has_release_dates ? "yes" : "none ingested"}</td>
                  <td>{p.has_revision_dates ? "yes" : "none ingested"}</td>
                  <td>{p.has_vintage_history ? "yes" : "no"}</td>
                  <td>
                    {p.assumed_lag_days != null
                      ? `${p.assumed_lag_days}d (assumption)`
                      : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {evidence.data && (
        <p className="body-sm">{evidence.data.disclaimer}</p>
      )}

      {/* Model disagreement from stored manifest */}
      {disagreement && (
        <p className="body-sm">
          Retrospective model disagreement ({iso3},{" "}
          {diagnostics.data?.period_range.join("–")}): mean score spread{" "}
          {disagreement.mean_spread?.toFixed(1) ?? "—"} · max{" "}
          {disagreement.max_spread?.toFixed(1) ?? "—"} across{" "}
          {disagreement.periods_compared} comparable periods.{" "}
          <em>Retrospective — not a backtest.</em>
        </p>
      )}
      {diagnostics.kind === "error" && (
        <p className="body-sm">
          Model diagnostics manifest unavailable — run{" "}
          <code>scripts/generate_model_diagnostics.py</code>.
        </p>
      )}
      {modes.data && (
        <p className="body-sm">{modes.data.backtest_safe_rule}</p>
      )}
    </div>
  );
}
