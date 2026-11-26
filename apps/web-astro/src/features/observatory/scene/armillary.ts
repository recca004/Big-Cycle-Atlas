/** Armillary globe module — graticule sphere plus nested brass rings.
 *  Decorative instrument motion only; economic meaning stays on the fixed dial. */
import * as THREE from "three";

export interface ArmillaryRig {
  group: THREE.Group;
  update: (dt: number, speed: number) => void;
  setTheme: (dark: boolean) => void;
}

const GOLD_DARK = 0xc8a24a;
const GOLD_LIGHT = 0x8a6c22;

function loop(points: THREE.Vector3[], material: THREE.Material) {
  return new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(points), material);
}

export function createArmillary(quality: "high" | "low" = "high"): ArmillaryRig {
  const group = new THREE.Group();
  group.name = "armillary-globe";
  const radius = 1.58;
  const segments = quality === "low" ? 48 : 96;

  const gridMat = new THREE.LineBasicMaterial({ color: 0x71839f, transparent: true, opacity: 0.22 });
  const ringMat = new THREE.MeshStandardMaterial({ color: GOLD_DARK, metalness: 0.65, roughness: 0.28, transparent: true, opacity: 0.86 });
  const tickMat = new THREE.MeshBasicMaterial({ color: GOLD_DARK, transparent: true, opacity: 0.62 });
  const innerMat = new THREE.MeshBasicMaterial({ color: 0x0e1420, transparent: true, opacity: 0.46 });

  const globe = new THREE.Group();
  globe.name = "wireframe-globe";
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(radius * 0.975, 32, 20), innerMat));

  for (const lat of [-60, -40, -20, 0, 20, 40, 60]) {
    const phi = (lat * Math.PI) / 180;
    const r = Math.cos(phi) * radius;
    const y = Math.sin(phi) * radius;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i < segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a) * r, y, Math.sin(a) * r));
    }
    globe.add(loop(pts, gridMat));
  }
  const meridians = quality === "low" ? 8 : 12;
  for (let m = 0; m < meridians; m++) {
    const yaw = (m / meridians) * Math.PI;
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i < segments; i++) {
      const a = (i / segments) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.sin(a) * radius * Math.cos(yaw), Math.cos(a) * radius, Math.sin(a) * radius * Math.sin(yaw)));
    }
    globe.add(loop(pts, gridMat));
  }
  group.add(globe);

  const spinners: { node: THREE.Object3D; speed: number }[] = [{ node: globe, speed: 0.09 }];
  const specs = [
    { radius: 1.92, rotation: new THREE.Euler(Math.PI / 2, 0, 0), speed: 0.05, ticks: false },
    { radius: 2.16, rotation: new THREE.Euler(Math.PI / 2.55, 0.42, 0.12), speed: -0.035, ticks: false },
    { radius: 2.38, rotation: new THREE.Euler(Math.PI / 1.72, -0.34, -0.08), speed: 0.024, ticks: true },
  ];
  for (const spec of specs) {
    const holder = new THREE.Group();
    holder.rotation.copy(spec.rotation);
    const spinner = new THREE.Group();
    spinner.add(new THREE.Mesh(new THREE.TorusGeometry(spec.radius, 0.008, 8, quality === "low" ? 96 : 160), ringMat));
    if (spec.ticks) {
      const count = quality === "low" ? 48 : 96;
      const geo = new THREE.BoxGeometry(0.012, 0.052, 0.012);
      for (let i = 0; i < count; i++) {
        const a = (i / count) * Math.PI * 2;
        const tick = new THREE.Mesh(geo, tickMat);
        tick.position.set(Math.cos(a) * spec.radius, Math.sin(a) * spec.radius, 0);
        tick.rotation.z = a;
        spinner.add(tick);
      }
    }
    holder.add(spinner);
    group.add(holder);
    spinners.push({ node: spinner, speed: spec.speed });
  }

  return {
    group,
    update(dt, speed) {
      for (const item of spinners) item.node.rotation.z += item.speed * dt * speed;
      globe.rotation.y += 0.055 * dt * speed;
    },
    setTheme(dark) {
      ringMat.color.setHex(dark ? GOLD_DARK : GOLD_LIGHT);
      tickMat.color.setHex(dark ? GOLD_DARK : GOLD_LIGHT);
      gridMat.color.setHex(dark ? 0x71839f : 0x8a7a5e);
      gridMat.opacity = dark ? 0.22 : 0.44;
      innerMat.color.setHex(dark ? 0x0e1420 : 0xf3ead8);
      innerMat.opacity = dark ? 0.46 : 0.16;
    },
  };
}
