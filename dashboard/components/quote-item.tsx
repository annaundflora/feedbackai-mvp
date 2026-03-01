import { memo } from 'react'
import Link from 'next/link'
import type { QuoteResponse } from '@/lib/types'

interface QuoteItemProps {
  quote: QuoteResponse
  projectId: string
}

export const QuoteItem = memo(function QuoteItem({ quote, projectId }: QuoteItemProps) {
  return (
    <li data-testid="quote-item" className="bg-white rounded-lg border border-gray-200 border-l-4 border-l-blue-500 p-4">
      <blockquote data-testid="quote-text" className="text-sm text-gray-700 italic">
        &ldquo;{quote.content}&rdquo;
      </blockquote>
      <Link
        href={`/projects/${projectId}/interviews/${quote.interview_id}`}
        data-testid="quote-interview-ref"
        className="block text-xs text-gray-500 text-right mt-2 hover:text-blue-600 transition-colors"
      >
        ── Interview #{quote.interview_number}
      </Link>
    </li>
  )
})
