/** Interactive country beacon module — raycastable markers fixed to the
 *  same stage-anchor geometry as the SVG dial. */
import * as THREE from "three";
import { layoutMarkers, hourToRad } from "../stages";

export interface BeaconDatum {
  iso3: string;
  name: string;
  stage: string | null;
  score: number | null;
  momentum: number | null;
  period: string | null;
}

interface BeaconEntry {
  root: THREE.Group;
  core: THREE.Mesh;
  halo: THREE.Mesh;
  baseScale: number;
  pulse: number;
}

const CORE_DARK = 0xd7b45f;
const CORE_LIGHT = 0x8a6c22;
const RISE = 0x7bc496;
const FALL = 0xd08a7c;

export class CountryBeacons {
  readonly group = new THREE.Group();
  private entries = new Map<string, BeaconEntry>();
  private hitTargets: THREE.Object3D[] = [];
  private selected: string | null = null;
  private hovered: string | null = null;
  private dark = true;

  constructor() {
    this.group.name = "country-beacons";
  }

  setCountries(countries: BeaconDatum[]) {
    this.clear();
    const valid = countries.filter((country) => country.stage);
    const layouts = new Map(
      layoutMarkers(valid.map((c) => ({ iso3: c.iso3, stage: c.stage }))).map((l) => [l.iso3, l]),
    );
    for (const country of valid) {
      const layout = layouts.get(country.iso3);
      if (!layout) continue;
      const radius = 2.52 - layout.ringIndex * 0.335;
      const angle = hourToRad(layout.hour);
      const root = new THREE.Group();
      root.position.set(Math.cos(angle) * radius, -Math.sin(angle) * radius, 0.09);
      root.userData.iso3 = country.iso3;

      const rising = (country.momentum ?? 0) >= 0;
      const coreMat = new THREE.MeshStandardMaterial({
        color: this.dark ? CORE_DARK : CORE_LIGHT,
        emissive: rising ? RISE : FALL,
        emissiveIntensity: 0.18,
        metalness: 0.35,
        roughness: 0.3,
      });
      const core = new THREE.Mesh(new THREE.SphereGeometry(0.085, 20, 14), coreMat);
      core.userData.iso3 = country.iso3;
      root.add(core);

      const haloMat = new THREE.MeshBasicMaterial({
        color: this.dark ? CORE_DARK : CORE_LIGHT,
        transparent: true,
        opacity: 0.24,
        depthWrite: false,
      });
      const halo = new THREE.Mesh(new THREE.TorusGeometry(0.145, 0.009, 8, 40), haloMat);
      halo.userData.iso3 = country.iso3;
      root.add(halo);

      const hit = new THREE.Mesh(
        new THREE.SphereGeometry(0.22, 10, 8),
        new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
      );
      hit.userData.iso3 = country.iso3;
      root.add(hit);

      this.group.add(root);
      this.entries.set(country.iso3, {
        root,
        core,
        halo,
        baseScale: 1,
        pulse: (country.iso3.charCodeAt(0) + country.iso3.charCodeAt(2)) * 0.37,
      });
      this.hitTargets.push(hit, core, halo);
    }
    this.applySelection();
  }

  pick(raycaster: THREE.Raycaster): string | null {
    const hit = raycaster.intersectObjects(this.hitTargets, false)[0];
    return (hit?.object.userData.iso3 as string | undefined) ?? null;
  }

  setHovered(iso3: string | null) {
    this.hovered = iso3;
    this.applySelection();
  }

  setSelected(iso3: string | null) {
    this.selected = iso3;
    this.applySelection();
  }

  beaconPoint(iso3: string | null): THREE.Vector3 | null {
    if (!iso3) return null;
    return this.entries.get(iso3)?.root.position.clone() ?? null;
  }

  private applySelection() {
    for (const [iso3, entry] of this.entries) {
      const active = iso3 === this.selected;
      const hovered = iso3 === this.hovered;
      entry.baseScale = active ? 1.55 : hovered ? 1.28 : 1;
      const haloMat = entry.halo.material as THREE.MeshBasicMaterial;
      haloMat.opacity = active ? 0.62 : hovered ? 0.42 : 0.24;
      const coreMat = entry.core.material as THREE.MeshStandardMaterial;
      coreMat.emissiveIntensity = active ? 0.46 : hovered ? 0.3 : 0.18;
    }
  }

  update(dt: number, elapsed: number, reducedMotion: boolean, paused: boolean) {
    for (const entry of this.entries.values()) {
      const pulse = reducedMotion || paused ? 0 : Math.sin(elapsed * 2.1 + entry.pulse) * 0.055;
      const target = entry.baseScale + pulse;
      entry.root.scale.setScalar(THREE.MathUtils.damp(entry.root.scale.x, target, 10, dt));
      entry.halo.rotation.z += reducedMotion || paused ? 0 : dt * 0.45;
    }
  }

  setTheme(dark: boolean) {
    this.dark = dark;
    for (const entry of this.entries.values()) {
      (entry.core.material as THREE.MeshStandardMaterial).color.setHex(dark ? CORE_DARK : CORE_LIGHT);
      (entry.halo.material as THREE.MeshBasicMaterial).color.setHex(dark ? CORE_DARK : CORE_LIGHT);
    }
  }

  clear() {
    for (const child of [...this.group.children]) {
      child.traverse((node) => {
        const mesh = node as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(material)) material.forEach((m) => m.dispose());
        else material?.dispose?.();
      });
      this.group.remove(child);
    }
    this.entries.clear();
    this.hitTargets = [];
  }
}
