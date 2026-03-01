import { memo } from 'react'
import type { QuoteResponse } from '@/lib/types'

interface QuoteItemProps {
  quote: QuoteResponse
}

export const QuoteItem = memo(function QuoteItem({ quote }: QuoteItemProps) {
  return (
    <li data-testid="quote-item" className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-blue-500 p-4">
      <blockquote data-testid="quote-text" className="text-sm text-gray-700 italic">
        &ldquo;{quote.content}&rdquo;
      </blockquote>
      <p
        data-testid="quote-interview-ref"
        className="text-xs text-gray-500 text-right mt-2"
      >
        ── Interview #{quote.interview_number}
      </p>
    </li>
  )
})
