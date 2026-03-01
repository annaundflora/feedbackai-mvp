'use client'

import Link from 'next/link'

interface ProjectTabsProps {
  projectId: string
  activeTab: 'insights' | 'interviews' | 'settings'
}

const tabs: {
  label: string
  getHref: (base: string) => string
  testid: string
  tab: ProjectTabsProps['activeTab']
}[] = [
  { label: 'Insights', getHref: (base) => base, testid: 'tab-insights', tab: 'insights' },
  { label: 'Interviews', getHref: (base) => `${base}/interviews`, testid: 'tab-interviews', tab: 'interviews' },
  { label: 'Settings', getHref: (base) => `${base}/settings`, testid: 'tab-settings', tab: 'settings' },
]

export function ProjectTabs({ projectId, activeTab }: ProjectTabsProps) {
  const base = `/projects/${projectId}`

  return (
    <nav role="tablist" className="flex gap-1 border-b mb-6">
      {tabs.map(tab => {
        const isActive = activeTab === tab.tab
        return (
          <Link
            key={tab.tab}
            href={tab.getHref(base)}
            role="tab"
            data-testid={tab.testid}
            aria-selected={isActive}
            tabIndex={isActive ? 0 : -1}
            className={
              isActive
                ? 'px-4 py-2 border-b-2 border-blue-600 font-medium text-blue-600 focus-visible:ring-2 focus-visible:ring-blue-500 rounded-t'
                : 'px-4 py-2 text-gray-500 hover:text-gray-900 focus-visible:ring-2 focus-visible:ring-blue-500 rounded-t'
            }
          >
            {tab.label}
          </Link>
        )
      })}
    </nav>
  )
}
