/**
 * Skeleton loading primitive component with shimmer effect.
 *
 * Variants:
 * - 'line': Text placeholder (default height 16px, full width)
 * - 'rect': Rectangle placeholder (explicit width/height)
 * - 'circle': Circular placeholder (equal width/height)
 */

interface SkeletonProps {
  variant?: 'line' | 'rect' | 'circle';
  width?: string | number;
  height?: string | number;
  className?: string;
  rounded?: boolean;
}

function formatSize(value: string | number | undefined): string | undefined {
  if (value === undefined) return undefined;
  return typeof value === 'number' ? `${value}px` : value;
}

export function Skeleton({
  variant = 'line',
  width,
  height,
  className = '',
  rounded = true,
}: SkeletonProps) {
  // Default dimensions based on variant
  const defaultHeight = variant === 'line' ? '16px' : undefined;
  const defaultWidth = variant === 'line' ? '100%' : undefined;

  // Calculate final dimensions
  const finalWidth = formatSize(width) ?? defaultWidth;
  const finalHeight = formatSize(height) ?? defaultHeight;

  // For circle, ensure equal dimensions
  const circleSize = variant === 'circle' ? (formatSize(width) ?? formatSize(height) ?? '40px') : undefined;

  // Determine border radius
  let borderRadius = '';
  if (variant === 'circle') {
    borderRadius = 'rounded-full';
  } else if (rounded) {
    borderRadius = variant === 'line' ? 'rounded-md' : 'rounded-lg';
  }

  const style: React.CSSProperties =
    variant === 'circle'
      ? { width: circleSize, height: circleSize }
      : { width: finalWidth, height: finalHeight };

  return (
    <div
      className={`skeleton-shimmer ${borderRadius} ${className}`}
      style={style}
      aria-hidden="true"
    />
  );
}
