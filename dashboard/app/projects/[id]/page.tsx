import { Suspense } from 'react'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { getAuthToken } from '@/lib/auth'
import { SkeletonCard } from '@/components/skeleton-card'
import { ProjectInsightsClient } from './insights-client'

// React.cache for deduplication if getProject is called multiple times on same page
const getProject = cache(apiClient.getProject.bind(apiClient))
const getClusters = cache(apiClient.getClusters.bind(apiClient))

async function ProjectInsights({ id }: { id: string }) {
  const [project, clusters, token] = await Promise.all([
    getProject(id),
    getClusters(id),
    getAuthToken(),
  ])

  return (
    <ProjectInsightsClient
      projectId={id}
      initialProject={project}
      initialClusters={clusters}
      token={token ?? ''}
    />
  )
}

interface Props {
  params: Promise<{ id: string }>
}

export default async function ProjectPage({ params }: Props) {
  const { id } = await params

  return (
    <Suspense
      fallback={
        <div aria-busy="true" className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      }
    >
      <ProjectInsights id={id} />
    </Suspense>
  )
}
