/** Big Cycle stage geometry — pure layout math shared by the SVG dial,
 *  the Three.js scene and tests. Positions are MODEL OUTPUTS placed at
 *  stage anchors; never interpolated as years or countdowns. */

export const STAGES = [
  "EARLY_RISE",
  "RISE",
  "LATE_RISE",
  "PEAK",
  "LATE_PEAK",
  "EARLY_DECLINE",
  "DECLINE",
  "RESET",
] as const;

export type Stage = (typeof STAGES)[number];

/** Internal stage -> clock hour position (12 = top, clockwise). */
export const STAGE_HOURS: Record<Stage, number> = {
  EARLY_RISE: 7.6,
  RISE: 8.9,
  LATE_RISE: 10.5,
  PEAK: 12,
  LATE_PEAK: 1.4,
  EARLY_DECLINE: 3,
  DECLINE: 4.5,
  RESET: 6,
};

export const STAGE_LABELS: Record<string, string> = {
  EARLY_RISE: "Early rise",
  RISE: "Rise",
  LATE_RISE: "Late rise",
  PEAK: "Peak",
  LATE_PEAK: "Late peak",
  EARLY_DECLINE: "Early decline",
  DECLINE: "Decline",
  RESET: "Reset",
};

export interface DialMarkerInput {
  iso3: string;
  stage: string | null;
}

export interface DialMarkerLayout {
  iso3: string;
  /** Clock hour (may be fanned within a stage group). */
  hour: number;
  /** Radial stagger index — 0 outer, 1 inner — for same-stage groups. */
  ringIndex: number;
  /** Size of the stage group this marker belongs to. */
  groupSize: number;
}

/** Fan markers that share a stage so labels don't stack — without
 *  inventing position differences (all share the stage anchor). */
export function layoutMarkers(
  markers: DialMarkerInput[],
  spreadHours = 0.55,
): DialMarkerLayout[] {
  const groups = new Map<string, DialMarkerInput[]>();
  for (const m of markers) {
    if (!m.stage || !(m.stage in STAGE_HOURS)) continue;
    const k = m.stage;
    groups.set(k, [...(groups.get(k) ?? []), m]);
  }
  const out: DialMarkerLayout[] = [];
  for (const [stage, members] of groups) {
    members.forEach((m, idx) => {
      out.push({
        iso3: m.iso3,
        hour:
          STAGE_HOURS[stage as Stage] +
          (idx - (members.length - 1) / 2) * spreadHours,
        ringIndex: idx % 2,
        groupSize: members.length,
      });
    });
  }
  return out;
}

/** Hour position -> degrees clockwise from 12 o'clock. */
export function hourToDeg(hour: number): number {
  return hour * 30;
}

/** Hour position -> radians for trig-based placement (0 = +x axis). */
export function hourToRad(hour: number): number {
  return ((hour * 30 - 90) * Math.PI) / 180;
}

export function polar(
  hour: number,
  r: number,
  cx = 320,
  cy = 300,
): { x: number; y: number } {
  const a = hourToRad(hour);
  return {
    x: Number((cx + r * Math.cos(a)).toFixed(3)),
    y: Number((cy + r * Math.sin(a)).toFixed(3)),
  };
}

export function stageLabel(stage: string | null): string {
  if (!stage) return "Unclassified";
  return STAGE_LABELS[stage] ?? stage;
}
