import {
  fetchCycleHistory,
  fetchForceHistory,
  fetchValidationQuestions,
  fetchValidationSummary,
} from "@/lib/api/client";
import type {
  CycleHistoryResponse,
  ForceHistoryResponse,
} from "@/types/research";
import type {
  ValidationQuestionsResponse,
  ValidationSummaryResponse,
} from "@/types/validation";
import { EChart } from "@/lib/charts/EChart";
import { cycleHistoryOption } from "@/lib/charts/cycleChart";
import { forceHistoryOption } from "@/lib/charts/forceChart";
import { useFetch } from "@/lib/ui/shared";
import { WidgetError, WidgetLoading } from "./common";
import type { WidgetProps } from "@/features/workspace/widgetRegistry";

/** Experimental Big Cycle history — retains experimental status when added
 *  to any workspace (Mission 3 §10/§23). */
export function CycleHistoryWidget({ config }: WidgetProps) {
  const iso3 = String(config.country ?? "USA");
  const model = String(config.model ?? "model_b_domain");
  const startYear = Number(config.startYear ?? 2000);
  const h = useFetch<CycleHistoryResponse>(
    (c) => fetchCycleHistory(iso3, model, startYear, { signal: c.signal }),
    [iso3, model, startYear],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  return (
    <div style={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <span className="badge badge-warn" style={{ alignSelf: "flex-start" }}>
        EXPERIMENTAL
      </span>
      <div style={{ flex: 1, minHeight: 0 }}>
        <EChart option={cycleHistoryOption(h.data)}
                ariaLabel={`Experimental cycle history ${iso3}`} />
      </div>
    </div>
  );
}

/** Historical force dimensions — level / relative / momentum, missing
 *  values never connected across gaps. */
export function ForceHistoryWidget({ config }: WidgetProps) {
  const iso3 = String(config.country ?? "USA");
  const force = String(config.force ?? "rule_of_law");
  const startYear = Number(config.startYear ?? 1996);
  const h = useFetch<ForceHistoryResponse>(
    (c) => fetchForceHistory(iso3, force, startYear, { signal: c.signal }),
    [iso3, force, startYear],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  return (
    <EChart option={forceHistoryOption(h.data)}
            ariaLabel={`Force history ${force} ${iso3}`} />
  );
}

/** 50-question registry implementation/scientific status — real registry data. */
export function ValidationCoverageWidget() {
  const h = useFetch<ValidationSummaryResponse>(
    (c) => fetchValidationSummary({ signal: c.signal }), [],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  const top = Object.entries(h.data.by_implementation_status)
    .sort((a, b) => b[1] - a[1]).slice(0, 4);
  return (
    <div className="flex h-full flex-col justify-between gap-3">
      <div>
        <div className="text-3xl font-semibold">{h.data.count}</div>
        <div className="mt-1 text-sm text-[var(--text-secondary)]">canonical validation questions</div>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {top.map(([key, value]) => (
          <span key={key} className="badge badge-info">{value} {key.replaceAll("_", " ")}</span>
        ))}
      </div>
      <a href="/research/validation" className="text-xs text-[var(--accent)]">Open validation registry</a>
    </div>
  );
}

/** Registry-list workspace widget. */
export function ValidationQuestionsWidget({ config }: WidgetProps) {
  const category = String(config.category ?? "all");
  const h = useFetch<ValidationQuestionsResponse>(
    (c) => fetchValidationQuestions({ signal: c.signal }), [],
  );
  if (h.kind === "loading") return <WidgetLoading />;
  if (h.kind === "error") return <WidgetError detail={h.error} />;
  const questions = h.data.questions
    .filter((question) => category === "all" || question.category === category)
    .slice(0, 12);
  return (
    <div className="h-full space-y-2 overflow-y-auto pr-1">
      {questions.map((question) => (
        <a
          key={question.question_code}
          href={`/research/validation?question=${question.question_code}`}
          className="block rounded-lg border border-[var(--border-subtle)] bg-[var(--surface-1)] p-2 hover:bg-[var(--surface-2)]"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="source-badge">{question.question_code}</span>
            <span className="badge badge-warn">{question.research_validation_status.replaceAll("_", " ")}</span>
          </div>
          <div className="mt-1 line-clamp-2 text-sm font-medium">{question.short_title}</div>
        </a>
      ))}
    </div>
  );
}
