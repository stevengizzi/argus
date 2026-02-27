/**
 * Full-page document editor with markdown preview.
 *
 * Replaces the research library view when editing or creating.
 * Features:
 * - Title input
 * - Category selector
 * - Side-by-side editor/preview on desktop
 * - Toggle between write/preview on mobile
 * - Tag input with autocomplete
 * - Unsaved changes indicator
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { motion } from 'framer-motion';
import { ArrowLeft, Code, Eye, AlertCircle } from 'lucide-react';
import { Card } from '../../../components/Card';
import { SegmentedTab, type SegmentedTabSegment } from '../../../components/SegmentedTab';
import { MarkdownRenderer } from '../../../components/MarkdownRenderer';
import { TagInput } from '../../../components/TagInput';
import { Skeleton } from '../../../components/Skeleton';
import {
  useDocument,
  useCreateDocument,
  useUpdateDocument,
  useDocumentTags,
} from '../../../hooks/useDocuments';
import { DURATION, EASE } from '../../../utils/motion';
import type { ResearchDocument } from '../../../api/types';

interface DocumentEditorProps {
  /** Document ID when editing an existing document, null for create mode */
  documentId: string | null;
  /** Called when editor should close */
  onClose: () => void;
}

type DocumentCategory = 'research' | 'strategy' | 'backtest' | 'ai_report';
type EditorMode = 'write' | 'preview';

const CATEGORY_SEGMENTS: SegmentedTabSegment[] = [
  { label: 'Research', value: 'research' },
  { label: 'Strategy', value: 'strategy' },
  { label: 'Backtest', value: 'backtest' },
  { label: 'AI Report', value: 'ai_report' },
];

const MODE_SEGMENTS: SegmentedTabSegment[] = [
  { label: 'Write', value: 'write' },
  { label: 'Preview', value: 'preview' },
];

interface FormState {
  title: string;
  content: string;
  category: DocumentCategory;
  tags: string[];
}

const initialFormState: FormState = {
  title: '',
  content: '',
  category: 'research',
  tags: [],
};

/**
 * Main editor component that loads document data if editing.
 */
export function DocumentEditor({ documentId, onClose }: DocumentEditorProps) {
  const isCreateMode = documentId === null;
  const { data: document, isLoading } = useDocument(documentId);
  const { data: tagsData } = useDocumentTags();

  // For create mode, render form immediately
  if (isCreateMode) {
    return (
      <DocumentEditorForm
        key="new"
        document={null}
        existingTags={tagsData?.tags ?? []}
        onClose={onClose}
      />
    );
  }

  // For edit mode, wait for document to load
  if (isLoading) {
    return <EditorSkeleton onClose={onClose} />;
  }

  if (!document) {
    return <EditorSkeleton onClose={onClose} />;
  }

  // Key ensures the form remounts when document changes, resetting state
  return (
    <DocumentEditorForm
      key={document.id}
      document={document}
      existingTags={tagsData?.tags ?? []}
      onClose={onClose}
    />
  );
}

interface DocumentEditorFormProps {
  document: ResearchDocument | null;
  existingTags: string[];
  onClose: () => void;
}

/**
 * Inner form component that receives document data as a prop.
 * Initializes state from props, avoiding the effect + setState pattern.
 */
function DocumentEditorForm({
  document: doc,
  existingTags,
  onClose,
}: DocumentEditorFormProps) {
  const isCreateMode = doc === null;
  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();

  // Initialize state from document data (only runs once due to key-based remount)
  const [formState, setFormState] = useState<FormState>(() =>
    doc
      ? {
          title: doc.title,
          content: doc.content,
          category: doc.category,
          tags: doc.tags,
        }
      : initialFormState
  );

  const [mode, setMode] = useState<EditorMode>('write');

  // Detect unsaved changes
  const hasUnsavedChanges = useMemo(() => {
    if (isCreateMode) {
      return (
        formState.title.trim() !== '' ||
        formState.content.trim() !== '' ||
        formState.tags.length > 0
      );
    }
    return (
      formState.title !== doc?.title ||
      formState.content !== doc?.content ||
      formState.category !== doc?.category ||
      JSON.stringify(formState.tags) !== JSON.stringify(doc?.tags ?? [])
    );
  }, [doc, formState, isCreateMode]);

  // Save handler
  const handleSave = useCallback(async () => {
    if (!formState.title.trim()) return;

    try {
      if (isCreateMode) {
        await createMutation.mutateAsync({
          title: formState.title,
          content: formState.content,
          category: formState.category,
          tags: formState.tags,
        });
      } else {
        await updateMutation.mutateAsync({
          id: doc!.id,
          data: {
            title: formState.title,
            content: formState.content,
            category: formState.category,
            tags: formState.tags,
          },
        });
      }
      onClose();
    } catch (error) {
      console.error('Failed to save document:', error);
    }
  }, [formState, isCreateMode, createMutation, updateMutation, doc, onClose]);

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

  const isSaving = createMutation.isPending || updateMutation.isPending;
  const saveError = createMutation.error || updateMutation.error;

  // Update handlers
  const updateTitle = (value: string) => {
    setFormState((prev) => ({ ...prev, title: value }));
  };

  const updateContent = (value: string) => {
    setFormState((prev) => ({ ...prev, content: value }));
  };

  const updateCategory = (value: string) => {
    setFormState((prev) => ({ ...prev, category: value as DocumentCategory }));
  };

  const updateTags = (tags: string[]) => {
    setFormState((prev) => ({ ...prev, tags }));
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
          <h2 className="text-lg font-semibold text-argus-text">
            {isCreateMode ? 'New Document' : 'Edit Document'}
          </h2>
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
        <label htmlFor="document-title" className="sr-only">
          Title
        </label>
        <input
          id="document-title"
          type="text"
          value={formState.title}
          onChange={(e) => updateTitle(e.target.value)}
          placeholder="Document title..."
          className="w-full px-4 py-3 text-lg font-medium bg-argus-surface-2 border border-argus-border rounded-lg text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors"
        />
      </div>

      {/* Category selector + mobile mode toggle */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <SegmentedTab
          segments={CATEGORY_SEGMENTS}
          activeValue={formState.category}
          onChange={updateCategory}
          size="sm"
          layoutId="document-category"
        />

        {/* Mobile mode toggle */}
        <div className="lg:hidden">
          <SegmentedTab
            segments={MODE_SEGMENTS}
            activeValue={mode}
            onChange={(v) => setMode(v as EditorMode)}
            size="sm"
            layoutId="document-mode"
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
              placeholder="Write your document in markdown..."
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
                placeholder="Write your document in markdown..."
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

      {/* Tags input */}
      <div>
        <label className="block text-sm font-medium text-argus-text-dim mb-2">
          Tags
        </label>
        <TagInput
          tags={formState.tags}
          onChange={updateTags}
          suggestions={existingTags}
          placeholder="Add tags..."
        />
      </div>

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
          {isSaving ? 'Saving...' : isCreateMode ? 'Create' : 'Save'}
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
      <Skeleton variant="rect" width={300} height={36} className="rounded-lg" />
      <Skeleton variant="rect" height={400} className="rounded-lg" />
      <Skeleton variant="rect" height={40} className="rounded-md" />
      <div className="flex justify-end gap-3">
        <Skeleton variant="rect" width={80} height={36} className="rounded-md" />
        <Skeleton variant="rect" width={80} height={36} className="rounded-md" />
      </div>
    </div>
  );
}
