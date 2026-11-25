/** Observatory Clock — modular Three.js instrument + fixed SVG dial +
 *  camera, playback and reduced-motion controls. Layers (back → front):
 *  WebGL canvas, fixed <CycleDial> overlay, unified control bar. */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ObservatoryCountry } from "@/types/observatory";
import { CycleDial, type DialCountry } from "./CycleDial";
import type { BigCycleScene } from "./scene";
import type { CameraPreset } from "./scene/camera";

interface Props {
  countries: ObservatoryCountry[];
  selectedIso3: string | null;
  onSelect: (iso3: string) => void;
  playbackPeriod: string | null;
  playbackControls?: React.ReactNode;
  periodLabel?: string;
}

const CAMERA_BUTTONS: { key: CameraPreset; label: string; hint: string }[] = [
  { key: "observatory", label: "Observatory", hint: "Balanced instrument view" },
  { key: "ecliptic", label: "Ecliptic", hint: "Flat clock-face view" },
  { key: "armillary", label: "Armillary", hint: "Angled globe and rings view" },
  { key: "beacon", label: "Beacon", hint: "Focus toward the selected country beacon" },
];

function usePreferredReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () =>
      setReduced(query.matches || document.documentElement.dataset.motion === "reduced");
    update();
    query.addEventListener("change", update);
    const observer = new MutationObserver(update);
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-motion"] });
    return () => {
      query.removeEventListener("change", update);
      observer.disconnect();
    };
  }, []);
  return reduced;
}

export function ObservatoryClock({
  countries,
  selectedIso3,
  onSelect,
  playbackPeriod,
  playbackControls,
  periodLabel,
}: Props) {
  const frameRef = useRef<HTMLDivElement>(null);
  const canvasHostRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<BigCycleScene | null>(null);
  const [webgl, setWebgl] = useState<"pending" | "ok" | "failed">("pending");
  const [mode3d, setMode3d] = useState(true);
  const [paused, setPaused] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [camera, setCamera] = useState<CameraPreset>("observatory");
  const [manualReduced, setManualReduced] = useState(false);
  const preferredReduced = usePreferredReducedMotion();
  const reducedMotion = preferredReduced || manualReduced;
  const latestRef = useRef({
    countries: [] as DialCountry[],
    selectedIso3,
    reducedMotion,
    paused,
    speed,
  });
  useEffect(() => {
    latestRef.current = { countries: dialCountriesRef.current, selectedIso3, reducedMotion, paused, speed };
  });
  const dialCountriesRef = useRef<DialCountry[]>([]);

  // Lazy-mount the scene only when the clock scrolls into view. Dynamic
  // import keeps three.js out of the initial homepage chunk.
  useEffect(() => {
    if (!mode3d) return;
    const host = canvasHostRef.current;
    if (!host) return;
    let scene: BigCycleScene | null = null;
    let cancelled = false;
    const io = new IntersectionObserver(
      async (entries) => {
        if (!entries.some((entry) => entry.isIntersecting) || cancelled || sceneRef.current) return;
        io.disconnect();
        const lowPower = window.matchMedia("(max-width: 768px)").matches || (navigator.hardwareConcurrency ?? 8) <= 4;
        try {
          const mod = await import("./scene");
          if (cancelled) return;
          scene = new mod.BigCycleScene({
            quality: lowPower ? "low" : "high",
            reducedMotion,
            onWebGLFailure: () => setWebgl("failed"),
            onSelect,
          });
          const ok = scene.mount(host);
          if (cancelled) {
            scene.dispose();
            return;
          }
          setWebgl(ok ? "ok" : "failed");
          sceneRef.current = ok ? scene : null;
          if (ok) {
            scene.updateCountries(latestRef.current.countries);
            scene.setSelectedIso3(latestRef.current.selectedIso3);
            scene.setReducedMotion(latestRef.current.reducedMotion);
            scene.setPaused(latestRef.current.paused);
            scene.setSpeed(latestRef.current.speed);
          }
        } catch {
          setWebgl("failed");
        }
      },
      { rootMargin: "200px" },
    );
    io.observe(frameRef.current ?? host);
    return () => {
      cancelled = true;
      io.disconnect();
      scene?.dispose();
      sceneRef.current = null;
    };
    // Mount once per 2D/3D mode transition; control state is pushed by effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode3d]);

  // Propagate control state into the scene.
  useEffect(() => sceneRef.current?.setPaused(paused), [paused]);
  useEffect(() => sceneRef.current?.setSpeed(speed), [speed]);
  useEffect(() => sceneRef.current?.setReducedMotion(reducedMotion), [reducedMotion]);
  useEffect(() => sceneRef.current?.setSelectedIso3(selectedIso3), [selectedIso3]);

  useEffect(() => {
    const observer = new MutationObserver(() => sceneRef.current?.applyTheme());
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => observer.disconnect();
  }, []);

  // Dial data — historical playback swaps each country's stage/score to
  // the selected period's actual classification (no interpolation).
  const dialCountries: DialCountry[] = useMemo(
    () =>
      countries.map((country) => {
        if (!playbackPeriod) {
          return {
            iso3: country.iso3,
            name: country.name,
            stage: country.stage,
            score: country.score,
            momentum: country.momentum,
            period: country.period,
          };
        }
        const point = country.history.find((item) => item.period === playbackPeriod);
        return {
          iso3: country.iso3,
          name: country.name,
          stage: point?.stage ?? null,
          score: point?.score ?? null,
          momentum: point?.momentum ?? null,
          period: playbackPeriod,
        };
      }),
    [countries, playbackPeriod],
  );

  useEffect(() => {
    dialCountriesRef.current = dialCountries;
    latestRef.current.countries = dialCountries;
    sceneRef.current?.updateCountries(dialCountries);
  }, [dialCountries]);

  const show3d = mode3d && webgl !== "failed";
  const handleSelect = useCallback((iso3: string) => onSelect(iso3), [onSelect]);

  const chooseCamera = (preset: CameraPreset) => {
    setCamera(preset);
    if (preset === "beacon") sceneRef.current?.focusBeacon(selectedIso3);
    else sceneRef.current?.setCameraPreset(preset);
  };

  useEffect(() => {
    if (camera === "beacon") sceneRef.current?.focusBeacon(selectedIso3);
  }, [camera, selectedIso3]);

  return (
    <div className="obs-clock">
      <div className="obs-clock-frame" ref={frameRef}>
        {show3d && <div className="obs-clock-canvas" ref={canvasHostRef} />}
        <div className="obs-clock-dial">
          <CycleDial
            countries={dialCountries}
            selectedIso3={selectedIso3}
            onSelect={handleSelect}
            decorative={!show3d}
            animate={!reducedMotion}
          />
        </div>
        {playbackPeriod && (
          <div className="obs-clock-hist-badge" role="status">
            Historical view · {playbackPeriod}
          </div>
        )}
        {webgl === "pending" && show3d && (
          <div className="obs-clock-webgl-status" role="status">Preparing instrument…</div>
        )}
      </div>

      <div className="obs-controlbar">
        <div className="obs-control-cluster" role="group" aria-label="View controls">
          <button
            type="button"
            className="glass-button"
            onClick={() => setMode3d((value) => !value)}
            disabled={webgl === "failed"}
            title={webgl === "failed" ? "WebGL unavailable — SVG fallback" : "Toggle 2D / 3D view"}
          >
            {show3d ? "2D" : "3D"}
          </button>
          <button
            type="button"
            className="glass-button"
            onClick={() => setPaused((value) => !value)}
            disabled={!show3d}
            aria-pressed={paused}
          >
            {paused ? "Resume" : "Pause"}
          </button>
          <button
            type="button"
            className={reducedMotion ? "glass-button active" : "glass-button"}
            onClick={() => setManualReduced((value) => !value)}
            aria-pressed={reducedMotion}
            title={preferredReduced ? "System or site reduced-motion preference is active; manual control adds the same static mode" : "Reduce instrument motion"}
          >
            Reduce motion
          </button>
        </div>

        <label className="obs-speed">
          <span className="obs-speed-label">Speed</span>
          <input
            type="range"
            min={0.25}
            max={3}
            step={0.25}
            value={speed}
            disabled={!show3d || reducedMotion}
            onChange={(event) => setSpeed(Number(event.target.value))}
          />
        </label>

        <div className="obs-control-cluster obs-camera-presets" role="group" aria-label="Camera presets">
          {CAMERA_BUTTONS.map((preset) => (
            <button
              key={preset.key}
              type="button"
              className={camera === preset.key ? "glass-button active" : "glass-button"}
              aria-pressed={camera === preset.key}
              title={preset.hint}
              disabled={!show3d}
              onClick={() => chooseCamera(preset.key)}
            >
              {preset.label}
            </button>
          ))}
        </div>

        <button type="button" className="glass-button" onClick={() => chooseCamera("observatory")} disabled={!show3d}>
          Reset view
        </button>

        {playbackControls && (
          <>
            <span className="sep" aria-hidden="true" />
            <div className="obs-playback-cluster" role="group" aria-label="Historical playback controls">
              {playbackControls}
            </div>
          </>
        )}
        {periodLabel && (
          <span className="obs-period-label" role="status">
            Observation period: <strong>{periodLabel}</strong>
          </span>
        )}
      </div>
      <p className="clock-honesty">
        Offline demonstration classification — position on the dial is synthetic interface evidence, not an observation,
        forecast, countdown or prediction.
      </p>
    </div>
  );
}
