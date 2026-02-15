import React from 'react'
import { PanelHeader } from './PanelHeader'

interface PanelProps {
  open: boolean
  onClose: () => void
  title: string
  children: React.ReactNode
}

export function Panel({ open, onClose, title, children }: PanelProps) {
  if (!open) return null

  return (
    <div
      className="
        fixed bottom-4 right-4
        w-[var(--panel-width)] h-[var(--panel-height)]
        bg-white rounded-[var(--panel-border-radius)]
        shadow-panel
        flex flex-col
        z-[10000]

        /* Mobile Fullscreen */
        max-md:fixed max-md:inset-0
        max-md:w-full max-md:h-full
        max-md:rounded-none
        max-md:bottom-0 max-md:right-0
      "
      style={{
        animation: 'slide-up var(--transition-slide)'
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="panel-title"
    >
      <PanelHeader title={title} onClose={onClose} />
      <div className="flex-1 overflow-y-auto p-[var(--panel-padding)]">
        {children}
      </div>
    </div>
  )
}
