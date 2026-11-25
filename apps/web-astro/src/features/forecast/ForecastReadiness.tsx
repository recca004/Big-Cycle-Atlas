import { useMemo, useState } from "react";
import {
  fetchCompositeModels,
  fetchCountryForecast,
  fetchForecastReadiness,
} from "@/lib/api/client";
import type {
  CountryForecastResponse,
  ForecastReadinessResponse,
  ModelReadiness,
} from "@/types/research";
import { useAsyncState, useCountryList } from "@/features/widgets/hooks";
import { resolveAsync } from "@/features/widgets/common";

const HORIZONS = ["1y", "2y", "5y", "10y"] as const;

function GateTable({ model }: { model: ModelReadiness }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Horizon</th>
            <th>Status</th>
            <th className="num">Eligible origins</th>
            <th className="num">Positive labels</th>
            <th>Failed gates</th>
          </tr>
        </thead>
        <tbody>
          {model.horizons.map((h) => (
            <tr key={h.horizon}>
              <td className="tabular-nums">{h.horizon}</td>
              <td>
                <span className={`badge badge-${h.available ? "ok" : "warn"}`}>
                  {h.available ? "available" : "gated"}
                </span>
              </td>
              <td className="num tabular-nums">{h.eligible_samples}</td>
              <td className="num tabular-nums">{h.positive_transitions}</td>
              <td>
                {h.available
                  ? "—"
                  : h.gates
                      .filter((g) => !g.passed)
                      .map((g) => (
                        <div key={g.gate} className="body-sm">
                          <code>{g.gate}</code>: {String(g.value)} (needs{" "}
                          {g.requirement})
                        </div>
                      ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Mission 5 §13 — forecast readiness surface.
 *
 * Shows the explicit gate evaluation per model and horizon and lets the
 * user probe a country forecast — which today always returns an honest
 * unavailability, never a fabricated probability.
 */
export function ForecastReadiness() {
  const countries = useCountryList();
  const [iso3, setIso3] = useState("USA");
  const [model, setModel] = useState("model_a_equal");
  const [horizon, setHorizon] = useState<string>("1y");

  const readiness = useAsyncState<ForecastReadinessResponse>(
    (s) => fetchForecastReadiness({ signal: s }),
    [],
  );
  const models = useAsyncState(
    (s) => fetchCompositeModels({ signal: s }),
    [],
  );
  const forecast = useAsyncState<CountryForecastResponse>(
    (s) => fetchCountryForecast(iso3, model, horizon, { signal: s }),
    [iso3, model, horizon],
  );

  const modelIds = useMemo(
    () => Object.keys(readiness.kind === "ready" ? readiness.data.models : {}),
    [readiness],
  );

  return (
    <>
      <div className="glass">
        <h2 className="headline-sm panel-title">Readiness evaluation</h2>
        <p className="body-sm">
          Every forecast horizon is gated on data sufficiency: scored
          periods, observable origins, genuine transitions, positive labels
          and strict-eligible evidence. A failed gate returns an{" "}
          <em>unavailable</em> forecast — never a fabricated probability.
        </p>
        {resolveAsync(
          readiness,
          (data) => (
            <>
              <p className="body-sm">
                <span className="badge badge-info">experimental</span>{" "}
                Dataset: <code>{data.dataset.source}</code> generated{" "}
                {data.dataset.generated_at.slice(0, 10)} ·{" "}
                {data.dataset.execution_mode}. {data.dataset.warning}
              </p>
              {modelIds.map((mid) => {
                const m = data.models[mid]!;
                return (
                  <section key={mid}>
                    <h3 className="headline-sm panel-title">
                      {mid}{" "}
                      <span className="label-md text-tertiary">
                        v{m.model_version} · req{" "}
                        {m.requirements_version}
                      </span>
                    </h3>
                    <p className="body-sm">
                      {m.total_scored_periods} scored periods ·{" "}
                      {m.total_genuine_transitions} genuine transitions ·{" "}
                      {m.strict_eligible_periods} strict-eligible
                      observations · blockers:{" "}
                      {m.blockers.length ? m.blockers.join(", ") : "none"}
                    </p>
                    <GateTable model={m} />
                  </section>
                );
              })}
            </>
          ),
          () =>
            modelIds.length === 0
              ? "Readiness report unavailable — run scripts/generate_model_diagnostics.py first."
              : null,
        )}
        {readiness.kind === "error" && null}
      </div>

      <div className="glass">
        <h2 className="headline-sm panel-title">Forecast probe</h2>
        <p className="body-sm">
          The forecast contract returns availability plus evidence counts.
          While gates fail, probability and calibration fields stay{" "}
          <code>null</code> by design.
        </p>
        <div className="research-controls glass-subtle">
          <label>
            Country{" "}
            <select
              className="config-select"
              value={iso3}
              onChange={(e) => setIso3(e.target.value)}
            >
              {countries.map((c) => (
                <option key={c.iso3} value={c.iso3}>
                  {c.iso3} — {c.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Model{" "}
            <select
              className="config-select"
              value={model}
              onChange={(e) => setModel(e.target.value)}
            >
              {(models.kind === "ready"
                ? models.data.map((m) => m.model_id)
                : modelIds.length
                  ? modelIds
                  : [model]
              ).map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label>
            Horizon{" "}
            <select
              className="config-select"
              value={horizon}
              onChange={(e) => setHorizon(e.target.value)}
            >
              {HORIZONS.map((h) => (
                <option key={h}>{h}</option>
              ))}
            </select>
          </label>
        </div>
        {resolveAsync(forecast, (f) => (
          <>
            <p className="body-sm">
              <span className={`badge badge-${f.forecast.available ? "ok" : "warn"}`}>
                {f.forecast.available ? "available" : "unavailable"}
              </span>{" "}
              {f.country} · {f.model_id} v{f.model_version} · {f.horizon}
            </p>
            {!f.forecast.available && (
              <p className="body-sm">
                Reason: {f.forecast.unavailable_reason}
              </p>
            )}
            <p className="body-sm">
              Evidence: {f.evidence.eligible_samples} eligible origins ·{" "}
              {f.evidence.positive_transitions} positive labels · dataset{" "}
              {f.evidence.dataset_generated_at?.slice(0, 10) ?? "missing"}
            </p>
            <p className="body-sm text-tertiary">
              stage_probabilities: {JSON.stringify(f.forecast.stage_probabilities)}{" "}
              · calibration: {JSON.stringify(f.forecast.calibration)}
            </p>
          </>
        ))}
      </div>
    </>
  );
}
