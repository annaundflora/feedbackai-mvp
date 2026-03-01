import { Suspense } from 'react'
import { apiClient } from '@/lib/api-client'
import { ProjectCard } from '@/components/project-card'
import { SkeletonCard } from '@/components/skeleton-card'
import { EmptyState } from '@/components/empty-state'
import { NewProjectDialog } from '@/components/new-project-dialog'

async function ProjectList() {
  const projects = await apiClient.getProjects()

  if (projects.length === 0) {
    return (
      <EmptyState
        data-testid="empty-state"
        message="No projects yet."
        ctaLabel="Create your first project"
      />
    )
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
      {projects.map(project => (
        <ProjectCard key={project.id} project={project} />
      ))}
    </div>
  )
}

export default function ProjectsPage() {
  return (
    <main className="max-w-6xl mx-auto px-4 py-8">
      <header className="flex items-center justify-between mb-8">
        <h1 className="text-2xl font-bold text-gray-900">FeedbackAI Insights</h1>
      </header>

      <div className="flex items-center justify-between mb-6">
        <NewProjectDialog />
      </div>

      <Suspense
        fallback={
          <div
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
            aria-busy="true"
          >
            <SkeletonCard data-testid="skeleton-card" />
            <SkeletonCard data-testid="skeleton-card" />
            <SkeletonCard data-testid="skeleton-card" />
          </div>
        }
      >
        <ProjectList />
      </Suspense>
    </main>
  )
}
