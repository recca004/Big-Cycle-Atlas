/** Three.js Big Cycle scene — decorative instrument behind the fixed
 *  SVG stage ring. A slowly rotating wireframe globe plus gold orbital
 *  (armillary) rings. Economic positions live in the DOM overlay so
 *  they never rotate with the decoration.
 *
 *  Lifecycle: mount(container) → animate loop is lazy (starts on first
 *  IntersectionObserver hit), pauses offscreen / on hidden tab /
 *  reduced-motion. dispose() frees all GPU resources. */

import * as THREE from "three";
import { gsap } from "gsap";

export interface SceneOptions {
  /** 0..1 quality hint — scales DPR cap and tick density. */
  quality?: "high" | "low";
  reducedMotion?: boolean;
  onWebGLFailure?: (reason: string) => void;
}

const INK = 0x0e1420;
const GOLD = 0xc8a24a;
const GOLD_DIM = 0x8a7440;
const PARCHMENT = 0xf3ead8;

export class BigCycleScene {
  private renderer: THREE.WebGLRenderer | null = null;
  private scene = new THREE.Scene();
  private root = new THREE.Group();
  private camera: THREE.PerspectiveCamera;
  private globe: THREE.Group | null = null;
  private rings: THREE.Group[] = [];
  private raf = 0;
  private observer: IntersectionObserver | null = null;
  private container: HTMLElement | null = null;
  private opts: Required<SceneOptions>;
  private running = false;
  private speed = 1;
  private paused = false;
  private resizeObserver: ResizeObserver | null = null;
  private onVis = () => this.handleVisibility();
  private disposed = false;

  constructor(opts: SceneOptions = {}) {
    this.opts = {
      quality: opts.quality ?? "high",
      reducedMotion: opts.reducedMotion ?? false,
      onWebGLFailure: opts.onWebGLFailure ?? (() => {}),
    };
    this.camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
    this.camera.position.set(0, 0.4, 7.4);
  }

  mount(container: HTMLElement): boolean {
    this.container = container;
    try {
      this.renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: "low-power",
      });
    } catch {
      this.opts.onWebGLFailure("WebGL context creation failed");
      return false;
    }
    const dprCap = this.opts.quality === "low" ? 1 : 1.75;
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, dprCap));
    this.renderer.setClearColor(0x000000, 0);
    container.appendChild(this.renderer.domElement);
    this.renderer.domElement.setAttribute("aria-hidden", "true");

    // Scale the instrument so the outermost orbital ring sits just
    // inside the SVG dial's rim (238/300 of the frame half-height).
    this.root.scale.setScalar(0.66);
    this.scene.add(this.root);
    this.build();
    this.handleResize();
    this.resizeObserver = new ResizeObserver(() => this.handleResize());
    this.resizeObserver.observe(container);

    // Render once immediately, then run the loop only while visible.
    this.renderFrame();
    this.observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.some((e) => e.isIntersecting);
        this.setActive(visible && !document.hidden);
      },
      { threshold: 0.05 },
    );
    this.observer.observe(container);
    document.addEventListener("visibilitychange", this.onVis);
    this.renderer.domElement.addEventListener("webglcontextlost", (e) => {
      e.preventDefault();
      this.setActive(false);
      this.opts.onWebGLFailure("WebGL context lost");
    });
    return true;
  }

  private build() {
    const dark =
      typeof document !== "undefined" &&
      document.documentElement.dataset.theme !== "light";
    const line = dark ? GOLD : GOLD_DIM;
    const gridCol = dark ? 0x5a6b85 : 0x9a8b6b;

    // Wireframe globe — lat/long graticule, no textures.
    this.globe = new THREE.Group();
    const sphere = new THREE.SphereGeometry(1.62, 36, 24);
    const wire = new THREE.WireframeGeometry(sphere);
    const wireMat = new THREE.LineBasicMaterial({
      color: gridCol,
      transparent: true,
      opacity: dark ? 0.16 : 0.22,
    });
    this.globe.add(new THREE.LineSegments(wire, wireMat));
    // Faint inner glow sphere for depth.
    const inner = new THREE.Mesh(
      new THREE.SphereGeometry(1.55, 32, 24),
      new THREE.MeshBasicMaterial({
        color: dark ? INK : PARCHMENT,
        transparent: true,
        opacity: dark ? 0.5 : 0.35,
      }),
    );
    this.globe.add(inner);
    this.root.add(this.globe);

    // Armillary orbital rings — three tilted brass circles + tick ring.
    const ringSpecs = [
      { r: 2.25, tilt: Math.PI / 2, yaw: 0.0, opacity: 0.85 },
      { r: 2.45, tilt: Math.PI / 2.6, yaw: 0.5, opacity: 0.55 },
      { r: 2.65, tilt: Math.PI / 1.75, yaw: -0.4, opacity: 0.4 },
    ];
    for (const spec of ringSpecs) {
      const g = new THREE.Group();
      const circle = new THREE.Mesh(
        new THREE.TorusGeometry(spec.r, 0.006, 8, 128),
        new THREE.MeshBasicMaterial({
          color: line,
          transparent: true,
          opacity: spec.opacity,
        }),
      );
      g.add(circle);
      // Fine ticks around the outermost ring.
      if (spec.opacity >= 0.85) {
        const ticks = new THREE.Group();
        const tickGeo = new THREE.BoxGeometry(0.008, 0.05, 0.008);
        const tickMat = new THREE.MeshBasicMaterial({
          color: line,
          transparent: true,
          opacity: 0.6,
        });
        const n = this.opts.quality === "low" ? 48 : 96;
        for (let i = 0; i < n; i++) {
          const a = (i / n) * Math.PI * 2;
          const t = new THREE.Mesh(tickGeo, tickMat);
          t.position.set(
            Math.cos(a) * spec.r,
            Math.sin(a) * spec.r,
            0,
          );
          t.rotation.z = a;
          ticks.add(t);
        }
        g.add(ticks);
      }
      g.rotation.set(spec.tilt - Math.PI / 2, spec.yaw, 0);
      g.userData.spin = 0.02 + spec.r * 0.008;
      this.rings.push(g);
      this.root.add(g);
    }

    // Entrance animation — rings scale in, globe fades up.
    if (!this.opts.reducedMotion) {
      for (const [i, r] of this.rings.entries()) {
        gsap.from(r.scale, {
          x: 0.6,
          y: 0.6,
          z: 0.6,
          duration: 1.1,
          delay: 0.15 * i,
          ease: "power3.out",
        });
        gsap.from(r.rotation, {
          y: r.rotation.y - 0.6,
          duration: 1.2,
          delay: 0.15 * i,
          ease: "power2.out",
        });
      }
      if (this.globe) {
        gsap.from(this.globe.rotation, {
          y: -0.9,
          duration: 1.6,
          ease: "power2.out",
        });
      }
    }
  }

  private handleResize() {
    if (!this.renderer || !this.container) return;
    const w = this.container.clientWidth || 1;
    const h = this.container.clientHeight || 1;
    this.camera.aspect = w / h;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
    this.renderFrame();
  }

  private handleVisibility() {
    const visible = this.container
      ? this.observer !== null && !document.hidden
      : false;
    // IntersectionObserver will re-fire on its own; here only tab-state.
    this.setActive(visible && this.lastIntersecting);
  }

  private lastIntersecting = true;

  private setActive(active: boolean) {
    if (active) {
      this.lastIntersecting = true;
      this.start();
    } else {
      this.lastIntersecting = false;
      this.stop();
    }
  }

  private start() {
    if (this.running || this.disposed) return;
    this.running = true;
    const loop = (t: number) => {
      if (!this.running) return;
      this.raf = requestAnimationFrame(loop);
      if (this.paused || this.opts.reducedMotion) {
        // Still render occasionally? No — static frame suffices.
        return;
      }
      const dt = Math.min(0.05, t * 0); // frame-agnostic: use fixed step
      void dt;
      const step = 0.0016 * this.speed;
      if (this.globe) this.globe.rotation.y += step;
      for (const r of this.rings) {
        r.rotation.z += (r.userData.spin as number) * 0.016 * this.speed;
      }
      this.renderFrame();
    };
    this.raf = requestAnimationFrame(loop);
  }

  private stop() {
    this.running = false;
    if (this.raf) cancelAnimationFrame(this.raf);
    this.raf = 0;
  }

  private renderFrame() {
    if (this.renderer) this.renderer.render(this.scene, this.camera);
  }

  /** Pause/resume the decorative motion (globe + rings). */
  setPaused(paused: boolean) {
    this.paused = paused;
    if (!paused) this.renderFrame();
  }

  setSpeed(speed: number) {
    this.speed = Math.max(0.1, Math.min(4, speed));
  }

  /** Smooth camera return to home position. */
  resetCamera() {
    gsap.to(this.camera.position, {
      x: 0,
      y: 0.4,
      z: 7.4,
      duration: this.opts.reducedMotion ? 0 : 0.8,
      ease: "power2.inOut",
      onUpdate: () => this.renderFrame(),
    });
  }

  /** Subtle camera nudge toward a clock-hour direction — selection focus. */
  focusHour(hour: number) {
    const rad = ((hour * 30 - 90) * Math.PI) / 180;
    gsap.to(this.camera.position, {
      x: Math.cos(rad) * 0.55,
      y: Math.sin(rad) * 0.55 + 0.4,
      z: 7.2,
      duration: this.opts.reducedMotion ? 0 : 0.9,
      ease: "power3.inOut",
      onUpdate: () => this.renderFrame(),
    });
  }

  /** Re-tint materials on theme switch. */
  applyTheme() {
    if (this.disposed) return;
    // Rebuild is simplest and cheap (few dozen objects).
    for (const r of this.rings) this.root.remove(r);
    if (this.globe) this.root.remove(this.globe);
    this.rings = [];
    this.globe = null;
    this.build();
    this.renderFrame();
  }

  dispose() {
    this.disposed = true;
    this.stop();
    this.observer?.disconnect();
    this.resizeObserver?.disconnect();
    document.removeEventListener("visibilitychange", this.onVis);
    this.scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (mesh.geometry) mesh.geometry.dispose();
      const mat = mesh.material as THREE.Material | THREE.Material[];
      if (Array.isArray(mat)) mat.forEach((m) => m.dispose());
      else mat?.dispose?.();
    });
    this.renderer?.dispose();
    this.renderer?.domElement.remove();
    this.renderer = null;
    this.container = null;
  }
}
