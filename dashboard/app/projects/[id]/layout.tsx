import { cache } from 'react'
import Link from 'next/link'
import { apiClient } from '@/lib/api-client'
import { ToastContainer } from '@/components/toast'
import { ProjectLayoutTabs } from './project-layout-tabs'

const getProject = cache(apiClient.getProject.bind(apiClient))

interface LayoutProps {
  children: React.ReactNode
  params: Promise<{ id: string }>
}

export default async function ProjectLayout({ children, params }: LayoutProps) {
  const { id } = await params
  const project = await getProject(id)

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

      <ProjectLayoutTabs projectId={id} />

      {children}

      <ToastContainer />
    </main>
  )
}
