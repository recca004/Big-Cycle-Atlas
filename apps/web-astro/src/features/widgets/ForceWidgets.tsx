import { useEffect, useState } from "react";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";
import { fetchForceScores } from "@/lib/api/client";
import type { ForceScoresResponse } from "@/types/api";
import {
  WidgetLoading,
  WidgetError,
  WidgetUnavailable,
} from "./common";
import { useForceCoverage } from "./hooks";
import { formatDate } from "@/lib/format";

function useForceScores(iso3: string | undefined) {
  const [state, setState] = useState<
    | { kind: "loading" }
    | { kind: "unavailable"; status?: number }
    | { kind: "error" }
    | { kind: "ready"; data: ForceScoresResponse }
  >({ kind: "loading" });

  useEffect(() => {
    if (!iso3) return;
    const controller = new AbortController();
    setState({ kind: "loading" });
    fetchForceScores(iso3, { signal: controller.signal })
      .then((data) => {
        if (!controller.signal.aborted) setState({ kind: "ready", data });
      })
      .catch((err: unknown) => {
        if (controller.signal.aborted) return;
        const status =
          err instanceof Error && "status" in err
            ? (err as { status?: number }).status
            : undefined;
        if (status === 404) setState({ kind: "unavailable", status });
        else setState({ kind: "error" });
      });
    return () => controller.abort();
  }, [iso3]);

  return state;
}

const DIM_LABELS: [keyof Pick<
  import("@/types/api").ForceScore,
  "level_score" | "relative_score" | "momentum_score" | "confidence"
>, string][] = [
  ["level_score", "Level"],
  ["relative_score", "Relative"],
  ["momentum_score", "Momentum"],
  ["confidence", "Confidence"],
];

/** Per-force score card — shows only approved, non-null dimensions. */
export function ForceScoreWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const forceCode = (config.force as string) || "rule_of_law";
  const state = useForceScores(iso3);

  if (state.kind === "loading") return <WidgetLoading />;
  if (state.kind === "unavailable") {
    return (
      <WidgetUnavailable
        reason="The force-score API is not deployed on this backend yet."
        methodologyStatus="Scores exist in-engine (5/17 forces) but are not yet exposed via the public API."
      />
    );
  }
  if (state.kind === "error") return <WidgetError />;

  const force = state.data.forces.find((f) => f.force_code === forceCode);
  if (!force) {
    return (
      <WidgetUnavailable
        reason={`Unknown force "${forceCode}".`}
        methodologyStatus="Check the force code in widget settings."
      />
    );
  }
  if (force.execution_status !== "scored") {
    return (
      <WidgetUnavailable
        reason={`"${force.force_name}" has no approved scoring methodology yet.`}
        methodologyStatus={
          force.reasons[0] ?? "DEFERRED — see decision records"
        }
      />
    );
  }
  return (
    <div className="force-score">
      <div className="force-score-dims">
        {DIM_LABELS.map(([key, label]) => (
          <div key={key} className="force-score-dim">
            <p className="label-md text-tertiary">{label}</p>
            <p className="metric-value">
              {force[key] != null ? force[key]!.toFixed(1) : "—"}
            </p>
          </div>
        ))}
      </div>
      <p className="body-sm" style={{ fontSize: "var(--text-xs)", marginTop: "var(--space-3)" }}>
        {force.coverage_status.toUpperCase()} coverage
        {force.period ? ` · ${formatDate(force.period)}` : ""}
        {force.model_version ? ` · ${force.model_version}` : ""}
      </p>
      {force.limitations.length > 0 && (
        <p className="body-sm" style={{ fontSize: "var(--text-xs)", color: "var(--text-tertiary)", marginTop: 4 }}>
          {force.limitations[0]}
        </p>
      )}
    </div>
  );
}

/** All-17 force overview — scores where executable, statuses elsewhere. */
export function AllForcesWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const scores = useForceScores(iso3);
  const coverage = useForceCoverage(iso3);

  if (scores.kind === "loading" || coverage.kind === "loading")
    return <WidgetLoading />;
  if (coverage.kind === "error") return <WidgetError />;

  const scoreByCode = new Map(
    scores.kind === "ready"
      ? scores.data.forces.map((f) => [f.force_code, f])
      : [],
  );

  return (
    <div className="widget-fill widget-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>Force</th>
            <th>Coverage</th>
            <th className="num">Level</th>
            <th className="num">Relative</th>
            <th className="num">Momentum</th>
          </tr>
        </thead>
        <tbody>
          {coverage.data.forces.map((f) => {
            const s = scoreByCode.get(f.code);
            const scored = s?.execution_status === "scored";
            return (
              <tr key={f.code}>
                <td>{f.name}</td>
                <td>
                  <span
                    className={`status-pill status-${
                      f.status === "available"
                        ? "good"
                        : f.status === "partial"
                          ? "warn"
                          : f.status === "missing"
                            ? "bad"
                            : "neutral"
                    }`}
                  >
                    {f.status.replaceAll("_", " ")}
                  </span>
                </td>
                {scored ? (
                  <>
                    <td className="num">{s!.level_score?.toFixed(1) ?? "—"}</td>
                    <td className="num">{s!.relative_score?.toFixed(1) ?? "—"}</td>
                    <td className="num">{s!.momentum_score?.toFixed(1) ?? "—"}</td>
                  </>
                ) : (
                  <td className="num" colSpan={3} style={{ color: "var(--text-tertiary)" }}>
                    {scores.kind === "unavailable" ? "API pending" : "deferred"}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Compact coverage list for a single country (same data as force page). */
export function ForceCoverageWidget({ config }: WidgetProps) {
  const iso3 = (config.country as string) || "USA";
  const state = useForceCoverage(iso3);

  if (state.kind === "loading") return <WidgetLoading />;
  if (state.kind === "error") return <WidgetError />;

  return (
    <div className="widget-fill widget-scroll">
      <table className="data-table">
        <tbody>
          {state.data.forces.map((f) => (
            <tr key={f.code}>
              <td>{f.name}</td>
              <td>
                <span
                  className={`status-pill status-${
                    f.status === "available"
                      ? "good"
                      : f.status === "partial"
                        ? "warn"
                        : f.status === "missing"
                          ? "bad"
                          : "neutral"
                  }`}
                >
                  {f.status.replaceAll("_", " ")}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
