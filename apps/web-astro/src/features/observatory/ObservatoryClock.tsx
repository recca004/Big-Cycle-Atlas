/** Observatory Clock — Three.js instrument + fixed SVG dial + controls.
 *
 *  Layers (back → front):
 *    1. WebGL canvas (decorative globe + orbital rings, lazy-mounted)
 *    2. <CycleDial> SVG overlay (stage ring + markers — never rotates)
 *    3. Control bar (2D/3D, pause, speed, reset camera)
 *    4. <HistoricalPlayback> timeline beneath the dial */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { ObservatoryCountry } from "@/types/observatory";
import { CycleDial, type DialCountry } from "./CycleDial";
import type { BigCycleScene } from "./scene";
import { STAGE_HOURS } from "./stages";

interface Props {
  countries: ObservatoryCountry[];
  selectedIso3: string | null;
  onSelect: (iso3: string) => void;
  /** Period shown when playing back history; null = latest. */
  playbackPeriod: string | null;
}

const REDUCED_MOTION =
  typeof window !== "undefined" &&
  (window.matchMedia("(prefers-reduced-motion: reduce)").matches ||
    document.documentElement.dataset.motion === "reduced");

export function ObservatoryClock({
  countries,
  selectedIso3,
  onSelect,
  playbackPeriod,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<BigCycleScene | null>(null);
  const [webgl, setWebgl] = useState<"pending" | "ok" | "failed">("pending");
  const [mode3d, setMode3d] = useState(true);
  const [paused, setPaused] = useState(REDUCED_MOTION);
  const [speed, setSpeed] = useState(1);

  // Lazy-mount the scene only when the clock scrolls into view and the
  // tab is visible — dynamic import keeps three.js out of the main chunk.
  useEffect(() => {
    if (!mode3d || webgl === "failed") return;
    const host = hostRef.current;
    if (!host) return;
    let scene: BigCycleScene | null = null;
    let cancelled = false;
    const io = new IntersectionObserver(
      async (entries) => {
        if (!entries.some((e) => e.isIntersecting) || cancelled) return;
        io.disconnect();
        const lowPower =
          window.matchMedia("(max-width: 768px)").matches ||
          (navigator.hardwareConcurrency ?? 8) <= 4;
        try {
          const mod = await import("./scene");
          if (cancelled) return;
          scene = new mod.BigCycleScene({
            quality: lowPower ? "low" : "high",
            reducedMotion: REDUCED_MOTION,
            onWebGLFailure: () => setWebgl("failed"),
          });
          const ok = scene.mount(host);
          if (cancelled) {
            scene.dispose();
            return;
          }
          setWebgl(ok ? "ok" : "failed");
          sceneRef.current = ok ? scene : null;
        } catch {
          setWebgl("failed");
        }
      },
      { rootMargin: "200px" },
    );
    io.observe(host);
    return () => {
      cancelled = true;
      io.disconnect();
      scene?.dispose();
      sceneRef.current = null;
    };
  }, [mode3d, webgl === "failed" ? "failed" : "ok"]);

  // Propagate control state into the scene.
  useEffect(() => sceneRef.current?.setPaused(paused), [paused]);
  useEffect(() => sceneRef.current?.setSpeed(speed), [speed]);

  // Re-tint on theme change.
  useEffect(() => {
    const obs = new MutationObserver(() => sceneRef.current?.applyTheme());
    obs.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-theme"],
    });
    return () => obs.disconnect();
  }, []);

  // Camera nudge toward the selected country's stage hour.
  useEffect(() => {
    if (!selectedIso3 || !sceneRef.current) return;
    const c = countries.find((x) => x.iso3 === selectedIso3);
    const hour = c?.stage ? STAGE_HOURS[c.stage as keyof typeof STAGE_HOURS] : null;
    if (hour != null) sceneRef.current.focusHour(hour);
  }, [selectedIso3, countries]);

  // Dial data — historical playback swaps each country's stage/score to
  // the selected period's actual classification (no interpolation).
  const dialCountries: DialCountry[] = useMemo(() => {
    return countries.map((c) => {
      if (!playbackPeriod) {
        return {
          iso3: c.iso3,
          name: c.name,
          stage: c.stage,
          score: c.score,
          momentum: c.momentum,
          period: c.period,
        };
      }
      const h = c.history.find((p) => p.period === playbackPeriod);
      return {
        iso3: c.iso3,
        name: c.name,
        stage: h?.stage ?? null,
        score: h?.score ?? null,
        momentum: h?.momentum ?? null,
        period: playbackPeriod,
      };
    });
  }, [countries, playbackPeriod]);

  const show3d = mode3d && webgl !== "failed";
  const handleSelect = useCallback((iso3: string) => onSelect(iso3), [onSelect]);

  return (
    <div className="obs-clock">
      <div className="obs-clock-frame" ref={hostRef}>
        {show3d && <div className="obs-clock-canvas" aria-hidden="true" />}
        <div className="obs-clock-dial">
          <CycleDial
            countries={dialCountries}
            selectedIso3={selectedIso3}
            onSelect={handleSelect}
            decorative={!show3d}
            animate={!REDUCED_MOTION}
          />
        </div>
        {playbackPeriod && (
          <div className="obs-clock-hist-badge" role="status">
            Historical view · {playbackPeriod}
          </div>
        )}
      </div>
      <div className="obs-clock-controls">
        <button
          type="button"
          className="glass-button"
          onClick={() => setMode3d((v) => !v)}
          disabled={webgl === "failed"}
          title={
            webgl === "failed"
              ? "WebGL unavailable — SVG fallback"
              : "Toggle 2D / 3D view"
          }
        >
          {show3d ? "2D" : "3D"}
        </button>
        <button
          type="button"
          className="glass-button"
          onClick={() => setPaused((v) => !v)}
          disabled={!show3d}
          title={paused ? "Resume instrument motion" : "Pause instrument motion"}
        >
          {paused ? "Resume" : "Pause"}
        </button>
        <label className="obs-speed">
          <span className="obs-speed-label">Speed</span>
          <input
            type="range"
            min={0.25}
            max={3}
            step={0.25}
            value={speed}
            disabled={!show3d}
            onChange={(e) => setSpeed(Number(e.target.value))}
          />
        </label>
        <button
          type="button"
          className="glass-button"
          onClick={() => sceneRef.current?.resetCamera()}
          disabled={!show3d}
        >
          Reset view
        </button>
      </div>
      <p className="clock-honesty">
        Experimental classification — position on the dial is a model output,
        not a prediction. No countdown or transition date is implied.
      </p>
    </div>
  );
}
