/**
 * Tests for RadarView camera transitions, labels, and orbit constraints.
 *
 * Three.js is mocked (no WebGL in jsdom). Tests verify behavioral contracts:
 * transition triggers, label visibility, orbit constraint application,
 * and transition completion callbacks.
 *
 * Sprint 25, Session 7.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock Three.js with the same classes as FunnelView.test.tsx ──

class MockVector3 {
  x: number;
  y: number;
  z: number;
  constructor(x = 0, y = 0, z = 0) {
    this.x = x;
    this.y = y;
    this.z = z;
  }
  copy(v: MockVector3) {
    this.x = v.x;
    this.y = v.y;
    this.z = v.z;
    return this;
  }
  clone() {
    return new MockVector3(this.x, this.y, this.z);
  }
  lerpVectors(a: MockVector3, b: MockVector3, t: number) {
    this.x = a.x + (b.x - a.x) * t;
    this.y = a.y + (b.y - a.y) * t;
    this.z = a.z + (b.z - a.z) * t;
    return this;
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
  }
  distanceTo(v: MockVector3) {
    const dx = this.x - v.x;
    const dy = this.y - v.y;
    const dz = this.z - v.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
}

class MockVector2 {
  x: number;
  y: number;
  constructor(x = 0, y = 0) {
    this.x = x;
    this.y = y;
  }
}

class MockColor {
  r = 0;
  g = 0;
  b = 0;
  constructor(_color?: number) {}
  copy() {
    return this;
  }
  offsetHSL() {
    return this;
  }
}

class MockMatrix4 {
  elements = new Float32Array(16);
  makeScale() {
    return this;
  }
  setPosition() {
    return this;
  }
}

vi.mock('three', () => ({
  Scene: class {
    add() {}
    remove() {}
    clear() {}
  },
  PerspectiveCamera: class {
    position = new MockVector3();
    aspect = 1;
    lookAt() {}
    updateProjectionMatrix() {}
  },
  WebGLRenderer: class {
    domElement = document.createElement('canvas');
    setSize() {}
    setPixelRatio() {}
    setClearColor() {}
    render() {}
    dispose() {}
  },
  CircleGeometry: class {
    dispose() {}
  },
  SphereGeometry: class {
    dispose() {}
  },
  MeshStandardMaterial: class {
    opacity = 0.2;
    constructor(opts?: Record<string, unknown>) {
      this.opacity = (opts?.opacity as number) ?? 0.2;
    }
    dispose() {}
  },
  Mesh: class {
    rotation = { x: 0 };
    position = { y: 0 };
    userData: Record<string, unknown> = {};
    material: unknown;
    constructor(_geo: unknown, mat: unknown) {
      this.material = mat;
    }
  },
  InstancedMesh: class {
    count = 0;
    frustumCulled = true;
    instanceMatrix = { needsUpdate: false };
    instanceColor = { needsUpdate: false };
    constructor(
      public geometry: unknown,
      public material: unknown,
      public maxCount: number,
    ) {}
    setMatrixAt() {}
    setColorAt() {}
  },
  LineBasicMaterial: class {
    dispose() {}
  },
  BufferGeometry: class {
    setFromPoints() {
      return this;
    }
    dispose() {}
  },
  LineLoop: class {},
  Line: class {},
  AmbientLight: class {},
  DirectionalLight: class {
    position = { set() {} };
  },
  Group: class {
    name = '';
    add() {}
    remove() {}
  },
  Raycaster: class {
    setFromCamera() {}
    intersectObject() {
      return [];
    }
  },
  Vector3: MockVector3,
  Vector2: MockVector2,
  Matrix4: MockMatrix4,
  Color: MockColor,
  DoubleSide: 2,
}));

/** Track orbit control state for constraint assertions. */
let orbitControlInstance: Record<string, unknown> = {};

vi.mock('three/examples/jsm/controls/OrbitControls.js', () => ({
  OrbitControls: class {
    enableDamping = false;
    dampingFactor = 0;
    minDistance = 0;
    maxDistance = Infinity;
    minPolarAngle = 0;
    maxPolarAngle = Math.PI;
    enableRotate = true;
    enabled = true;
    target = new MockVector3();
    update() {}
    dispose() {}
    constructor() {
      // eslint-disable-next-line @typescript-eslint/no-this-alias
      orbitControlInstance = this;
    }
  },
}));

vi.mock('three/examples/jsm/renderers/CSS2DRenderer.js', () => ({
  CSS2DRenderer: class {
    domElement = document.createElement('div');
    setSize() {}
    render() {}
  },
  CSS2DObject: class {
    position = new MockVector3();
    visible = true;
    element: HTMLElement;
    constructor(element: HTMLElement) {
      this.element = element;
    }
  },
}));

describe('FunnelScene radar mode', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800, configurable: true });
    Object.defineProperty(container, 'clientHeight', { value: 600, configurable: true });
    orbitControlInstance = {};
  });

  it('transitionToRadar triggers camera animation and disables controls', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    expect(scene.cameraMode).toBe('funnel');
    expect(scene.isTransitioning).toBe(false);

    scene.transitionToRadar();

    expect(scene.cameraMode).toBe('radar');
    expect(scene.isTransitioning).toBe(true);
    // Controls should be disabled during transition
    expect(scene.controls.enabled).toBe(false);

    scene.dispose();
  });

  it('transition completes and fires callback', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    const onComplete = vi.fn();
    scene.transitionToRadar(onComplete);

    // Simulate passage of time > TRANSITION_DURATION_MS (800ms)
    // by advancing performance.now via the animation loop
    const originalPerfNow = performance.now;
    const startTime = originalPerfNow.call(performance);
    vi.spyOn(performance, 'now').mockReturnValue(startTime + 900);

    // Manually tick the animation by calling the internal method
    // We need to trigger the animation update
    // Access the private animate method indirectly via a render cycle
    // @ts-expect-error accessing private for test
    scene.updateCameraAnimation();

    expect(scene.isTransitioning).toBe(false);
    expect(onComplete).toHaveBeenCalledTimes(1);
    // Controls re-enabled after transition
    expect(scene.controls.enabled).toBe(true);

    vi.restoreAllMocks();
    scene.dispose();
  });

  it('radar labels are visible after transition and hidden after return to funnel', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    // Initially labels should be hidden
    // @ts-expect-error accessing private for test
    const tierLabels: Array<{ visible: boolean; element: HTMLElement }> = scene.radarTierLabels;
    // @ts-expect-error accessing private for test
    const triggerLabel: { visible: boolean; element: HTMLElement } = scene.radarTriggerLabel;

    for (const label of tierLabels) {
      expect(label.visible).toBe(false);
    }
    expect(triggerLabel.visible).toBe(false);

    // Start radar transition — labels become visible
    scene.transitionToRadar();

    for (const label of tierLabels) {
      expect(label.visible).toBe(true);
    }
    expect(triggerLabel.visible).toBe(true);

    // Complete the transition
    const startTime = performance.now();
    vi.spyOn(performance, 'now').mockReturnValue(startTime + 900);
    // @ts-expect-error accessing private for test
    scene.updateCameraAnimation();

    // Labels still visible in radar mode
    for (const label of tierLabels) {
      expect(label.visible).toBe(true);
    }

    // Transition back to funnel
    vi.restoreAllMocks();
    scene.transitionToFunnel();

    const startTime2 = performance.now();
    vi.spyOn(performance, 'now').mockReturnValue(startTime2 + 900);
    // @ts-expect-error accessing private for test
    scene.updateCameraAnimation();

    // Labels hidden after returning to funnel
    for (const label of tierLabels) {
      expect(label.visible).toBe(false);
    }
    expect(triggerLabel.visible).toBe(false);

    vi.restoreAllMocks();
    scene.dispose();
  });

  it('orbit controls constrained to vertical axis in radar mode', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    scene.transitionToRadar();

    // Complete the transition
    const startTime = performance.now();
    vi.spyOn(performance, 'now').mockReturnValue(startTime + 900);
    // @ts-expect-error accessing private for test
    scene.updateCameraAnimation();

    // Polar angle locked to Math.PI (bottom-up only)
    expect(scene.controls.minPolarAngle).toBe(Math.PI);
    expect(scene.controls.maxPolarAngle).toBe(Math.PI);

    // Return to funnel — polar angle unlocked
    vi.restoreAllMocks();
    scene.transitionToFunnel();

    const startTime2 = performance.now();
    vi.spyOn(performance, 'now').mockReturnValue(startTime2 + 900);
    // @ts-expect-error accessing private for test
    scene.updateCameraAnimation();

    expect(scene.controls.minPolarAngle).toBe(0);
    expect(scene.controls.maxPolarAngle).toBe(Math.PI);

    vi.restoreAllMocks();
    scene.dispose();
  });
});

describe('RadarView wrapper', () => {
  it('exports RadarView as a named export', async () => {
    const mod = await import('./RadarView');
    expect(mod.RadarView).toBeDefined();
    expect(typeof mod.RadarView).toBe('object'); // forwardRef returns object
  });
});
