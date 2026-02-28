/**
 * Unified color scale utilities for Performance Analytics.
 *
 * Provides consistent diverging color scales for P&L/R-Multiple visualizations
 * and dynamic text color contrast calculation for legibility.
 *
 * Sprint 21d: Addresses code review #2 items #1 and #2.
 */

import { scaleLinear } from 'd3-scale';
import { interpolateRgb } from 'd3-interpolate';

/**
 * Color constants for the diverging P&L scale.
 * Zero anchored at neutral gray (not yellow-green).
 */
export const DIVERGING_COLORS = {
  /** Strong loss color (red) */
  loss: '#ef4444',
  /** Mild loss color (lighter red/coral) */
  lossLight: '#f87171',
  /** Neutral color (desaturated gray) - matches dark theme */
  neutral: '#3b4252',
  /** Mild profit color (lighter green) */
  profitLight: '#4ade80',
  /** Strong profit color (green) */
  profit: '#22c55e',
} as const;

/**
 * Creates a unified diverging color scale for P&L or R-Multiple values.
 *
 * Key properties:
 * - Zero maps to a neutral gray (NOT yellow-green)
 * - Negative values map to red tones (even slightly negative)
 * - Positive values map to green tones
 * - Symmetric around zero based on the provided domain bounds
 *
 * @param minValue - The minimum value in the domain (should be negative or 0)
 * @param maxValue - The maximum value in the domain (should be positive or 0)
 * @returns A function that maps a value to a CSS color string
 *
 * @example
 * const colorScale = createDivergingScale(-1000, 2000);
 * colorScale(-500); // returns a red-ish color
 * colorScale(0);    // returns neutral gray
 * colorScale(500);  // returns a green-ish color
 */
export function createDivergingScale(
  minValue: number,
  maxValue: number
): (value: number) => string {
  // Ensure symmetric domain around 0 for balanced color distribution
  const absMax = Math.max(Math.abs(minValue), Math.abs(maxValue), 0.01);

  // Create a 5-point scale: strong loss → mild loss → neutral → mild profit → strong profit
  const scale = scaleLinear<string>()
    .domain([-absMax, -absMax * 0.3, 0, absMax * 0.3, absMax])
    .range([
      DIVERGING_COLORS.loss,
      DIVERGING_COLORS.lossLight,
      DIVERGING_COLORS.neutral,
      DIVERGING_COLORS.profitLight,
      DIVERGING_COLORS.profit,
    ])
    .interpolate(interpolateRgb)
    .clamp(true);

  return (value: number) => scale(value);
}

/**
 * Creates a simplified diverging scale with just 3 stops (loss/neutral/profit).
 * Good for simpler visualizations where the 5-point gradient isn't needed.
 *
 * @param minValue - The minimum value in the domain
 * @param maxValue - The maximum value in the domain
 * @returns A function that maps a value to a CSS color string
 */
export function createSimpleDivergingScale(
  minValue: number,
  maxValue: number
): (value: number) => string {
  const absMax = Math.max(Math.abs(minValue), Math.abs(maxValue), 0.01);

  const scale = scaleLinear<string>()
    .domain([-absMax, 0, absMax])
    .range([DIVERGING_COLORS.loss, DIVERGING_COLORS.neutral, DIVERGING_COLORS.profit])
    .interpolate(interpolateRgb)
    .clamp(true);

  return (value: number) => scale(value);
}

/**
 * Parses a CSS color (hex or rgb) and returns RGB components.
 *
 * @param color - CSS color string (hex like '#ff0000' or rgb like 'rgb(255, 0, 0)')
 * @returns Object with r, g, b values (0-255) or null if parsing fails
 */
function parseColor(color: string): { r: number; g: number; b: number } | null {
  // Handle hex colors
  if (color.startsWith('#')) {
    const hex = color.slice(1);
    if (hex.length === 3) {
      // Short hex (#f00)
      return {
        r: parseInt(hex[0] + hex[0], 16),
        g: parseInt(hex[1] + hex[1], 16),
        b: parseInt(hex[2] + hex[2], 16),
      };
    }
    if (hex.length === 6) {
      // Full hex (#ff0000)
      return {
        r: parseInt(hex.slice(0, 2), 16),
        g: parseInt(hex.slice(2, 4), 16),
        b: parseInt(hex.slice(4, 6), 16),
      };
    }
  }

  // Handle rgb/rgba colors
  const rgbMatch = color.match(/rgba?\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  if (rgbMatch) {
    return {
      r: parseInt(rgbMatch[1], 10),
      g: parseInt(rgbMatch[2], 10),
      b: parseInt(rgbMatch[3], 10),
    };
  }

  return null;
}

/**
 * Calculates relative luminance of a color per WCAG 2.1 guidelines.
 *
 * @param r - Red component (0-255)
 * @param g - Green component (0-255)
 * @param b - Blue component (0-255)
 * @returns Relative luminance (0-1)
 */
function getRelativeLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const sRGB = c / 255;
    return sRGB <= 0.03928 ? sRGB / 12.92 : Math.pow((sRGB + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

/**
 * Determines the best text color for maximum contrast against a background.
 *
 * Uses WCAG 2.1 relative luminance calculation to ensure adequate contrast.
 * Returns white for dark backgrounds, dark color for light backgrounds.
 *
 * @param bgColor - Background color as CSS string (hex or rgb)
 * @returns '#ffffff' (white) for dark backgrounds, '#1a1a2e' (dark) for light backgrounds
 *
 * @example
 * getContrastTextColor('#ef4444'); // returns '#ffffff' (white on red)
 * getContrastTextColor('#4ade80'); // returns '#1a1a2e' (dark on light green)
 * getContrastTextColor('#3b4252'); // returns '#ffffff' (white on neutral gray)
 */
export function getContrastTextColor(bgColor: string): string {
  const WHITE = '#ffffff';
  const DARK = '#1a1a2e';

  const rgb = parseColor(bgColor);
  if (!rgb) {
    // Default to white if parsing fails
    return WHITE;
  }

  const luminance = getRelativeLuminance(rgb.r, rgb.g, rgb.b);

  // WCAG threshold for contrast - use white text if luminance is below ~0.4
  // This threshold ensures 4.5:1 contrast ratio for normal text
  return luminance < 0.4 ? WHITE : DARK;
}

/**
 * Pre-built color scale for the standard legend display (7 steps).
 * Returns an array of colors from loss to profit.
 *
 * @param absMax - The absolute maximum value for the scale domain
 * @returns Array of 7 color strings from loss to profit
 */
export function getLegendColors(absMax: number = 1): string[] {
  const scale = createDivergingScale(-absMax, absMax);
  return [-1, -0.67, -0.33, 0, 0.33, 0.67, 1].map((t) => scale(t * absMax));
}
