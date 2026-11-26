/** Scientific validation-question API contracts. */

export interface DatasetRef {
  source_key?: string;
  dataset?: string;
  role?: string;
  reason?: string;
  variables?: string[];
  indicators?: string[];
  [key: string]: unknown;
}

export interface ValidationQuestionSummary {
  question_code: string;
  registry_version: string;
  category: string;
  original_question: string;
  short_title: string;
  implementation_status: string;
  research_validation_status: string;
  current_answer: string;
  previous_implementation_status: string;
  last_reviewed_at: string | null;
  methodology_version: string;
  related_hypotheses: string[];
  related_forces: string[];
  related_power_measures: string[];
}

export interface ValidationQuestionDetail extends ValidationQuestionSummary {
  theory_claims: string[];
  required_datasets: DatasetRef[];
  available_datasets: DatasetRef[];
  missing_datasets: DatasetRef[];
  historical_coverage: Record<string, unknown>;
  country_coverage: Record<string, unknown>;
  existing_research_methods: string[];
  supporting_evidence: string[];
  contradictory_evidence: string[];
  alternative_explanations: string[];
  falsification_criteria: string;
  scientific_limitations: string[];
  source_references: { label?: string; url?: string }[];
  chart: EvidenceChartSpec | null;
  content_checksum: string;
}

export interface ActualEvidenceItem {
  declared_dataset: DatasetRef;
  observed: Record<string, unknown>[];
}

export interface EvidenceChartSpec {
  kind?: string;
  label?: string;
  entity_code?: string;
  points?: { period: string; value: number; unit?: string | null }[];
  [key: string]: unknown;
}

export interface ValidationQuestionsResponse {
  methodology_status: string;
  count: number;
  questions: ValidationQuestionSummary[];
}

export interface ValidationQuestionResponse {
  methodology_status: string;
  question: ValidationQuestionDetail;
  actual_evidence: ActualEvidenceItem[];
  chart: EvidenceChartSpec | null;
  related_protocols: Record<string, unknown>[];
  related_evaluations: Record<string, unknown>[];
  stable_url: string;
}

export interface FoundationEvaluationsResponse {
  count: number;
  evaluations: Record<string, unknown>[];
}

export interface ValidationSummaryResponse {
  count: number;
  registry_version: string | null;
  methodology_status: string;
  by_category: Record<string, number>;
  by_implementation_status: Record<string, number>;
  by_research_validation_status: Record<string, number>;
  available_dataset_mentions: Record<string, number>;
  missing_dataset_mentions: Record<string, number>;
  legacy_assessment: {
    implemented: number;
    partially_addressed: number;
    missing: number;
    note: string;
  };
}
