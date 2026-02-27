/**
 * Research Library tab for The Debrief page.
 *
 * Displays a unified view of all research documents:
 * - Filesystem documents (read-only, from repo)
 * - Database documents (full CRUD)
 *
 * Features:
 * - Category filter via SegmentedTab
 * - "Add Document" button for creating new database docs
 * - DocumentModal for reading
 * - DocumentEditor for create/edit
 * - ConfirmModal for delete confirmation
 * - Responsive grid layout (2 cols desktop, 1 col tablet/mobile)
 */

import { useState, useMemo } from 'react';
import { motion } from 'framer-motion';
import { Plus, FileText } from 'lucide-react';
import { ResearchDocCard } from './ResearchDocCard';
import { DocumentEditor } from './DocumentEditor';
import { DebriefSkeleton } from '../DebriefSkeleton';
import { DocumentModal } from '../../../components/DocumentModal';
import { ConfirmModal } from '../../../components/ConfirmModal';
import { EmptyState } from '../../../components/EmptyState';
import { SegmentedTab, type SegmentedTabSegment } from '../../../components/SegmentedTab';
import { useDebriefUI } from '../../../stores/debriefUI';
import { useDocuments, useDocument, useDeleteDocument } from '../../../hooks/useDocuments';
import type { ResearchDocument } from '../../../api/types';
import { DURATION, EASE } from '../../../utils/motion';

// Animation variants for list items
const listItemVariants = {
  hidden: { opacity: 0, y: 10 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: {
      delay: i * 0.05,
      duration: DURATION.normal,
      ease: EASE.out,
    },
  }),
};

const CATEGORY_SEGMENTS: SegmentedTabSegment[] = [
  { label: 'All', value: '' },
  { label: 'Research', value: 'research' },
  { label: 'Strategy', value: 'strategy' },
  { label: 'Backtest', value: 'backtest' },
  { label: 'AI Reports', value: 'ai_report' },
];

export function ResearchLibrary() {
  // Zustand state
  const researchCategoryFilter = useDebriefUI((s) => s.researchCategoryFilter);
  const setResearchCategoryFilter = useDebriefUI((s) => s.setResearchCategoryFilter);
  const editingDocumentId = useDebriefUI((s) => s.editingDocumentId);
  const setEditingDocumentId = useDebriefUI((s) => s.setEditingDocumentId);
  const readingDocumentId = useDebriefUI((s) => s.readingDocumentId);
  const setReadingDocumentId = useDebriefUI((s) => s.setReadingDocumentId);

  // Data fetching - pass category filter if set
  const { data, isLoading, error } = useDocuments(researchCategoryFilter ?? undefined);
  const { data: readingDocument } = useDocument(readingDocumentId);

  // Mutations
  const deleteMutation = useDeleteDocument();

  // Local state
  const [deletingDocument, setDeletingDocument] = useState<ResearchDocument | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  // Handle category filter change
  const handleCategoryChange = (value: string) => {
    setResearchCategoryFilter(value || null);
  };

  // Handle creating a new document
  const handleCreateDocument = () => {
    setIsCreating(true);
  };

  // Handle editor close
  const handleEditorClose = () => {
    setEditingDocumentId(null);
    setIsCreating(false);
  };

  // Handle delete confirmation
  const handleConfirmDelete = async () => {
    if (!deletingDocument) return;

    try {
      await deleteMutation.mutateAsync(deletingDocument.id);
      setDeletingDocument(null);
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  // If creating or editing, show editor instead of list
  if (isCreating) {
    return <DocumentEditor documentId={null} onClose={handleEditorClose} />;
  }

  if (editingDocumentId) {
    return (
      <DocumentEditor documentId={editingDocumentId} onClose={handleEditorClose} />
    );
  }

  // Loading state
  if (isLoading) {
    return <DebriefSkeleton section="research" />;
  }

  // Error state
  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <p className="text-argus-warning mb-2 text-sm">
          Unable to load documents
        </p>
        <p className="text-xs text-argus-text-dim">{error.message}</p>
      </div>
    );
  }

  // Sort documents: database docs (Custom) first, then filesystem (Repo), then by title
  const documents = useMemo(() => {
    return [...(data?.documents ?? [])].sort((a, b) => {
      // Database docs first
      if (a.source === 'database' && b.source !== 'database') return -1;
      if (a.source !== 'database' && b.source === 'database') return 1;
      // Then sort by title
      return a.title.localeCompare(b.title);
    });
  }, [data?.documents]);

  // Adapt document for DocumentModal (which expects StrategyDocument shape)
  const documentForModal = readingDocument
    ? {
        doc_id: readingDocument.id,
        title: readingDocument.title,
        filename: '', // Not used
        word_count: readingDocument.word_count,
        reading_time_min: readingDocument.reading_time_min,
        last_modified: readingDocument.updated_at,
        content: readingDocument.content,
      }
    : null;

  return (
    <>
      <div className="space-y-4">
        {/* Header row */}
        <div className="flex items-center justify-between flex-wrap gap-3">
          <h3 className="text-sm font-medium text-argus-text-dim">
            {documents.length > 0
              ? `${documents.length} document${documents.length !== 1 ? 's' : ''}`
              : 'Research Library'}
          </h3>

          <button
            onClick={handleCreateDocument}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md bg-argus-accent hover:bg-argus-accent/80 text-white font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Add Document</span>
          </button>
        </div>

        {/* Category filter */}
        <div className="overflow-x-auto -mx-4 px-4 pb-1">
          <SegmentedTab
            segments={CATEGORY_SEGMENTS}
            activeValue={researchCategoryFilter ?? ''}
            onChange={handleCategoryChange}
            size="sm"
            layoutId="research-category"
          />
        </div>

        {/* Documents grid */}
        {documents.length === 0 ? (
          <EmptyState
            icon={FileText}
            message={
              researchCategoryFilter
                ? 'No documents in this category.'
                : 'No documents yet. Create your first one!'
            }
            action={
              !researchCategoryFilter && (
                <button
                  onClick={handleCreateDocument}
                  className="text-sm text-argus-accent hover:underline"
                >
                  Create a document
                </button>
              )
            }
          />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {documents.map((doc, index) => (
              <motion.div
                key={doc.id}
                custom={index}
                initial="hidden"
                animate="visible"
                variants={listItemVariants}
              >
                <ResearchDocCard
                  document={doc}
                  onRead={() => setReadingDocumentId(doc.id)}
                  onEdit={
                    doc.is_editable
                      ? () => setEditingDocumentId(doc.id)
                      : undefined
                  }
                  onDelete={
                    doc.is_editable
                      ? () => setDeletingDocument(doc)
                      : undefined
                  }
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Document modal for reading */}
      <DocumentModal
        document={documentForModal}
        isOpen={!!readingDocumentId && !!readingDocument}
        onClose={() => setReadingDocumentId(null)}
      />

      {/* Delete confirmation modal */}
      <ConfirmModal
        isOpen={!!deletingDocument}
        title="Delete Document"
        message={`Are you sure you want to delete "${deletingDocument?.title}"? This action cannot be undone.`}
        confirmText="Delete"
        isLoading={deleteMutation.isPending}
        variant="danger"
        onConfirm={handleConfirmDelete}
        onCancel={() => setDeletingDocument(null)}
      />
    </>
  );
}
