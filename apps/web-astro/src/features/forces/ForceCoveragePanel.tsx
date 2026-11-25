import { useEffect, useState } from "react";
import { fetchForceCoverage } from "@/lib/api/client";
import type { ForceCoverageData, ForceCoverageStatus } from "@/types/api";
import { formatDate } from "@/lib/format";

const STATUS_META: Record<
  ForceCoverageStatus,
  { cls: string; label: string }
> = {
  available: { cls: "status-good", label: "Available" },
  partial: { cls: "status-warn", label: "Partial" },
  defined_not_sourced: { cls: "status-neutral", label: "Defined — not sourced" },
  missing: { cls: "status-bad", label: "Missing" },
};

export function ForceCoveragePanel({ iso3 }: { iso3: string }) {
  const [data, setData] = useState<ForceCoverageData | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchForceCoverage(iso3, { signal: controller.signal })
      .then(setData)
      .catch(() => setError(true));
    return () => controller.abort();
  }, [iso3]);

  if (error) {
    return (
      <div className="glass-subtle state-box" role="alert">
        <p className="headline-sm">Force coverage is currently unavailable.</p>
      </div>
    );
  }
  if (!data) {
    return <p className="body-sm">Loading force coverage…</p>;
  }

  return (
    <div className="section-stack">
      {data.forces.map((force) => {
        const meta = STATUS_META[force.status] ?? STATUS_META.missing;
        return (
          <div key={force.code} className="glass" style={{ padding: "var(--space-5)" }}>
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                justifyContent: "space-between",
                gap: "var(--space-4)",
                flexWrap: "wrap",
              }}
            >
              <div>
                <p className="headline-sm">{force.name}</p>
                {force.description && (
                  <p className="body-sm" style={{ marginTop: 4, maxWidth: "42rem" }}>
                    {force.description}
                  </p>
                )}
              </div>
              <span className={`status-pill ${meta.cls}`}>{meta.label}</span>
            </div>
            {force.coverage_notes && (
              <p className="section-note">{force.coverage_notes}</p>
            )}
            {force.live_inputs.length > 0 && (
              <div style={{ marginTop: "var(--space-3)" }}>
                <p className="label-md text-tertiary">Live inputs</p>
                <ul className="body-sm" style={{ marginTop: 4 }}>
                  {force.live_inputs.map((inp) => (
                    <li key={inp.indicator_code}>
                      {inp.name ?? inp.indicator_code}
                      {inp.has_data
                        ? ` — data through ${inp.latest_period ? formatDate(inp.latest_period) : "—"}`
                        : " — no data"}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {force.candidate_inputs.length > 0 && (
              <div style={{ marginTop: "var(--space-3)" }}>
                <p className="label-md text-tertiary">Candidate inputs</p>
                <ul className="body-sm" style={{ marginTop: 4 }}>
                  {force.candidate_inputs.map((inp) => (
                    <li key={inp.indicator_code}>
                      {inp.name ?? inp.indicator_code}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
