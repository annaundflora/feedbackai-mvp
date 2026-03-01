import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { SkeletonCard } from '@/components/skeleton-card'
import { ProjectInsightsClient } from './insights-client'

// React.cache for deduplication if getProject is called multiple times on same page
const getProject = cache(apiClient.getProject.bind(apiClient))
const getClusters = cache(apiClient.getClusters.bind(apiClient))

async function ProjectInsights({ id }: { id: string }) {
  const [project, clusters] = await Promise.all([
    getProject(id),
    getClusters(id),
  ])

  return (
    <ProjectInsightsClient
      projectId={id}
      initialProject={project}
      initialClusters={clusters}
    />
  )
}

interface Props {
  params: Promise<{ id: string }>
}

export default async function ProjectPage({ params }: Props) {
  const { id } = await params

  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/projects"
          data-testid="back-to-projects"
          aria-label="Back to projects"
          className="text-sm text-gray-500 hover:text-gray-900 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
        >
          ← Projects
        </Link>
      </div>

      <Suspense
        fallback={
          <div aria-busy="true">
            <div className="h-8 bg-gray-200 rounded w-64 mb-2 animate-pulse" />
            <div className="h-4 bg-gray-200 rounded w-96 mb-6 animate-pulse" />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </div>
          </div>
        }
      >
        <ProjectInsights id={id} />
      </Suspense>
    </main>
  )
}
