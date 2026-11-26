import {
  fetchFoundationEvaluations,
  fetchValidationSummary,
} from "@/lib/api/client";
import { Badge, useFetch } from "@/lib/ui/shared";

function topEntries(record: Record<string, number>, limit = 5) {
  return Object.entries(record).sort((a, b) => b[1] - a[1]).slice(0, limit);
}

export function ResearchEvidenceSummary() {
  if (typeof window !== "undefined" && new URLSearchParams(window.location.search).has("demo")) {
    return (
      <section className="glass rounded-3xl p-5 md:p-6">
        <p className="label-md text-tertiary">Research evidence</p>
        <p className="mt-2 text-sm text-[var(--text-secondary)]">
          Demonstration fixture: validation registry calls are deliberately disabled in demo mode.
        </p>
      </section>
    );
  }
  const summary = useFetch((c) => fetchValidationSummary({ signal: c.signal }), []);
  const evaluations = useFetch((c) => fetchFoundationEvaluations({ signal: c.signal }), []);
  if (summary.kind === "loading" || evaluations.kind === "loading") {
    return <div className="glass-subtle rounded-2xl p-4 text-sm text-[var(--text-secondary)]">Loading research evidence…</div>;
  }
  if (summary.kind === "error" || evaluations.kind === "error") {
    return <div className="glass-subtle rounded-2xl p-4 text-sm text-[var(--status-warn)]">Research evidence unavailable.</div>;
  }
  const latestEvaluation = evaluations.data.evaluations.at(-1);
  return (
    <section className="glass rounded-3xl p-5 md:p-6" aria-labelledby="research-evidence-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="label-md text-tertiary">Research evidence</p>
          <h2 id="research-evidence-title" className="mt-1 text-2xl font-semibold">Scientific validation status</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--text-secondary)]">
            The Observatory clock remains an experimental national-condition model.
            These counts describe research coverage, not the probability that the
            Big Cycle theory is correct and not an international-order countdown.
          </p>
        </div>
        <a className="glass-button" href="/research/validation">Open Theory Validation</a>
      </div>
      <div className="mt-5 grid gap-4 lg:grid-cols-4">
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
          <div className="text-3xl font-semibold">{summary.data.count}</div>
          <div className="mt-1 text-sm text-[var(--text-secondary)]">registered questions</div>
        </div>
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
          <div className="text-sm font-semibold">Implementation</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {topEntries(summary.data.by_implementation_status, 3).map(([key, value]) => (
              <Badge key={key} tone={key === "not_implemented" ? "err" : "info"}>{value} {key.replaceAll("_", " ")}</Badge>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
          <div className="text-sm font-semibold">Scientific status</div>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {topEntries(summary.data.by_research_validation_status, 3).map(([key, value]) => (
              <Badge key={key} tone={key === "evidence_inconsistent_with_registered_claim" ? "err" : "warn"}>{value} {key.replaceAll("_", " ")}</Badge>
            ))}
          </div>
        </div>
        <div className="rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
          <div className="text-sm font-semibold">Latest evaluation</div>
          {latestEvaluation ? (
            <div className="mt-2 text-sm text-[var(--text-secondary)]">
              <div className="font-medium text-[var(--text-primary)]">{String(latestEvaluation.evaluation_key)}</div>
              <div className="mt-1">{String(latestEvaluation.result_state).replaceAll("_", " ")}</div>
            </div>
          ) : <div className="mt-2 text-sm text-[var(--text-tertiary)]">No evaluation registered.</div>}
        </div>
      </div>
      <div className="mt-4 rounded-2xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
        <div className="text-sm font-semibold">Largest missing evidence dependencies</div>
        <div className="mt-2 flex flex-wrap gap-2">
          {topEntries(summary.data.missing_dataset_mentions, 8).map(([key, value]) => (
            <span key={key} className="source-badge">{key} × {value}</span>
          ))}
        </div>
      </div>
    </section>
  );
}
