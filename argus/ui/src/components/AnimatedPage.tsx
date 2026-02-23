/**
 * Page transition wrapper component.
 *
 * Wraps page content in a motion.div with standardized entry/exit animations.
 * Use this when you need to wrap content manually outside of the AppShell.
 */

import { motion } from 'framer-motion';
import type { ReactNode } from 'react';
import { pageVariants } from '../utils/motion';

interface AnimatedPageProps {
  children: ReactNode;
  className?: string;
}

export function AnimatedPage({ children, className = '' }: AnimatedPageProps) {
  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  );
}
