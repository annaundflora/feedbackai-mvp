'use client'

import { useState, useRef, useEffect } from 'react'

interface FactContextMenuProps {
  factId: string
  currentClusterId: string | null
  availableClusters: Array<{ id: string; name: string }>
  onMove: (factId: string, newClusterId: string | null) => Promise<void>
  onMarkUnassigned: (factId: string) => Promise<void>
}

export function FactContextMenu({
  factId,
  currentClusterId,
  availableClusters,
  onMove,
  onMarkUnassigned,
}: FactContextMenuProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isActing, setIsActing] = useState(false)
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

  async function handleMove(newClusterId: string | null) {
    setIsActing(true)
    setIsOpen(false)
    try {
      await onMove(factId, newClusterId)
    } finally {
      setIsActing(false)
    }
  }

  async function handleMarkUnassigned() {
    setIsActing(true)
    setIsOpen(false)
    try {
      await onMarkUnassigned(factId)
    } finally {
      setIsActing(false)
    }
  }

  const otherClusters = availableClusters.filter((c) => c.id !== currentClusterId)

  return (
    <div ref={menuRef} className="relative" data-testid="fact-context-menu">
      <button
        onClick={(e) => {
          e.preventDefault()
          e.stopPropagation()
          setIsOpen((prev) => !prev)
        }}
        disabled={isActing}
        aria-label="Fact actions"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        className="p-1 rounded hover:bg-gray-100 focus-visible:ring-2 focus-visible:ring-blue-500 disabled:opacity-50"
        data-testid="fact-menu-trigger"
      >
        ⋮
      </button>
      {isOpen && (
        <div
          role="menu"
          aria-label="Fact actions"
          className="absolute right-0 top-6 z-10 bg-white border border-gray-200 rounded-lg shadow-lg py-1 min-w-[180px]"
          data-testid="fact-menu-dropdown"
        >
          {otherClusters.map((cluster) => (
            <button
              key={cluster.id}
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation()
                handleMove(cluster.id)
              }}
              className="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 truncate"
              data-testid={`fact-move-to-${cluster.id}`}
            >
              Move to {cluster.name}...
            </button>
          ))}
          {currentClusterId !== null && (
            <button
              role="menuitem"
              onClick={(e) => {
                e.stopPropagation()
                handleMarkUnassigned()
              }}
              className="w-full text-left px-3 py-2 text-sm text-gray-500 hover:bg-gray-50 border-t border-gray-100"
              data-testid="fact-mark-unassigned"
            >
              Mark as unassigned
            </button>
          )}
        </div>
      )}
    </div>
  )
}
