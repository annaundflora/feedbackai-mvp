import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { ProjectTabs } from '@/components/project-tabs'
import { FactItem } from '@/components/fact-item'
import { QuoteItem } from '@/components/quote-item'
import { ClusterDetailSkeleton } from '@/components/cluster-detail-skeleton'
import type { ClusterDetailResponse } from '@/lib/types'

// React.cache for per-request deduplication (server-cache-react rule)
const getClusterDetail = cache(
  (projectId: string, clusterId: string) =>
    apiClient.getClusterDetail(projectId, clusterId)
)

interface ClusterDetailContentProps {
  projectId: string
  clusterId: string
}

async function ClusterDetailContent({ projectId, clusterId }: ClusterDetailContentProps) {
  const cluster: ClusterDetailResponse = await getClusterDetail(projectId, clusterId)

  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <h1
          data-testid="cluster-detail-name"
          className="text-xl font-bold text-gray-900"
        >
          {cluster.name}
        </h1>
        <div className="flex gap-2 shrink-0 ml-4">
          <button
            type="button"
            data-testid="merge-btn"
            disabled
            aria-disabled="true"
            aria-label="Merge cluster (available in next version)"
            className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-gray-400 bg-gray-100 border border-gray-200 rounded-lg cursor-not-allowed"
          >
            Merge ▼
          </button>
          <button
            type="button"
            data-testid="split-btn"
            disabled
            aria-disabled="true"
            aria-label="Split cluster (available in next version)"
            className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-400 bg-gray-100 border border-gray-200 rounded-lg cursor-not-allowed"
          >
            Split
          </button>
        </div>
      </div>

      {/* Summary */}
      {cluster.summary !== null ? (
        <section aria-label="Cluster summary" className="mb-8">
          <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-3">
            Summary
          </h2>
          <p
            data-testid="cluster-summary"
            className="text-sm text-gray-700 leading-relaxed"
          >
            {cluster.summary}
          </p>
        </section>
      ) : null}

      <hr className="border-gray-200 mb-8" />

      {/* Facts Section */}
      <section data-testid="facts-section" aria-label="Facts" className="mb-8">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
          Facts{' '}
          <span data-testid="facts-count" className="font-normal text-gray-500">
            ({cluster.facts.length})
          </span>
        </h2>

        {cluster.facts.length === 0 ? (
          <p
            data-testid="facts-empty-state"
            className="text-sm text-gray-500 italic"
          >
            No facts extracted yet.
          </p>
        ) : (
          <ol className="space-y-3">
            {cluster.facts.map((fact, index) => (
              <FactItem key={fact.id} fact={fact} index={index} />
            ))}
          </ol>
        )}
      </section>

      {/* Quotes Section — only rendered when at least 1 quote present */}
      {cluster.quotes.length > 0 ? (
        <>
          <hr className="border-gray-200 mb-8" />
          <section data-testid="quotes-section" aria-label="Supporting quotes">
            <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wide mb-4">
              Quotes
            </h2>
            <ul className="space-y-3">
              {cluster.quotes.map(quote => (
                <QuoteItem key={quote.fact_id} quote={quote} />
              ))}
            </ul>
          </section>
        </>
      ) : null}
    </>
  )
}

interface Props {
  params: Promise<{ id: string; cluster_id: string }>
}

export default async function ClusterDetailPage({ params }: Props) {
  const { id, cluster_id } = await params

  return (
    <main className="max-w-4xl mx-auto px-4 py-8">
      {/* Back navigation */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          href={`/projects/${id}`}
          data-testid="back-to-clusters"
          aria-label="Back to project clusters"
          className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          ← Back to Clusters
        </Link>
      </div>

      <ProjectTabs projectId={id} activeTab="insights" />

      <Suspense fallback={<ClusterDetailSkeleton />}>
        <ClusterDetailContent projectId={id} clusterId={cluster_id} />
      </Suspense>
    </main>
  )
}
