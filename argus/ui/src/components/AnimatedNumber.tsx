/**
 * AnimatedNumber component for smooth number transitions.
 *
 * Uses requestAnimationFrame to interpolate between values with ease-out cubic easing.
 * Handles rapid updates by interrupting current animation and starting from current position.
 */

import { useRef, useEffect, useState } from 'react';

interface AnimatedNumberProps {
  /** The target value to animate to */
  value: number;
  /** Formatting function (e.g., formatCurrency) */
  format: (n: number) => string;
  /** Animation duration in milliseconds (default 400) */
  duration?: number;
  /** Additional CSS classes */
  className?: string;
}

/** Ease-out cubic: decelerating to zero velocity */
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}

export function AnimatedNumber({
  value,
  format,
  duration = 400,
  className = '',
}: AnimatedNumberProps) {
  // Track the displayed value (what we render)
  // Initialize with the prop value so first render shows correct value immediately
  const [displayValue, setDisplayValue] = useState(value);

  // Track animation state with refs to avoid re-renders
  const currentValueRef = useRef(value);
  const targetValueRef = useRef(value);
  const startTimeRef = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  // Keep currentValueRef in sync with displayValue without triggering effects
  useEffect(() => {
    currentValueRef.current = displayValue;
  }, [displayValue]);

  // Handle value changes - start animation when target changes
  useEffect(() => {
    // If value hasn't changed from our target, nothing to do
    if (value === targetValueRef.current) {
      return;
    }

    // Cancel any running animation
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current);
    }

    // Record the starting position (current displayed value) and new target
    const startValue = currentValueRef.current;
    targetValueRef.current = value;
    startTimeRef.current = null;

    const animate = (timestamp: number) => {
      if (startTimeRef.current === null) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);

      const current = startValue + (value - startValue) * easedProgress;

      setDisplayValue(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        rafRef.current = null;
        // Ensure final value is exact
        setDisplayValue(value);
      }
    };

    rafRef.current = requestAnimationFrame(animate);

    // Cleanup on unmount or when dependencies change
    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [value, duration]);

  return <span className={`tabular-nums ${className}`}>{format(displayValue)}</span>;
}
