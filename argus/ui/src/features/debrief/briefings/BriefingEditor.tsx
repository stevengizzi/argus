/**
 * Full-page briefing editor with markdown preview.
 *
 * Replaces the briefing list view when editing.
 * Features:
 * - Title input
 * - Status selector (draft/final)
 * - Side-by-side editor/preview on desktop
 * - Toggle between write/preview on mobile
 * - Unsaved changes indicator
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Code, Eye, AlertCircle } from 'lucide-react';
import { Card } from '../../../components/Card';
import { SegmentedTab, type SegmentedTabSegment } from '../../../components/SegmentedTab';
import { MarkdownRenderer } from '../../../components/MarkdownRenderer';
import { Skeleton } from '../../../components/Skeleton';
import { useBriefing, useUpdateBriefing } from '../../../hooks/useBriefings';
import { DURATION, EASE } from '../../../utils/motion';
import type { Briefing } from '../../../api/types';

interface BriefingEditorProps {
  /** Briefing ID when editing an existing briefing */
  briefingId?: string | null;
  /** Called when editor should close */
  onClose: () => void;
}

type EditorStatus = 'draft' | 'final';
type EditorMode = 'write' | 'preview';

const STATUS_SEGMENTS: SegmentedTabSegment[] = [
  { label: 'Draft', value: 'draft' },
  { label: 'Final', value: 'final' },
];

const MODE_SEGMENTS: SegmentedTabSegment[] = [
  { label: 'Write', value: 'write' },
  { label: 'Preview', value: 'preview' },
];

/**
 * Normalizes briefing status for editing (ai_generated → draft).
 */
function normalizeStatus(status: string): EditorStatus {
  return status === 'ai_generated' ? 'draft' : (status as EditorStatus);
}

/**
 * Main editor component that loads briefing data.
 */
export function BriefingEditor({
  briefingId,
  onClose,
}: BriefingEditorProps) {
  const { data: briefing, isLoading } = useBriefing(briefingId ?? null);

  if (isLoading) {
    return <EditorSkeleton onClose={onClose} />;
  }

  if (!briefing) {
    return <EditorSkeleton onClose={onClose} />;
  }

  // Key ensures the form remounts when briefing changes, resetting state
  return (
    <BriefingEditorForm
      key={briefing.id}
      briefing={briefing}
      onClose={onClose}
    />
  );
}

interface BriefingEditorFormProps {
  briefing: Briefing;
  onClose: () => void;
}

/**
 * Inner form component that receives briefing data as a prop.
 * Initializes state from props, avoiding the effect + setState pattern.
 */
function BriefingEditorForm({ briefing, onClose }: BriefingEditorFormProps) {
  const updateMutation = useUpdateBriefing();

  // Initialize state from briefing data (only runs once due to key-based remount)
  const [formState, setFormState] = useState(() => ({
    title: briefing.title,
    content: briefing.content,
    status: normalizeStatus(briefing.status),
  }));

  const [mode, setMode] = useState<EditorMode>('write');

  // Detect unsaved changes
  const hasUnsavedChanges = useMemo(() => {
    const originalStatus = normalizeStatus(briefing.status);
    return (
      formState.title !== briefing.title ||
      formState.content !== briefing.content ||
      formState.status !== originalStatus
    );
  }, [briefing, formState]);

  // Save handler
  const handleSave = useCallback(async () => {
    try {
      await updateMutation.mutateAsync({
        id: briefing.id,
        data: {
          title: formState.title,
          content: formState.content,
          status: formState.status,
        },
      });
      onClose();
    } catch (error) {
      console.error('Failed to save briefing:', error);
    }
  }, [briefing.id, formState, updateMutation, onClose]);

  // Cancel handler
  const handleCancel = useCallback(() => {
    onClose();
  }, [onClose]);

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && document.activeElement?.tagName !== 'TEXTAREA') {
        handleCancel();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave, handleCancel]);

  const isSaving = updateMutation.isPending;
  const saveError = updateMutation.error;

  // Update handlers
  const updateTitle = (value: string) => {
    setFormState((prev) => ({ ...prev, title: value }));
  };

  const updateContent = (value: string) => {
    setFormState((prev) => ({ ...prev, content: value }));
  };

  const updateStatus = (value: string) => {
    setFormState((prev) => ({ ...prev, status: value as EditorStatus }));
  };

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      transition={{ duration: DURATION.normal, ease: EASE.out }}
      className="space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button
            onClick={handleCancel}
            className="p-2 rounded-lg text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
            aria-label="Go back"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h2 className="text-lg font-semibold text-argus-text">Edit Briefing</h2>
          {hasUnsavedChanges && (
            <span className="flex items-center gap-1 text-xs text-argus-warning">
              <AlertCircle className="w-3 h-3" />
              Unsaved changes
            </span>
          )}
        </div>
      </div>

      {/* Title input */}
      <div>
        <label htmlFor="briefing-title" className="sr-only">
          Title
        </label>
        <input
          id="briefing-title"
          type="text"
          value={formState.title}
          onChange={(e) => updateTitle(e.target.value)}
          placeholder="Briefing title..."
          className="w-full px-4 py-3 text-lg font-medium bg-argus-surface-2 border border-argus-border rounded-lg text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors"
        />
      </div>

      {/* Status selector */}
      <div className="flex items-center justify-between">
        <SegmentedTab
          segments={STATUS_SEGMENTS}
          activeValue={formState.status}
          onChange={updateStatus}
          size="sm"
          layoutId="briefing-status"
        />

        {/* Mobile mode toggle */}
        <div className="lg:hidden">
          <SegmentedTab
            segments={MODE_SEGMENTS}
            activeValue={mode}
            onChange={(v) => setMode(v as EditorMode)}
            size="sm"
            layoutId="briefing-mode"
          />
        </div>
      </div>

      {/* Editor area */}
      <Card className="p-0 overflow-hidden">
        {/* Desktop: side-by-side */}
        <div className="hidden lg:grid lg:grid-cols-2">
          {/* Write panel */}
          <div className="border-r border-argus-border">
            <div className="flex items-center gap-2 px-4 py-2 border-b border-argus-border bg-argus-surface-2">
              <Code className="w-4 h-4 text-argus-text-dim" />
              <span className="text-xs font-medium text-argus-text-dim">Write</span>
            </div>
            <textarea
              value={formState.content}
              onChange={(e) => updateContent(e.target.value)}
              placeholder="Write your briefing in markdown..."
              className="w-full min-h-[400px] p-4 bg-argus-surface font-mono text-sm text-argus-text placeholder:text-argus-text-dim focus:outline-none resize-none"
              spellCheck={false}
            />
          </div>

          {/* Preview panel */}
          <div>
            <div className="flex items-center gap-2 px-4 py-2 border-b border-argus-border bg-argus-surface-2">
              <Eye className="w-4 h-4 text-argus-text-dim" />
              <span className="text-xs font-medium text-argus-text-dim">Preview</span>
            </div>
            <div className="min-h-[400px] p-4 overflow-y-auto">
              {formState.content ? (
                <MarkdownRenderer content={formState.content} />
              ) : (
                <p className="text-sm text-argus-text-dim italic">
                  Preview will appear here...
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Mobile: toggle between write/preview */}
        <div className="lg:hidden">
          {mode === 'write' ? (
            <>
              <div className="flex items-center gap-2 px-4 py-2 border-b border-argus-border bg-argus-surface-2">
                <Code className="w-4 h-4 text-argus-text-dim" />
                <span className="text-xs font-medium text-argus-text-dim">Write</span>
              </div>
              <textarea
                value={formState.content}
                onChange={(e) => updateContent(e.target.value)}
                placeholder="Write your briefing in markdown..."
                className="w-full min-h-[400px] p-4 bg-argus-surface font-mono text-sm text-argus-text placeholder:text-argus-text-dim focus:outline-none resize-none"
                spellCheck={false}
              />
            </>
          ) : (
            <>
              <div className="flex items-center gap-2 px-4 py-2 border-b border-argus-border bg-argus-surface-2">
                <Eye className="w-4 h-4 text-argus-text-dim" />
                <span className="text-xs font-medium text-argus-text-dim">Preview</span>
              </div>
              <div className="min-h-[400px] p-4 overflow-y-auto">
                {formState.content ? (
                  <MarkdownRenderer content={formState.content} />
                ) : (
                  <p className="text-sm text-argus-text-dim italic">
                    Preview will appear here...
                  </p>
                )}
              </div>
            </>
          )}
        </div>
      </Card>

      {/* Error message */}
      {saveError && (
        <div className="flex items-center gap-2 p-3 rounded-lg bg-argus-loss/10 border border-argus-loss/30">
          <AlertCircle className="w-4 h-4 text-argus-loss flex-shrink-0" />
          <p className="text-sm text-argus-loss">
            Failed to save: {saveError.message}
          </p>
        </div>
      )}

      {/* Footer actions */}
      <div className="flex items-center justify-end gap-3">
        <button
          onClick={handleCancel}
          disabled={isSaving}
          className="px-4 py-2 text-sm rounded-md border border-argus-border bg-argus-surface hover:bg-argus-surface-2 text-argus-text transition-colors disabled:opacity-50"
        >
          Cancel
        </button>
        <button
          onClick={handleSave}
          disabled={isSaving || !formState.title.trim()}
          className="px-4 py-2 text-sm rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save'}
        </button>
      </div>
    </motion.div>
  );
}

/**
 * Loading skeleton for the editor.
 */
function EditorSkeleton({ onClose }: { onClose: () => void }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onClose}
          className="p-2 rounded-lg text-argus-text-dim hover:text-argus-text hover:bg-argus-surface-2 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <Skeleton variant="line" width={120} height={24} />
      </div>
      <Skeleton variant="rect" height={52} className="rounded-lg" />
      <Skeleton variant="rect" width={200} height={36} className="rounded-lg" />
      <Skeleton variant="rect" height={400} className="rounded-lg" />
      <div className="flex justify-end gap-3">
        <Skeleton variant="rect" width={80} height={36} className="rounded-md" />
        <Skeleton variant="rect" width={80} height={36} className="rounded-md" />
      </div>
    </div>
  );
}
