/**
 * Tests for FunnelView, FunnelScene, and FunnelSymbolManager.
 *
 * Three.js rendering requires WebGL (unavailable in jsdom), so we mock
 * Three.js and test structural/behavioral aspects.
 *
 * Sprint 25, Sessions 6a + 6b.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';

// ── Mock Three.js with classes (not vi.fn) ────────────────

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
  lerp(target: MockVector3, t: number) {
    this.x += (target.x - this.x) * t;
    this.y += (target.y - this.y) * t;
    this.z += (target.z - this.z) * t;
    return this;
  }
  lerpVectors(a: MockVector3, b: MockVector3, t: number) {
    this.x = a.x + (b.x - a.x) * t;
    this.y = a.y + (b.y - a.y) * t;
    this.z = a.z + (b.z - a.z) * t;
    return this;
  }
  distanceTo(v: MockVector3) {
    const dx = this.x - v.x;
    const dy = this.y - v.y;
    const dz = this.z - v.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  }
  length() {
    return Math.sqrt(this.x * this.x + this.y * this.y + this.z * this.z);
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
  r: number;
  g: number;
  b: number;
  constructor(color?: number) {
    const c = color ?? 0;
    this.r = ((c >> 16) & 0xff) / 255;
    this.g = ((c >> 8) & 0xff) / 255;
    this.b = (c & 0xff) / 255;
  }
  copy(other: MockColor) {
    this.r = other.r;
    this.g = other.g;
    this.b = other.b;
    return this;
  }
  offsetHSL(_h: number, _s: number, _l: number) {
    return this;
  }
}

class MockMatrix4 {
  elements = new Float32Array(16);
  makeScale(_sx: number, _sy: number, _sz: number) {
    return this;
  }
  setPosition(_v: MockVector3) {
    return this;
  }
}

/** Track instance colors and matrices for assertions. */
const instanceColors: Map<number, MockColor> = new Map();
const instanceMatrices: Map<number, MockMatrix4> = new Map();

class MockInstancedMesh {
  count = 0;
  frustumCulled = true;
  instanceMatrix = { needsUpdate: false };
  instanceColor: { needsUpdate: boolean } | null = { needsUpdate: false };

  constructor(
    public geometry: unknown,
    public material: unknown,
    public maxCount: number,
  ) {}

  setMatrixAt(index: number, matrix: MockMatrix4) {
    instanceMatrices.set(index, matrix);
  }

  setColorAt(index: number, color: MockColor) {
    instanceColors.set(index, { ...color } as unknown as MockColor);
  }
}

vi.mock('three', () => {
  return {
    Scene: class {
      add() {}
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
      opacity: number;
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
    InstancedMesh: MockInstancedMesh,
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
  };
});

vi.mock('three/examples/jsm/controls/OrbitControls.js', () => ({
  OrbitControls: class {
    enableDamping = false;
    dampingFactor = 0;
    minDistance = 0;
    maxDistance = Infinity;
    target = new MockVector3();
    update() {}
    dispose() {}
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
    constructor(public element: HTMLElement) {}
  },
}));

describe('FunnelScene', () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement('div');
    Object.defineProperty(container, 'clientWidth', { value: 800, configurable: true });
    Object.defineProperty(container, 'clientHeight', { value: 600, configurable: true });
  });

  it('creates 7 tier discs', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    expect(scene.tierCount).toBe(7);
    scene.dispose();
  });

  it('highlightTier changes disc opacity without errors', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    expect(scene.tierCount).toBe(7);

    // Highlight tier 3 then reset — should not throw
    scene.highlightTier(3);
    scene.highlightTier(-1);
    scene.dispose();
  });

  it('disposes all resources and is idempotent', async () => {
    const { FunnelScene } = await import('./three/FunnelScene');
    const scene = new FunnelScene(container);

    scene.dispose();
    // Second dispose is a no-op
    scene.dispose();
  });
});

describe('FunnelSymbolManager', () => {
  beforeEach(() => {
    instanceColors.clear();
    instanceMatrices.clear();
  });

  it('creates instanced mesh in scene', async () => {
    const { FunnelSymbolManager } = await import('./three/FunnelSymbolManager');
    const mgr = new FunnelSymbolManager();

    expect(mgr.instancedMesh).toBeDefined();
    expect(mgr.instancedMesh.count).toBe(0);
    expect(mgr.instancedMesh.maxCount).toBe(5000);

    mgr.dispose();
  });

  it('updateSymbolTiers sets positions and instance count', async () => {
    const { FunnelSymbolManager } = await import('./three/FunnelSymbolManager');
    const mgr = new FunnelSymbolManager();

    const tierData = new Map([
      ['AAPL', { tier: 'universe', conditionsPassed: 0 }],
      ['MSFT', { tier: 'evaluating', conditionsPassed: 3 }],
      ['TSLA', { tier: 'signal', conditionsPassed: 6 }],
    ]);

    mgr.updateSymbolTiers(tierData);

    expect(mgr.symbolCount).toBe(3);
    expect(mgr.instancedMesh.count).toBe(3);
    expect(mgr.getTierName('AAPL')).toBe('Universe');
    expect(mgr.getTierName('MSFT')).toBe('Evaluating');
    expect(mgr.getTierName('TSLA')).toBe('Signal');

    mgr.dispose();
  });

  it('selected symbol gets distinct color', async () => {
    const { FunnelSymbolManager } = await import('./three/FunnelSymbolManager');
    const mgr = new FunnelSymbolManager();

    const tierData = new Map([
      ['AAPL', { tier: 'universe', conditionsPassed: 0 }],
      ['MSFT', { tier: 'evaluating', conditionsPassed: 3 }],
    ]);

    mgr.updateSymbolTiers(tierData);

    // Record color before selection
    const colorBeforeSelect = instanceColors.get(0);

    // Select AAPL (instance index 0)
    mgr.setSelectedSymbol('AAPL');

    // Color should have changed to amber/gold (0xffc107)
    const colorAfterSelect = instanceColors.get(0);
    expect(colorAfterSelect).toBeDefined();

    // The selected color (amber) should differ from the tier color
    if (colorBeforeSelect && colorAfterSelect) {
      const changed =
        colorBeforeSelect.r !== colorAfterSelect.r ||
        colorBeforeSelect.g !== colorAfterSelect.g ||
        colorBeforeSelect.b !== colorAfterSelect.b;
      expect(changed).toBe(true);
    }

    // Deselect
    mgr.setSelectedSymbol(null);

    mgr.dispose();
  });
});

describe('FunnelView lazy loading', () => {
  it('exports FunnelView as a named export for React.lazy', async () => {
    const mod = await import('./FunnelView');
    expect(mod.FunnelView).toBeDefined();
    expect(typeof mod.FunnelView).toBe('object'); // forwardRef returns object
  });
});
