import type { ObservatoryCountry, TopForce } from "@/types/observatory";

interface Props {
  country: ObservatoryCountry | null;
  demo?: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  scored: "level",
  dimension_only: "dimension",
  context_only: "context",
  context: "context",
  deferred: "unavailable",
};

function forceValue(force: TopForce): number | null {
  return force.level_score ?? force.relative_score;
}

export function ForcesOverview({ country, demo = false }: Props) {
  const forces = country?.force_summary?.forces ?? [];
  if (!country) {
    return <p className="obs-muted">Select a power to inspect the seventeen forces.</p>;
  }

  return (
    <div className="force-grid" role="list" aria-label={`${country.iso3} — seventeen forces`}>
      {forces.map((force, index) => {
        const numeric = forceValue(force);
        return (
          <a
            key={force.force_code}
            role="listitem"
            className="force-row"
            href={`/forces?force=${force.force_code}&country=${country.iso3}`}
          >
            <span className="force-num">{String(index + 1).padStart(2, "0")}</span>
            <span className="force-name">{force.force_name}</span>
            {numeric !== null && (
              <span className="force-meter" aria-hidden="true">
                <span style={{ width: `${Math.max(3, Math.min(100, Math.abs(numeric)))}%` }} />
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
            <span className={`force-status s-${force.execution_status}`}>
              {STATUS_LABELS[force.execution_status] ?? force.execution_status}
            </span>
          </a>
        );
      })}
      <p className="obs-note" style={{ gridColumn: "1 / -1" }}>
        {demo ? "Demonstration fixture" : "Production evidence"} — {country.force_summary.scored_count} numerical levels, {country.force_summary.dimension_only_count} dimension-only and {country.force_summary.context_only_count} context profiles. Missing evidence remains unavailable, not zero-filled.{" "}
        <a href={`/forces?country=${country.iso3}`}>Full force research →</a>
      </p>
    </div>
  );
}
