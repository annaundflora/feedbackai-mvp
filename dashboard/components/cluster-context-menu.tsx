'use client'

import { useState, useRef, useEffect } from 'react'
import type { ClusterResponse } from '@/lib/types'

interface ClusterContextMenuProps {
  cluster: ClusterResponse
  projectId: string
  onRenameStart: () => void
  onMergeStart: () => void
  onSplitStart: () => void
}

export function ClusterContextMenu({
  cluster,
  projectId,
  onRenameStart,
  onMergeStart,
  onSplitStart,
}: ClusterContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <div ref={menuRef} className="relative" data-testid="cluster-context-menu">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsOpen((prev) => !prev)
        }}
        aria-label={`Open menu for cluster ${cluster.name}`}
        aria-haspopup="menu"
        aria-expanded={isOpen}
        className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500"
        data-testid="cluster-menu-trigger"
      >
        ⋮
      </button>
      {isOpen && (
        <div
          role="menu"
          className="absolute right-0 top-6 z-10 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[140px]"
        >
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onRenameStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-rename"
          >
            Rename
          </button>
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onMergeStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-merge"
          >
            Merge with...
          </button>
          <button
            role="menuitem"
            onClick={(e) => {
              e.stopPropagation()
              setIsOpen(false)
              onSplitStart()
            }}
            className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
            data-testid="menu-split"
          >
            Split
          </button>
        </div>
      )}
    </div>
  )
}
