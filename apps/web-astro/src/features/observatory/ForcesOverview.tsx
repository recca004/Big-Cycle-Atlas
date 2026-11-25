/** Seventeen-forces overview for the homepage — offline demonstration
 *  force rows with explicit scored / dimension / context semantics. */

import { useMemo } from "react";
import { buildOfflineForceScores } from "./offlineData";

const STATUS_LABELS: Record<string, string> = {
  scored: "level",
  dimension_only: "dimension",
  context: "context",
  deferred: "unavailable",
};

export function ForcesOverview({ iso3 }: { iso3: string | null }) {
  const data = useMemo(() => (iso3 ? buildOfflineForceScores(iso3) : null), [iso3]);
  if (!iso3 || !data) return null;

  return (
    <div className="force-grid" role="list" aria-label={`${iso3} — 17 forces, offline demonstration`}>
      {data.forces.map((force, index) => {
        const status = force.execution_status;
        const numeric = force.level_score ?? force.relative_score;
        return (
          <a
            key={force.force_code}
            role="listitem"
            className="force-row"
            href={`/forces?force=${force.force_code}&country=${iso3}`}
          >
            <span className="force-num">{String(index + 1).padStart(2, "0")}</span>
            <span className="force-name">{force.force_name}</span>
            {numeric !== null && (
              <span className="force-meter" aria-hidden="true">
                <span style={{ width: `${Math.max(3, Math.min(100, numeric))}%` }} />
              </span>
            )}
            <span className="force-value">
              {numeric !== null ? (
                <>
                  <strong>{numeric.toFixed(0)}</strong>
                  {force.momentum_score !== null && (
                    <span className={force.momentum_score >= 0 ? "force-mom up" : "force-mom down"}>
                      {force.momentum_score >= 0 ? "+" : ""}{force.momentum_score.toFixed(0)}
                    </span>
                  )}
                </>
              ) : (
                "—"
              )}
            </span>
            <span className={`force-status s-${status}`}>{STATUS_LABELS[status] ?? status}</span>
          </a>
        );
      })}
      <p className="obs-note" style={{ gridColumn: "1 / -1" }}>
        Offline demonstration force surface — {data.forces.filter((force) => force.execution_status === "scored").length} synthetic levels,
        dimension-only and context profiles shown as such. No composite average is computed.{" "}
        <a href={`/forces?country=${iso3}`}>Full force research →</a>
      </p>
    </div>
  );
}
