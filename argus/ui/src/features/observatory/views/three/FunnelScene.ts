/**
 * Pure Three.js funnel scene — no React dependency.
 *
 * Sets up camera, lighting, 7 translucent tier discs in a cone/funnel
 * arrangement, connecting wireframe lines, and orbit controls.
 *
 * Sprint 25, Session 6a.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { CSS2DRenderer } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import {
  FunnelSymbolManager,
  type FunnelSymbolManagerCallbacks,
  type SymbolTierData,
} from './FunnelSymbolManager';

/** Tier definition: name, vertical position, disc radius, color. */
interface TierDef {
  name: string;
  y: number;
  radius: number;
  color: number;
}

const TIER_DEFS: TierDef[] = [
  { name: 'Universe',      y: 6, radius: 5.0, color: 0x6b7b8d },
  { name: 'Viable',        y: 5, radius: 4.2, color: 0x7b8d9e },
  { name: 'Routed',        y: 4, radius: 3.4, color: 0xc9963a },
  { name: 'Evaluating',    y: 3, radius: 2.6, color: 0x8b6bb5 },
  { name: 'Near-trigger',  y: 2, radius: 1.8, color: 0xd4a03c },
  { name: 'Signal',        y: 1, radius: 1.0, color: 0x4caf50 },
  { name: 'Traded',        y: 0, radius: 0.4, color: 0x66bb6a },
];

const DISC_SEGMENTS = 64;
const DEFAULT_OPACITY = 0.2;
const HIGHLIGHT_OPACITY = 0.45;
const DIM_OPACITY = 0.1;
const EDGE_OPACITY = 0.35;
const CONNECTING_LINE_OPACITY = 0.12;

const DEFAULT_CAMERA_POS = new THREE.Vector3(0, 5, 12);
const DEFAULT_CAMERA_TARGET = new THREE.Vector3(0, 3, 0);

const ANIMATE_DURATION_MS = 600;

export class FunnelScene {
  readonly scene: THREE.Scene;
  readonly camera: THREE.PerspectiveCamera;
  readonly renderer: THREE.WebGLRenderer;
  readonly controls: OrbitControls;
  readonly symbolManager: FunnelSymbolManager;

  private readonly css2dRenderer: CSS2DRenderer;
  private readonly raycaster = new THREE.Raycaster();
  private readonly pointer = new THREE.Vector2();

  private readonly discMeshes: THREE.Mesh[] = [];
  private readonly edgeLines: THREE.LineLoop[] = [];
  private readonly connectingLines: THREE.Line[] = [];
  private readonly geometries: THREE.BufferGeometry[] = [];
  private readonly materials: THREE.Material[] = [];

  private lastTime = 0;
  private animationId: number | null = null;
  private cameraAnimation: {
    startPos: THREE.Vector3;
    endPos: THREE.Vector3;
    startTarget: THREE.Vector3;
    endTarget: THREE.Vector3;
    startTime: number;
    duration: number;
  } | null = null;

  private disposed = false;

  constructor(container: HTMLElement) {
    this.scene = new THREE.Scene();

    const width = container.clientWidth;
    const height = container.clientHeight;

    this.camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 100);
    this.camera.position.copy(DEFAULT_CAMERA_POS);
    this.camera.lookAt(DEFAULT_CAMERA_TARGET);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: true,
    });
    this.renderer.setSize(width, height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setClearColor(0x000000, 0);
    container.appendChild(this.renderer.domElement);

    this.setupLighting();
    this.createTierDiscs();
    this.createConnectingLines();

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 3;
    this.controls.maxDistance = 30;
    this.controls.target.copy(DEFAULT_CAMERA_TARGET);
    this.controls.update();

    // CSS2D renderer for ticker labels (overlays on top of WebGL canvas)
    this.css2dRenderer = new CSS2DRenderer();
    this.css2dRenderer.setSize(width, height);
    this.css2dRenderer.domElement.style.position = 'absolute';
    this.css2dRenderer.domElement.style.top = '0';
    this.css2dRenderer.domElement.style.left = '0';
    this.css2dRenderer.domElement.style.pointerEvents = 'none';
    container.style.position = 'relative';
    container.appendChild(this.css2dRenderer.domElement);

    // Symbol particle manager
    this.symbolManager = new FunnelSymbolManager();
    this.symbolManager.setCamera(this.camera);
    this.scene.add(this.symbolManager.instancedMesh);
    this.scene.add(this.symbolManager.getLabelGroup());

    this.lastTime = performance.now();
    this.animate();
  }

  /** Resize renderer and camera to match container. */
  resize(width: number, height: number): void {
    if (this.disposed) return;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
    this.css2dRenderer.setSize(width, height);
  }

  /** Animate camera back to default perspective position. */
  resetCamera(): void {
    this.startCameraAnimation(
      DEFAULT_CAMERA_POS.clone(),
      DEFAULT_CAMERA_TARGET.clone(),
    );
  }

  /** Adjust camera to fit entire funnel in view. */
  fitView(): void {
    const fitPos = new THREE.Vector3(0, 6, 16);
    const fitTarget = new THREE.Vector3(0, 3, 0);
    this.startCameraAnimation(fitPos, fitTarget);
  }

  /** Highlight a tier disc by index — brighten it, dim others. */
  highlightTier(tierIndex: number): void {
    for (let i = 0; i < this.discMeshes.length; i++) {
      const mat = this.discMeshes[i].material as THREE.MeshStandardMaterial;
      if (tierIndex < 0) {
        mat.opacity = DEFAULT_OPACITY;
      } else if (i === tierIndex) {
        mat.opacity = HIGHLIGHT_OPACITY;
      } else {
        mat.opacity = DIM_OPACITY;
      }
    }
  }

  /** Forward tier data to symbol manager. */
  updateSymbolTiers(data: Map<string, SymbolTierData>): void {
    this.symbolManager.updateSymbolTiers(data);
  }

  /** Set symbol manager event callbacks. */
  setSymbolCallbacks(callbacks: FunnelSymbolManagerCallbacks): void {
    this.symbolManager.setCallbacks(callbacks);
  }

  /** Raycast from screen coordinates against symbol particles. */
  raycastSymbols(clientX: number, clientY: number): void {
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    this.pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.pointer, this.camera);
    const intersections = this.raycaster.intersectObject(this.symbolManager.instancedMesh);
    this.symbolManager.handleMouseMove(intersections, clientX, clientY);
  }

  /** Forward click to symbol manager. */
  handleSymbolClick(): void {
    this.symbolManager.handleClick();
  }

  /** Number of tier disc meshes in the scene. */
  get tierCount(): number {
    return this.discMeshes.length;
  }

  /** Dispose all Three.js resources. */
  dispose(): void {
    if (this.disposed) return;
    this.disposed = true;

    if (this.animationId !== null) {
      cancelAnimationFrame(this.animationId);
      this.animationId = null;
    }

    this.controls.dispose();
    this.symbolManager.dispose();

    for (const geo of this.geometries) geo.dispose();
    for (const mat of this.materials) mat.dispose();

    this.scene.clear();
    this.renderer.dispose();

    if (this.renderer.domElement.parentElement) {
      this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
    }
    if (this.css2dRenderer.domElement.parentElement) {
      this.css2dRenderer.domElement.parentElement.removeChild(
        this.css2dRenderer.domElement,
      );
    }
  }

  // ── Private ──────────────────────────────────────────────

  private setupLighting(): void {
    const ambient = new THREE.AmbientLight(0xffffff, 0.6);
    this.scene.add(ambient);

    const directional = new THREE.DirectionalLight(0xffffff, 0.4);
    directional.position.set(4, 8, 4);
    this.scene.add(directional);
  }

  private createTierDiscs(): void {
    for (const tier of TIER_DEFS) {
      // Disc
      const discGeo = new THREE.CircleGeometry(tier.radius, DISC_SEGMENTS);
      const discMat = new THREE.MeshStandardMaterial({
        color: tier.color,
        transparent: true,
        opacity: DEFAULT_OPACITY,
        side: THREE.DoubleSide,
        roughness: 0.8,
        metalness: 0.1,
      });
      const disc = new THREE.Mesh(discGeo, discMat);
      disc.rotation.x = -Math.PI / 2;
      disc.position.y = tier.y;
      disc.userData = { tierName: tier.name };
      this.scene.add(disc);
      this.discMeshes.push(disc);
      this.geometries.push(discGeo);
      this.materials.push(discMat);

      // Edge ring
      const edgePoints: THREE.Vector3[] = [];
      for (let i = 0; i <= DISC_SEGMENTS; i++) {
        const angle = (i / DISC_SEGMENTS) * Math.PI * 2;
        edgePoints.push(new THREE.Vector3(
          Math.cos(angle) * tier.radius,
          tier.y,
          Math.sin(angle) * tier.radius,
        ));
      }
      const edgeGeo = new THREE.BufferGeometry().setFromPoints(edgePoints);
      const edgeMat = new THREE.LineBasicMaterial({
        color: tier.color,
        transparent: true,
        opacity: EDGE_OPACITY,
      });
      const edge = new THREE.LineLoop(edgeGeo, edgeMat);
      this.scene.add(edge);
      this.edgeLines.push(edge);
      this.geometries.push(edgeGeo);
      this.materials.push(edgeMat);
    }
  }

  private createConnectingLines(): void {
    const lineCount = 12;
    const lineMat = new THREE.LineBasicMaterial({
      color: 0x8899aa,
      transparent: true,
      opacity: CONNECTING_LINE_OPACITY,
    });
    this.materials.push(lineMat);

    for (let i = 0; i < lineCount; i++) {
      const angle = (i / lineCount) * Math.PI * 2;
      const points: THREE.Vector3[] = [];
      for (const tier of TIER_DEFS) {
        points.push(new THREE.Vector3(
          Math.cos(angle) * tier.radius,
          tier.y,
          Math.sin(angle) * tier.radius,
        ));
      }
      const geo = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geo, lineMat);
      this.scene.add(line);
      this.connectingLines.push(line);
      this.geometries.push(geo);
    }
  }

  private startCameraAnimation(endPos: THREE.Vector3, endTarget: THREE.Vector3): void {
    this.cameraAnimation = {
      startPos: this.camera.position.clone(),
      endPos,
      startTarget: this.controls.target.clone(),
      endTarget,
      startTime: performance.now(),
      duration: ANIMATE_DURATION_MS,
    };
  }

  private updateCameraAnimation(): void {
    if (!this.cameraAnimation) return;

    const elapsed = performance.now() - this.cameraAnimation.startTime;
    const t = Math.min(elapsed / this.cameraAnimation.duration, 1);
    // Ease-out cubic
    const ease = 1 - Math.pow(1 - t, 3);

    this.camera.position.lerpVectors(
      this.cameraAnimation.startPos,
      this.cameraAnimation.endPos,
      ease,
    );
    this.controls.target.lerpVectors(
      this.cameraAnimation.startTarget,
      this.cameraAnimation.endTarget,
      ease,
    );

    if (t >= 1) {
      this.cameraAnimation = null;
    }
  }

  private animate = (): void => {
    if (this.disposed) return;
    this.animationId = requestAnimationFrame(this.animate);

    const now = performance.now();
    const deltaTime = (now - this.lastTime) / 1000;
    this.lastTime = now;

    this.updateCameraAnimation();
    this.symbolManager.update(deltaTime);
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
    this.css2dRenderer.render(this.scene, this.camera);
  };
}
