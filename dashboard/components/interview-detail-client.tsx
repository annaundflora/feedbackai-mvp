'use client'

import Link from 'next/link'
import type { InterviewDetailResponse } from '@/lib/types'

interface InterviewDetailClientProps {
  projectId: string
  interview: InterviewDetailResponse
}

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  completed: { label: 'completed', className: 'bg-green-100 text-green-700' },
  pending: { label: 'pending', className: 'bg-yellow-100 text-yellow-700' },
  running: { label: 'running', className: 'bg-yellow-100 text-yellow-700' },
  failed: { label: 'failed', className: 'bg-red-100 text-red-700' },
}

export function InterviewDetailClient({
  projectId,
  interview,
}: InterviewDetailClientProps) {
  const extractionBadge = STATUS_BADGE[interview.extraction_status] ?? STATUS_BADGE.pending
  const clusteringBadge = STATUS_BADGE[interview.clustering_status] ?? STATUS_BADGE.pending

  return (
    <>
      {/* Header */}
      <div className="mb-6">
        <h1
          data-testid="interview-detail-title"
          className="text-xl font-bold text-gray-900 mb-2"
        >
          Interview #{interview.interview_number}
        </h1>
        <div className="flex items-center flex-wrap gap-3 text-sm text-gray-500">
          <span>
            {new Date(interview.date).toLocaleDateString('en-US', {
              year: 'numeric',
              month: 'short',
              day: 'numeric',
            })}
          </span>
          <span>{interview.message_count} messages</span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${extractionBadge.className}`}
            data-testid="extraction-status-badge"
          >
            extraction: {extractionBadge.label}
          </span>
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${clusteringBadge.className}`}
            data-testid="clustering-status-badge"
          >
            clustering: {clusteringBadge.label}
          </span>
        </div>
      </div>

      {/* Summary */}
      {interview.summary ? (
        <section aria-label="Interview summary" className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Summary
          </h2>
          <p
            data-testid="interview-summary"
            className="text-sm text-gray-700 leading-relaxed"
          >
            {interview.summary}
          </p>
        </section>
      ) : null}

      <hr className="border-gray-200 mb-8" />

      {/* Transcript */}
      <section aria-label="Transcript" className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
          Transcript{' '}
          <span className="font-normal text-gray-500">
            ({interview.transcript.length} messages)
          </span>
        </h2>

        {interview.transcript.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No transcript available.</p>
        ) : (
          <div data-testid="transcript-section" className="space-y-3">
            {interview.transcript.map((msg, i) => {
              const isUser = msg.role === 'user' || msg.role === 'human'
              const roleLabel = isUser ? 'User' : 'AI'
              return (
                <div
                  key={i}
                  className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[80%] ${isUser ? 'text-right' : 'text-left'}`}>
                    <span className="text-[11px] font-medium text-gray-400 mb-1 block">
                      {roleLabel}
                    </span>
                    <div
                      className={`rounded-2xl px-4 py-2.5 text-sm ${
                        isUser
                          ? 'bg-blue-600 text-white rounded-br-sm'
                          : 'bg-gray-100 text-gray-800 rounded-bl-sm'
                      }`}
                    >
                      <p className="whitespace-pre-wrap text-left">{msg.content}</p>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      <hr className="border-gray-200 mb-8" />

      {/* Facts */}
      <section data-testid="interview-facts-section" aria-label="Extracted facts">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
          Facts{' '}
          <span className="font-normal text-gray-500">
            ({interview.fact_count})
          </span>
        </h2>

        {interview.facts.length === 0 ? (
          <p className="text-sm text-gray-500 italic">No facts extracted yet.</p>
        ) : (
          <ol className="space-y-3">
            {interview.facts.map((fact, index) => (
              <li
                key={fact.id}
                data-testid="interview-fact-item"
                className="bg-white rounded-lg border border-gray-200 p-4"
              >
                <div className="flex items-start gap-3">
                  <span className="text-sm font-semibold text-gray-500 min-w-[1.5rem] shrink-0">
                    {index + 1}.
                  </span>
                  <div className="flex-1">
                    <p className="text-sm text-gray-900">{fact.content}</p>
                    {fact.quote ? (
                      <blockquote className="mt-2 text-xs text-gray-500 italic border-l-2 border-gray-200 pl-2">
                        &ldquo;{fact.quote}&rdquo;
                      </blockquote>
                    ) : null}
                    <div className="flex items-center gap-2 mt-2">
                      {fact.cluster_id ? (
                        <Link
                          href={`/projects/${projectId}/clusters/${fact.cluster_id}`}
                          className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors"
                        >
                          {fact.cluster_name ?? 'Cluster'}
                        </Link>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-50 text-gray-500 border border-gray-200">
                          Unassigned
                        </span>
                      )}
                      {fact.confidence !== null ? (
                        <span className="text-xs text-gray-500">
                          Confidence: {fact.confidence}
                        </span>
                      ) : null}
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </>
  )
}
