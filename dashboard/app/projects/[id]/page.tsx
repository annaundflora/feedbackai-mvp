import { Suspense } from 'react'
import Link from 'next/link'
import { cache } from 'react'
import { apiClient } from '@/lib/api-client'
import { ClusterCard } from '@/components/cluster-card'
import { StatusBar } from '@/components/status-bar'
import { ProjectTabs } from '@/components/project-tabs'
import { EmptyState } from '@/components/empty-state'
import { SkeletonCard } from '@/components/skeleton-card'

// React.cache for deduplication if getProject is called multiple times on same page
const getProject = cache(apiClient.getProject.bind(apiClient))
const getClusters = cache(apiClient.getClusters.bind(apiClient))

async function ProjectInsights({ id }: { id: string }) {
  // Promise.all for parallel fetching (async-parallel rule)
  const [project, clusters] = await Promise.all([
    getProject(id),
    getClusters(id),
  ])

  return (
    <>
      <header className="mb-6">
        <h2
          data-testid="project-title"
          className="text-2xl font-bold text-gray-900"
        >
          {project.name}
        </h2>
        <p data-testid="project-research-goal" className="text-gray-600 mt-1">
          {project.research_goal}
        </p>
      </header>

      <ProjectTabs projectId={id} activeTab="insights" />

      <StatusBar
        interviewCount={project.interview_count}
        factCount={project.fact_count}
        clusterCount={project.cluster_count}
      />

      {clusters.length === 0 ? (
        <EmptyState
          data-testid="clusters-empty-state"
          message="No clusters yet."
          ctaLabel="Assign interviews to get started"
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
          {clusters.map(cluster => (
            <ClusterCard key={cluster.id} cluster={cluster} projectId={id} />
          ))}
        </div>
      )}
    </>
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
