/**
 * Platform detection utilities
 *
 * Detects whether the app is running as a Tauri desktop app, PWA, or web browser.
 */

/**
 * Check if running in Tauri desktop environment
 */
export function isTauri(): boolean {
  return '__TAURI__' in window && '__TAURI_INTERNALS__' in window;
}

/**
 * Check if running as an installed PWA (standalone mode)
 */
export function isPWA(): boolean {
  // Check display-mode media query
  const isStandalone = window.matchMedia('(display-mode: standalone)').matches;

  // iOS Safari specific check
  const isIOSStandalone =
    'standalone' in window.navigator &&
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true;

  return isStandalone || isIOSStandalone;
}

/**
 * Check if running in a regular web browser
 */
export function isWeb(): boolean {
  return !isTauri() && !isPWA();
}

/**
 * Get the current platform as a string
 */
export function getPlatform(): 'tauri' | 'pwa' | 'web' {
  if (isTauri()) return 'tauri';
  if (isPWA()) return 'pwa';
  return 'web';
}

/**
 * Check if running on macOS
 */
export function isMacOS(): boolean {
  return navigator.platform.toLowerCase().includes('mac');
}

/**
 * Check if running on Windows
 */
export function isWindows(): boolean {
  return navigator.platform.toLowerCase().includes('win');
}

/**
 * Check if running on Linux
 */
export function isLinux(): boolean {
  return navigator.platform.toLowerCase().includes('linux');
}

/**
 * Check if running on iOS
 */
export function isIOS(): boolean {
  return (
    /iPad|iPhone|iPod/.test(navigator.userAgent) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  );
}

/**
 * Check if running on Android
 */
export function isAndroid(): boolean {
  return /Android/.test(navigator.userAgent);
}

/**
 * Check if running on a mobile device
 */
export function isMobile(): boolean {
  return isIOS() || isAndroid();
}

/**
 * Check if the device supports touch
 */
export function hasTouch(): boolean {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}
