/**
 * The Debrief page — institutional knowledge layer.
 *
 * Six sections:
 * - Intelligence Brief: Pre-market AI-generated intelligence briefs
 * - Briefings: Pre-market and end-of-day structured reports
 * - Quality: Quality vs. outcome scatter plot for scored signals
 * - Research: Unified view of all project documentation
 * - Journal: Typed entries for observations, trade annotations, and notes
 * - Learning Journal: AI Copilot conversation history browser
 *
 * Uses SegmentedTab for section switching with Framer Motion transitions.
 *
 * Keyboard shortcuts:
 * - 'i' → switch to Intelligence Brief tab
 * - 'b' → switch to Briefings tab
 * - 'q' → switch to Quality tab
 * - 'r' → switch to Research tab
 * - 'j' → switch to Journal tab
 * - 'l' → switch to Learning Journal tab
 * - 'n' → start new entry (expand form in current tab)
 * - Escape → close editor/form
 *
 * Sprint 22 Session 6: Added Learning Journal section.
 * Sprint 23.5 Session 6: Added Intelligence Brief section.
 * Sprint 24 Session 11: Added Quality section.
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
import { JournalList, ConversationBrowser } from '../features/debrief/journal';
import { IntelligenceBriefView } from '../components/IntelligenceBriefView';
import { QualityOutcomeScatter } from '../features/debrief/QualityOutcomeScatter';
import { DURATION, EASE } from '../utils/motion';
import { useCopilotContext } from '../hooks/useCopilotContext';

const SECTIONS: SegmentedTabSegment[] = [
  { label: 'Intelligence Brief', value: 'intelligence_brief' },
  { label: 'Briefings', value: 'briefings' },
  { label: 'Quality', value: 'quality' },
  { label: 'Research', value: 'research' },
  { label: 'Journal', value: 'journal' },
  { label: 'Learning Journal', value: 'learning_journal' },
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
        case 'i':
          setActiveSection('intelligence_brief');
          break;
        case 'b':
          setActiveSection('briefings');
          break;
        case 'q':
          setActiveSection('quality');
          break;
        case 'r':
          setActiveSection('research');
          break;
        case 'j':
          setActiveSection('journal');
          break;
        case 'l':
          setActiveSection('learning_journal');
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
            {activeSection === 'intelligence_brief' && <IntelligenceBriefView />}
            {activeSection === 'briefings' && <BriefingList />}
            {activeSection === 'quality' && <QualityOutcomeScatter />}
            {activeSection === 'research' && <ResearchLibrary />}
            {activeSection === 'journal' && <JournalList />}
            {activeSection === 'learning_journal' && <ConversationBrowser />}
          </ErrorBoundary>
        </motion.div>
      </AnimatePresence>
    </AnimatedPage>
  );
}
