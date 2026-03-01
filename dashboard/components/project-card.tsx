import Link from 'next/link'
import { memo } from 'react'
import type { ProjectListItem } from '@/lib/types'
import { formatRelativeTime } from '@/lib/relative-time'

interface ProjectCardProps {
  project: ProjectListItem
}

export const ProjectCard = memo(function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Link
      href={`/projects/${project.id}`}
      data-testid="project-card"
      className="block rounded-xl border bg-white p-5 shadow-sm transition-all duration-200 hover:shadow-md hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2"
    >
      <h3 data-testid="project-name" className="font-semibold text-gray-900 truncate">
        {project.name}
      </h3>
      <div className="mt-3 flex gap-4 text-sm text-gray-600">
        <span data-testid="project-interview-count">{project.interview_count} Interviews</span>
        <span data-testid="project-cluster-count">{project.cluster_count} Clusters</span>
      </div>
      <p data-testid="project-updated-at" className="mt-2 text-xs text-gray-400">
        {formatRelativeTime(project.updated_at)}
      </p>
    </Link>
  )
})
