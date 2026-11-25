/** Camera preset module — named observatory views with reduced-motion aware GSAP transitions. */
import * as THREE from "three";
import { gsap } from "gsap";
import type { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export type CameraPreset = "observatory" | "ecliptic" | "armillary" | "beacon";

export const CAMERA_PRESETS: Record<
  Exclude<CameraPreset, "beacon">,
  { position: [number, number, number]; target: [number, number, number]; label: string }
> = {
  observatory: { position: [0, 0.42, 7.4], target: [0, 0, 0], label: "Observatory" },
  ecliptic: { position: [0, 0.02, 8.05], target: [0, 0, 0], label: "Ecliptic" },
  armillary: { position: [4.35, 2.45, 5.15], target: [0, 0.05, 0], label: "Armillary" },
};

export function applyCameraPreset(
  camera: THREE.PerspectiveCamera,
  controls: OrbitControls,
  preset: CameraPreset,
  reducedMotion: boolean,
  beaconPoint?: THREE.Vector3 | null,
) {
  const base = preset === "beacon" ? CAMERA_PRESETS.observatory : CAMERA_PRESETS[preset];
  const target = new THREE.Vector3(...base.target);
  const position = new THREE.Vector3(...base.position);
  if (preset === "beacon" && beaconPoint) {
    target.copy(beaconPoint).multiplyScalar(0.22);
    position.set(beaconPoint.x * 0.24, beaconPoint.y * 0.24 + 0.35, 7.15);
  }
  const duration = reducedMotion ? 0 : 0.75;
  gsap.to(camera.position, {
    x: position.x,
    y: position.y,
    z: position.z,
    duration,
    ease: "power3.inOut",
  });
  gsap.to(controls.target, {
    x: target.x,
    y: target.y,
    z: target.z,
    duration,
    ease: "power3.inOut",
    onUpdate: () => controls.update(),
  });
  if (duration === 0) controls.update();
}
