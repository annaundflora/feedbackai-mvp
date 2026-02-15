import React from 'react'

interface PanelBodyProps {
  children: React.ReactNode
}

export function PanelBody({ children }: PanelBodyProps) {
  return (
    <div className="flex-1 overflow-y-auto p-[var(--panel-padding)]">
      {children}
    </div>
  )
}
