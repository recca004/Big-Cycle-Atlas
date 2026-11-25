/** Seventeen-forces overview for the homepage — live per-country force
 *  rows (level / dimension / context / unavailable), click-through to the
 *  country's force research surface. No unsupported cross-force average. */

import { useEffect, useState } from "react";
import { fetchForceScores } from "@/lib/api/client";
import type { ForceScoresResponse } from "@/types/api";

const STATUS_LABELS: Record<string, string> = {
  scored: "level",
  dimension_only: "dimension",
  context: "context",
  deferred: "unavailable",
};

export function ForcesOverview({ iso3 }: { iso3: string | null }) {
  const [data, setData] = useState<ForceScoresResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!iso3) return;
    let alive = true;
    setData(null);
    fetchForceScores(iso3)
      .then((d) => {
        if (alive) setData(d);
      })
      .catch(() => {
        if (alive) setError(true);
      });
    return () => {
      alive = false;
    };
  }, [iso3]);

  if (!iso3) return null;
  if (error)
    return (
      <p className="obs-muted" role="alert">
        Force scores unavailable for {iso3}.
      </p>
    );
  if (!data) return <div className="clock-skeleton" aria-busy="true" />;

  return (
    <div className="force-grid" role="list" aria-label={`${iso3} — 17 forces`}>
      {data.forces.map((f, i) => {
        const status = f.execution_status;
        const hasLevel = status === "scored" && f.level_score !== null;
        return (
          <a
            key={f.force_code}
            role="listitem"
            className="force-row"
            href={`/forces?force=${f.force_code}&country=${iso3}`}
          >
            <span className="force-num">{String(i + 1).padStart(2, "0")}</span>
            <span className="force-name">{f.force_name}</span>
            <span className="force-value">
              {hasLevel ? (
                <>
                  <strong>{f.level_score!.toFixed(1)}</strong>
                  {f.momentum_score !== null && (
                    <span className="force-mom">
                      {f.momentum_score > 0 ? "▲" : "▼"}
                      {Math.abs(f.momentum_score).toFixed(1)}
                    </span>
                  )}
                </>
              ) : (
                <span className={`force-status s-${status}`}>
                  {STATUS_LABELS[status] ?? status}
                </span>
              )}
            </span>
          </a>
        );
      })}
      <p className="obs-note" style={{ gridColumn: "1 / -1" }}>
        {iso3} force surface — {data.forces.filter((f) => f.execution_status === "scored").length}{" "}
        published levels · dimension-only and context profiles shown as such.
        No composite average of force values is computed.{" "}
        <a href={`/country/${iso3}/forces`}>Full force research →</a>
      </p>
    </div>
  );
}
