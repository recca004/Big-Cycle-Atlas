/** Fixed ecliptic ring module — always coplanar with the SVG dial. */
import * as THREE from "three";
import { hourToRad } from "../stages";

export const ECLIPTIC_RADIUS = 3.06;

export interface EclipticRig {
  group: THREE.Group;
  setTheme: (dark: boolean) => void;
}

export function createEcliptic(quality: "high" | "low" = "high"): EclipticRig {
  const group = new THREE.Group();
  group.name = "fixed-ecliptic";
  const brass = new THREE.MeshStandardMaterial({ color: 0xc8a24a, metalness: 0.7, roughness: 0.24, transparent: true, opacity: 0.82 });
  const dim = new THREE.MeshBasicMaterial({ color: 0x8a7440, transparent: true, opacity: 0.46 });

  group.add(new THREE.Mesh(new THREE.TorusGeometry(ECLIPTIC_RADIUS, 0.012, 8, quality === "low" ? 144 : 224), brass));
  group.add(new THREE.Mesh(new THREE.TorusGeometry(ECLIPTIC_RADIUS - 0.42, 0.006, 8, 192), dim));

  const tickCount = quality === "low" ? 48 : 96;
  const majorGeo = new THREE.BoxGeometry(0.014, 0.13, 0.012);
  const minorGeo = new THREE.BoxGeometry(0.009, 0.07, 0.009);
  for (let i = 0; i < tickCount; i++) {
    const hour = i / 8;
    const major = i % 8 === 0;
    const a = hourToRad(hour);
    const tick = new THREE.Mesh(major ? majorGeo : minorGeo, dim);
    const r = ECLIPTIC_RADIUS - (major ? 0.045 : 0.02);
    tick.position.set(Math.cos(a) * r, -Math.sin(a) * r, 0.012);
    tick.rotation.z = a;
    group.add(tick);
  }



  return {
    group,
    setTheme(dark) {
      brass.color.setHex(dark ? 0xc8a24a : 0x8a6c22);
      dim.color.setHex(dark ? 0x8a7440 : 0x8f8061);
      dim.opacity = dark ? 0.46 : 0.55;
    },
  };
}
