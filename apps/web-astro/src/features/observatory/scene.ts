/** Three.js Big Cycle scene — modular instrument behind the fixed SVG
 *  stage ring. Modules: fixed ecliptic, rotating armillary globe and
 *  raycastable country beacons. Economic positions are never rotated with
 *  the globe and never imply predictions. */

import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { gsap } from "gsap";
import { createArmillary, type ArmillaryRig } from "./scene/armillary";
import { createEcliptic, type EclipticRig } from "./scene/ecliptic";
import { CountryBeacons, type BeaconDatum } from "./scene/beacons";
import { applyCameraPreset, type CameraPreset } from "./scene/camera";

export interface SceneOptions {
  quality?: "high" | "low";
  reducedMotion?: boolean;
  onWebGLFailure?: (reason: string) => void;
  onSelect?: (iso3: string) => void;
}

export class BigCycleScene {
  private renderer: THREE.WebGLRenderer | null = null;
  private scene = new THREE.Scene();
  private dialScene = new THREE.Scene();
  private root = new THREE.Group();
  private dialRoot = new THREE.Group();
  private camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
  private dialCamera = new THREE.OrthographicCamera(-3.2, 3.2, 3, -3, 0.1, 20);
  private controls: OrbitControls | null = null;
  private timer = new THREE.Timer();
  private observer: IntersectionObserver | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private container: HTMLElement | null = null;
  private opts: Required<Omit<SceneOptions, "onSelect">> & { onSelect?: (iso3: string) => void };
  private armillary: ArmillaryRig | null = null;
  private ecliptic: EclipticRig | null = null;
  private beacons = new CountryBeacons();
  private raycaster = new THREE.Raycaster();
  private pointer = new THREE.Vector2();
  private visible = false;
  private running = false;
  private speed = 1;
  private paused = false;
  private reducedMotion: boolean;
  private disposed = false;
  private downAt: { x: number; y: number } | null = null;
  private onVis = () => this.handleVisibility();

  constructor(opts: SceneOptions = {}) {
    this.opts = {
      quality: opts.quality ?? "high",
      reducedMotion: opts.reducedMotion ?? false,
      onWebGLFailure: opts.onWebGLFailure ?? (() => {}),
      onSelect: opts.onSelect ?? (() => {}),
    };
    this.reducedMotion = this.opts.reducedMotion;
    this.camera.position.set(0, 0.42, 7.4);
    this.dialCamera.position.set(0, 0, 7);
  }

  mount(container: HTMLElement): boolean {
    this.container = container;
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
    } catch {
      this.opts.onWebGLFailure("WebGL context creation failed");
      return false;
    }
    const canvas = this.renderer.domElement;
    const dprCap = this.opts.quality === "low" ? 1 : 1.75;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, dprCap));
    this.renderer.setClearColor(0x000000, 0);
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.05;
    this.renderer.autoClear = false;
    canvas.setAttribute("role", "img");
    canvas.setAttribute(
      "aria-label",
      "Decorative rotating armillary globe behind a fixed Big Cycle clock. Country positions are available as keyboard-accessible markers in the dial overlay.",
    );
    container.appendChild(canvas);

    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.07;
    this.controls.enablePan = false;
    this.controls.minDistance = 5.2;
    this.controls.maxDistance = 10.5;
    this.controls.minPolarAngle = Math.PI * 0.22;
    this.controls.maxPolarAngle = Math.PI * 0.78;
    this.controls.target.set(0, 0, 0);

    this.root.scale.setScalar(0.66);
    this.scene.add(this.root);
    this.build();

    canvas.addEventListener("pointermove", this.handlePointerMove);
    canvas.addEventListener("pointerdown", this.handlePointerDown);
    canvas.addEventListener("pointerup", this.handlePointerUp);
    canvas.addEventListener("pointerleave", this.handlePointerLeave);
    canvas.addEventListener("webglcontextlost", this.handleContextLost);

    this.handleResize();
    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(container);
    this.observer = new IntersectionObserver(
      (entries) => {
        this.visible = entries.some((entry) => entry.isIntersecting);
        this.handleVisibility();
      },
      { threshold: 0.05 },
    );
    this.observer.observe(container);
    document.addEventListener("visibilitychange", this.onVis);
    this.timer.connect(document);
    this.renderFrame();
    return true;
  }

  private build() {
    const dark = document.documentElement.dataset.theme !== "light";
    this.scene.add(new THREE.HemisphereLight(0xf8ead0, 0x172033, 1.8));
    const key = new THREE.DirectionalLight(0xffe2a8, 2.4);
    key.position.set(4, 5, 6);
    this.scene.add(key);

    this.armillary = createArmillary(this.opts.quality);
    this.ecliptic = createEcliptic(this.opts.quality);
    this.armillary.setTheme(dark);
    this.ecliptic.setTheme(dark);
    this.beacons.setTheme(dark);
    this.root.add(this.armillary.group);
    this.scene.add(this.createStarfield());

    // The economically meaningful ecliptic and beacons live in a separate
    // orthographic scene. Camera presets can explore the armillary globe
    // without ever rotating or displacing cycle positions.
    this.dialScene.add(new THREE.HemisphereLight(0xf8ead0, 0x172033, 1.8));
    const dialKey = new THREE.DirectionalLight(0xffe2a8, 2.1);
    dialKey.position.set(3, 4, 6);
    this.dialScene.add(dialKey);
    this.dialRoot.scale.setScalar(2.38 / 3.06);
    this.dialRoot.add(this.ecliptic.group);
    this.dialRoot.add(this.beacons.group);
    this.dialScene.add(this.dialRoot);

    if (!this.reducedMotion) {
      gsap.from(this.root.scale, { x: 0.48, y: 0.48, z: 0.48, duration: 1.1, ease: "power3.out" });
      gsap.from(this.root.rotation, { y: -0.35, duration: 1.35, ease: "power2.out" });
    }
  }

  private createStarfield() {
    const count = this.opts.quality === "low" ? 120 : 260;
    const positions = new Float32Array(count * 3);
    let seed = 1848;
    const random = () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return seed / 4294967296;
    };
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (random() - 0.5) * 18;
      positions[i * 3 + 1] = (random() - 0.5) * 11;
      positions[i * 3 + 2] = -3 - random() * 7;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    const dark = document.documentElement.dataset.theme !== "light";
    const material = new THREE.PointsMaterial({ color: dark ? 0xb9c5dc : 0x6f6652, size: 0.018, transparent: true, opacity: dark ? 0.55 : 0.35, depthWrite: false });
    const points = new THREE.Points(geometry, material);
    points.name = "observatory-starfield";
    return points;
  }

  private handleResize() {
    if (!this.renderer || !this.container) return;
    const width = this.container.clientWidth || 1;
    const height = this.container.clientHeight || 1;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
    this.renderFrame();
  }

  private handleVisibility() {
    this.setActive(this.visible && !document.hidden);
  }

  private setActive(active: boolean) {
    if (!this.renderer || this.disposed) return;
    if (active === this.running) return;
    this.running = active;
    if (active) {
      this.timer.reset();
      this.renderer.setAnimationLoop(this.animate);
    } else {
      this.renderer.setAnimationLoop(null);
      this.renderFrame();
    }
  }

  private animate = (time?: number) => {
    if (!this.renderer || this.disposed) return;
    this.timer.update(time);
    const dt = Math.min(this.timer.getDelta(), 0.08);
    const elapsed = this.timer.getElapsed();
    const moving = !this.paused && !this.reducedMotion;
    if (moving) {
      this.armillary?.update(dt, this.speed);
    }
    this.beacons.update(dt, elapsed, this.reducedMotion, this.paused);
    this.controls?.update();
    this.renderFrame();
  };

  private renderFrame() {
    if (!this.renderer) return;
    this.renderer.clear(true, true, true);
    this.renderer.render(this.scene, this.camera);
    this.renderer.clearDepth();
    this.renderer.render(this.dialScene, this.dialCamera);
  }

  private updatePointer(event: PointerEvent) {
    const canvas = this.renderer?.domElement;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    this.pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
    this.raycaster.setFromCamera(this.pointer, this.dialCamera);
  }

  private handlePointerMove = (event: PointerEvent) => {
    this.updatePointer(event);
    const iso3 = this.beacons.pick(this.raycaster);
    this.beacons.setHovered(iso3);
    if (this.renderer) this.renderer.domElement.style.cursor = iso3 ? "pointer" : "grab";
  };

  private handlePointerDown = (event: PointerEvent) => {
    this.downAt = { x: event.clientX, y: event.clientY };
  };

  private handlePointerUp = (event: PointerEvent) => {
    const down = this.downAt;
    this.downAt = null;
    if (down && Math.hypot(event.clientX - down.x, event.clientY - down.y) > 7) return;
    this.updatePointer(event);
    const iso3 = this.beacons.pick(this.raycaster);
    if (iso3) this.opts.onSelect?.(iso3);
  };

  private handlePointerLeave = () => {
    this.beacons.setHovered(null);
    if (this.renderer) this.renderer.domElement.style.cursor = "grab";
  };

  private handleContextLost = (event: Event) => {
    event.preventDefault();
    this.setActive(false);
    this.opts.onWebGLFailure("WebGL context lost");
  };

  setPaused(paused: boolean) {
    this.paused = paused;
    this.renderFrame();
  }

  setSpeed(speed: number) {
    this.speed = Math.max(0.1, Math.min(4, speed));
  }

  setReducedMotion(reduced: boolean) {
    this.reducedMotion = reduced;
    this.renderFrame();
  }

  updateCountries(countries: BeaconDatum[]) {
    this.beacons.setCountries(countries);
    this.renderFrame();
  }

  setSelectedIso3(iso3: string | null) {
    this.beacons.setSelected(iso3);
    this.renderFrame();
  }

  setCameraPreset(preset: CameraPreset) {
    if (!this.controls) return;
    applyCameraPreset(this.camera, this.controls, preset, this.reducedMotion, null);
  }

  focusBeacon(iso3: string | null) {
    if (!this.controls) return;
    applyCameraPreset(this.camera, this.controls, "beacon", this.reducedMotion, this.beacons.beaconPoint(iso3));
  }

  resetCamera() {
    this.setCameraPreset("observatory");
  }

  /** Backwards-compatible selection nudge used by legacy callers. */
  focusHour(hour: number) {
    const angle = ((hour * 30 - 90) * Math.PI) / 180;
    if (!this.controls) return;
    gsap.to(this.camera.position, {
      x: Math.cos(angle) * 0.55,
      y: Math.sin(angle) * 0.55 + 0.42,
      z: 7.25,
      duration: this.reducedMotion ? 0 : 0.75,
      ease: "power3.inOut",
    });
  }

  applyTheme() {
    const dark = document.documentElement.dataset.theme !== "light";
    this.armillary?.setTheme(dark);
    this.ecliptic?.setTheme(dark);
    this.beacons.setTheme(dark);
    this.renderFrame();
  }

  dispose() {
    this.disposed = true;
    this.renderer?.setAnimationLoop(null);
    this.observer?.disconnect();
    this.resizeObserver?.disconnect();
    document.removeEventListener("visibilitychange", this.onVis);
    this.timer.dispose();
    const canvas = this.renderer?.domElement;
    canvas?.removeEventListener("pointermove", this.handlePointerMove);
    canvas?.removeEventListener("pointerdown", this.handlePointerDown);
    canvas?.removeEventListener("pointerup", this.handlePointerUp);
    canvas?.removeEventListener("pointerleave", this.handlePointerLeave);
    canvas?.removeEventListener("webglcontextlost", this.handleContextLost);
    gsap.killTweensOf(this.camera.position);
    if (this.controls) gsap.killTweensOf(this.controls.target);
    this.controls?.dispose();
    this.beacons.clear();
    for (const targetScene of [this.scene, this.dialScene]) {
      targetScene.traverse((object) => {
        const mesh = object as THREE.Mesh;
        mesh.geometry?.dispose?.();
        const material = mesh.material as THREE.Material | THREE.Material[] | undefined;
        if (Array.isArray(material)) material.forEach((m) => m.dispose());
        else material?.dispose?.();
      });
    }
    this.renderer?.dispose();
    canvas?.remove();
    this.renderer = null;
    this.container = null;
  }
}
