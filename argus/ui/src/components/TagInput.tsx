/**
 * Tag input component with autocomplete suggestions.
 *
 * Features:
 * - Text input with filtered suggestions dropdown
 * - Add tag on Enter or click suggestion
 * - Removable tag chips displayed above input
 * - Prevents duplicate tags
 *
 * Used by Research Library and Learning Journal.
 */

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { X } from 'lucide-react';

interface TagInputProps {
  /** Current list of tags */
  tags: string[];
  /** Callback when tags change */
  onChange: (tags: string[]) => void;
  /** Autocomplete suggestions */
  suggestions: string[];
  /** Input placeholder */
  placeholder?: string;
  /** Disable input */
  disabled?: boolean;
}

export function TagInput({
  tags,
  onChange,
  suggestions,
  placeholder = 'Add tags...',
  disabled = false,
}: TagInputProps) {
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Filter suggestions based on input (case-insensitive), excluding already added tags
  const filteredSuggestions = useMemo(() => {
    if (!inputValue.trim()) return [];

    const lowerInput = inputValue.toLowerCase();
    return suggestions.filter(
      (s) =>
        s.toLowerCase().includes(lowerInput) &&
        !tags.includes(s)
    );
  }, [inputValue, suggestions, tags]);

  // Add a tag
  const addTag = useCallback(
    (tag: string) => {
      const trimmed = tag.trim();
      if (trimmed && !tags.includes(trimmed)) {
        onChange([...tags, trimmed]);
      }
      setInputValue('');
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    },
    [tags, onChange]
  );

  // Remove a tag
  const removeTag = useCallback(
    (tagToRemove: string) => {
      onChange(tags.filter((t) => t !== tagToRemove));
    },
    [tags, onChange]
  );

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (highlightedIndex >= 0 && highlightedIndex < filteredSuggestions.length) {
        addTag(filteredSuggestions[highlightedIndex]);
      } else if (inputValue.trim()) {
        addTag(inputValue);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setHighlightedIndex((prev) =>
        Math.min(prev + 1, filteredSuggestions.length - 1)
      );
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setHighlightedIndex((prev) => Math.max(prev - 1, -1));
    } else if (e.key === 'Escape') {
      setShowSuggestions(false);
      setHighlightedIndex(-1);
    } else if (e.key === 'Backspace' && !inputValue && tags.length > 0) {
      // Remove last tag on backspace when input is empty
      removeTag(tags[tags.length - 1]);
    }
  };

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setShowSuggestions(false);
        setHighlightedIndex(-1);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Show suggestions when input has value
  useEffect(() => {
    setShowSuggestions(inputValue.trim().length > 0 && filteredSuggestions.length > 0);
    setHighlightedIndex(-1);
  }, [inputValue, filteredSuggestions.length]);

  return (
    <div ref={containerRef} className="relative">
      {/* Tag chips */}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {tags.map((tag) => (
            <span
              key={tag}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-full bg-argus-surface-2 text-argus-text"
            >
              {tag}
              <button
                type="button"
                onClick={() => removeTag(tag)}
                disabled={disabled}
                className="p-0.5 rounded-full hover:bg-argus-surface-3 transition-colors disabled:opacity-50"
                aria-label={`Remove ${tag}`}
              >
                <X className="w-3 h-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Input */}
      <input
        ref={inputRef}
        type="text"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={() => {
          if (inputValue.trim() && filteredSuggestions.length > 0) {
            setShowSuggestions(true);
          }
        }}
        placeholder={placeholder}
        disabled={disabled}
        className="w-full px-3 py-2 text-sm bg-argus-surface-2 border border-argus-border rounded-md text-argus-text placeholder:text-argus-text-dim focus:outline-none focus:border-argus-accent transition-colors disabled:opacity-50"
      />

      {/* Suggestions dropdown */}
      {showSuggestions && filteredSuggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-1 py-1 bg-argus-surface border border-argus-border rounded-lg shadow-xl max-h-40 overflow-y-auto">
          {filteredSuggestions.map((suggestion, index) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => addTag(suggestion)}
              className={`w-full px-3 py-2 text-sm text-left transition-colors ${
                index === highlightedIndex
                  ? 'bg-argus-surface-2 text-argus-text'
                  : 'text-argus-text-dim hover:bg-argus-surface-2 hover:text-argus-text'
              }`}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
