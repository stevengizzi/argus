/**
 * Audio notification utilities for the AI Copilot.
 *
 * Uses Web Audio API to generate simple notification tones without
 * requiring external audio files. Audio context is created on first
 * user interaction to comply with browser autoplay policies.
 *
 * Sprint 22, Session 5.
 */

let audioContext: AudioContext | null = null;
let contextInitialized = false;

/**
 * Initialize the audio context on user interaction.
 * Must be called from a user gesture (click, keypress) due to browser policies.
 */
export function initializeAudioContext(): void {
  if (contextInitialized) return;

  try {
    audioContext = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
    contextInitialized = true;
  } catch {
    console.warn('Web Audio API not supported');
  }
}

/**
 * Play a simple tone at the specified frequency and duration.
 */
function playTone(frequency: number, duration: number, startTime: number = 0): void {
  if (!audioContext) return;

  const oscillator = audioContext.createOscillator();
  const gainNode = audioContext.createGain();

  oscillator.connect(gainNode);
  gainNode.connect(audioContext.destination);

  oscillator.frequency.value = frequency;
  oscillator.type = 'sine';

  // Fade in and out to avoid clicks
  const currentTime = audioContext.currentTime + startTime;
  gainNode.gain.setValueAtTime(0, currentTime);
  gainNode.gain.linearRampToValueAtTime(0.15, currentTime + 0.01);
  gainNode.gain.linearRampToValueAtTime(0.15, currentTime + duration - 0.01);
  gainNode.gain.linearRampToValueAtTime(0, currentTime + duration);

  oscillator.start(currentTime);
  oscillator.stop(currentTime + duration);
}

/**
 * Play a notification sound when a new action proposal appears.
 * Two-tone ascending beep: 440Hz -> 660Hz, 100ms each.
 */
export function playProposalNotification(): void {
  if (!audioContext) {
    initializeAudioContext();
    if (!audioContext) return;
  }

  // Resume context if suspended (browser policy)
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }

  // 440Hz (A4) for 100ms
  playTone(440, 0.1, 0);
  // 660Hz (E5) for 100ms after 100ms delay
  playTone(660, 0.1, 0.1);
}

/**
 * Play an expiry warning sound when a proposal has < 1 minute remaining.
 * Three rapid beeps: 880Hz, 80ms each with 50ms gaps.
 */
export function playExpiryWarning(): void {
  if (!audioContext) {
    initializeAudioContext();
    if (!audioContext) return;
  }

  // Resume context if suspended (browser policy)
  if (audioContext.state === 'suspended') {
    audioContext.resume();
  }

  // Three rapid beeps at 880Hz (A5)
  playTone(880, 0.08, 0);
  playTone(880, 0.08, 0.13); // 80ms + 50ms gap
  playTone(880, 0.08, 0.26); // 80ms + 50ms gap
}
