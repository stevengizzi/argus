/**
 * The Debrief page — institutional knowledge layer.
 *
 * Three sections:
 * - Briefings: Pre-market and end-of-day structured reports
 * - Research: Unified view of all project documentation
 * - Journal: Typed entries for observations, trade annotations, and notes
 *
 * Uses SegmentedTab for section switching with Framer Motion transitions.
 *
 * Keyboard shortcuts:
 * - 'b' → switch to Briefings tab
 * - 'r' → switch to Research tab
 * - 'j' → switch to Journal tab
 * - 'n' → start new entry (expand form in current tab)
 * - Escape → close editor/form
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { GraduationCap } from 'lucide-react';
import { AnimatedPage } from '../components/AnimatedPage';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { SegmentedTab, type SegmentedTabSegment } from '../components/SegmentedTab';
import { useDebriefUI, type DebriefSection } from '../stores/debriefUI';
import { BriefingList } from '../features/debrief/briefings';
import { ResearchLibrary } from '../features/debrief/research';
import { JournalList } from '../features/debrief/journal';
import { DURATION, EASE } from '../utils/motion';
import { useCopilotContext } from '../hooks/useCopilotContext';

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
  const journalDraftExpanded = useDebriefUI((state) => state.journalDraftExpanded);
  const setJournalDraftExpanded = useDebriefUI((state) => state.setJournalDraftExpanded);
  const editingBriefingId = useDebriefUI((state) => state.editingBriefingId);
  const setEditingBriefingId = useDebriefUI((state) => state.setEditingBriefingId);
  const readingBriefingId = useDebriefUI((state) => state.readingBriefingId);
  const setReadingBriefingId = useDebriefUI((state) => state.setReadingBriefingId);
  const editingDocumentId = useDebriefUI((state) => state.editingDocumentId);
  const setEditingDocumentId = useDebriefUI((state) => state.setEditingDocumentId);
  const readingDocumentId = useDebriefUI((state) => state.readingDocumentId);
  const setReadingDocumentId = useDebriefUI((state) => state.setReadingDocumentId);
  const editingJournalEntryId = useDebriefUI((state) => state.editingJournalEntryId);
  const setEditingJournalEntryId = useDebriefUI((state) => state.setEditingJournalEntryId);

  // Register Copilot context
  useCopilotContext('Debrief', () => ({
    currentView: activeSection,
  }));

  const handleSectionChange = (value: string) => {
    setActiveSection(value as DebriefSection);
  };

  // Keyboard shortcuts for tab navigation and actions
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Ignore if typing in an input, textarea, or contenteditable
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'b':
          setActiveSection('briefings');
          break;
        case 'r':
          setActiveSection('research');
          break;
        case 'j':
          setActiveSection('journal');
          break;
        case 'n':
          // Start new entry in current tab
          if (activeSection === 'journal') {
            setJournalDraftExpanded(true);
          }
          // Note: Briefings and Research "new" actions require dropdown/navigation,
          // which are handled within their respective components
          break;
        case 'escape':
          // Close one thing at a time with priority: modal → editor → form
          if (readingBriefingId) {
            setReadingBriefingId(null);
          } else if (readingDocumentId) {
            setReadingDocumentId(null);
          } else if (editingBriefingId) {
            setEditingBriefingId(null);
          } else if (editingDocumentId) {
            setEditingDocumentId(null);
          } else if (editingJournalEntryId) {
            setEditingJournalEntryId(null);
          } else if (journalDraftExpanded) {
            // Collapse journal form
            setJournalDraftExpanded(false);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [
    activeSection,
    journalDraftExpanded,
    editingBriefingId,
    readingBriefingId,
    editingDocumentId,
    readingDocumentId,
    editingJournalEntryId,
    setActiveSection,
    setJournalDraftExpanded,
    setEditingBriefingId,
    setReadingBriefingId,
    setEditingDocumentId,
    setReadingDocumentId,
    setEditingJournalEntryId,
  ]);

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
          <ErrorBoundary name={activeSection}>
            {activeSection === 'briefings' && <BriefingList />}
            {activeSection === 'research' && <ResearchLibrary />}
            {activeSection === 'journal' && <JournalList />}
          </ErrorBoundary>
        </motion.div>
      </AnimatePresence>
    </AnimatedPage>
  );
}
