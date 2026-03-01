import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { ClusterDetailSkeleton } from '@/components/cluster-detail-skeleton'
import type { ClusterDetailResponse } from '@/lib/types'
import { ClusterDetailClient } from './cluster-detail-client'

// React.cache for per-request deduplication (server-cache-react rule)
const getClusterDetail = cache(
  (projectId: string, clusterId: string) =>
    apiClient.getClusterDetail(projectId, clusterId)
)

const getClusters = cache(
  (projectId: string) => apiClient.getClusters(projectId)
)

interface ClusterDetailContentProps {
  projectId: string
  clusterId: string
}

async function ClusterDetailContent({
  projectId,
  clusterId,
}: ClusterDetailContentProps) {
  const [cluster, allClusters] = await Promise.all([
    getClusterDetail(projectId, clusterId),
    getClusters(projectId),
  ])

  const otherClusters = allClusters.filter((c) => c.id !== clusterId)

  return (
    <ClusterDetailClient
      projectId={projectId}
      initialCluster={cluster}
      otherClusters={otherClusters}
    />
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

      <Suspense fallback={<ClusterDetailSkeleton />}>
        <ClusterDetailContent projectId={id} clusterId={cluster_id} />
      </Suspense>
    </main>
  )
}
