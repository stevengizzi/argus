import { useRef, useEffect, useState } from 'react';
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
  const [flashClass, setFlashClass] = useState<string>('');

  useEffect(() => {
    if (flash && prevValueRef.current !== value) {
      const newFlashClass = value > prevValueRef.current ? 'flash-profit' : 'flash-loss';
      setFlashClass(newFlashClass);
      prevValueRef.current = value;

      const timer = setTimeout(() => setFlashClass(''), 600);
      return () => clearTimeout(timer);
    }
  }, [value, flash]);

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
      className={`tabular-nums font-medium ${sizeClasses[size]} ${formatted.className} ${flashClass}`}
    >
      {formatted.text}
    </span>
  );
}
