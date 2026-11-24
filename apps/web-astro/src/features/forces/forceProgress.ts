/** Research/implementation stage tracking for the 17 Big Cycle forces.
 *  Maintained manually alongside DECISIONS.md — this is the single source
 *  the /progress page derives all counts from. Keep honest: a stage is only
 *  true when the corresponding artefact exists in the repo.
 */
export interface ForceProgress {
  code: string;
  name: string;
  researchStarted: boolean;
  researchCompleted: boolean;
  dataSourced: boolean;
  methodologyProposed: boolean;
  methodologyApproved: boolean;
  implemented: boolean;
  testsPassing: boolean;
  apiAvailable: boolean;
  frontendConnected: boolean;
  /** "ratified" | "provisional" | "pending" | "n/a" */
  ratification: string;
  note?: string;
}

const DONE = {
  researchStarted: true,
  researchCompleted: true,
  dataSourced: true,
  methodologyProposed: true,
  methodologyApproved: true,
  implemented: true,
  testsPassing: true,
  apiAvailable: true,
  frontendConnected: true,
  ratification: "ratified",
} satisfies Omit<ForceProgress, "code" | "name" | "note">;

export const FORCE_PROGRESS: ForceProgress[] = [
  {
    code: "leadership_capabilities",
    name: "Leadership capabilities",
    ...DONE,
    note: "DEC-041 ratified: WGI Government Effectiveness proxy, PARTIAL-capped.",
  },
  { code: "education", name: "Education", ...DONE },
  {
    code: "character_determination",
    name: "Character / determination",
    researchStarted: true, researchCompleted: false, dataSourced: false,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: false,
    ratification: "n/a",
  },
  { code: "rule_of_law", name: "Rule of law", ...DONE },
  { code: "corruption", name: "Corruption", ...DONE },
  {
    code: "resource_allocation_efficiency",
    name: "Resource allocation efficiency",
    researchStarted: true, researchCompleted: false, dataSourced: false,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: false,
    ratification: "n/a",
  },
  {
    code: "global_openness",
    name: "Global openness",
    researchStarted: true, researchCompleted: true, dataSourced: true,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: true,
    ratification: "pending",
    note: "Trade data imported; narrower proxy methodology needs owner approval.",
  },
  {
    code: "productivity_output_growth",
    name: "Productivity / output growth",
    ...DONE,
    note: "DEC-042 Option A implemented: OECD reference percentile (oecd_lpph_v1), PARTIAL-capped. CHN/IND unavailable (non-OECD).",
  },
  {
    code: "cost_competitiveness",
    name: "Cost competitiveness",
    researchStarted: true, researchCompleted: true, dataSourced: true,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: true,
    ratification: "pending",
    note: "DEC-018; OECD ULC coverage excludes CHN/IND — REER research open (6.15).",
  },
  {
    code: "trade_capital_flows",
    name: "Trade and capital flows",
    researchStarted: true, researchCompleted: true, dataSourced: true,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: true,
    ratification: "pending",
    note: "DEC-039; relative/momentum dimensions under review (6.16).",
  },
  {
    code: "infrastructure_investment",
    name: "Infrastructure and investment",
    researchStarted: true, researchCompleted: true, dataSourced: true,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: true,
    ratification: "pending",
    note: "Gross capital formation %GDP live for all 8 countries.",
  },
  {
    code: "indebtedness",
    name: "Indebtedness",
    ...DONE,
    ratification: "ratified",
    note: "DEC-040 CONDITION_MINUS_PENALTY — ratified with documented limitations.",
  },
  {
    code: "military_strength",
    name: "Military strength",
    researchStarted: true, researchCompleted: true, dataSourced: true,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: true,
    ratification: "pending",
    note: "DEC-009 ceiling: spending inputs alone can never reach available.",
  },
  { code: "wealth_opportunity_values_gaps", name: "Wealth / opportunity / values gaps", ...DONE,
    note: "Income-vs-consumption Gini comparability limitation preserved." },
  { code: "internal_conflict", name: "Internal conflict", ...DONE },
  {
    code: "geography",
    name: "Geography",
    researchStarted: true, researchCompleted: false, dataSourced: false,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: false,
    ratification: "n/a",
  },
  {
    code: "acts_of_nature",
    name: "Acts of nature",
    researchStarted: true, researchCompleted: false, dataSourced: false,
    methodologyProposed: false, methodologyApproved: false, implemented: false,
    testsPassing: false, apiAvailable: false, frontendConnected: false,
    ratification: "n/a",
  },
];

export const EXECUTABLE_COUNT = FORCE_PROGRESS.filter((f) => f.implemented).length;
export const TOTAL_FORCES = FORCE_PROGRESS.length;
