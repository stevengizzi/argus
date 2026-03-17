/**
 * Camera transition presets and interpolation config for the Funnel/Radar views.
 *
 * Defines camera positions, look-at targets, and orbit-control constraints
 * for each view mode. The actual lerp runs inside FunnelScene's animation
 * loop (requestAnimationFrame) — this module provides the declarative config.
 *
 * Sprint 25, Session 7.
 */

import * as THREE from 'three';

export type CameraMode = 'funnel' | 'radar';

export interface CameraPreset {
  position: THREE.Vector3;
  target: THREE.Vector3;
}

/** Angled perspective — default funnel viewpoint. */
export const FUNNEL_PRESET: CameraPreset = {
  position: new THREE.Vector3(0, 5, 12),
  target: new THREE.Vector3(0, 3, 0),
};

/** Bottom-up viewpoint — directly below the funnel looking up. */
export const RADAR_PRESET: CameraPreset = {
  position: new THREE.Vector3(0, -2, 0),
  target: new THREE.Vector3(0, 3, 0),
};

/** Transition duration in milliseconds (~800ms with ease-out). */
export const TRANSITION_DURATION_MS = 800;

/** Ease-out cubic curve: fast start, gentle stop. */
export function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

/**
 * Orbit control constraints per mode.
 *
 * In radar mode the camera sits on the vertical axis looking up,
 * so we lock polar angle to prevent the user from flipping back
 * to the funnel perspective via drag — they must press `f` for that.
 */
export interface OrbitConstraints {
  minPolarAngle: number;
  maxPolarAngle: number;
  enableRotate: boolean;
}

export const FUNNEL_ORBIT: OrbitConstraints = {
  minPolarAngle: 0,
  maxPolarAngle: Math.PI,
  enableRotate: true,
};

/** Lock polar angle so only azimuthal (vertical-axis) rotation is allowed. */
export const RADAR_ORBIT: OrbitConstraints = {
  minPolarAngle: Math.PI,
  maxPolarAngle: Math.PI,
  enableRotate: true,
};
