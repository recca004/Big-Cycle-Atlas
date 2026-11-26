/** Fixed cycle dial — the readable instrument layer. Rendered as an SVG
 *  overlay on top of the Three.js canvas (3D mode) or standalone as the
 *  full SVG fallback (2D mode / no WebGL). Economic positions live here
 *  and NEVER rotate with the decorative globe. */

import { useEffect, useMemo, useRef, useState } from "react";
import { gsap } from "gsap";
import {
  STAGE_HOURS,
  STAGE_LABELS,
  layoutMarkers,
  polar,
  stageLabel,
  type Stage,
} from "./stages";

export interface DialCountry {
  iso3: string;
  name: string;
  stage: string | null;
  score: number | null;
  momentum: number | null;
  period: string | null;
}

export interface DialModelGhost {
  modelId: string;
  modelLabel: string;
  stage: string;
  score: number | null;
}

interface Props {
  countries: DialCountry[];
  selectedIso3: string | null;
  onSelect: (iso3: string) => void;
  /** Render the decorative armillary rings (2D fallback mode). */
  decorative?: boolean;
  /** Animate marker entrance (skipped under reduced motion). */
  animate?: boolean;
  compact?: boolean;
  /** Optional all-model comparison markers for the selected power. */
  allModelGhosts?: DialModelGhost[];
}

const CX = 320;
const CY = 300;

export function CycleDial({
  countries,
  selectedIso3,
  onSelect,
  decorative = false,
  animate = true,
  compact = false,
  allModelGhosts = [],
}: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const placed = useMemo(
    () => countries.filter((c) => c.stage && c.stage in STAGE_HOURS),
    [countries],
  );
  const layouts = useMemo(
    () =>
      new Map(
        layoutMarkers(placed.map((c) => ({ iso3: c.iso3, stage: c.stage }))).map(
          (l) => [l.iso3, l],
        ),
      ),
    [placed],
  );
  const byStage = useMemo(() => {
    const m = new Map<string, DialCountry[]>();
    for (const c of placed) {
      const k = c.stage!;
      m.set(k, [...(m.get(k) ?? []), c]);
    }
    return m;
  }, [placed]);

  // Marker entrance — staggered scale-in via GSAP (skipped in 2D static
  // fallback and under reduced motion by the caller passing animate=false).
  useEffect(() => {
    if (!animate || !svgRef.current) return;
    const markers = svgRef.current.querySelectorAll<SVGGElement>(
      "[data-marker]",
    );
    gsap.fromTo(
      markers,
      { opacity: 0, scale: 0.4, transformOrigin: "center" },
      {
        opacity: 1,
        scale: 1,
        duration: 0.5,
        stagger: 0.07,
        ease: "back.out(1.8)",
        clearProps: "transform",
      },
    );
  }, [animate, placed.length]);

  // Selection emphasis — restrained GSAP pulse on the selected marker
  // (the camera never moves; the dial coordinates stay stable).
  useEffect(() => {
    if (!animate || !svgRef.current || !selectedIso3) return;
    const el = svgRef.current.querySelector<SVGGElement>(
      `[data-marker="${selectedIso3}"] circle.clock-marker`,
    );
    if (!el) return;
    gsap.fromTo(
      el,
      { scale: 0.6, transformOrigin: "center" },
      { scale: 1, duration: 0.45, ease: "back.out(2.2)" },
    );
  }, [selectedIso3, animate]);

  const hovered = countries.find((c) => c.iso3 === hover);

  return (
    <svg
      ref={svgRef}
      viewBox="-36 0 712 600"
      role="img"
      aria-label="Big Cycle Clock — experimental model positions"
      className={compact ? "clock-svg compact" : "clock-svg"}
    >
      {/* Decorative instrument rings — drawn here only for the flat SVG
          fallback; in 3D mode the WebGL canvas supplies them. */}
      {decorative && (
        <g aria-hidden="true">
          <ellipse cx={CX} cy={CY} rx="238" ry="92" className="clock-meridian" />
          <ellipse cx={CX} cy={CY} rx="92" ry="238" className="clock-meridian" />
          <ellipse
            cx={CX}
            cy={CY}
            rx="200"
            ry="60"
            className="clock-meridian faint"
            transform={`rotate(-24 ${CX} ${CY})`}
          />
          <circle cx={CX} cy={CY} r="118" className="clock-globe-ring" />
          {Array.from({ length: 12 }, (_, i) => {
            const a = (i / 12) * Math.PI * 2;
            return (
              <ellipse
                key={i}
                cx={CX}
                cy={CY}
                rx={118 * Math.abs(Math.cos(a)) || 1}
                ry="118"
                className="clock-globe-line"
                transform={`rotate(${(i * 180) / 12} ${CX} ${CY})`}
              />
            );
          })}
        </g>
      )}

      {/* Fixed instrument frame */}
      <circle cx={CX} cy={CY} r="238" className="clock-rim" />
      <circle cx={CX} cy={CY} r="196" className="clock-ring-inner" />
      <path d={`M${CX} 46 L${CX + 8.6} 60 L${CX - 8.6} 60 Z`} className="clock-apex" />

      {/* Fine tick marks around the rim — precision instrument feel */}
      {Array.from({ length: 96 }, (_, i) => {
        const hour = i / 8; // 96 ticks over 12 hours
        const p1 = polar(hour, 232);
        const p2 = polar(hour, i % 8 === 0 ? 224 : 229);
        return (
          <line
            key={i}
            x1={p1.x}
            y1={p1.y}
            x2={p2.x}
            y2={p2.y}
            className="clock-fine-tick"
          />
        );
      })}

      {/* Stage ring — fixed, readable, radially anchored outside the rim */}
      {Object.entries(STAGE_HOURS).map(([stage, hour]) => {
        const p1 = polar(hour, 214);
        const p2 = polar(hour, 238);
        const isRight = hour > 0.5 && hour < 5.5;
        const isLeft = hour > 6.5 && hour < 11.5;
        const labelRadius = isRight || isLeft ? 250 : 262;
        const lp = polar(hour, labelRadius);
        const anchor = isRight ? "start" : isLeft ? "end" : "middle";
        const occupied = byStage.has(stage);
        const count = byStage.get(stage)?.length ?? 0;
        return (
          <g key={stage} className="clock-stage">
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
              className={occupied ? "clock-stage-label occupied" : "clock-stage-label"}
              textAnchor={anchor}
              dominantBaseline="middle"
            >
              {STAGE_LABELS[stage]}
              {count > 1 ? ` ·${count}` : ""}
            </text>
          </g>
        );
      })}

      {/* Optional all-model comparison markers for the selected country */}
      {allModelGhosts.map((ghost, idx) => {
        const baseHour = STAGE_HOURS[ghost.stage as Stage];
        if (baseHour === undefined) return null;
        const offset = (idx - (allModelGhosts.length - 1) / 2) * 0.16;
        const gm = polar(baseHour + offset, 152);
        return (
          <g key={ghost.modelId} className="clock-model-ghost" aria-label={`${selectedIso3} ${ghost.modelLabel}: ${stageLabel(ghost.stage)}`}>
            <circle cx={gm.x} cy={gm.y} r="5.5" className="clock-ghost-dot" />
            <text x={gm.x} y={gm.y - 10} textAnchor="middle" className="clock-ghost-label">
              {ghost.modelLabel}
            </text>
            <title>{`${selectedIso3 ?? ""} — ${ghost.modelLabel}: ${stageLabel(ghost.stage)}${ghost.score !== null ? ` (${ghost.score.toFixed(1)})` : ""}`}</title>
          </g>
        );
      })}

      {/* Country markers — positioned at stage anchors, fanned within
          stage groups so siblings don't stack. */}
      {placed.map((c) => {
        const l = layouts.get(c.iso3);
        if (!l) return null;
        const r = 196 - l.ringIndex * 28;
        const m = polar(l.hour, r);
        const isSel = c.iso3 === selectedIso3;
        const rising = (c.momentum ?? 0) > 0;
        const labelY = m.y + (isSel ? 26 : 22);
        return (
          <g
            key={c.iso3}
            data-marker={c.iso3}
            className="clock-marker-g"
            role="button"
            tabIndex={0}
            aria-label={`${c.name} — ${stageLabel(c.stage)}${
              c.score !== null ? `, score ${c.score.toFixed(1)}` : ""
            }, ${rising ? "improving" : "softening"} experimental momentum`}
            onClick={() => onSelect(c.iso3)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSelect(c.iso3);
              }
            }}
            onMouseEnter={() => setHover(c.iso3)}
            onMouseLeave={() => setHover(null)}
            onFocus={() => setHover(c.iso3)}
            onBlur={() => setHover(null)}
          >
            <circle
              cx={m.x}
              cy={m.y}
              r="20"
              className="clock-marker-hit"
              aria-hidden="true"
            />
            {isSel && (
              <circle
                cx={m.x}
                cy={m.y}
                r="16"
                className="clock-marker-halo"
              />
            )}
            <circle
              cx={m.x}
              cy={m.y}
              r={isSel ? 10.5 : 8}
              className={
                isSel ? "clock-marker selected" : "clock-marker"
              }
            />
            <rect
              x={m.x - 21}
              y={labelY - 10}
              width="42"
              height="14"
              rx="4"
              className={isSel ? "clock-iso-pill selected" : "clock-iso-pill"}
              aria-hidden="true"
            />
            <text
              x={m.x}
              y={labelY}
              className={isSel ? "clock-iso selected" : "clock-iso"}
              textAnchor="middle"
            >
              {c.iso3}
              {rising ? "▲" : "▼"}
            </text>
          </g>
        );
      })}

      {/* Hover tooltip — SVG-native so it tracks markers exactly. */}
      {hovered && (
        <g pointerEvents="none" className="clock-tooltip">
          {(() => {
            const l = layouts.get(hovered.iso3);
            if (!l) return null;
            const m = polar(l.hour, 196 - l.ringIndex * 26);
            const tx = Math.min(Math.max(m.x, 120), 520);
            const ty = m.y - 52;
            return (
              <>
                <rect
                  x={tx - 92}
                  y={ty - 22}
                  width="184"
                  height="40"
                  rx="6"
                  className="clock-tooltip-bg"
                />
                <text x={tx} y={ty - 7} className="clock-tooltip-t1" textAnchor="middle">
                  {hovered.name} — {stageLabel(hovered.stage)}
                </text>
                <text x={tx} y={ty + 9} className="clock-tooltip-t2" textAnchor="middle">
                  {hovered.score !== null
                    ? `condition ${hovered.score.toFixed(1)}`
                    : "unscored"}
                  {hovered.period ? ` · ${hovered.period}` : ""}
                </text>
              </>
            );
          })()}
        </g>
      )}

      <text x={CX} y={CY} className="clock-hub" textAnchor="middle">
        BIG CYCLE
      </text>
    </svg>
  );
}

export { STAGE_HOURS, stageLabel };
export type { Stage };
