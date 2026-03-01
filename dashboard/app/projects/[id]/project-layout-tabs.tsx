'use client'

import { usePathname } from 'next/navigation'
import { ProjectTabs } from '@/components/project-tabs'

export function ProjectLayoutTabs({ projectId }: { projectId: string }) {
  const pathname = usePathname()
  const activeTab: 'insights' | 'interviews' | 'settings' = pathname.endsWith('/interviews')
    ? 'interviews'
    : pathname.endsWith('/settings')
    ? 'settings'
    : 'insights'

  return <ProjectTabs projectId={projectId} activeTab={activeTab} />
}
