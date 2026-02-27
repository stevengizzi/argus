/**
 * The Debrief page — institutional knowledge layer.
 *
 * Three sections:
 * - Briefings: Pre-market and end-of-day structured reports
 * - Research: Unified view of all project documentation
 * - Journal: Typed entries for observations, trade annotations, and notes
 *
 * Uses SegmentedTab for section switching with Framer Motion transitions.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { Card } from '../components/Card';
import { SegmentedTab, type SegmentedTabSegment } from '../components/SegmentedTab';
import { useDebriefUI, type DebriefSection } from '../stores/debriefUI';
import { BriefingList } from '../features/debrief/briefings';
import { ResearchLibrary } from '../features/debrief/research';
import { DURATION, EASE } from '../utils/motion';

const SECTIONS: SegmentedTabSegment[] = [
  { label: 'Briefings', value: 'briefings' },
  { label: 'Research', value: 'research' },
  { label: 'Journal', value: 'journal' },
];

const tabContentVariants = {
  initial: { opacity: 0, y: 8 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out },
  },
  exit: {
    opacity: 0,
    transition: { duration: DURATION.fast, ease: EASE.inOut },
  },
};

export function DebriefPage() {
  const activeSection = useDebriefUI((state) => state.activeSection);
  const setActiveSection = useDebriefUI((state) => state.setActiveSection);

  const handleSectionChange = (value: string) => {
    setActiveSection(value as DebriefSection);
  };

  return (
    <AnimatedPage>
      {/* Page header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <GraduationCap className="w-6 h-6 text-argus-accent" />
          <h1 className="text-xl font-semibold text-argus-text">The Debrief</h1>
        </div>
      </div>

      {/* Section tabs */}
      <div className="mb-6">
        <SegmentedTab
          segments={SECTIONS}
          activeValue={activeSection}
          onChange={handleSectionChange}
          layoutId="debrief-tabs"
        />
      </div>

      {/* Tab content with AnimatePresence for smooth transitions */}
      <AnimatePresence mode="wait">
        <motion.div
          key={activeSection}
          variants={tabContentVariants}
          initial="initial"
          animate="animate"
          exit="exit"
        >
          {activeSection === 'briefings' && <BriefingList />}
          {activeSection === 'research' && <ResearchLibrary />}
          {activeSection === 'journal' && <JournalPlaceholder />}
        </motion.div>
      </AnimatePresence>
    </AnimatedPage>
  );
}

/**
 * Placeholder for Journal tab (Session 7 will implement JournalList).
 */
function JournalPlaceholder() {
  return (
    <Card>
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-argus-text-dim mb-2">Learning Journal tab placeholder</p>
        <p className="text-sm text-argus-text-dim">
          Observations, trade annotations, and notes will appear here.
        </p>
      </div>
    </Card>
  );
}
