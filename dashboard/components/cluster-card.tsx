import { memo } from 'react'
import Link from 'next/link'
import type { ClusterResponse } from '@/lib/types'

interface ClusterCardProps {
  cluster: ClusterResponse
  projectId: string
}

export const ClusterCard = memo(function ClusterCard({ cluster, projectId }: ClusterCardProps) {
  return (
    <Link
      href={`/projects/${projectId}/clusters/${cluster.id}`}
      data-testid="cluster-card"
      className="block cursor-pointer focus-visible:ring-2 focus-visible:ring-blue-500 rounded-xl"
      aria-label={`View cluster: ${cluster.name}`}
    >
      <article
        className="bg-white rounded-xl border border-gray-200 shadow-sm p-5 hover:shadow-md transition-shadow duration-200"
      >
        <div className="flex items-start justify-between">
          <h3
            data-testid="cluster-name"
            className="text-base font-semibold text-gray-900"
          >
            {cluster.name}
          </h3>
          <button
            type="button"
            aria-label="Cluster options"
            className="text-gray-400 hover:text-gray-600 focus-visible:ring-2 focus-visible:ring-blue-500 rounded p-1 -mr-1 -mt-1"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
            }}
          >
            ⋮
          </button>
        </div>

        <div className="flex gap-4 mt-2">
          <span data-testid="cluster-fact-count" className="text-sm text-gray-600">
            ● {cluster.fact_count} Facts
          </span>
          <span data-testid="cluster-interview-count" className="text-sm text-gray-600">
            ● {cluster.interview_count} Interviews
          </span>
        </div>

        {cluster.summary !== null ? (
          <p className="text-sm text-gray-600 mt-2 line-clamp-3">
            {cluster.summary}
          </p>
        ) : (
          <p className="text-sm text-gray-400 mt-2 italic">
            Generating summary…
          </p>
        )}
      </article>
    </Link>
  )
})
