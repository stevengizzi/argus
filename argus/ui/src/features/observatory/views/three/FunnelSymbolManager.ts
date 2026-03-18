/**
 * Manages symbol particles on the funnel tier discs using InstancedMesh.
 *
 * Each symbol is a small sphere positioned on its tier disc. Supports:
 * - Instanced rendering for 5,000+ symbols at 60fps
 * - Tier transition animations (0.5s lerp)
 * - Raycasting for hover/click interaction
 * - LOD ticker labels via CSS2DObject (max 50 visible)
 * - Selected symbol highlighting (amber/gold, 2× scale)
 *
 * Sprint 25, Session 6b.
 */

import * as THREE from 'three';
import { CSS2DObject } from 'three/examples/jsm/renderers/CSS2DRenderer.js';
import { TIER_DEFS } from './constants';

/** Tier name → index lookup. */
const TIER_NAME_TO_INDEX: Record<string, number> = {
  universe: 0,
  viable: 1,
  routed: 2,
  evaluating: 3,
  near_trigger: 4,
  'near-trigger': 4,
  signal: 5,
  traded: 6,
};

/** Saturated versions of tier colors for particles (brighter than disc). */
const TIER_PARTICLE_COLORS: THREE.Color[] = [
  new THREE.Color(0x8b9baf),
  new THREE.Color(0x9badbe),
  new THREE.Color(0xe0aa44),
  new THREE.Color(0xa07fd0),
  new THREE.Color(0xeab44a),
  new THREE.Color(0x5cc960),
  new THREE.Color(0x7dd07f),
];

const SELECTED_COLOR = new THREE.Color(0xffc107); // amber/gold
const MAX_INSTANCES = 5000;
const SPHERE_RADIUS = 0.04;
const SPHERE_SEGMENTS = 8;
const TRANSITION_DURATION = 0.5; // seconds
const LOD_DISTANCE_THRESHOLD = 5;
const MAX_VISIBLE_LABELS = 50;
const BASE_SCALE = 1.0;
const HOVER_SCALE = 1.5;
const SELECTED_SCALE = 2.0;

interface SymbolState {
  tierIndex: number;
  position: THREE.Vector3;
  targetPosition: THREE.Vector3;
  instanceIndex: number;
  transitioning: boolean;
  transitionElapsed: number;
  label: CSS2DObject | null;
}

export interface SymbolTierData {
  tier: string;
  conditionsPassed: number;
}

export interface FunnelSymbolManagerCallbacks {
  onHoverSymbol: (symbol: string | null, screenX: number, screenY: number) => void;
  onSelectSymbol: (symbol: string) => void;
}

export class FunnelSymbolManager {
  readonly instancedMesh: THREE.InstancedMesh;

  private readonly geometry: THREE.SphereGeometry;
  private readonly material: THREE.MeshStandardMaterial;
  private readonly symbolMap = new Map<string, SymbolState>();
  private readonly indexToSymbol = new Map<number, string>();
  private readonly labels: CSS2DObject[] = [];
  private readonly labelGroup: THREE.Group;

  private nextInstanceIndex = 0;
  private selectedSymbol: string | null = null;
  private hoveredSymbol: string | null = null;
  private callbacks: FunnelSymbolManagerCallbacks | null = null;
  private camera: THREE.PerspectiveCamera | null = null;

  // Reusable objects to avoid per-frame allocation
  private readonly tempMatrix = new THREE.Matrix4();
  private readonly tempColor = new THREE.Color();
  private readonly tempVec = new THREE.Vector3();

  constructor() {
    this.geometry = new THREE.SphereGeometry(SPHERE_RADIUS, SPHERE_SEGMENTS, SPHERE_SEGMENTS);
    this.material = new THREE.MeshStandardMaterial({
      roughness: 0.4,
      metalness: 0.2,
    });

    this.instancedMesh = new THREE.InstancedMesh(this.geometry, this.material, MAX_INSTANCES);
    this.instancedMesh.count = 0;
    this.instancedMesh.frustumCulled = false;

    this.labelGroup = new THREE.Group();
    this.labelGroup.name = 'symbol-labels';
  }

  /** Scene group containing CSS2D labels. Add to scene after instanced mesh. */
  getLabelGroup(): THREE.Group {
    return this.labelGroup;
  }

  /** Set camera reference for LOD distance checks. */
  setCamera(camera: THREE.PerspectiveCamera): void {
    this.camera = camera;
  }

  /** Set event callbacks. */
  setCallbacks(callbacks: FunnelSymbolManagerCallbacks): void {
    this.callbacks = callbacks;
  }

  /**
   * Update symbol positions and colors based on tier assignments.
   *
   * Called when WS pipeline data arrives. Symbols not in the new data
   * are removed; new symbols get fresh instance slots.
   */
  updateSymbolTiers(tierData: Map<string, SymbolTierData>): void {
    const seenSymbols = new Set<string>();

    for (const [symbol, data] of tierData) {
      seenSymbols.add(symbol);
      const tierIndex = TIER_NAME_TO_INDEX[data.tier] ?? 0;

      const existing = this.symbolMap.get(symbol);
      if (existing) {
        if (existing.tierIndex !== tierIndex) {
          // Tier changed — start transition animation
          const newTarget = this.computePositionOnDisc(tierIndex);
          existing.targetPosition.copy(newTarget);
          existing.transitioning = true;
          existing.transitionElapsed = 0;
          existing.tierIndex = tierIndex;
        }
      } else {
        // New symbol — allocate instance
        const instanceIndex = this.nextInstanceIndex++;
        if (instanceIndex >= MAX_INSTANCES) continue;

        const position = this.computePositionOnDisc(tierIndex);
        this.symbolMap.set(symbol, {
          tierIndex,
          position: position.clone(),
          targetPosition: position.clone(),
          instanceIndex,
          transitioning: false,
          transitionElapsed: 0,
          label: null,
        });
        this.indexToSymbol.set(instanceIndex, symbol);

        // Set initial transform
        this.setInstanceTransform(instanceIndex, position, BASE_SCALE);
        this.setInstanceColor(instanceIndex, tierIndex);
      }
    }

    // Remove symbols no longer in data
    for (const [symbol, state] of this.symbolMap) {
      if (!seenSymbols.has(symbol)) {
        this.removeLabel(state);
        this.indexToSymbol.delete(state.instanceIndex);
        this.symbolMap.delete(symbol);
      }
    }

    this.instancedMesh.count = Math.min(this.nextInstanceIndex, MAX_INSTANCES);
    this.instancedMesh.instanceMatrix.needsUpdate = true;
    this.instancedMesh.instanceColor!.needsUpdate = true;
  }

  /** Highlight a selected symbol (amber/gold, 2× scale). Pass null to deselect. */
  setSelectedSymbol(symbol: string | null): void {
    const previousSymbol = this.selectedSymbol;
    this.selectedSymbol = symbol;

    // Restore previous selected symbol to tier color
    if (previousSymbol) {
      const prevState = this.symbolMap.get(previousSymbol);
      if (prevState) {
        this.setInstanceColor(prevState.instanceIndex, prevState.tierIndex);
        this.setInstanceTransform(prevState.instanceIndex, prevState.position, BASE_SCALE);
      }
    }

    // Apply selected styling
    if (symbol) {
      const state = this.symbolMap.get(symbol);
      if (state) {
        this.tempColor.copy(SELECTED_COLOR);
        this.instancedMesh.setColorAt(state.instanceIndex, this.tempColor);
        this.setInstanceTransform(state.instanceIndex, state.position, SELECTED_SCALE);
      }
    }

    this.instancedMesh.instanceMatrix.needsUpdate = true;
    if (this.instancedMesh.instanceColor) {
      this.instancedMesh.instanceColor.needsUpdate = true;
    }
  }

  /**
   * Animation loop update — handles tier transitions and LOD labels.
   *
   * @param deltaTime Seconds since last frame.
   */
  update(deltaTime: number): void {
    let matrixDirty = false;
    let colorDirty = false;

    for (const [symbol, state] of this.symbolMap) {
      if (!state.transitioning) continue;

      state.transitionElapsed += deltaTime;
      const t = Math.min(state.transitionElapsed / TRANSITION_DURATION, 1);

      // Lerp position
      state.position.lerp(state.targetPosition, Math.min(t * 3, 1));

      const isSelected = symbol === this.selectedSymbol;
      const isHovered = symbol === this.hoveredSymbol;
      const scale = isSelected ? SELECTED_SCALE : isHovered ? HOVER_SCALE : BASE_SCALE;
      this.setInstanceTransform(state.instanceIndex, state.position, scale);

      // Brightness pulse for symbols moving DOWN the funnel (higher tier index = closer to trigger)
      if (t < 1) {
        const pulse = Math.sin(t * Math.PI) * 0.3;
        this.tempColor.copy(TIER_PARTICLE_COLORS[state.tierIndex]);
        this.tempColor.offsetHSL(0, 0, pulse);
        this.instancedMesh.setColorAt(state.instanceIndex, this.tempColor);
        colorDirty = true;
      }

      matrixDirty = true;

      if (t >= 1) {
        state.transitioning = false;
        state.position.copy(state.targetPosition);
        // Restore final color
        if (!isSelected) {
          this.setInstanceColor(state.instanceIndex, state.tierIndex);
          colorDirty = true;
        }
      }
    }

    if (matrixDirty) {
      this.instancedMesh.instanceMatrix.needsUpdate = true;
    }
    if (colorDirty && this.instancedMesh.instanceColor) {
      this.instancedMesh.instanceColor.needsUpdate = true;
    }

    // Update LOD labels
    this.updateLabels();
  }

  /**
   * Handle raycaster intersection results from mouse move.
   *
   * @param intersections Intersections from Raycaster.intersectObject().
   * @param screenX Mouse screen X for tooltip positioning.
   * @param screenY Mouse screen Y for tooltip positioning.
   */
  handleMouseMove(
    intersections: THREE.Intersection[],
    screenX: number,
    screenY: number,
  ): void {
    const previousHovered = this.hoveredSymbol;

    if (intersections.length > 0 && intersections[0].instanceId !== undefined) {
      const instanceId = intersections[0].instanceId;
      const symbol = this.indexToSymbol.get(instanceId) ?? null;
      this.hoveredSymbol = symbol;

      if (symbol !== previousHovered) {
        // Restore previous hovered instance
        if (previousHovered) {
          const prevState = this.symbolMap.get(previousHovered);
          if (prevState && previousHovered !== this.selectedSymbol) {
            this.setInstanceTransform(prevState.instanceIndex, prevState.position, BASE_SCALE);
          }
        }
        // Scale up new hovered instance
        if (symbol) {
          const state = this.symbolMap.get(symbol);
          if (state && symbol !== this.selectedSymbol) {
            this.setInstanceTransform(state.instanceIndex, state.position, HOVER_SCALE);
          }
        }
        this.instancedMesh.instanceMatrix.needsUpdate = true;
      }
    } else {
      this.hoveredSymbol = null;
      if (previousHovered) {
        const prevState = this.symbolMap.get(previousHovered);
        if (prevState && previousHovered !== this.selectedSymbol) {
          this.setInstanceTransform(prevState.instanceIndex, prevState.position, BASE_SCALE);
          this.instancedMesh.instanceMatrix.needsUpdate = true;
        }
      }
    }

    this.callbacks?.onHoverSymbol(this.hoveredSymbol, screenX, screenY);
  }

  /** Handle click — select the hovered symbol. */
  handleClick(): void {
    if (this.hoveredSymbol) {
      this.callbacks?.onSelectSymbol(this.hoveredSymbol);
    }
  }

  /** Get the tier name for a symbol, or null if not tracked. */
  getTierName(symbol: string): string | null {
    const state = this.symbolMap.get(symbol);
    if (!state) return null;
    return TIER_DEFS[state.tierIndex]?.name ?? null;
  }

  /** Current number of tracked symbols. */
  get symbolCount(): number {
    return this.symbolMap.size;
  }

  /** Dispose all Three.js resources. */
  dispose(): void {
    // Remove all labels
    for (const [, state] of this.symbolMap) {
      this.removeLabel(state);
    }
    for (const label of this.labels) {
      this.labelGroup.remove(label);
    }
    this.labels.length = 0;

    this.geometry.dispose();
    this.material.dispose();
    this.symbolMap.clear();
    this.indexToSymbol.clear();
  }

  // ── Private ──────────────────────────────────────────────

  private computePositionOnDisc(tierIndex: number): THREE.Vector3 {
    const tier = TIER_DEFS[tierIndex];
    const angle = Math.random() * Math.PI * 2;
    const r = Math.random() * tier.radius * 0.85;
    return new THREE.Vector3(
      Math.cos(angle) * r,
      tier.y + 0.05, // slightly above disc surface
      Math.sin(angle) * r,
    );
  }

  private setInstanceTransform(
    index: number,
    position: THREE.Vector3,
    scale: number,
  ): void {
    this.tempMatrix.makeScale(scale, scale, scale);
    this.tempMatrix.setPosition(position);
    this.instancedMesh.setMatrixAt(index, this.tempMatrix);
  }

  private setInstanceColor(index: number, tierIndex: number): void {
    this.tempColor.copy(TIER_PARTICLE_COLORS[tierIndex]);
    this.instancedMesh.setColorAt(index, this.tempColor);
  }

  private updateLabels(): void {
    if (!this.camera) return;

    const cameraDistance = this.camera.position.length();
    const showLabels = cameraDistance < LOD_DISTANCE_THRESHOLD;

    if (!showLabels) {
      // Hide all labels
      for (const label of this.labels) {
        label.visible = false;
      }
      return;
    }

    // Find nearest symbols to camera (up to MAX_VISIBLE_LABELS)
    const symbolDistances: { symbol: string; dist: number; state: SymbolState }[] = [];

    for (const [symbol, state] of this.symbolMap) {
      this.tempVec.copy(state.position);
      const dist = this.tempVec.distanceTo(this.camera.position);
      symbolDistances.push({ symbol, dist, state });
    }

    symbolDistances.sort((a, b) => a.dist - b.dist);
    const visible = symbolDistances.slice(0, MAX_VISIBLE_LABELS);
    const visibleSet = new Set(visible.map((v) => v.symbol));

    // Hide labels not in visible set
    for (const [symbol, state] of this.symbolMap) {
      if (state.label && !visibleSet.has(symbol)) {
        state.label.visible = false;
      }
    }

    // Show/create labels for visible symbols
    for (const { symbol, state } of visible) {
      if (!state.label) {
        state.label = this.createLabel(symbol);
        this.labelGroup.add(state.label);
        this.labels.push(state.label);
      }
      state.label.position.copy(state.position);
      state.label.position.y += 0.08; // above sphere
      state.label.visible = true;
    }
  }

  private createLabel(text: string): CSS2DObject {
    const div = document.createElement('div');
    div.textContent = text;
    div.style.cssText =
      'font-size:9px;font-family:monospace;color:#e0e0e0;background:rgba(0,0,0,0.6);' +
      'padding:1px 3px;border-radius:2px;pointer-events:none;white-space:nowrap;';
    return new CSS2DObject(div);
  }

  private removeLabel(state: SymbolState): void {
    if (state.label) {
      this.labelGroup.remove(state.label);
      const idx = this.labels.indexOf(state.label);
      if (idx >= 0) this.labels.splice(idx, 1);
      state.label = null;
    }
  }
}
