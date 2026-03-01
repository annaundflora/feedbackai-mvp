'use client'

import type { SuggestionResponse } from '@/lib/types'

interface SuggestionBannerProps {
  suggestion: SuggestionResponse
  onAccept: (suggestionId: string) => Promise<void>
  onDismiss: (suggestionId: string) => Promise<void>
}

export function SuggestionBanner({
  suggestion,
  onAccept,
  onDismiss,
}: SuggestionBannerProps) {
  const isMerge = suggestion.type === 'merge'
  const description = isMerge
    ? `Merge "${suggestion.source_cluster_name}" with "${suggestion.target_cluster_name}"${
        suggestion.similarity_score
          ? ` (${Math.round(suggestion.similarity_score * 100)}% similar)`
          : ''
      }`
    : `Split "${suggestion.source_cluster_name}" into sub-clusters`

  return (
    <div
      role="alert"
      aria-label={`Suggestion: ${description}`}
      className="flex items-center justify-between gap-4 px-4 py-3 bg-amber-50 border border-amber-200 rounded-lg text-sm"
      data-testid="suggestion-banner"
    >
      <div className="flex items-center gap-2 min-w-0">
        <span aria-hidden="true" className="flex-shrink-0 text-amber-500">
          ⚡
        </span>
        <span className="text-gray-700 truncate">
          <span className="font-medium">Suggestion:</span> {description}
        </span>
      </div>
      <div className="flex gap-2 flex-shrink-0">
        <button
          onClick={() => onDismiss(suggestion.id)}
          className="px-3 py-1.5 text-xs border border-gray-300 rounded-lg hover:bg-gray-50 focus-visible:ring-2 focus-visible:ring-gray-400"
          data-testid="suggestion-dismiss"
        >
          Dismiss
        </button>
        <button
          onClick={() => onAccept(suggestion.id)}
          className="px-3 py-1.5 text-xs bg-amber-500 text-white rounded-lg hover:bg-amber-600 focus-visible:ring-2 focus-visible:ring-amber-400"
          data-testid="suggestion-accept"
        >
          {isMerge ? 'Merge' : 'Split'}
        </button>
      </div>
    </div>
  )
}
