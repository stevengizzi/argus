/**
 * Journal entry creation/edit form.
 *
 * Two modes controlled by journalDraftExpanded in Zustand:
 * - Collapsed: Single-line input that expands on focus/click
 * - Expanded: Full form with title, content, type, strategy, tags
 *
 * Supports pre-fill props for edit mode (initialData, onSave, onCancel).
 */

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, Target, Lightbulb, Settings, X } from 'lucide-react';
import { JournalTagInput } from './JournalTagInput';
import { TradeSearchInput } from './TradeSearchInput';
import { Card } from '../../../components/Card';
import { useDebriefUI } from '../../../stores/debriefUI';
import { useStrategies } from '../../../hooks/useStrategies';
import { useCreateJournalEntry, useUpdateJournalEntry } from '../../../hooks/useJournal';
import type { JournalEntry, JournalEntryType } from '../../../api/types';
import { DURATION, EASE } from '../../../utils/motion';

interface JournalEntryFormProps {
  /** Pre-filled data for edit mode */
  initialData?: JournalEntry;
  /** Callback when entry is saved (edit mode) */
  onSave?: (data: JournalEntry) => void;
  /** Callback when form is cancelled (edit mode) */
  onCancel?: () => void;
}

interface EntryTypeOption {
  value: JournalEntryType;
  label: string;
  icon: typeof Eye;
  colorClass: string;
  bgClass: string;
}

const ENTRY_TYPES: EntryTypeOption[] = [
  {
    value: 'observation',
    label: 'Observation',
    icon: Eye,
    colorClass: 'text-blue-400',
    bgClass: 'bg-blue-400/15 border-blue-400/30',
  },
  {
    value: 'trade_annotation',
    label: 'Trade Annotation',
    icon: Target,
    colorClass: 'text-argus-profit',
    bgClass: 'bg-argus-profit/15 border-argus-profit/30',
  },
  {
    value: 'pattern_note',
    label: 'Pattern Note',
    icon: Lightbulb,
    colorClass: 'text-amber-400',
    bgClass: 'bg-amber-400/15 border-amber-400/30',
  },
  {
    value: 'system_note',
    label: 'System Note',
    icon: Settings,
    colorClass: 'text-argus-text-dim',
    bgClass: 'bg-argus-surface-2 border-argus-border',
  },
];

const formVariants = {
  collapsed: { height: 'auto' },
  expanded: {
    height: 'auto',
    transition: { duration: DURATION.normal, ease: EASE.out },
  },
};

const contentVariants = {
  hidden: { opacity: 0, y: -8 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: DURATION.normal, ease: EASE.out },
  },
  exit: {
    opacity: 0,
    y: -8,
    transition: { duration: DURATION.fast },
  },
};

export function JournalEntryForm({ initialData, onSave, onCancel }: JournalEntryFormProps) {
  const isEditMode = !!initialData;

  // Zustand state (only used in create mode)
  const journalDraftExpanded = useDebriefUI((s) => s.journalDraftExpanded);
  const setJournalDraftExpanded = useDebriefUI((s) => s.setJournalDraftExpanded);

  // In edit mode, form is always expanded
  const isExpanded = isEditMode || journalDraftExpanded;

  // Form state
  const [title, setTitle] = useState(initialData?.title ?? '');
  const [content, setContent] = useState(initialData?.content ?? '');
  const [entryType, setEntryType] = useState<JournalEntryType>(
    initialData?.entry_type ?? 'observation'
  );
  const [strategyId, setStrategyId] = useState<string>(
    initialData?.linked_strategy_id ?? ''
  );
  const [tags, setTags] = useState<string[]>(initialData?.tags ?? []);
  const [linkedTradeIds, setLinkedTradeIds] = useState<string[]>(
    initialData?.linked_trade_ids ?? []
  );
  const [showSuccess, setShowSuccess] = useState(false);

  const collapsedInputRef = useRef<HTMLInputElement>(null);
  const titleInputRef = useRef<HTMLInputElement>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Data hooks
  const { data: strategiesData } = useStrategies();
  const createMutation = useCreateJournalEntry();
  const updateMutation = useUpdateJournalEntry();

  const strategies = strategiesData?.strategies ?? [];
  const isSaving = createMutation.isPending || updateMutation.isPending;

  // Reset form after successful save
  useEffect(() => {
    if (createMutation.isSuccess && !isEditMode) {
      setTitle('');
      setContent('');
      setEntryType('observation');
      setStrategyId('');
      setTags([]);
      setLinkedTradeIds([]);
      setJournalDraftExpanded(false);
      setShowSuccess(true);
      // Clear any existing timer before setting a new one
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current);
      }
      successTimerRef.current = setTimeout(() => setShowSuccess(false), 2000);
    }
  }, [createMutation.isSuccess, isEditMode, setJournalDraftExpanded]);

  // Cleanup success timer on unmount
  useEffect(() => {
    return () => {
      if (successTimerRef.current) {
        clearTimeout(successTimerRef.current);
      }
    };
  }, []);

  // Focus title input when form expands
  useEffect(() => {
    if (isExpanded && !isEditMode) {
      // Small delay to ensure animation has started
      setTimeout(() => titleInputRef.current?.focus(), 50);
    }
  }, [isExpanded, isEditMode]);

  // Handle expand
  const handleExpand = () => {
    if (!isEditMode) {
      setJournalDraftExpanded(true);
    }
  };

  // Handle collapse (cancel)
  const handleCancel = () => {
    if (isEditMode && onCancel) {
      onCancel();
    } else {
      setTitle('');
      setContent('');
      setEntryType('observation');
      setStrategyId('');
      setTags([]);
      setLinkedTradeIds([]);
      setJournalDraftExpanded(false);
    }
  };

  // Handle save
  const handleSave = async () => {
    if (!content.trim()) return;

    try {
      if (isEditMode && initialData) {
        const updated = await updateMutation.mutateAsync({
          id: initialData.id,
          data: {
            title: title.trim(),
            content: content.trim(),
            entry_type: entryType,
            linked_strategy_id: strategyId || undefined,
            linked_trade_ids: linkedTradeIds,
            tags,
          },
        });
        onSave?.(updated);
        onCancel?.();
      } else {
        await createMutation.mutateAsync({
          entry_type: entryType,
          title: title.trim(),
          content: content.trim(),
          linked_strategy_id: strategyId || undefined,
          linked_trade_ids: linkedTradeIds,
          tags,
        });
      }
    } catch (error) {
      console.error('Failed to save journal entry:', error);
    }
  };

  // Collapsed state
  if (!isExpanded) {
    return (
      <Card className="relative">
        <input
          ref={collapsedInputRef}
          type="text"
          placeholder="What did you observe today?"
          onClick={handleExpand}
          onFocus={handleExpand}
          readOnly
          className="w-full bg-transparent text-argus-text placeholder:text-argus-text-dim focus:outline-none cursor-text"
        />

        {/* Success flash */}
        <AnimatePresence>
          {showSuccess && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-sm text-argus-profit"
            >
              Entry saved!
            </motion.div>
          )}
        </AnimatePresence>
      </Card>
    );
  }

  // Expanded state
  return (
    <motion.div
      variants={formVariants}
      initial="collapsed"
      animate="expanded"
    >
      <Card>
        <AnimatePresence mode="wait">
          <motion.div
            variants={contentVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="space-y-4"
          >
            {/* Title input */}
            <input
              ref={titleInputRef}
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Title (brief summary)"
              disabled={isSaving}
              className="w-full text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors disabled:opacity-50"
            />

            {/* Content textarea */}
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Write your observation..."
              disabled={isSaving}
              rows={5}
              className="w-full min-h-[120px] text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors resize-y disabled:opacity-50"
            />

            {/* Entry type selector */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-argus-text-dim">Type</label>
              <div className="flex flex-wrap gap-2">
                {ENTRY_TYPES.map((type) => {
                  const Icon = type.icon;
                  const isSelected = entryType === type.value;

                  return (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setEntryType(type.value)}
                      disabled={isSaving}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border transition-all disabled:opacity-50 ${
                        isSelected
                          ? `${type.bgClass} ${type.colorClass} border-current`
                          : 'bg-argus-surface-2 border-argus-border text-argus-text-dim hover:text-argus-text hover:border-argus-text-dim'
                      }`}
                    >
                      <Icon className="w-3.5 h-3.5" />
                      <span>{type.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Strategy link */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-argus-text-dim">
                Linked Strategy (optional)
              </label>
              <select
                value={strategyId}
                onChange={(e) => setStrategyId(e.target.value)}
                disabled={isSaving}
                className="w-full text-sm bg-argus-surface-2 border border-argus-border rounded-md px-3 py-2 text-argus-text focus:outline-none focus:border-argus-accent transition-colors disabled:opacity-50"
              >
                <option value="">None</option>
                {strategies.map((strategy) => (
                  <option key={strategy.strategy_id} value={strategy.strategy_id}>
                    {strategy.name}
                  </option>
                ))}
              </select>
            </div>

            {/* Tags */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-argus-text-dim">Tags</label>
              <JournalTagInput
                tags={tags}
                onChange={setTags}
                disabled={isSaving}
              />
            </div>

            {/* Linked Trades */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-argus-text-dim">
                Linked Trades (optional)
              </label>
              <TradeSearchInput
                linkedTradeIds={linkedTradeIds}
                onChange={setLinkedTradeIds}
                disabled={isSaving}
              />
            </div>

            {/* Action buttons */}
            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isSaving}
                className="flex items-center gap-1 px-3 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 text-argus-text-dim transition-colors disabled:opacity-50"
              >
                <X className="w-4 h-4" />
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving || !content.trim()}
                className="px-4 py-2 text-sm rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : isEditMode ? 'Update' : 'Save'}
              </button>
            </div>
          </motion.div>
        </AnimatePresence>
      </Card>
    </motion.div>
  );
}
