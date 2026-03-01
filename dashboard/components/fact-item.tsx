import { memo } from 'react'
import type { FactResponse } from '@/lib/types'

interface FactItemProps {
  fact: FactResponse
  index: number
}

export const FactItem = memo(function FactItem({ fact, index }: FactItemProps) {
  const number = index + 1

  return (
    <li
      data-testid="fact-item"
      className="bg-white rounded-lg border border-gray-200 p-4"
    >
      <div className="flex items-start gap-3">
        <span
          data-testid="fact-number"
          className="text-sm font-semibold text-gray-500 min-w-[1.5rem] shrink-0"
        >
          {number}.
        </span>
        <div className="flex-1">
          <p
            data-testid="fact-content"
            className="text-sm text-gray-900"
          >
            {fact.content}
          </p>
          <div className="flex items-center flex-wrap gap-2 mt-2">
            <span
              data-testid="fact-interview-badge"
              aria-label={`Source: Interview #${number}`}
              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200"
            >
              Interview #{number}
            </span>
            {fact.confidence !== null ? (
              <span
                data-testid="fact-confidence"
                className="text-xs text-gray-500"
              >
                Confidence: {fact.confidence}
              </span>
            ) : null}
          </div>
        </div>
      </div>
    </li>
  )
})
