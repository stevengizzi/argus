import { useRef, useEffect, useCallback } from 'react';
import { formatPnl, formatPnlPercent, formatR } from '../utils/format';

interface PnlValueProps {
  value: number;
  format?: 'currency' | 'percent' | 'r-multiple';
  size?: 'sm' | 'md' | 'lg' | 'xl';
  flash?: boolean;
}

const sizeClasses: Record<NonNullable<PnlValueProps['size']>, string> = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-xl',
  xl: 'text-3xl',
};

export function PnlValue({ value, format = 'currency', size = 'md', flash = false }: PnlValueProps) {
  const prevValueRef = useRef<number>(value);
  const spanRef = useRef<HTMLSpanElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, []);

  // Handle flash animation via DOM manipulation to avoid setState in effect
  const triggerFlash = useCallback(() => {
    if (!flash || !spanRef.current) return;
    if (prevValueRef.current === value) return;

    const flashClass = value > prevValueRef.current ? 'flash-profit' : 'flash-loss';
    prevValueRef.current = value;

    // Clear any existing timer
    if (timerRef.current) {
      clearTimeout(timerRef.current);
    }

    // Add flash class via DOM
    spanRef.current.classList.add(flashClass);

    // Remove after animation completes
    timerRef.current = setTimeout(() => {
      spanRef.current?.classList.remove('flash-profit', 'flash-loss');
    }, 600);
  }, [value, flash]);

  // Trigger flash on value change
  useEffect(() => {
    triggerFlash();
  }, [triggerFlash]);

  let formatted: { text: string; className: string };
  switch (format) {
    case 'percent':
      formatted = formatPnlPercent(value);
      break;
    case 'r-multiple':
      formatted = formatR(value);
      break;
    default:
      formatted = formatPnl(value);
  }

  return (
    <span
      ref={spanRef}
      className={`tabular-nums font-medium ${sizeClasses[size]} ${formatted.className}`}
    >
      {formatted.text}
    </span>
  );
}
