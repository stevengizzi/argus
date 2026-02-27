/**
 * Journal-specific tag input with autocomplete suggestions.
 *
 * Thin wrapper around TagInput that provides journal-specific
 * suggestions via the useJournalTags() hook.
 */

import { TagInput } from '../../../components/TagInput';
import { useJournalTags } from '../../../hooks/useJournal';

interface JournalTagInputProps {
  /** Current list of tags */
  tags: string[];
  /** Callback when tags change */
  onChange: (tags: string[]) => void;
  /** Disable input */
  disabled?: boolean;
}

export function JournalTagInput({ tags, onChange, disabled = false }: JournalTagInputProps) {
  const { data } = useJournalTags();
  const suggestions = data?.tags ?? [];

  return (
    <TagInput
      tags={tags}
      onChange={onChange}
      suggestions={suggestions}
      placeholder="Add tags..."
      disabled={disabled}
    />
  );
}
