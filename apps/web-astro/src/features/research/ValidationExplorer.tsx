import { useEffect, useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import {
  fetchValidationQuestion,
  fetchValidationQuestions,
  fetchValidationSummary,
} from "@/lib/api/client";
import { EChart, baseChartOption } from "@/lib/charts/EChart";
import { Badge, useFetch } from "@/lib/ui/shared";
import type {
  DatasetRef,
  ValidationQuestionDetail,
  ValidationQuestionSummary,
  ValidationSummaryResponse,
} from "@/types/validation";

const CATEGORY_LABELS: Record<string, string> = {
  core_theory: "Core theory",
  debt_money: "Debt & money",
  internal_conflict: "Internal conflict",
  external_rivalry: "External rivalry",
  technology_shocks: "Technology & shocks",
};

const IMPLEMENTATION_LABELS: Record<string, string> = {
  not_implemented: "Not implemented",
  partially_implemented: "Partially implemented",
  data_available: "Data available",
  research_method_implemented: "Research method implemented",
  evaluation_implemented: "Evaluation implemented",
};

const VALIDATION_LABELS: Record<string, string> = {
  untested: "Untested",
  currently_untestable: "Currently untestable",
  insufficient_evidence: "Insufficient evidence",
  exploratory_findings: "Exploratory findings",
  evaluated_with_no_clear_conclusion: "Evaluated with no clear conclusion",
  evidence_supporting_registered_claim: "Evidence supporting a registered claim",
  evidence_inconsistent_with_registered_claim: "Evidence inconsistent with a registered claim",
  independent_replication_required: "Independent replication required",
};

const CHART_ENTITIES = [
  "USA", "CHN", "JPN", "DEU", "FRA", "GBR", "CHE", "IND",
  "AUS", "BEL", "CAN", "DNK", "ESP", "FIN", "IRL", "ITA",
  "NLD", "NOR", "PRT", "SWE",
];

function label(map: Record<string, string>, key: string) {
  return map[key] ?? key.replaceAll("_", " ");
}

function toneForImplementation(status: string) {
  if (status === "evaluation_implemented") return "ok";
  if (status === "research_method_implemented" || status === "data_available") return "info";
  if (status === "partially_implemented") return "warn";
  return "err";
}

function toneForValidation(status: string) {
  if (status === "evidence_supporting_registered_claim") return "ok";
  if (status === "evidence_inconsistent_with_registered_claim") return "err";
  if (status === "currently_untestable" || status === "insufficient_evidence") return "warn";
  return "info";
}

function questionCodeFromUrl(): string | null {
  if (typeof window === "undefined") return null;
  const value = new URLSearchParams(window.location.search).get("question");
  return /^Q\d{2}$/.test(value ?? "") ? value : null;
}

function StatusPair({ question }: { question: ValidationQuestionSummary }) {
  return (
    <div className="flex flex-wrap gap-1.5">
      <Badge tone={toneForImplementation(question.implementation_status)}>
        {label(IMPLEMENTATION_LABELS, question.implementation_status)}
      </Badge>
      <Badge tone={toneForValidation(question.research_validation_status)}>
        {label(VALIDATION_LABELS, question.research_validation_status)}
      </Badge>
    </div>
  );
}

function TextList({ title, items }: { title: string; items?: string[] }) {
  if (!items?.length) return null;
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      <ul className="list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">
        {items.map((item) => <li key={item}>{item}</li>)}
      </ul>
    </section>
  );
}

function DatasetList({ title, items }: { title: string; items?: DatasetRef[] }) {
  if (!items?.length) return null;
  return (
    <section>
      <h3 className="mb-2 text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      <div className="space-y-2">
        {items.map((item, index) => (
          <div key={`${item.source_key}-${item.dataset}-${index}`} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-3 text-sm">
            <div className="font-medium text-[var(--text-primary)]">{item.dataset ?? item.source_key}</div>
            <div className="mt-1 text-[var(--text-secondary)]">
              {item.source_key && <span className="source-badge mr-2">{item.source_key}</span>}
              {item.role ?? item.reason}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function JsonRecord({ value }: { value: Record<string, unknown> }) {
  return (
    <dl className="grid gap-1 text-xs text-[var(--text-secondary)] sm:grid-cols-[9rem_1fr]">
      {Object.entries(value).map(([key, raw]) => (
        <div key={key} className="contents">
          <dt className="text-[var(--text-tertiary)]">{key.replaceAll("_", " ")}</dt>
          <dd>{typeof raw === "object" && raw !== null ? JSON.stringify(raw) : String(raw)}</dd>
        </div>
      ))}
    </dl>
  );
}

function EvidenceChart({ chart }: { chart: NonNullable<ValidationQuestionDetail["chart"]> }) {
  const option = useMemo<EChartsOption>(() => {
    const points = (chart.points ?? [])
      .filter((point) => point.period && typeof point.value === "number")
      .map((point) => [point.period, point.value]);
    return {
      ...baseChartOption(),
      xAxis: { type: "time" },
      yAxis: { type: "value", name: chart.points?.[0]?.unit ?? "" },
      series: [{ type: "line", name: chart.label ?? "Evidence", data: points, showSymbol: false }],
      tooltip: { trigger: "axis" },
    };
  }, [chart]);
  if (!chart.points?.length) {
    return <p className="text-sm text-[var(--text-tertiary)]">No historical observations are available for this evidence view.</p>;
  }
  return <EChart option={option} style={{ height: 220 }} ariaLabel={chart.label ?? "Evidence history"} />;
}

function QuestionDetails({ code }: { code: string }) {
  const [entity, setEntity] = useState("USA");
  const state = useFetch(
    (c) => fetchValidationQuestion(code, entity, { signal: c.signal }),
    [code, entity],
  );
  if (state.kind === "loading") return <div className="state-box glass-subtle">Loading research evidence…</div>;
  if (state.kind === "error") return <div className="state-box glass-subtle text-[var(--status-warn)]">{state.error}</div>;

  const { question, actual_evidence: evidence, chart, related_protocols, related_evaluations } = state.data;
  return (
    <article className="glass rounded-2xl p-4 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="label-md text-tertiary">{question.question_code} · {label(CATEGORY_LABELS, question.category)}</p>
          <h2 className="mt-1 text-2xl font-semibold">{question.short_title}</h2>
        </div>
        <a className="glass-button" href={`/research/validation?question=${question.question_code}`}>Stable URL</a>
      </div>

      <p className="mt-4 max-w-4xl text-base leading-7">{question.original_question}</p>
      <div className="mt-4"><StatusPair question={question} /></div>

      <section className="mt-5 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-4">
        <h3 className="text-sm font-semibold">Current documented answer</h3>
        <p className="mt-2 text-sm leading-6 text-[var(--text-secondary)]">{question.current_answer}</p>
      </section>

      <div className="mt-5 grid gap-5 xl:grid-cols-2">
        <DatasetList title="Required datasets" items={question.required_datasets} />
        <DatasetList title="Available datasets" items={question.available_datasets} />
        <DatasetList title="Missing datasets" items={question.missing_datasets} />
        <section>
          <h3 className="mb-2 text-sm font-semibold">Coverage</h3>
          <div className="space-y-2">
            <JsonRecord value={question.historical_coverage} />
            <JsonRecord value={question.country_coverage} />
          </div>
        </section>
      </div>

      <section className="mt-6">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
          <h3 className="text-sm font-semibold">Actual imported evidence</h3>
          {chart && (
            <label className="text-xs text-[var(--text-secondary)]">
              Entity{" "}
              <select
                className="glass-button ml-1"
                value={entity}
                onChange={(event) => setEntity(event.target.value)}
              >
                {CHART_ENTITIES.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>
          )}
        </div>
        {chart && (
          <div className="mb-4 rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-3">
            <div className="mb-2 flex items-center justify-between gap-3">
              <span className="text-sm font-medium">{chart.label}</span>
              <span className="source-badge">{chart.entity_code}</span>
            </div>
            <EvidenceChart chart={chart} />
          </div>
        )}
        <div className="space-y-3">
          {evidence.map((item, index) => (
            <div key={index} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-3">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="source-badge">{item.declared_dataset.source_key}</span>
                <span className="text-sm font-medium">{item.declared_dataset.dataset}</span>
              </div>
              {item.observed.length ? (
                <div className="grid gap-2 lg:grid-cols-2">
                  {item.observed.slice(0, 8).map((record, recordIndex) => (
                    <JsonRecord key={recordIndex} value={record} />
                  ))}
                  {item.observed.length > 8 && <p className="text-xs text-[var(--text-tertiary)]">+{item.observed.length - 8} additional evidence rows</p>}
                </div>
              ) : (
                <p className="text-sm text-[var(--text-tertiary)]">Registry metadata only; no row-level observations imported.</p>
              )}
            </div>
          ))}
        </div>
      </section>

      <div className="mt-6 grid gap-5 xl:grid-cols-2">
        <TextList title="Research methods" items={question.existing_research_methods} />
        <TextList title="Supporting evidence" items={question.supporting_evidence} />
        <TextList title="Contradictory evidence" items={question.contradictory_evidence} />
        <TextList title="Alternative explanations" items={question.alternative_explanations} />
        <TextList title="Scientific limitations" items={question.scientific_limitations} />
        <section>
          <h3 className="mb-2 text-sm font-semibold">Falsification criteria</h3>
          <p className="text-sm leading-6 text-[var(--text-secondary)]">{question.falsification_criteria}</p>
        </section>
      </div>

      <section className="mt-6 grid gap-5 xl:grid-cols-2">
        <div>
          <h3 className="mb-2 text-sm font-semibold">Related registered hypotheses</h3>
          {related_protocols.length ? (
            <div className="space-y-2">
              {related_protocols.map((protocol) => (
                <div key={String(protocol.protocol_version)} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-3 text-sm">
                  <div className="font-medium">{String(protocol.hypothesis_code)} · {String(protocol.protocol_version)}</div>
                  <div className="mt-1 text-[var(--text-secondary)]">{String(protocol.title)}</div>
                  <div className="mt-1 text-xs text-[var(--text-tertiary)]">{String(protocol.protocol_status)}</div>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-[var(--text-tertiary)]">No registered hypothesis is linked to this question yet.</p>}
        </div>
        <div>
          <h3 className="mb-2 text-sm font-semibold">Evaluation results</h3>
          {related_evaluations.length ? (
            <div className="space-y-2">
              {related_evaluations.map((evaluation) => (
                <div key={String(evaluation.evaluation_key)} className="rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] p-3 text-sm">
                  <div className="font-medium">{String(evaluation.evaluation_key)}</div>
                  <div className="mt-1"><Badge tone={toneForValidation(String(evaluation.result_state))}>{label(VALIDATION_LABELS, String(evaluation.result_state))}</Badge></div>
                  <div className="mt-2 text-xs text-[var(--text-secondary)]">Model: {String(evaluation.model_id)} · {String(evaluation.model_version)}</div>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-[var(--text-tertiary)]">No held-out evaluation exists for this question.</p>}
        </div>
      </section>

      <section className="mt-6">
        <h3 className="mb-2 text-sm font-semibold">Source references</h3>
        <div className="flex flex-wrap gap-2">
          {question.source_references.map((reference) => (
            <a
              key={`${reference.label}-${reference.url}`}
              className="glass-button"
              href={reference.url}
              target={reference.url?.startsWith("http") ? "_blank" : undefined}
              rel={reference.url?.startsWith("http") ? "noreferrer" : undefined}
            >
              {reference.label ?? reference.url}
            </a>
          ))}
        </div>
      </section>
    </article>
  );
}

function SummaryBand({ summary }: { summary: ValidationSummaryResponse }) {
  const implementation = summary.by_implementation_status;
  const validation = summary.by_research_validation_status;
  return (
    <div className="grid gap-3 md:grid-cols-3">
      <div className="glass-subtle rounded-2xl p-4">
        <div className="text-3xl font-semibold">{summary.count}</div>
        <div className="mt-1 text-sm text-[var(--text-secondary)]">canonical research questions</div>
      </div>
      <div className="glass-subtle rounded-2xl p-4">
        <div className="text-sm font-semibold">Implementation coverage</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(implementation).map(([key, value]) => <Badge key={key} tone={toneForImplementation(key)}>{value} {label(IMPLEMENTATION_LABELS, key)}</Badge>)}
        </div>
      </div>
      <div className="glass-subtle rounded-2xl p-4">
        <div className="text-sm font-semibold">Scientific status</div>
        <div className="mt-2 flex flex-wrap gap-1.5">
          {Object.entries(validation).map(([key, value]) => <Badge key={key} tone={toneForValidation(key)}>{value} {label(VALIDATION_LABELS, key)}</Badge>)}
        </div>
      </div>
    </div>
  );
}

export function ValidationExplorer() {
  const questions = useFetch((c) => fetchValidationQuestions({ signal: c.signal }), []);
  const summary = useFetch((c) => fetchValidationSummary({ signal: c.signal }), []);
  const [category, setCategory] = useState("all");
  const [implementation, setImplementation] = useState("all");
  const [validation, setValidation] = useState("all");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<string | null>(questionCodeFromUrl());

  const allQuestions = questions.kind === "ready" ? questions.data.questions : [];
  const filtered = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return allQuestions.filter((question) =>
      (category === "all" || question.category === category) &&
      (implementation === "all" || question.implementation_status === implementation) &&
      (validation === "all" || question.research_validation_status === validation) &&
      (!needle || `${question.question_code} ${question.short_title} ${question.original_question}`.toLowerCase().includes(needle))
    );
  }, [allQuestions, category, implementation, validation, search]);

  useEffect(() => {
    if (!selected && filtered[0]) setSelected(filtered[0].question_code);
  }, [filtered, selected]);

  useEffect(() => {
    if (!selected || typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("question", selected);
    window.history.replaceState(null, "", url);
  }, [selected]);

  if (questions.kind === "loading" || summary.kind === "loading") {
    return <div className="state-box glass-subtle">Loading validation registry…</div>;
  }
  if (questions.kind === "error") return <div className="state-box glass-subtle text-[var(--status-warn)]">{questions.error}</div>;
  if (summary.kind === "error") return <div className="state-box glass-subtle text-[var(--status-warn)]">{summary.error}</div>;

  const categories = Object.keys(CATEGORY_LABELS);
  const selectedQuestion = allQuestions.find((question) => question.question_code === selected) ?? filtered[0];

  return (
    <div className="space-y-5">
      <SummaryBand summary={summary.data} />
      <div className="grid gap-5 xl:grid-cols-[25rem_minmax(0,1fr)]">
        <aside className="glass rounded-2xl p-3 xl:sticky xl:top-28 xl:max-h-[calc(100vh-8rem)] xl:overflow-y-auto">
          <div className="space-y-2">
            <input
              className="w-full rounded-xl border border-[var(--border-subtle)] bg-[var(--surface-1)] px-3 py-2 text-sm"
              type="search"
              aria-label="Search validation questions"
              placeholder="Search all 50 questions…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
            <div className="grid gap-2 sm:grid-cols-3 xl:grid-cols-1">
              <select className="glass-button" value={category} onChange={(event) => setCategory(event.target.value)} aria-label="Category">
                <option value="all">All categories</option>
                {categories.map((item) => <option key={item} value={item}>{CATEGORY_LABELS[item]}</option>)}
              </select>
              <select className="glass-button" value={implementation} onChange={(event) => setImplementation(event.target.value)} aria-label="Implementation status">
                <option value="all">All implementation states</option>
                {Object.entries(IMPLEMENTATION_LABELS).map(([key, text]) => <option key={key} value={key}>{text}</option>)}
              </select>
              <select className="glass-button" value={validation} onChange={(event) => setValidation(event.target.value)} aria-label="Scientific status">
                <option value="all">All scientific states</option>
                {Object.entries(VALIDATION_LABELS).map(([key, text]) => <option key={key} value={key}>{text}</option>)}
              </select>
            </div>
          </div>
          <div className="mt-3 flex items-center justify-between text-xs text-[var(--text-tertiary)]">
            <span>{filtered.length} questions</span>
            <span>{summary.data.registry_version}</span>
          </div>
          <div className="mt-3 space-y-2">
            {filtered.map((question) => (
              <button
                key={question.question_code}
                type="button"
                onClick={() => setSelected(question.question_code)}
                className={`w-full rounded-xl border p-3 text-left transition ${question.question_code === selectedQuestion?.question_code ? "border-[var(--accent)] bg-[var(--accent-soft)]" : "border-[var(--border-subtle)] bg-[var(--surface-1)] hover:bg-[var(--surface-2)]"}`}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="source-badge">{question.question_code}</span>
                  <span className="text-xs text-[var(--text-tertiary)]">{label(CATEGORY_LABELS, question.category)}</span>
                </div>
                <div className="mt-2 text-sm font-medium">{question.short_title}</div>
                <div className="mt-2"><StatusPair question={question} /></div>
              </button>
            ))}
          </div>
        </aside>
        <div className="min-w-0">
          {selectedQuestion ? <QuestionDetails code={selectedQuestion.question_code} /> : <div className="state-box glass-subtle">No question matches the current filters.</div>}
        </div>
      </div>
    </div>
  );
}
