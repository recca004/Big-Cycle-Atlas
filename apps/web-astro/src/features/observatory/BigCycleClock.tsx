/** Big Cycle Clock — signature observatory instrument.
 *
 *  Places every tracked power on the cycle dial by its latest
 *  EXPERIMENTAL composite-model stage. Position is a model output —
 *  no countdown or transition probability is implied. */
import { useEffect, useState } from "react";
import { fetchCyclePositions } from "@/lib/api/client";

const MODEL = "model_b_domain";

/** Internal stage -> clock hour position (12 = top, clockwise). */
const STAGE_HOURS: Record<string, number> = {
  EARLY_RISE: 7.6,
  RISE: 8.9,
  LATE_RISE: 10.5,
  PEAK: 12,
  LATE_PEAK: 1.4,
  EARLY_DECLINE: 3,
  DECLINE: 4.5,
  RESET: 6,
};
const STAGE_LABELS: Record<string, string> = {
  EARLY_RISE: "Early rise",
  RISE: "Rise",
  LATE_RISE: "Late rise",
  PEAK: "Peak",
  LATE_PEAK: "Late peak",
  EARLY_DECLINE: "Early decline",
  DECLINE: "Decline",
  RESET: "Reset",
};

interface Power {
  iso3: string;
  name: string;
  stage: string | null;
  phase: string | null;
  score: number | null;
  momentum: number | null;
  period: string | null;
}

const polar = (hour: number, r: number, cx = 320, cy = 300) => {
  const a = ((hour * 30 - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
};

export function BigCycleClock() {
  const [powers, setPowers] = useState<Power[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetchCyclePositions(MODEL);
        if (alive)
          setPowers(
            res.positions.map((p) => ({
              iso3: p.iso3,
              name: p.name,
              stage: p.stage,
              phase: p.phase,
              score: p.score,
              momentum: p.momentum,
              period: p.period,
            })),
          );
      } catch (e) {
        if (alive) setError(e instanceof Error ? e.message : "Clock unavailable");
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  if (error)
    return (
      <p className="body-md" role="alert">
        Clock unavailable: {error}
      </p>
    );
  if (!powers)
    return (
      <div className="clock-loading" aria-busy="true">
        <div className="clock-skeleton" />
      </div>
    );

  const placed = powers.filter((p) => p.stage && STAGE_HOURS[p.stage]);
  const unplaced = powers.filter((p) => !p.stage || !STAGE_HOURS[p.stage]);
  const dominant = [...placed]
    .filter((p) => p.score !== null)
    .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))[0];
  // Offset markers sharing a stage radially so they don't overlap.
  const byStage = new Map<string, Power[]>();
  placed.forEach((p) => {
    const k = p.stage!;
    byStage.set(k, [...(byStage.get(k) ?? []), p]);
  });

  return (
    <figure className="clock-figure" aria-label="Big Cycle Clock — experimental model positions">
      <svg viewBox="0 0 640 600" role="img" className="clock-svg">
        {/* Armillary instrument rings */}
        <circle cx="320" cy="300" r="238" className="clock-rim" />
        <circle cx="320" cy="300" r="196" className="clock-ring-inner" />
        <ellipse cx="320" cy="300" rx="238" ry="92" className="clock-meridian" />
        <ellipse cx="320" cy="300" rx="92" ry="238" className="clock-meridian" />
        {/* Apex marker — matches the logo mark */}
        <path d="M320 46 L328.6 60 L311.4 60 Z" className="clock-apex" />
        {/* Stage ticks + labels */}
        {Object.entries(STAGE_HOURS).map(([stage, hour]) => {
          const p1 = polar(hour, 216);
          const p2 = polar(hour, 238);
          const lp = polar(hour, 268);
          const occupied = byStage.has(stage);
          return (
            <g key={stage}>
              <line
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                className={occupied ? "clock-tick occupied" : "clock-tick"}
              />
              <text
                x={lp.x}
                y={lp.y}
                className="clock-stage-label"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {STAGE_LABELS[stage]}
              </text>
            </g>
          );
        })}
        {/* Country markers */}
        {placed.map((p) => {
          const siblings = byStage.get(p.stage!) ?? [p];
          const idx = siblings.indexOf(p);
          // Spread same-stage powers along the arc (±~0.45h each) and
          // stagger radius slightly so labels don't stack.
          const hour =
            (STAGE_HOURS[p.stage!] ?? 12) +
            (idx - (siblings.length - 1) / 2) * 0.55;
          const r = 196 - (idx % 2) * 26;
          const m = polar(hour, r);
          const isDom = p === dominant;
          const rising = (p.momentum ?? 0) > 0;
          return (
            <g key={p.iso3}>
              <circle
                cx={m.x}
                cy={m.y}
                r={isDom ? 9 : 6.5}
                className={isDom ? "clock-marker dominant" : "clock-marker"}
              >
                <title>
                  {p.name} — {STAGE_LABELS[p.stage!] ?? p.stage}
                  {p.score !== null ? ` · score ${p.score.toFixed(1)}` : ""}
                </title>
              </circle>
              <text
                x={m.x}
                y={m.y + (isDom ? 24 : 21)}
                className={isDom ? "clock-iso dominant" : "clock-iso"}
                textAnchor="middle"
              >
                {p.iso3}
                {rising ? "▲" : "▼"}
              </text>
            </g>
          );
        })}
        <text x="320" y="300" className="clock-hub" textAnchor="middle">
          BIG CYCLE
        </text>
      </svg>
      <figcaption className="clock-caption">
        <p>
          <strong>{dominant ? dominant.name : "—"}</strong> currently scores
          highest on the {MODEL} experimental composite
          {dominant?.period ? ` (${dominant.period})` : ""}.
          {unplaced.length > 0 &&
            ` ${unplaced.map((p) => p.iso3).join(", ")} unclassified (insufficient coverage).`}
        </p>
        <p className="clock-honesty">
          Experimental classification — position on the dial is a model output,
          not a prediction. No countdown or transition date is implied.
        </p>
      </figcaption>
    </figure>
  );
}
